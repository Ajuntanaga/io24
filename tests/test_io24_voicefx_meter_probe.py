import importlib.util
import json
import os
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "io24_voicefx_meter_probe.py")
SPEC = importlib.util.spec_from_file_location("io24_voicefx_meter_probe", SCRIPT)
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def _window(label, ratio_db, source=1.0, main=1.0, mad=0.01):
    return {
        "label": label,
        "samples": 40,
        "median_input1": source,
        "median_main": main,
        "median_main_to_input1": 10 ** (ratio_db / 20.0),
        "median_main_to_input1_db": ratio_db,
        "mad_main_to_input1_db": mad,
        "minimum_main_to_input1_db": ratio_db - mad,
        "maximum_main_to_input1_db": ratio_db + mad,
    }


class ClassificationTests(unittest.TestCase):
    def test_detects_one_effect_with_stable_aba_baselines(self):
        low = _window("low", 0.0, source=0.01, main=0.01)
        high = _window("high", 0.0, source=1.0, main=0.5)
        trials = [{
            "model": "ringmod",
            "off_before": _window("a1", 0.0),
            "on": _window("b", -4.0),
            "off_after": _window("a2", 0.1),
        }]
        result = PROBE.classify_measurements(low, high, trials)
        self.assertEqual("DIRECT_BLOCK201_METER_EFFECT_DETECTED",
                         result["classification"])
        self.assertTrue(result["models"][0]["meter_effect_detected"])

    def test_classifies_stable_null(self):
        low = _window("low", 0.0, source=0.01, main=0.01)
        high = _window("high", 0.0, source=1.0, main=0.5)
        trials = [{
            "model": "delay",
            "off_before": _window("a1", 0.0),
            "on": _window("b", 0.08),
            "off_after": _window("a2", -0.02),
        }]
        result = PROBE.classify_measurements(low, high, trials)
        self.assertEqual("NO_DIRECT_BLOCK201_METER_EFFECT_DETECTED",
                         result["classification"])

    def test_rejects_blind_control_and_drifting_baseline(self):
        low = _window("low", 0.0, source=0.1, main=0.1)
        high = _window("high", 0.0, source=0.2, main=0.2)
        trial = [{
            "model": "filters",
            "off_before": _window("a1", 0.0),
            "on": _window("b", -5.0),
            "off_after": _window("a2", 1.0),
        }]
        result = PROBE.classify_measurements(low, high, trial)
        self.assertEqual("INCONCLUSIVE_METER_ROUTE_CONTROL_FAILED",
                         result["classification"])


class _Device:
    def __init__(self):
        self.gain = 30.0
        self.main = 0.76
        self.hp = 0.51
        self.quantize_safe_outputs = False
        self.fx_calls = []
        self.gate_calls = []

    def read_params(self):
        return {
            "flags": 449,
            "input1Gain": self.gain,
            "input2Gain": 24.287769317626953,
            "hpVolume": self.hp,
            "mainVolume": self.main,
            "input1ProcessingChannel": 0,
            "input2ProcessingChannel": 1,
            "input1PhantomPower": False,
            "input2PhantomPower": False,
        }

    def set_main_volume(self, value):
        self.main = (value + 2e-7
                     if self.quantize_safe_outputs and value == 0.01 else value)

    def set_hp_volume(self, value):
        self.hp = (value + 2e-7
                   if self.quantize_safe_outputs and value == 0.01 else value)

    def set_gain(self, channel, value):
        self.assert_channel(channel)
        self.gain = value

    def assert_channel(self, channel):
        if channel != 1:
            raise AssertionError("probe changed the wrong input")

    def set_fx(self, model, **kwargs):
        self.fx_calls.append((model, kwargs))

    def gate_off(self, channel):
        self.assert_channel(channel)
        self.gate_calls.append(("off", {"channel": channel}))

    def set_gate(self, **kwargs):
        self.gate_calls.append(("restore", kwargs))


class SequenceTests(unittest.TestCase):
    def setUp(self):
        self.restore = {"model": "transformer", "kwargs": {
            "on": False, "lows": 0.12, "width": 0.51, "mix": 0.61}}
        self.restore_gate = {
            "channel": 1, "on": True, "threshold_db": -48.72,
            "range_db": -55.0, "attack_s": 0.0007, "release_s": 1.57,
            "keyfilter_hz": 325.0, "expander": True, "keylisten": False,
            "instance": None, "fs": 96000.0,
        }

    def _sample(self, label):
        source = 0.01 if label == "gain_control_low" else 1.0
        main = 0.01 if label == "gain_control_low" else 0.5
        return _window(label, 0.0, source=source, main=main)

    def test_sequence_restores_readable_state_and_host_fx_intent(self):
        device = _Device()
        device.quantize_safe_outputs = True
        result = PROBE.run_sequence(
            device, self.restore, self.restore_gate, self._sample,
            settle=lambda _seconds: None)
        self.assertEqual("MEASURED_AND_RESTORED", result["status"])
        self.assertEqual(30.0, device.gain)
        self.assertEqual(0.76, device.main)
        self.assertEqual(0.51, device.hp)
        self.assertEqual(("transformer", self.restore["kwargs"]),
                         device.fx_calls[-1])
        self.assertEqual(("restore", self.restore_gate), device.gate_calls[-1])
        self.assertTrue(result["restoration"]["readable_exact"])
        self.assertEqual(len(PROBE.MODEL_PROFILES) * 3 + 1,
                         len(device.fx_calls))

    def test_failure_still_restores(self):
        device = _Device()

        def fail(label):
            if label == "transformer_on":
                raise RuntimeError("meter failed")
            return self._sample(label)

        result = PROBE.run_sequence(
            device, self.restore, self.restore_gate, fail,
            settle=lambda _seconds: None)
        self.assertEqual("MEASUREMENT_FAILED_RESTORED", result["status"])
        self.assertEqual(30.0, device.gain)
        self.assertEqual(0.76, device.main)
        self.assertEqual(0.51, device.hp)
        self.assertEqual(("transformer", self.restore["kwargs"]),
                         device.fx_calls[-1])


class ShadowTests(unittest.TestCase):
    def test_loads_and_validates_complete_restore_call(self):
        gate = {
            "channel": 1, "on": True, "threshold_db": -48.72,
            "range_db": -55.0, "attack_s": 0.0007, "release_s": 1.57,
            "keyfilter_hz": 325.0, "expander": True, "keylisten": False,
            "instance": None, "fs": 96000.0,
        }
        payload = {
            "set_fx": {"fn": "set_fx", "kwargs": {
                "model": "transformer", "on": False, "lows": 0.12,
                "width": 0.51, "mix": 0.61}},
            "set_gate#channel=1,instance=None": {
                "fn": "set_gate", "kwargs": gate},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "shadow.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            result = PROBE.restore_fx_from_shadow(path)
            restored_gate = PROBE.restore_gate_from_shadow(path)
        self.assertEqual("transformer", result["model"])
        self.assertFalse(result["kwargs"]["on"])
        self.assertEqual(gate, restored_gate)


if __name__ == "__main__":
    unittest.main()
