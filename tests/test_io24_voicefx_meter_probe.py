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
    def test_quiet_preflight_accepts_only_stable_self_noise(self):
        first = _window("preflight_1", 0.0, source=0.0010)
        second = _window("preflight_2", 0.0, source=0.00105)

        result = PROBE.classify_quiet_preflight(first, second)

        self.assertTrue(result["valid"])

    def test_quiet_preflight_rejects_an_active_or_changing_input(self):
        first = _window("preflight_1", 0.0, source=0.02)
        second = _window("preflight_2", 0.0, source=0.002)

        result = PROBE.classify_quiet_preflight(first, second)

        self.assertFalse(result["valid"])
        self.assertGreater(result["maximum_median_input1"],
                           PROBE.PREFLIGHT_INPUT1_MAX)
        self.assertGreater(abs(result["median_input1_drift_db"]),
                           PROBE.PREFLIGHT_DRIFT_MAX_DB)

    def test_detects_one_effect_with_stable_aba_baselines(self):
        low = _window("gate_closed", -20.0, source=1.0, main=0.1)
        high = _window("gate_open", 0.0, source=1.0, main=1.0)
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
        low = _window("gate_closed", -20.0, source=1.0, main=0.1)
        high = _window("gate_open", 0.0, source=1.0, main=1.0)
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
        low = _window("gate_closed", -2.0, source=1.0, main=0.8)
        high = _window("gate_open", 0.0, source=1.0, main=1.0)
        trial = [{
            "model": "filters",
            "off_before": _window("a1", 0.0),
            "on": _window("b", -5.0),
            "off_after": _window("a2", 1.0),
        }]
        result = PROBE.classify_measurements(low, high, trial)
        self.assertEqual("INCONCLUSIVE_METER_ROUTE_CONTROL_FAILED",
                         result["classification"])

    def test_repeatability_requires_every_on_step_and_off_return(self):
        closed = _window("gate_closed", -20.0, source=1.0, main=0.1)
        opened = _window("gate_open", 0.0, source=1.0, main=1.0)
        trials = [
            {"model": "transformer",
             "off_before": _window("a1", 0.0),
             "on": _window("b1", -4.0),
             "off_after": _window("a2", 0.0)},
            {"model": "transformer",
             "off_before": _window("a3", 0.0),
             "on": _window("b2", -0.1),
             "off_after": _window("a4", 0.0)},
        ]

        result = PROBE.classify_measurements(
            closed, opened, trials, require_repeatable_model=True)

        self.assertEqual("INCONCLUSIVE_MODEL_EFFECT_NOT_REPEATABLE",
                         result["classification"])
        self.assertFalse(result["repeatability"]["valid"])

    def test_repeatability_accepts_two_reversible_same_sign_steps(self):
        closed = _window("gate_closed", -20.0, source=1.0, main=0.1)
        opened = _window("gate_open", 0.0, source=1.0, main=1.0)
        trials = [
            {"model": "transformer",
             "off_before": _window("a1", 0.0),
             "on": _window("b1", -4.0),
             "off_after": _window("a2", 0.0)},
            {"model": "transformer",
             "off_before": _window("a3", 0.0),
             "on": _window("b2", -3.8),
             "off_after": _window("a4", 0.1)},
        ]

        result = PROBE.classify_measurements(
            closed, opened, trials, require_repeatable_model=True)

        self.assertEqual("DIRECT_BLOCK201_METER_EFFECT_DETECTED",
                         result["classification"])
        self.assertTrue(result["repeatability"]["valid"])


class _Device:
    def __init__(self):
        self.gain = 30.0
        self.main = 0.76
        self.hp = 0.51
        self.channel2_processing = True
        self.quantize_safe_outputs = False
        self.fx_calls = []
        self.gate_calls = []
        self.processing_mix_calls = []

    def read_params(self):
        return {
            "flags": 385 if self.channel2_processing else 449,
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

    def set_fx_mix(self, channel, value):
        if channel != 2:
            raise AssertionError("discriminator changed the wrong DSP Amount")
        self.processing_mix_calls.append((channel, value))
        self.channel2_processing = value != 0.0

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
        if label == "gate_control_closed":
            return _window(label, -20.0, source=1.0, main=0.1)
        return _window(label, 0.0, source=1.0, main=1.0)

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

    def test_channel2_zero_discriminator_resends_supplied_amount(self):
        device = _Device()
        result = PROBE.run_sequence(
            device, self.restore, self.restore_gate, self._sample,
            settle=lambda _seconds: None,
            model_profiles=PROBE.MODEL_PROFILES[:1],
            channel2_zero_discriminator=True,
            channel2_restore_amount=1.0)

        self.assertEqual("MEASURED_AND_RESTORED", result["status"])
        self.assertEqual([(2, 0.0), (2, 1.0)],
                         device.processing_mix_calls)
        self.assertTrue(device.channel2_processing)
        self.assertEqual(1, len(result["trials"]))
        self.assertTrue(result["restoration"]["readable_exact"])
        self.assertEqual(
            "CHANNEL2_SUPPLIED_1.000000_RESENT_ZERO_NONZERO_READBACK_RESTORED",
            result["restoration"]["dsp_amount"])

    def test_transformer_repeatability_runs_two_complete_aba_cycles(self):
        device = _Device()
        result = PROBE.run_sequence(
            device, self.restore, self.restore_gate, self._sample,
            settle=lambda _seconds: None,
            model_profiles=PROBE.MODEL_PROFILES[:1] * 2,
            require_repeatable_model=True)

        self.assertEqual("MEASURED_AND_RESTORED", result["status"])
        self.assertEqual(2, len(result["trials"]))
        self.assertFalse(result["analysis"]["repeatability"]["valid"])
        self.assertEqual("NO_DIRECT_BLOCK201_METER_EFFECT_DETECTED",
                         result["analysis"]["classification"])


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
