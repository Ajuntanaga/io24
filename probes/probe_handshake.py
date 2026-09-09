#!/usr/bin/env python3
"""
Active UCNET handshake probe for the PreSonus Revelator io24 over USB interface 5.

This is the decisive Architecture A/B test. We reproduce oddbear's
MessageWriter.CreateWelcomeMessages (UM welcome + JM subscribe) byte-for-byte and
send it straight to the vendor bulk OUT endpoint (0x01), then read the bulk IN
endpoint (0x81). If the device answers with UCNET frames ("UC\\x00\\x01"), the
PreSonus USB service is a transparent UCNET pipe (Architecture B) and oddbear's
whole protocol stack ports directly.

We try several candidate deviceId ("To") values because, unlike oddbear, we have
no UDP DA broadcast to learn the real id from.

Read/write only to interface 5. Never touches interface 6 (DFU).
"""
import json
import struct
import time
import usb.core
import usb.util

VID, PID = 0x194F, 0x0422
IFACE = 5
EP_OUT = 0x01
EP_IN = 0x81
FROM_ID = 104  # 0x68, constant "from" per oddbear's PackageHelper notes

SUBSCRIBE = {
    "id": "Subscribe",
    "clientName": "UC-Surface",
    "clientInternalName": "ucremoteapp",
    "clientType": "CustomAPI",
    "clientDescription": "CustomAPI for Revelator io24",
    "clientIdentifier": "661b1ece-b4d3-44b3-913c-d12964456f0b",
    "clientOptions": "perm users",
    "clientEncoding": 23117,
}


def header(device_id):
    h = bytearray()
    h += b"UC"                        # [0:2]
    h += struct.pack("<H", 256)       # [2:4] version -> 00 01
    h += b"\x00\x00"                  # [4:6] length placeholder
    h += b"\x00\x00"                  # [6:8] msgtype placeholder
    h += struct.pack("<H", FROM_ID)   # [8:10] from
    h += struct.pack("<H", device_id) # [10:12] to
    return h


def finalize(data, mtype):
    data[4:6] = struct.pack("<H", len(data) - 6)  # length = bytes after offset 6
    data[6:8] = mtype.encode("ascii")
    return bytes(data)


def welcome_message(device_id, monitor_port=0):
    um = header(device_id)
    um += struct.pack("<H", monitor_port)          # [12:14] monitor port
    um = finalize(um, "UM")

    j = json.dumps(SUBSCRIBE, separators=(",", ":"))  # compact, matches C# JsonSerializer
    jm = header(device_id)
    jm += struct.pack("<I", len(j))                # [12:16] json length (uint32 LE)
    jm += j.encode("ascii")                        # [16:]  json
    jm = finalize(jm, "JM")
    return um + jm


def keepalive(device_id):
    return finalize(header(device_id), "KA")


def hexdump(b, limit=256):
    b = bytes(b)
    shown = b[:limit]
    hexs = " ".join(f"{x:02x}" for x in shown)
    ascii_ = "".join(chr(x) if 32 <= x < 127 else "." for x in shown)
    tail = f"  …(+{len(b) - limit} more)" if len(b) > limit else ""
    return f"[{len(b):4d}] {hexs}  |{ascii_}|{tail}"


def drain(ep, seconds, tag):
    """Read the IN endpoint for `seconds`, printing every frame. Returns list of frames."""
    frames = []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            data = ep.read(ep.wMaxPacketSize, timeout=400)
        except usb.core.USBTimeoutError:
            continue
        except usb.core.USBError as e:
            print(f"    [{tag}] read error: {e}")
            break
        if data:
            b = bytes(data)
            frames.append(b)
            magic = " <<< UC MAGIC" if b[:4] == b"UC\x00\x01" else ""
            mtype = ""
            if len(b) >= 8 and b[:2] == b"UC":
                mtype = f" type={b[6:8].decode('ascii', 'replace')!r}"
            print(f"    [{tag}] RX {hexdump(b)}{mtype}{magic}")
    return frames


def main():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        raise SystemExit("io24 not found")

    usb.util.claim_interface(dev, IFACE)
    dev.set_interface_altsetting(interface=IFACE, alternate_setting=1)
    cfg = dev.get_active_configuration()
    intf = cfg[(IFACE, 1)]
    ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: e.bEndpointAddress == EP_IN)
    ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: e.bEndpointAddress == EP_OUT)
    print(f"iface {IFACE} alt 1 claimed; IN=0x{EP_IN:02x} OUT=0x{EP_OUT:02x}\n")

    # 0) Catch anything spontaneous first.
    print(">> pre-read (spontaneous frames?)")
    drain(ep_in, 1.5, "pre")

    any_reply = False
    for device_id in (0x0000, 0x0066, 0x006B, 0xFFFF):
        tag = f"id=0x{device_id:04x}"
        msg = welcome_message(device_id)
        print(f"\n>> {tag}: sending welcome (UM+JM), {len(msg)} bytes")
        try:
            ep_out.write(msg, timeout=1000)
        except usb.core.USBError as e:
            print(f"    write failed: {e}")
            continue
        frames = drain(ep_in, 2.0, tag)
        # a keepalive nudge, then read a bit more
        try:
            ep_out.write(keepalive(device_id), timeout=1000)
        except usb.core.USBError:
            pass
        frames += drain(ep_in, 1.0, tag)
        if any(f[:2] == b"UC" for f in frames):
            any_reply = True
            print(f"    *** {tag} GOT A UCNET REPLY — this is the device id. ***")
            break

    usb.util.release_interface(dev, IFACE)
    print("\n=== RESULT ===")
    if any_reply:
        print("Architecture B CONFIRMED: device speaks UCNET directly over USB iface 5.")
        print("oddbear's protocol stack ports over a libusb bridge.")
    else:
        print("No UCNET reply on any deviceId. Either the wrong first frame, or the")
        print("PreSonus USB service does more than pipe bytes (needs deeper capture).")


if __name__ == "__main__":
    main()
