#!/usr/bin/env python3
"""Hardware-free contracts for the native gate slot discriminator."""

import importlib.util
from pathlib import Path
import struct
import unittest

import io24_native_stat as native


ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin")
PROBE_PATH = ROOT / "re" / "io24_native_gate_slot_probe.py"


def _load_probe():
    spec = importlib.util.spec_from_file_location("native_gate_probe", PROBE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(FIRMWARE.exists(), "firmware image not retained")
class NativeGateSlotProbeTests(unittest.TestCase):
    def setUp(self):
        self.probe = _load_probe()
        self.records = self.probe.build_test_records(FIRMWARE.read_bytes())

    def _channel(self, record):
        top = native.decode_native_stat_record(record)
        strip = next(chunk.payload for chunk in top.chunks
                     if chunk.key == native.CHANNEL_STRIP_KEY)
        return {chunk.key: chunk.payload
                for chunk in native.decode_chunk_group(strip)}

    def test_records_are_complete_native_channel2_slot_bodies(self):
        self.assertEqual(set(self.records), {"restore", "flat", "boosted"})
        for record in self.records.values():
            self.assertEqual(native.validate_native_stat_record(record, 3), record)
            self.assertEqual(len(record), 1028)

    def test_gate_is_the_only_candidate_difference(self):
        off = self._channel(self.records["flat"])
        on = self._channel(self.records["boosted"])

        self.assertNotEqual(off[b"gate"], on[b"gate"])
        for key in set(off) - {b"gate"}:
            with self.subTest(key=key):
                self.assertEqual(off[key], on[key])

    def test_both_native_gate_states_carry_the_requested_enable(self):
        off = self._channel(self.records["flat"])[b"gate"]
        on = self._channel(self.records["boosted"])[b"gate"]

        for index in (0, 1):
            at = 8 + index * 60
            self.assertEqual(struct.unpack_from("<I", off, at + 48)[0], 0)
            self.assertEqual(struct.unpack_from("<I", on, at + 48)[0], 1)

    def test_restore_remains_the_pinned_piano_strip(self):
        self.assertEqual(
            self.probe.record_sha256(self.records["restore"]),
            "4976d6e597c6caafb25c85b9011b59cb9faa23e671d56a191c4bb460a62673f8",
        )


if __name__ == "__main__":
    unittest.main()
