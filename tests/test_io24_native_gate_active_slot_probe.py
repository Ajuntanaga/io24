#!/usr/bin/env python3
"""Contracts for the source-bound active-slot native gate probe."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "re" / "io24_native_gate_active_slot_probe.py"
FIRMWARE = Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin")


def _load():
    if not SCRIPT.is_file():
        return None
    spec = importlib.util.spec_from_file_location(
        "io24_native_gate_active_slot_probe", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROBE = _load()


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
        self.actions = []

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
        self.actions.append(("select", slot))

    def recall_device_slot(self, channel, slot):
        self.set_preset_slot(channel, slot)
        return {"channel": channel, "slot": slot,
                "selection": "SENT_UNVERIFIED"}

    def save_device_slot(self, slot, record):
        if self.slot != slot:
            raise AssertionError("writer target was not active")
        self.actions.append(("write", slot, bytes(record)))
        return {"slot": slot, "fragments_sent": 1,
                "replies_received": 0}


@unittest.skipUnless(FIRMWARE.is_file(), "firmware image not retained")
class ActiveSlotSequenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(PROBE, "active-slot gate probe is missing")
        self.records = PROBE.build_test_records(FIRMWARE.read_bytes())

    def test_each_candidate_and_restore_are_written_while_slot_three_is_active(self):
        device = _Device()
        levels = {"gate_off_before": 0.0, "gate_on": -8.0,
                  "gate_off_after": 0.1}

        result = PROBE.run_active_sequence(
            device, self.records,
            lambda label: _window(levels[label]),
            settle=lambda _seconds: None)

        self.assertEqual(result["status"], "MEASURED_AND_RESTORED")
        self.assertEqual(device.slot, 2)
        self.assertEqual(device.gain, 24.287769317626953)
        self.assertEqual(device.main, 0.7599995732307434)
        self.assertEqual(device.hp, 0.510000467300415)
        self.assertEqual(
            [action for action in device.actions if action[0] == "write"],
            [
                ("write", 3, self.records["flat"]),
                ("write", 3, self.records["boosted"]),
                ("write", 3, self.records["flat"]),
                ("write", 3, self.records["restore"]),
            ],
        )
        self.assertTrue(result["analysis"]["effect_detected"])
        self.assertTrue(result["restoration"]["readable_exact"])

    def test_failure_after_first_active_write_still_restores_active_slot_body(self):
        device = _Device()

        def fail(_label):
            raise RuntimeError("meter failure")

        result = PROBE.run_active_sequence(
            device, self.records, fail, settle=lambda _seconds: None)

        self.assertEqual(result["status"], "MEASUREMENT_FAILED_RESTORED")
        writes = [action for action in device.actions if action[0] == "write"]
        self.assertEqual(writes[-1], ("write", 3, self.records["restore"]))
        self.assertEqual(device.slot, 2)

    def test_slot_three_precondition_is_refused_before_a_write(self):
        device = _Device()
        device.slot = 3

        with self.assertRaises(PROBE.NativeActiveSlotProbeError):
            PROBE.run_active_sequence(
                device, self.records, lambda _label: _window(0.0),
                settle=lambda _seconds: None)

        self.assertEqual(
            [action for action in device.actions if action[0] == "write"], [])


if __name__ == "__main__":
    unittest.main()
