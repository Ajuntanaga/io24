#!/usr/bin/env python3
"""Read a UCNET hardware service's published state without changing it.

The probe sends only the required UM welcome, Subscribe JSON, and KA
keepalives.  It deliberately has no PV/PS control-write option.

    python3 tests/ucnet_service_probe.py
    python3 tests/ucnet_service_probe.py --port 50925 --device-id 107
"""

import argparse
import json
import os
import socket
import struct
import sys
import time
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ucnet_shim import CLIENT_ID, MAGIC, frame, jm, parse_frames


DISCOVERY_PORT = 47809
SUBSCRIBE = {
    "id": "Subscribe",
    "clientName": "UC-Surface",
    "clientInternalName": "ucremoteapp",
    "clientType": "CustomAPI",
    "clientDescription": "Read-only UCNET state probe",
    "clientIdentifier": "661b1ece-b4d3-44b3-913c-d12964456f0b",
    "clientOptions": "perm users",
    "clientEncoding": 23117,
}


def parse_discovery(data, peer):
    """Return the accepted fields from one UDP DA announcement."""
    if len(data) < 33 or data[:4] != MAGIC or data[6:8] != b"DA":
        return None
    tcp_port, = struct.unpack_from("<H", data, 4)
    device_id, = struct.unpack_from("<I", data, 8)
    fields = data[32:].split(b"\x00")
    if len(fields) < 3:
        return None
    try:
        model_firmware = fields[0].decode("ascii")
        family = fields[1].decode("ascii")
        serial = fields[2].decode("ascii")
        display = fields[3].decode("ascii") if len(fields) > 3 else ""
        model, firmware = model_firmware.rsplit("/", 1)
    except (UnicodeDecodeError, ValueError):
        return None
    if family != "AUD" or not serial or not firmware.isdecimal():
        return None
    return {
        "host": peer[0],
        "port": tcp_port,
        "device_id": device_id & 0xFFFF,
        "model": model,
        "firmware_word": int(firmware),
        "serial": serial,
        "display": display,
    }


def discover(timeout):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", DISCOVERY_PORT))
    sock.settimeout(timeout)
    deadline = time.monotonic() + timeout
    try:
        while True:
            sock.settimeout(max(0.05, deadline - time.monotonic()))
            data, peer = sock.recvfrom(65535)
            target = parse_discovery(data, peer)
            if target:
                return target
    except socket.timeout:
        raise TimeoutError("no UCNET DA announcement within %.1f seconds" % timeout)
    finally:
        sock.close()


def decode_json(message_type, payload):
    if len(payload) < 4:
        raise ValueError("short %s payload" % message_type)
    expected, = struct.unpack_from("<I", payload, 0)
    data = payload[4:]
    if message_type == "ZM":
        data = zlib.decompress(data)
    if len(data) != expected:
        raise ValueError("%s JSON length %d, expected %d" %
                         (message_type, len(data), expected))
    return json.loads(data.decode("ascii"))


def count_state(state):
    counts = {"values": 0, "strings": 0, "arrays": 0}

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "values" and isinstance(child, dict):
                    counts["values"] += len(child)
                elif key == "strings" and isinstance(child, dict):
                    counts["strings"] += len(child)
                else:
                    walk(child)
        elif isinstance(value, list):
            counts["arrays"] += 1

    walk(state.get("children", {}))
    return counts


def subscribe(target, timeout, output):
    peer = (target["host"], target["port"])
    device_id = target["device_id"]
    sock = socket.create_connection(peer, timeout=timeout)
    sock.settimeout(0.25)
    sock.sendall(
        frame("UM", struct.pack("<H", 0), CLIENT_ID, device_id)
        + jm(SUBSCRIBE, CLIENT_ID, device_id)
    )
    print("connected to %s:%d, deviceId=%d" % (peer[0], peer[1], device_id))

    deadline = time.monotonic() + timeout
    next_keepalive = time.monotonic() + 1.0
    reply = None
    state = None
    seen = {}
    buffer = b""
    try:
        while time.monotonic() < deadline and state is None:
            now = time.monotonic()
            if now >= next_keepalive:
                sock.sendall(frame("KA", b"", CLIENT_ID, device_id))
                next_keepalive = now + 1.0
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                raise EOFError("UCNET peer closed the connection")
            buffer += chunk
            messages, buffer = parse_frames(buffer)
            for message_type, source, destination, payload in messages:
                seen[message_type] = seen.get(message_type, 0) + 1
                if message_type not in ("JM", "ZM"):
                    continue
                obj = decode_json(message_type, payload)
                if obj.get("id") == "SubscriptionReply":
                    reply = obj
                elif obj.get("id") == "Synchronize":
                    state = obj
    finally:
        sock.close()

    if reply is None:
        raise RuntimeError("no SubscriptionReply; saw %r" % seen)
    if state is None:
        raise TimeoutError("no Synchronize within %.1f seconds; saw %r" %
                           (timeout, seen))
    counts = count_state(state)
    print("subscription result: %s" % reply.get("result", "<unspecified>"))
    print("synchronized: %(values)d values, %(strings)d strings, %(arrays)d arrays" % counts)
    if output:
        with open(output, "w", encoding="utf-8") as stream:
            json.dump(state, stream, indent=2, sort_keys=True)
            stream.write("\n")
        print("wrote %s" % output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1",
                        help="TCP host when bypassing discovery")
    parser.add_argument("--port", type=int,
                        help="TCP port; bypass UDP discovery")
    parser.add_argument("--device-id", type=int, default=107,
                        help="device id with --port (default: 107)")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--output", help="write Synchronize JSON to this path")
    args = parser.parse_args(argv)
    if args.port is None:
        target = discover(args.timeout)
        print("discovered %(model)s firmwareWord=%(firmware_word)d serial=%(serial)s" % target)
    else:
        if not 1 <= args.port <= 65535:
            parser.error("--port must be in 1..65535")
        if not 0 <= args.device_id <= 65535:
            parser.error("--device-id must be in 0..65535")
        target = {"host": args.host, "port": args.port, "device_id": args.device_id}
    subscribe(target, args.timeout, args.output)


if __name__ == "__main__":
    try:
        main()
    except (EOFError, OSError, RuntimeError, TimeoutError, ValueError) as exc:
        sys.exit("ucnet probe: %s" % exc)
