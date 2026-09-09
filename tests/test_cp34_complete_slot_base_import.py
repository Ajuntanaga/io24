#!/usr/bin/env python3
"""Host-only contracts for explicit complete channel-base imports."""

import json
from pathlib import Path
import struct
import tempfile
import unittest

import io24
from io24_preset_record import (
    complete_device_slot_record,
    decode_preset_record,
    load_complete_device_slot_record,
    load_paired_device_slot_bases,
)


ROOT = Path(__file__).resolve().parents[1]


def reverb_factory_record():
    records = json.loads((ROOT / "re" / "uc_factory_presets.json").read_text())
    return next(record for record in records if record.get("preset_name") == "Reverb")


def record_from_frame(frame):
    size = struct.unpack_from("<H", frame, 35)[0]
    return decode_preset_record(frame[41:41 + size])


class CompleteSlotBaseImportTests(unittest.TestCase):
    def test_pair_import_preserves_separate_complete_channel_bases(self):
        ch1 = reverb_factory_record()
        ch2 = reverb_factory_record()
        ch1["preset_name"] = "Ch1 retained strip"
        ch2["preset_name"] = "Ch2 retained strip"
        ch1["gate"]["threshold"] = -31.0
        ch2["gate"]["threshold"] = -47.0

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "channel-1.json"
            second = Path(directory) / "channel-2.json"
            first.write_text(json.dumps(ch1))
            second.write_text(json.dumps(ch2))
            base1, base2 = load_paired_device_slot_bases(first, second)
            frames = io24.build_paired_doubler_private_reverb_frames_from_local_bases(
                1, first, 3, second, preset_name=None, lows=0.2, width=0.4,
                mix=0.6)

        self.assertEqual(base1["gate"]["threshold"], -31.0)
        self.assertEqual(base2["gate"]["threshold"], -47.0)
        self.assertNotIn("_offset", base1)
        self.assertNotIn("_offset", base2)
        record1, record2 = (record_from_frame(frames[1][0]),
                            record_from_frame(frames[3][0]))
        self.assertEqual(record1["preset_name"], "Ch1 retained strip")
        self.assertEqual(record2["preset_name"], "Ch2 retained strip")
        self.assertEqual(record1["gate"]["threshold"], -31.0)
        self.assertEqual(record2["gate"]["threshold"], -47.0)
        self.assertEqual(record1["voicefx"], record2["voicefx"])

    def test_import_requires_one_complete_mapping_and_has_no_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "partial.json"
            path.write_text(json.dumps({"preset_name": "partial", "gate": {}}))
            with self.assertRaisesRegex(ValueError, "incomplete; missing"):
                load_complete_device_slot_record(path)

            path.write_text(json.dumps([reverb_factory_record()]))
            with self.assertRaisesRegex(TypeError, "must be a mapping"):
                load_complete_device_slot_record(path)

    def test_import_rejects_nonfinite_json_and_codec_incompatible_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"preset_name": NaN}')
            with self.assertRaisesRegex(ValueError, "non-finite JSON"):
                load_complete_device_slot_record(path)

        base = reverb_factory_record()
        base["gate"]["unsupported"] = []
        with self.assertRaisesRegex(TypeError, "unsupported preset record value"):
            complete_device_slot_record(base)

    def test_imported_record_is_copied_not_mutated(self):
        original = reverb_factory_record()
        retained = complete_device_slot_record(original)
        retained["gate"]["threshold"] = -12.0
        self.assertNotEqual(original["gate"]["threshold"], -12.0)
        self.assertIn("_offset", original)
        self.assertNotIn("_offset", retained)


if __name__ == "__main__":
    unittest.main()
