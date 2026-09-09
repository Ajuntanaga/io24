#!/usr/bin/env python3
"""Hardware-free contracts for the source-bound CP34 recall analyzer."""

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
RE_DIR = ROOT / "re"
if str(RE_DIR) not in sys.path:
    sys.path.insert(0, str(RE_DIR))
SPEC = importlib.util.spec_from_file_location(
    "cp34_preset_recall_static", RE_DIR / "cp34_preset_recall_static.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

from io24_preset_record import (  # noqa: E402
    decode_preset_record,
    decode_preset_record_prefix,
    encode_preset_record,
)


class PresetRecallStaticTests(unittest.TestCase):
    def test_prefix_decoder_stops_at_end_of_record(self):
        record = {
            "preset_name": "Slap Echo",
            "voicefx": {"on": 1, "time": 0.15, "mix": 0.5},
        }
        encoded = encode_preset_record(record)
        decoded, consumed = decode_preset_record_prefix(encoded + b"firmware")
        self.assertEqual(decoded["preset_name"], record["preset_name"])
        self.assertEqual(decoded["voicefx"]["on"], 1)
        self.assertAlmostEqual(decoded["voicefx"]["time"], 0.15, places=6)
        self.assertEqual(encode_preset_record(decoded), encoded)
        self.assertEqual(consumed, len(encoded))
        with self.assertRaisesRegex(ValueError, "trailing bytes"):
            decode_preset_record(encoded + b"firmware")

    def test_x86_field_scan_counts_only_instruction_operands(self):
        base = 0x180001000
        code = bytes.fromhex(
            "b8e6000000"          # immediate 0xe6: not a memory access
            "c681e600000000"      # mov byte ptr [rcx+0xe6], 0
            "8039e6"              # byte immediate 0xe6: not a displacement
            "0fb682e6000000"      # movzx eax, byte ptr [rdx+0xe6]
            "c3")
        accesses = MODULE.scan_byte_field_accesses(code, base, 0xE6)
        self.assertEqual(
            [(item["address"], item["access"]) for item in accesses],
            [(base + 5, "write"), (base + 15, "read")],
        )

    def test_u32_table_is_little_endian_and_bounded(self):
        self.assertEqual(
            MODULE._u32_table(bytes.fromhex("4004000004040000"), 0, 2),
            [0x440, 0x404],
        )
        with self.assertRaisesRegex(MODULE.AnalysisError, "exceeds"):
            MODULE._u32_table(b"\0" * 7, 0, 2)

    def test_static_conclusion_keeps_live_claims_out_of_scope(self):
        source = (RE_DIR / "cp34_preset_recall_static.py").read_text()
        self.assertIn("does not prove physical nonvolatile commit", source)
        self.assertIn("sets +0x39=1", source)
        self.assertIn("no additional standalone enable", source)
        self.assertNotIn("import io24", source)
        self.assertNotIn("usb.core", source)

    def test_voicefx_vtable_ownership_and_gate_assignments_are_pinned(self):
        self.assertEqual(
            MODULE.FIRMWARE_VTABLE_ANCHORS["voicefx_primary_gate_handler"],
            (0x10C6CC, 0x50AF8),
        )
        self.assertEqual(
            MODULE.FIRMWARE_VTABLE_ANCHORS["voicefx_primary_work_slot"],
            (0x10C6F0, 0x5F1F4),
        )
        self.assertEqual(
            MODULE.FIRMWARE_VTABLE_ANCHORS["voicefx_state_apply_adjustor"],
            (0x10C704, 0x555B8),
        )
        self.assertEqual(
            MODULE.FIRMWARE_INSTRUCTION_ANCHORS[
                "voicefx_model_gate_a_assignment"][0],
            0x553A2,
        )
        self.assertEqual(
            MODULE.FIRMWARE_INSTRUCTION_ANCHORS[
                "voicefx_state_gate_bc_assignment"][0],
            0x554B0,
        )


if __name__ == "__main__":
    unittest.main()
