#!/usr/bin/env python3
"""Behavioral contract for the CP34 offline PE queue inventory."""

import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "cp34_host_queue_inventory.py")
IMAGE_BASE = 0x180000000


def _section(name, virtual_size, virtual_address, raw_size, raw_pointer):
    return struct.pack(
        "<8sIIIIIIHHI",
        name.encode("ascii").ljust(8, b"\0"),
        virtual_size,
        virtual_address,
        raw_size,
        raw_pointer,
        0,
        0,
        0,
        0,
        0,
    )


def _minimal_pe(code):
    """Build a hand-checked PE32+ fixture with .text and .pdata sections."""
    data = bytearray(0x800)
    struct.pack_into("<H", data, 0, 0x5A4D)
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x84, 0x8664, 2, 0, 0, 0, 0xF0, 0x2022)

    optional = 0x98
    struct.pack_into("<H", data, optional, 0x20B)
    struct.pack_into("<Q", data, optional + 24, IMAGE_BASE)

    sections = optional + 0xF0
    data[sections:sections + 40] = _section(".text", len(code), 0x1000, 0x200, 0x400)
    data[sections + 40:sections + 80] = _section(".pdata", 12, 0x2000, 0x200, 0x600)
    data[0x400:0x400 + len(code)] = code
    struct.pack_into("<III", data, 0x600, 0x1000, 0x1000 + len(code), 0x2100)
    return bytes(data)


class HostQueueInventoryTests(unittest.TestCase):
    def test_cli_reports_direct_call_and_nearby_fourcc_without_false_opcode_hits(self):
        """A byte 0xe8 inside an immediate must not become a fake call site."""
        target = IMAGE_BASE + 0x3000
        code = bytearray()
        code += b"\xb8\x33\xe8\x22\x11"       # mov eax,0x1122e833
        code += b"\xb8\x50\x6d\x65\x4d"       # mov eax,0x4d656d50 ('MemP')
        code += b"\xff\xd0"                       # call rax (not the target)
        call_offset = len(code)
        displacement = target - (IMAGE_BASE + 0x1000 + call_offset + 5)
        code += b"\xe8" + struct.pack("<i", displacement)
        code += b"\xc3"

        with tempfile.TemporaryDirectory() as temporary:
            fixture = os.path.join(temporary, "queue-fixture.dll")
            with open(fixture, "wb") as handle:
                handle.write(_minimal_pe(code))
            result = subprocess.run(
                [sys.executable, SCRIPT, fixture, "--target", hex(target),
                 "--context-before", "64"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["image_base"], hex(IMAGE_BASE))
        self.assertEqual(report["queue_target"], hex(target))
        self.assertEqual(
            report["call_sites"],
            [{
                "address": hex(IMAGE_BASE + 0x1000 + call_offset),
                "function_start": hex(IMAGE_BASE + 0x1000),
                "function_end": hex(IMAGE_BASE + 0x1000 + len(code)),
                "nearby_ascii_immediates": ["MemP"],
            }],
        )

    def test_cli_resynchronizes_after_non_instruction_bytes(self):
        """Mixed code/data in .text must not hide later direct call sites."""
        target = IMAGE_BASE + 0x3000
        # The real DLL has this jump-table-like data at .text+0x4560.  With
        # Capstone's default settings it terminates linear disassembly here.
        code = bytearray(bytes.fromhex("8f540000ac54000033550000"))
        code += b"\xb8\x50\x6d\x65\x4d"
        call_offset = len(code)
        displacement = target - (IMAGE_BASE + 0x1000 + call_offset + 5)
        code += b"\xe8" + struct.pack("<i", displacement)
        code += b"\xc3"

        with tempfile.TemporaryDirectory() as temporary:
            fixture = os.path.join(temporary, "mixed-text.dll")
            with open(fixture, "wb") as handle:
                handle.write(_minimal_pe(code))
            result = subprocess.run(
                [sys.executable, SCRIPT, fixture, "--target", hex(target),
                 "--context-before", "64"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(
            [site["address"] for site in report["call_sites"]],
            [hex(IMAGE_BASE + 0x1000 + call_offset)],
        )

    def test_cli_can_inventory_rip_relative_iat_calls(self):
        """A WinUSB IAT call must resolve to its slot, not its next address."""
        target = IMAGE_BASE + 0x3000
        code = bytearray(b"\xb8\x50\x6d\x65\x4d")
        call_offset = len(code)
        displacement = target - (IMAGE_BASE + 0x1000 + call_offset + 6)
        code += b"\xff\x15" + struct.pack("<i", displacement)
        code += b"\xc3"

        with tempfile.TemporaryDirectory() as temporary:
            fixture = os.path.join(temporary, "iat-fixture.dll")
            with open(fixture, "wb") as handle:
                handle.write(_minimal_pe(code))
            result = subprocess.run(
                [sys.executable, SCRIPT, fixture, "--target", hex(target),
                 "--call-kind", "rip-indirect", "--context-before", "64"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["call_kind"], "rip-indirect")
        self.assertEqual(
            [site["address"] for site in report["call_sites"]],
            [hex(IMAGE_BASE + 0x1000 + call_offset)],
        )


if __name__ == "__main__":
    unittest.main()
