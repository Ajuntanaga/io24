#!/usr/bin/env python3
"""Offline contract for io24_usbmon_range_extract.py."""

import importlib.util
import struct
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
EXTRACTOR_PATH = HERE / "io24_usbmon_range_extract.py"
SPEC = importlib.util.spec_from_file_location("io24_usbmon_range_extract", EXTRACTOR_PATH)
EXTRACTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXTRACTOR)


def usbmon_packet(urb_id, event, device, setup=None, payload=b"", status=0):
    packet = bytearray(64)
    struct.pack_into("<Q", packet, 0, urb_id)
    packet[8] = ord(event)
    packet[9] = 2
    packet[10] = 0x80
    packet[11] = device
    struct.pack_into("<H", packet, 12, 3)
    packet[14] = 0 if setup is not None else 1
    packet[15] = 0 if payload else 1
    struct.pack_into("<q", packet, 16, 1_700_000_000)
    struct.pack_into("<i", packet, 24, 123456)
    struct.pack_into("<i", packet, 28, status)
    struct.pack_into("<I", packet, 32, len(payload))
    struct.pack_into("<I", packet, 36, len(payload))
    if setup is not None:
        struct.pack_into("<BBHHH", packet, 40, *setup)
    return bytes(packet) + payload


def pcap(packets):
    output = bytearray(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 512, 220))
    for number, packet in enumerate(packets):
        output.extend(struct.pack("<IIII", 1_700_000_000 + number, 0, len(packet), len(packet)))
        output.extend(packet)
    return bytes(output)


def main():
    count_setup = (0xA1, 0x02, 0x0100, 0x0500, 2)
    full_setup = (0xA1, 0x02, 0x0100, 0x0500, 50)
    noise_setup = (0xA1, 0x02, 0x0100, 0x0600, 50)
    rates = (44100, 48000, 88200, 96000)
    full_payload = struct.pack("<H", len(rates)) + b"".join(
        struct.pack("<III", rate, rate, 0) for rate in rates
    )
    packets = [
        usbmon_packet(0x10, "S", 7, noise_setup),
        usbmon_packet(0x10, "C", 7, payload=b"\x00\x00"),
        usbmon_packet(0x20, "S", 7, count_setup),
        usbmon_packet(0x20, "C", 7, payload=struct.pack("<H", len(rates))),
        usbmon_packet(0x21, "S", 7, full_setup),
        usbmon_packet(0x21, "C", 7, payload=full_payload),
    ]
    with tempfile.TemporaryDirectory(prefix="io24-usbmon-range-contract.") as directory:
        capture = Path(directory) / "fixture.pcap"
        capture.write_bytes(pcap(packets))
        result = EXTRACTOR.analyze_capture(capture)

    assert result["linktype"] == 220
    assert result["snaplen"] == 512
    assert result["packet_count"] == 6
    assert result["target_request_count"] == 2
    assert result["full_response_count"] == 1
    assert result["requests"][0]["requested_bytes"] == 2
    assert result["requests"][0]["completion"]["subrange_count"] == 4
    assert not result["requests"][0]["completion"]["complete"]
    full = result["requests"][1]["completion"]
    assert full["complete"]
    assert full["expected_bytes"] == 50
    assert [entry["minimum_hz"] for entry in full["subranges"]] == list(rates)
    assert all(entry["minimum_hz"] == entry["maximum_hz"] for entry in full["subranges"])
    assert all(entry["resolution_hz"] == 0 for entry in full["subranges"])
    print("io24 passive usbmon RANGE extractor contract: pass")


if __name__ == "__main__":
    main()
