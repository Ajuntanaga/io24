import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "io24_corrected_fx_rebuild_probe",
    ROOT / "re" / "io24_corrected_fx_rebuild_probe.py")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def _window(label, ratio, mad=0.01):
    return {
        "label": label,
        "median_main_to_input1_db": ratio,
        "mad_db": mad,
    }


class _Device:
    def __init__(self):
        self.gain = 30.0
        self.main = 0.7599995732307434
        self.hp = 0.510000467300415
        self.fx_calls = []
        self.gate_calls = []

    def read_params(self):
        return {
            "flags": 897,
            "input1Gain": self.gain,
            "input2Gain": 24.287769317626953,
            "input1SlotIndex": 0,
            "input2SlotIndex": 2,
            "input1ProcessingChannel": 0,
            "input2ProcessingChannel": 1,
            "input1PhantomPower": False,
            "input2PhantomPower": False,
            "mainVolume": self.main,
            "hpVolume": self.hp,
        }

    def set_main_volume(self, value):
        self.main = value

    def set_hp_volume(self, value):
        self.hp = value

    def set_gain(self, channel, value):
        self.assert_channel(channel)
        self.gain = value

    def assert_channel(self, channel):
        if channel != 1:
            raise AssertionError("probe touched the wrong channel")

    def gate_off(self, channel):
        self.assert_channel(channel)
        self.gate_calls.append(("off", channel))

    def set_gate(self, **kwargs):
        self.assert_channel(kwargs["channel"])
        self.gate_calls.append(("on", dict(kwargs)))

    def set_fx(self, model, **kwargs):
        self.fx_calls.append((model, dict(kwargs)))


RESTORE_FX = {
    "model": "transformer",
    "kwargs": {"on": False, "lows": 0.12, "width": 0.51, "mix": 0.61},
}
RESTORE_GATE = {
    "channel": 1,
    "on": True,
    "threshold_db": -48.720008850097656,
    "range_db": -55.0,
    "attack_s": 0.0007686163298785686,
    "release_s": 1.5712599754333496,
    "keyfilter_hz": 325.12066650390625,
    "expander": True,
    "keylisten": False,
    "instance": None,
    "fs": 96000.0,
}


class ClassificationTests(unittest.TestCase):
    def test_detects_a_stable_effect(self):
        result = PROBE.classify(
            [_window("off", -0.2), _window("on", 5.8),
             _window("off", -0.1)],
            "SEEN", "NONE")
        self.assertEqual("SEEN", result["classification"])
        self.assertTrue(result["effect_detected"])

    def test_rejects_a_flat_or_drifting_result(self):
        flat = PROBE.classify(
            [_window("off", 0.0), _window("on", 0.1),
             _window("off", 0.0)], "SEEN", "NONE")
        drift = PROBE.classify(
            [_window("off", 0.0), _window("on", -5.0),
             _window("off", 1.0)], "SEEN", "NONE")
        self.assertEqual("NONE", flat["classification"])
        self.assertEqual("INCONCLUSIVE_BASELINE_DRIFT",
                         drift["classification"])


class SequenceTests(unittest.TestCase):
    def sample(self, label):
        ratios = {
            "gate_off_before": -0.2,
            "gate_on": -20.0,
            "gate_off_after": -0.1,
            "delay_off_before": -0.2,
            "delay_on": 5.8,
            "delay_off_after": -0.1,
        }
        return _window(label, ratios[label])

    def test_one_delay_and_gate_control_restore_every_known_control(self):
        device = _Device()
        result = PROBE.run_sequence(
            device, RESTORE_FX, RESTORE_GATE, self.sample,
            settle=lambda _seconds: None)
        self.assertEqual("MEASURED_AND_RESTORED", result["status"])
        self.assertEqual("CORRECTED_DELAY_AUDIBLE_BY_METER",
                         result["conclusion"])
        self.assertEqual(30.0, device.gain)
        self.assertEqual(0.7599995732307434, device.main)
        self.assertEqual(0.510000467300415, device.hp)
        self.assertEqual(("transformer", RESTORE_FX["kwargs"]),
                         device.fx_calls[-1])
        self.assertEqual(("on", RESTORE_GATE), device.gate_calls[-1])
        self.assertTrue(result["restoration"]["readable_exact"])
        self.assertEqual(4, len(device.fx_calls))

    def test_flat_delay_is_inconclusive_when_its_expected_gain_is_below_noise(self):
        device = _Device()

        def sample(label):
            if label == "gate_on":
                return _window(label, -20.0)
            return _window(label, -0.2, mad=0.34)

        result = PROBE.run_sequence(
            device, RESTORE_FX, RESTORE_GATE, sample,
            settle=lambda _seconds: None)
        self.assertEqual(
            "INCONCLUSIVE_EXPECTED_LEVEL_SIGNATURE_BELOW_THRESHOLD",
            result["conclusion"])
        self.assertLess(
            result["delay"]["expected_stationary_noise_gain_db"],
            result["delay"]["analysis"]["detection_threshold_db"])

    def test_failure_still_restores(self):
        device = _Device()

        def fail(label):
            if label == "gate_on":
                raise RuntimeError("meter failed")
            return self.sample(label)

        result = PROBE.run_sequence(
            device, RESTORE_FX, RESTORE_GATE, fail,
            settle=lambda _seconds: None)
        self.assertEqual("MEASUREMENT_FAILED_RESTORED", result["status"])
        self.assertEqual(("transformer", RESTORE_FX["kwargs"]),
                         device.fx_calls[-1])
        self.assertEqual(("on", RESTORE_GATE), device.gate_calls[-1])


class BoundaryTests(unittest.TestCase):
    def test_default_is_hardware_free(self):
        self.assertEqual(0, PROBE.main([]))


if __name__ == "__main__":
    unittest.main()
