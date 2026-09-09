#!/usr/bin/env python3
"""Offline contract for io24_usbmon_class_in_evidence.py."""

import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
EXTRACTOR = HERE / "io24_usbmon_class_in_evidence.py"


def usbmon_packet(urb_id, event, setup=None, payload=b"", status=0):
    packet = bytearray(64)
    struct.pack_into("<Q", packet, 0, urb_id)
    packet[8] = ord(event)
    packet[9] = 2
    packet[10] = 0x80
    packet[11] = 4
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
        output.extend(
            struct.pack("<IIII", 1_700_000_000 + number, 0, len(packet), len(packet))
        )
        output.extend(packet)
    return bytes(output)


def uac2_configuration():
    # Entity 2 advertises read-only latency; entity 3 advertises no latency
    # control. These literal descriptors independently exercise both branches.
    output_terminal_2 = bytes.fromhex(
        "0c2403020101000305001000"
    )
    input_terminal_3 = bytes.fromhex(
        "1124020301010005020000000000000000"
    )
    interface = bytes.fromhex("090400000001012000")
    total_length = 9 + len(interface) + len(output_terminal_2) + len(input_terminal_3)
    configuration = bytes(
        [9, 2, total_length & 0xFF, total_length >> 8, 1, 1, 0, 0x80, 50]
    )
    return configuration + interface + output_terminal_2 + input_terminal_3


def main():
    configuration = uac2_configuration()
    packets = [
        usbmon_packet(
            0x10,
            "S",
            (0x80, 0x06, 0x0200, 0x0000, len(configuration)),
        ),
        usbmon_packet(0x10, "C", payload=configuration),
        usbmon_packet(0x20, "S", (0xA1, 0x01, 0x0100, 0x0500, 4)),
        usbmon_packet(0x20, "C", payload=struct.pack("<I", 48000)),
        usbmon_packet(0x21, "S", (0xA1, 0x01, 0x0100, 0x0500, 4)),
        usbmon_packet(0x21, "C", payload=struct.pack("<I", 96000)),
        usbmon_packet(0x30, "S", (0xA1, 0x01, 0x0700, 0x0200, 4)),
        usbmon_packet(0x30, "C", payload=struct.pack("<I", 12)),
        usbmon_packet(0x40, "S", (0xA1, 0x01, 0x0700, 0x0400, 4)),
        usbmon_packet(0x40, "C", payload=struct.pack("<I", 99)),
    ]
    with tempfile.TemporaryDirectory(prefix="io24-class-in-contract.") as directory:
        capture = Path(directory) / "fixture.pcap"
        capture.write_bytes(pcap(packets))
        completed = subprocess.run(
            [sys.executable, str(EXTRACTOR), "--json", "--require-evidence", str(capture)],
            check=False,
            capture_output=True,
            text=True,
        )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["packet_count"] == 10
    assert result["complete_uac2_configuration_count"] == 1

    clock = result["targets"]["clock_source_5_sampling_frequency_cur"]
    assert clock["request_count"] == 2
    assert clock["successful_response_count"] == 2
    assert clock["unique_values_u32"] == [48000, 96000]

    terminal_2 = result["targets"]["terminal_2_latency_cur"]
    assert terminal_2["request_count"] == 1
    assert terminal_2["successful_response_count"] == 1
    assert terminal_2["unique_values_u32"] == [12]
    terminal_3 = result["targets"]["terminal_3_latency_cur"]
    assert terminal_3["request_count"] == 0
    assert terminal_3["successful_response_count"] == 0
    assert terminal_3["unique_values_u32"] == []

    entities = {entry["entity_id"]: entry for entry in result["uac2_terminals"]}
    assert entities[2] == {
        "bm_controls": 0x1000,
        "entity_id": 2,
        "kind": "output_terminal",
        "latency_access": "read_only",
        "latency_readable": True,
    }
    assert entities[3] == {
        "bm_controls": 0,
        "entity_id": 3,
        "kind": "input_terminal",
        "latency_access": "not_present",
        "latency_readable": False,
    }
    print("io24 usbmon class-IN evidence contract: pass")


if __name__ == "__main__":
    main()
