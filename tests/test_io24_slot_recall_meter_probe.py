import importlib.util
import os
import unittest

import io24_presets


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "io24_slot_recall_meter_probe.py")
SPEC = importlib.util.spec_from_file_location(
    "io24_slot_recall_meter_probe", SCRIPT)
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def _window(label, ratio_db):
    return {
        "label": label,
        "samples": 40,
        "median_input1": 1.0,
        "buses": {
            bus: {
                "median": 10 ** (ratio_db / 20.0),
                "median_output": 10 ** (ratio_db / 20.0),
                "median_to_input1_db": ratio_db,
                "mad_to_input1_db": 0.01,
                "minimum_to_input1_db": ratio_db - 0.01,
                "maximum_to_input1_db": ratio_db + 0.01,
            } for bus in ("main", "mixa", "mixb")
        },
    }


def _original():
    return io24_presets.load()["Broadcast"]


class RecordTests(unittest.TestCase):
    def test_records_are_complete_and_differ_only_as_intended(self):
        original = _original()
        flat, boosted = PROBE.build_test_records(original)
        self.assertEqual("CP34 FLAT RECALL PROBE", flat["preset_name"])
        self.assertEqual("CP34 BOOST RECALL PROBE", boosted["preset_name"])
        self.assertEqual(0, flat["eq"]["eqbandon4"])
        self.assertEqual(1, boosted["eq"]["eqbandon4"])
        self.assertEqual(1, boosted["eq"]["eqbandop4"])
        self.assertEqual(15.0, boosted["eq"]["eqgain4"])
        copy = dict(boosted)
        copy["preset_name"] = flat["preset_name"]
        copy["eq"] = flat["eq"]
        self.assertEqual(flat, copy)


class ClassificationTests(unittest.TestCase):
    def test_detects_repeatable_boost(self):
        result = PROBE.classify_windows(
            _window("a1", 0.0), _window("b", 8.0), _window("a2", 0.1))
        self.assertEqual("INACTIVE_SLOT_SAVE_RECALL_EFFECT_DETECTED",
                         result["classification"])

    def test_stable_null_and_drift_are_distinct(self):
        null = PROBE.classify_windows(
            _window("a1", 0.0), _window("b", 0.1), _window("a2", 0.0))
        drift = PROBE.classify_windows(
            _window("a1", 0.0), _window("b", 4.0), _window("a2", 2.0))
        self.assertEqual("NO_SAVED_BODY_RECALL_EFFECT_DETECTED",
                         null["classification"])
        self.assertEqual("INCONCLUSIVE_FLAT_BASELINE_DRIFT",
                         drift["classification"])


class _Device:
    def __init__(self):
        self.slot = 0
        self.gain = 30.0
        self.main = 0.76
        self.hp = 0.51
        self.saved = []

    def read_params(self):
        return {
            "flags": 449,
            "input1Gain": self.gain,
            "input2Gain": 24.287769317626953,
            "hpVolume": self.hp,
            "mainVolume": self.main,
            "input1SlotIndex": self.slot,
            "input2SlotIndex": 2,
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
        if channel != 1:
            raise AssertionError("wrong channel")
        self.gain = value

    def set_preset_slot(self, channel, slot):
        if channel != 1:
            raise AssertionError("wrong channel")
        self.slot = slot

    def save_uc_device_slot(self, slot, record):
        self.saved.append((slot, record))
        return {"slot": slot, "fragments_sent": 1, "replies_received": 0}

    def recall_device_slot(self, channel, slot):
        self.set_preset_slot(channel, slot)
        return {"channel": channel, "slot": slot, "selection": "SENT_UNVERIFIED"}


class SequenceTests(unittest.TestCase):
    def test_sequence_restores_original_body_selector_and_controls(self):
        original = _original()
        flat, boosted = PROBE.build_test_records(original)
        device = _Device()
        levels = {"flat_before": 0.0, "boosted": 8.0, "flat_after": 0.1}
        result = PROBE.run_sequence(
            device, original, flat, boosted,
            lambda label: _window(label, levels[label]),
            settle=lambda _seconds: None)
        self.assertEqual("MEASURED_AND_RESTORED", result["status"])
        self.assertEqual(0, device.slot)
        self.assertEqual(30.0, device.gain)
        self.assertEqual(0.76, device.main)
        self.assertEqual(0.51, device.hp)
        self.assertEqual([flat, boosted, flat, original],
                         [record for _slot, record in device.saved])
        self.assertTrue(result["restoration"]["readable_exact"])

    def test_failure_after_first_write_still_restores_original(self):
        original = _original()
        flat, boosted = PROBE.build_test_records(original)
        device = _Device()

        def fail(label):
            raise RuntimeError("meter failed at " + label)

        result = PROBE.run_sequence(
            device, original, flat, boosted, fail,
            settle=lambda _seconds: None)
        self.assertEqual("MEASUREMENT_FAILED_RESTORED", result["status"])
        self.assertEqual(original, device.saved[-1][1])
        self.assertEqual(0, device.slot)


if __name__ == "__main__":
    unittest.main()
