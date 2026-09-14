#!/usr/bin/env python3
"""Contracts for the reversible native Standard-EQ slot probe."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest

import io24_native_stat as native


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "re" / "io24_native_standard_slot_probe.py"
FIRMWARE = Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin")
SCENE = (ROOT / ".superpowers" / "sdd" /
         "2026-08-28-cp34-preset-effect-control" / "runs" /
         "20260914T031459-0700-native-slot-builder" / "backup" /
         "Piano Accomany.scene")


def _load():
    if not SCRIPT.is_file():
        return None
    spec = importlib.util.spec_from_file_location(
        "io24_native_standard_slot_probe", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROBE = _load()


def _piano_eq():
    return json.loads(SCENE.read_text(encoding="utf-8-sig"))["line"]["ch2"]["eq"]


def _window(value_db, mad_db=0.02):
    return {
        "median_main_to_input2_db": value_db,
        "mad_main_to_input2_db": mad_db,
    }


class _Device:
    def __init__(self):
        self.slot = 2
        self.gain = 24.287769317626953
        self.main = 0.7599995732307434
        self.hp = 0.510000467300415
        self.saved = []

    def read_params(self):
        return {
            "flags": 385,
            "input1Gain": 30.0,
            "input2Gain": self.gain,
            "hpVolume": self.hp,
            "mainVolume": self.main,
            "input1SlotIndex": 0,
            "input2SlotIndex": self.slot,
            "input1ProcessingChannel": 0,
            "input2ProcessingChannel": 1,
            "input1PhantomPower": False,
            "input2PhantomPower": False,
        }

    def set_main_volume(self, value):
        self.main = value

    def set_hp_volume(self, value):
        self.hp = value

    def set_gain(self, channel, value):
        if channel != 2:
            raise AssertionError("wrong gain channel")
        self.gain = value

    def set_preset_slot(self, channel, slot):
        if channel != 2:
            raise AssertionError("wrong preset channel")
        self.slot = slot

    def recall_device_slot(self, channel, slot):
        self.set_preset_slot(channel, slot)
        return {"channel": channel, "slot": slot,
                "selection": "SENT_UNVERIFIED"}

    def save_device_slot(self, slot, record):
        self.saved.append((slot, bytes(record)))
        return {"slot": slot, "fragments_sent": 1,
                "replies_received": 0}


@unittest.skipUnless(FIRMWARE.is_file(), "firmware image not retained")
class NativeRecordTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(PROBE, "native Standard slot probe is missing")

    def test_builds_flat_boost_and_native_piano_restore_bodies(self):
        records = PROBE.build_test_records(FIRMWARE.read_bytes(), _piano_eq())

        for name in ("restore", "flat", "boosted"):
            with self.subTest(name=name):
                self.assertEqual(
                    native.validate_native_stat_record(records[name], 3),
                    records[name])
        restored = native.decode_native_stat_record(records["restore"])
        self.assertEqual([chunk.key for chunk in restored.chunks], [b"opt "])

        leaves = {}
        for name, record in records.items():
            top = {chunk.key: chunk.payload
                   for chunk in native.decode_native_stat_record(record).chunks}
            leaves[name] = {chunk.key: chunk.payload for chunk in
                            native.decode_chunk_group(top[b"opt "])}
        for key in leaves["restore"]:
            if key != b"eq  ":
                self.assertEqual(leaves["flat"][key], leaves["restore"][key])
                self.assertEqual(leaves["boosted"][key], leaves["restore"][key])
        self.assertNotEqual(leaves["flat"][b"eq  "],
                            leaves["boosted"][b"eq  "])

    def test_classification_distinguishes_effect_null_and_drift(self):
        detected = PROBE.classify_windows(
            _window(0.0), _window(6.0), _window(0.1))
        null = PROBE.classify_windows(
            _window(0.0), _window(0.1), _window(0.0))
        drift = PROBE.classify_windows(
            _window(0.0), _window(6.0), _window(2.0))

        self.assertEqual(detected["classification"],
                         "NATIVE_STANDARD_SLOT_RECALL_EFFECT_DETECTED")
        self.assertEqual(null["classification"],
                         "NO_NATIVE_SLOT_RECALL_EFFECT_DETECTED")
        self.assertEqual(drift["classification"],
                         "INCONCLUSIVE_FLAT_BASELINE_DRIFT")


@unittest.skipUnless(FIRMWARE.is_file(), "firmware image not retained")
class SequenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(PROBE, "native Standard slot probe is missing")
        self.records = PROBE.build_test_records(
            FIRMWARE.read_bytes(), _piano_eq())

    def test_sequence_restores_native_piano_body_selector_and_controls(self):
        device = _Device()
        levels = {"flat_before": 0.0, "boosted": 6.0, "flat_after": 0.1}

        result = PROBE.run_sequence(
            device, self.records,
            lambda label: _window(levels[label]),
            settle=lambda _seconds: None)

        self.assertEqual(result["status"], "MEASURED_AND_RESTORED")
        self.assertEqual(device.slot, 2)
        self.assertEqual(device.gain, 24.287769317626953)
        self.assertEqual(device.main, 0.7599995732307434)
        self.assertEqual(device.hp, 0.510000467300415)
        self.assertEqual([record for _slot, record in device.saved], [
            self.records["flat"], self.records["boosted"],
            self.records["flat"], self.records["restore"],
        ])
        self.assertTrue(result["restoration"]["readable_exact"])

    def test_failure_after_first_write_still_restores_native_piano(self):
        device = _Device()

        def fail(_label):
            raise RuntimeError("meter failure")

        result = PROBE.run_sequence(
            device, self.records, fail, settle=lambda _seconds: None)

        self.assertEqual(result["status"], "MEASUREMENT_FAILED_RESTORED")
        self.assertEqual(device.saved[-1], (3, self.records["restore"]))
        self.assertEqual(device.slot, 2)

    def test_active_slot_three_is_refused_before_a_write(self):
        device = _Device()
        device.slot = 3

        with self.assertRaises(PROBE.NativeSlotProbeError):
            PROBE.run_sequence(
                device, self.records, lambda _label: _window(0.0),
                settle=lambda _seconds: None)

        self.assertEqual(device.saved, [])


if __name__ == "__main__":
    unittest.main()
