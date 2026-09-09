#!/usr/bin/env python3
"""Offline contract for io24_usbmon_function_topology.py."""

import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ANALYZER = HERE / "io24_usbmon_function_topology.py"


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


def io24_configuration():
    descriptors = [
        # IAD: UAC2 audio function rooted at interface 0, spanning 0-2.
        bytes.fromhex("080b000301002010"),
        bytes.fromhex("090400000001012010"),
        bytes.fromhex("090401000001022013"),
        bytes.fromhex("090402000001022016"),
        # Legacy AudioControl header: interface 3 owns MIDIStreaming interface 4.
        bytes.fromhex("090403000001010005"),
        bytes.fromhex("092401000109000104"),
        bytes.fromhex("090404000201030000"),
        bytes.fromhex("090502020002000000"),
        bytes.fromhex("090582020002000000"),
        # Vendor transport exists only on alternate 1 of interface 5.
        bytes.fromhex("0904050000ff000006"),
        bytes.fromhex("0904050102ff000006"),
        bytes.fromhex("07058102000200"),
        bytes.fromhex("07050102000200"),
        # DFU runtime interface.
        bytes.fromhex("0904060000fe010107"),
    ]
    total_length = 9 + sum(map(len, descriptors))
    configuration = bytes(
        [9, 2, total_length & 0xFF, total_length >> 8, 7, 1, 0, 0x80, 250]
    )
    return configuration + b"".join(descriptors)


def main():
    device = bytes.fromhex("12010002000000404f192204280101020301")
    configuration = io24_configuration()
    packets = [
        usbmon_packet(0x10, "S", (0x80, 0x06, 0x0100, 0, len(device))),
        usbmon_packet(0x10, "C", payload=device),
        # Enumeration asks for the nine-byte configuration header first.
        usbmon_packet(0x18, "S", (0x80, 0x06, 0x0200, 0, 9)),
        usbmon_packet(0x18, "C", payload=configuration[:9]),
        usbmon_packet(
            0x20,
            "S",
            (0x80, 0x06, 0x0200, 0, len(configuration)),
        ),
        usbmon_packet(0x20, "C", payload=configuration),
    ]

    with tempfile.TemporaryDirectory(prefix="io24-topology-contract.") as directory:
        capture = Path(directory) / "fixture.pcap"
        capture.write_bytes(pcap(packets))
        completed = subprocess.run(
            [
                sys.executable,
                str(ANALYZER),
                "--json",
                "--require-io24-topology",
                str(capture),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["target_device_count"] == 1
    assert result["configuration_count"] == 1
    topology = result["configurations"][0]
    assert topology["configuration"]["num_interfaces"] == 7
    assert topology["functions"] == [
        {"interfaces": [0, 1, 2], "root": 0, "source": "iad"},
        {
            "interfaces": [3, 4],
            "root": 3,
            "source": "audio_control_collection",
        },
        {"interfaces": [5], "root": 5, "source": "ungrouped"},
        {"interfaces": [6], "root": 6, "source": "ungrouped"},
    ]

    interfaces = {
        (entry["number"], entry["alternate"]): entry
        for entry in topology["interfaces"]
    }
    assert interfaces[(4, 0)]["class"] == 1
    assert interfaces[(4, 0)]["subclass"] == 3
    assert [ep["address"] for ep in interfaces[(4, 0)]["endpoints"]] == [2, 130]
    assert interfaces[(5, 0)]["endpoints"] == []
    assert [ep["address"] for ep in interfaces[(5, 1)]["endpoints"]] == [129, 1]
    assert interfaces[(6, 0)]["class"] == 0xFE
    assert interfaces[(6, 0)]["subclass"] == 1
    print("io24 usbmon function topology contract: pass")


if __name__ == "__main__":
    main()
