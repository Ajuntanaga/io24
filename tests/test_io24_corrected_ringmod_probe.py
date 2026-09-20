import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "io24_corrected_ringmod_probe",
    ROOT / "re" / "io24_corrected_ringmod_probe.py")
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
        self.main = 0.7699995636940002
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
        self._assert_channel(channel)
        self.gain = value

    def _assert_channel(self, channel):
        if channel != 1:
            raise AssertionError("probe touched the wrong channel")

    def gate_off(self, channel):
        self._assert_channel(channel)
        self.gate_calls.append(("off", channel))

    def set_gate(self, **kwargs):
        self._assert_channel(kwargs["channel"])
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


class RingModDesignTests(unittest.TestCase):
    def test_zero_volume_fully_wet_has_zero_dry_and_wet_output_gain(self):
        gains = PROBE.ringmod_output_gains(PROBE.RINGMOD_PARAMETERS)
        self.assertEqual({"dry": 0.0, "wet": 0.0}, gains)

    def test_restoration_ignores_only_documented_session_bit_nine(self):
        device = _Device()
        before = PROBE.common._state(device)
        before["flags"] = 385
        session_only = dict(before, flags=897)
        user_control_change = dict(session_only, main_volume=0.5)
        self.assertTrue(PROBE.restoration_matches(before, session_only))
        self.assertFalse(PROBE.restoration_matches(before,
                                                   user_control_change))


class SequenceTests(unittest.TestCase):
    def sample(self, label):
        ratios = {
            "gate_off_before": -0.2,
            "gate_on": -20.0,
            "gate_off_after": -0.1,
            "ringmod_off_before": -0.2,
            "ringmod_on": -24.0,
            "ringmod_off_after": -0.1,
        }
        return _window(label, ratios[label])

    def test_one_ringmod_and_gate_control_restore_every_known_control(self):
        device = _Device()
        result = PROBE.run_sequence(
            device, RESTORE_FX, RESTORE_GATE, self.sample,
            settle=lambda _seconds: None)
        self.assertEqual("MEASURED_AND_RESTORED", result["status"])
        self.assertEqual(
            "CORRECTED_RINGMOD_ZERO_OUTPUT_EFFECT_DETECTED",
            result["conclusion"])
        self.assertEqual({"dry": 0.0, "wet": 0.0},
                         result["ringmod"]["predicted_output_gains"])
        self.assertEqual(30.0, device.gain)
        self.assertEqual(0.7699995636940002, device.main)
        self.assertEqual(0.510000467300415, device.hp)
        self.assertEqual(("transformer", RESTORE_FX["kwargs"]),
                         device.fx_calls[-1])
        self.assertEqual(("on", RESTORE_GATE), device.gate_calls[-1])
        self.assertTrue(result["restoration"]["readable_exact"])
        self.assertEqual(4, len(device.fx_calls))
        for model, kwargs in device.fx_calls[:-1]:
            self.assertEqual("ringmod", model)
            self.assertEqual(0.0, kwargs["vol"])
            self.assertEqual(1.0, kwargs["mix"])

    def test_flat_ringmod_is_a_resolved_negative_when_control_passes(self):
        device = _Device()

        def sample(label):
            if label == "gate_on":
                return _window(label, -20.0)
            return _window(label, -0.2)

        result = PROBE.run_sequence(
            device, RESTORE_FX, RESTORE_GATE, sample,
            settle=lambda _seconds: None)
        self.assertEqual(
            "NO_CORRECTED_RINGMOD_ZERO_OUTPUT_EFFECT_DETECTED",
            result["conclusion"])

    def test_failure_still_restores(self):
        device = _Device()

        def fail(label):
            if label == "ringmod_on":
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
    def test_live_report_does_not_present_unobserved_audio_timing_as_configured(self):
        with tempfile.TemporaryDirectory() as output_dir, \
                mock.patch.object(PROBE.prior, "restore_fx_from_shadow",
                                  return_value={}), \
                mock.patch.object(PROBE.prior, "restore_gate_from_shadow",
                                  return_value={}), \
                mock.patch.object(PROBE.foundation, "_battery", return_value=10):
            report = PROBE.run_live(output_dir, "battery", "shadow")

        self.assertNotIn("host_configured_sample_rate_hz", report)
        self.assertNotIn("host_configured_quantum_frames", report)
        self.assertEqual(report["audio_stream_timing"], {
            "observed": False,
            "sample_rate_hz": None,
            "quantum_frames": None,
            "source": "NO_ALSA_STREAM_OPENED_BY_METER_ONLY_PROBE",
        })

    def test_default_is_hardware_free(self):
        self.assertEqual(0, PROBE.main([]))


if __name__ == "__main__":
    unittest.main()
