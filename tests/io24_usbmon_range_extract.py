#!/usr/bin/env python3
"""Extract the io24 UAC2 Clock Source Sampling Frequency RANGE from usbmon pcap."""

import argparse
import json
import struct
import sys
from pathlib import Path


DLT_USB_LINUX_MMAPPED = 220
USBMON_HEADER_LENGTH = 64
USBMON_CONTROL = 2
TARGET_BUS = 3
TARGET_BM_REQUEST_TYPE = 0xA1
TARGET_REQUEST = 0x02
TARGET_VALUE = 0x0100
TARGET_INDEX = 0x0500


class CaptureError(ValueError):
    """Raised when a capture is malformed or uses an unsupported format."""


def _pcap_byte_order(data):
    magic = data[:4]
    if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"):
        return "<"
    if magic in (b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d"):
        return ">"
    raise CaptureError("unsupported pcap magic")


def parse_pcap(path):
    raw = Path(path).read_bytes()
    if len(raw) < 24:
        raise CaptureError("truncated pcap global header")
    byte_order = _pcap_byte_order(raw)
    _, major, minor, _, _, snaplen, network = struct.unpack_from(
        byte_order + "IHHIIII", raw, 0
    )
    linktype = network & 0xFFFF
    if (major, minor) != (2, 4):
        raise CaptureError("unsupported pcap version %d.%d" % (major, minor))
    if linktype != DLT_USB_LINUX_MMAPPED:
        raise CaptureError(
            "expected DLT_USB_LINUX_MMAPPED 220, found %d" % linktype
        )

    packets = []
    offset = 24
    while offset < len(raw):
        if len(raw) - offset < 16:
            raise CaptureError("truncated pcap packet header")
        ts_sec, ts_fraction, captured_length, original_length = struct.unpack_from(
            byte_order + "IIII", raw, offset
        )
        offset += 16
        if captured_length > len(raw) - offset:
            raise CaptureError("truncated pcap packet data")
        packet = raw[offset:offset + captured_length]
        offset += captured_length
        if len(packet) < USBMON_HEADER_LENGTH:
            raise CaptureError("truncated usbmon packet header")

        urb_id = struct.unpack_from(byte_order + "Q", packet, 0)[0]
        event_type = chr(packet[8])
        transfer_type = packet[9]
        endpoint = packet[10]
        device = packet[11]
        bus = struct.unpack_from(byte_order + "H", packet, 12)[0]
        setup_flag = packet[14]
        data_flag = packet[15]
        status = struct.unpack_from(byte_order + "i", packet, 28)[0]
        urb_length = struct.unpack_from(byte_order + "I", packet, 32)[0]
        data_length = struct.unpack_from(byte_order + "I", packet, 36)[0]
        setup = None
        if event_type == "S" and transfer_type == USBMON_CONTROL and setup_flag == 0:
            bm_request_type, request, value, index, length = struct.unpack_from(
                byte_order + "BBHHH", packet, 40
            )
            setup = {
                "bm_request_type": bm_request_type,
                "request": request,
                "value": value,
                "index": index,
                "length": length,
                "bytes": packet[40:48].hex(),
            }
        payload = b""
        if data_flag == 0 and data_length:
            available = max(0, len(packet) - USBMON_HEADER_LENGTH)
            payload = packet[
                USBMON_HEADER_LENGTH:
                USBMON_HEADER_LENGTH + min(data_length, available)
            ]
        packets.append({
            "timestamp": [ts_sec, ts_fraction],
            "captured_length": captured_length,
            "original_length": original_length,
            "urb_id": urb_id,
            "event_type": event_type,
            "transfer_type": transfer_type,
            "endpoint": endpoint,
            "device": device,
            "bus": bus,
            "setup_flag": setup_flag,
            "data_flag": data_flag,
            "status": status,
            "urb_length": urb_length,
            "data_length": data_length,
            "setup": setup,
            "payload": payload,
        })
    return {"snaplen": snaplen, "linktype": linktype, "packets": packets}


def _is_target_setup(setup):
    return setup is not None and (
        setup["bm_request_type"] == TARGET_BM_REQUEST_TYPE
        and setup["request"] == TARGET_REQUEST
        and setup["value"] == TARGET_VALUE
        and setup["index"] == TARGET_INDEX
    )


def _decode_range(payload):
    decoded = {
        "response_hex": payload.hex(),
        "captured_bytes": len(payload),
        "subrange_count": None,
        "expected_bytes": None,
        "complete": False,
        "subranges": [],
    }
    if len(payload) < 2:
        return decoded
    count = int.from_bytes(payload[:2], "little")
    expected = 2 + 12 * count
    decoded["subrange_count"] = count
    decoded["expected_bytes"] = expected
    decoded["complete"] = len(payload) >= expected
    available_count = min(count, max(0, (len(payload) - 2) // 12))
    for position in range(available_count):
        base = 2 + 12 * position
        minimum, maximum, resolution = struct.unpack_from("<III", payload, base)
        decoded["subranges"].append({
            "minimum_hz": minimum,
            "maximum_hz": maximum,
            "resolution_hz": resolution,
        })
    return decoded


def analyze_capture(path):
    capture = parse_pcap(path)
    target_submits = {}
    requests = []
    for packet in capture["packets"]:
        if (
            packet["event_type"] == "S"
            and packet["transfer_type"] == USBMON_CONTROL
            and packet["bus"] == TARGET_BUS
            and _is_target_setup(packet["setup"])
        ):
            request = {
                "urb_id": "%016x" % packet["urb_id"],
                "device": packet["device"],
                "endpoint": packet["endpoint"],
                "setup_hex": packet["setup"]["bytes"],
                "requested_bytes": packet["setup"]["length"],
                "completion": None,
            }
            requests.append(request)
            target_submits[packet["urb_id"]] = request
            continue
        if packet["event_type"] not in ("C", "E"):
            continue
        request = target_submits.get(packet["urb_id"])
        if request is None or request["completion"] is not None:
            continue
        response = _decode_range(packet["payload"])
        response.update({
            "event_type": packet["event_type"],
            "status": packet["status"],
            "urb_length": packet["urb_length"],
            "usbmon_data_length": packet["data_length"],
            "data_flag": packet["data_flag"],
            "payload_truncated": (
                len(packet["payload"]) < packet["data_length"]
                or packet["data_length"] < packet["urb_length"]
            ),
        })
        request["completion"] = response

    full_responses = [
        request for request in requests
        if request["completion"] is not None
        and request["completion"]["status"] == 0
        and request["completion"]["complete"]
    ]
    return {
        "pcap": str(Path(path).resolve()),
        "linktype": capture["linktype"],
        "snaplen": capture["snaplen"],
        "packet_count": len(capture["packets"]),
        "target_request_count": len(requests),
        "full_response_count": len(full_responses),
        "requests": requests,
    }


def print_human(result):
    print("pcap=%s" % result["pcap"])
    print("linktype=%s" % result["linktype"])
    print("snaplen=%s" % result["snaplen"])
    print("packet_count=%s" % result["packet_count"])
    print("target_request_count=%s" % result["target_request_count"])
    print("full_response_count=%s" % result["full_response_count"])
    for request in result["requests"]:
        print(
            "request urb=%s device=%s requested=%s setup=%s"
            % (
                request["urb_id"],
                request["device"],
                request["requested_bytes"],
                request["setup_hex"],
            )
        )
        completion = request["completion"]
        if completion is None:
            print("  completion=missing")
            continue
        print(
            "  completion event=%s status=%s captured=%s expected=%s complete=%s data=%s"
            % (
                completion["event_type"],
                completion["status"],
                completion["captured_bytes"],
                completion["expected_bytes"],
                completion["complete"],
                completion["response_hex"],
            )
        )
        for subrange in completion["subranges"]:
            print(
                "  subrange min=%s max=%s res=%s"
                % (
                    subrange["minimum_hz"],
                    subrange["maximum_hz"],
                    subrange["resolution_hz"],
                )
            )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pcap")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--require-full-range", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = analyze_capture(args.pcap)
    except (CaptureError, OSError) as error:
        print("io24 usbmon extract: %s" % error, file=sys.stderr)
        return 1
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_human(result)
    if args.require_full_range and result["full_response_count"] == 0:
        print("io24 usbmon extract: no complete target RANGE response", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
