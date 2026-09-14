import importlib.util
import json
import os
import tempfile
import unittest
import wave

import numpy as np


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "io24_dsp_amount_passive.py")
SPEC = importlib.util.spec_from_file_location("io24_dsp_amount_passive", SCRIPT)
PASSIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PASSIVE)

AMOUNTS = (0.0, 0.25, 0.5, 0.75, 1.0)


def _write_wav(path, audio):
    pcm = np.rint(np.clip(audio, -1.0, 1.0) * (2**31 - 1)).astype("<i4")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(6)
        handle.setsampwidth(4)
        handle.setframerate(96000)
        handle.writeframes(pcm.tobytes())


def _manifest(directory, mode="linear", unrelated_monitor=False):
    captures = []
    frames = 96000 * 3
    for index, amount in enumerate(AMOUNTS):
        rng = np.random.default_rng(2400 + index)
        source = rng.normal(0.0, 10 ** (-50 / 20), frames)
        dry = 0.72 * source + np.r_[np.zeros(17), 0.16 * source[:-17]]
        wet = 0.31 * source - np.r_[np.zeros(83), 0.27 * source[:-83]]
        if mode == "linear":
            monitor = (1.0 - amount) * dry + amount * wet
        elif mode == "gate":
            monitor = dry if amount == 0.0 else wet
        elif mode == "level":
            monitor = amount * wet
        elif mode == "curved":
            position = amount * amount
            monitor = (1.0 - position) * dry + position * wet
        elif mode == "same":
            monitor = dry
        else:
            raise ValueError(mode)
        audio = np.zeros((frames, 6), dtype=np.float64)
        audio[:, 1] = source
        audio[:, 2] = monitor
        audio[:, 3] = monitor
        if unrelated_monitor and index == 2:
            audio[:, 2] = rng.normal(0.0, 10 ** (-50 / 20), frames)
        path = os.path.join(directory, "amount-%03d.wav" % round(amount * 100))
        _write_wav(path, audio)
        captures.append({"amount": amount, "path": os.path.basename(path)})
    manifest = {
        "schema": "io24-dsp-amount-passive-captures-v1",
        "rate_hz": 96000,
        "channels": 6,
        "sample_width_bytes": 4,
        "reference_channel": 2,
        "monitor_channels": [3, 4],
        "captures": captures,
    }
    path = os.path.join(directory, "captures.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle)
    return path


class PassiveTransferTests(unittest.TestCase):
    def test_independent_noise_classifies_linear_endpoint_interpolation(self):
        with tempfile.TemporaryDirectory() as temp:
            result = PASSIVE.analyze_manifest(_manifest(temp, "linear"))
        self.assertEqual("VALID", result["status"])
        self.assertEqual("LINEAR_ENDPOINT_INTERPOLATION",
                         result["classification"])
        self.assertEqual("CONSISTENT_WITH_DRY_WET_NOT_ARCHITECTURE_PROOF",
                         result["interpretation"])
        self.assertGreater(result["minimum_median_coherence"], 0.95)

    def test_distinguishes_gate_level_curve_and_no_effect(self):
        expected = {
            "gate": ("VALID", "ZERO_NONZERO_GATE"),
            "level": ("VALID", "ZERO_ANCHORED_OUTPUT_LEVEL_SCALING"),
            "curved": ("VALID", "NONLINEAR_ENDPOINT_BLEND"),
            "same": ("INCONCLUSIVE", "ENDPOINT_TRANSFERS_INDISTINGUISHABLE"),
        }
        for mode, pair in expected.items():
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                result = PASSIVE.analyze_manifest(_manifest(temp, mode))
                self.assertEqual(pair, (result["status"], result["classification"]))

    def test_rejects_unrelated_monitor(self):
        with tempfile.TemporaryDirectory() as temp:
            result = PASSIVE.analyze_manifest(
                _manifest(temp, "linear", unrelated_monitor=True))
        self.assertEqual("INVALID_CAPTURE_SET", result["status"])
        self.assertTrue(any("coherence" in reason for reason in result["reasons"]))


class _Device:
    def __init__(self, fail_capture=False):
        self.amount = 0.0
        self.main = 0.76
        self.amount_writes = []
        self.main_writes = []
        self.highpass_writes = []
        self.eq_writes = []
        self.fail_capture = fail_capture

    def read_params(self):
        flags = 449 if self.amount == 0.0 else 385
        return {
            "flags": flags,
            "input1Gain": 30.0,
            "input2Gain": 24.287769317626953,
            "mainVolume": self.main,
            "input1ProcessingChannel": 0,
            "input2ProcessingChannel": 1,
            "input1PhantomPower": False,
            "input2PhantomPower": False,
        }

    def set_main_volume(self, value):
        self.main = value
        self.main_writes.append(value)

    def set_fx_mix(self, channel, value):
        assert channel == 2
        self.amount = value
        self.amount_writes.append(value)

    def set_highpass_freq(self, channel, value, fs=48000.0):
        self.highpass_writes.append((channel, value, fs))

    def set_eq_band(self, channel, band, **kwargs):
        self.eq_writes.append((channel, band, kwargs))


class PassiveSequenceTests(unittest.TestCase):
    def test_sequence_changes_only_main_and_amount_then_restores(self):
        device = _Device()
        seen = []
        result = PASSIVE.run_passive_sequence(
            device, lambda amount: seen.append(amount) or {"amount": amount},
            settle=lambda _seconds: None)
        self.assertEqual("CAPTURED_AND_RESTORED", result["status"])
        self.assertEqual(list(PASSIVE.CAPTURE_ORDER), seen)
        self.assertEqual([PASSIVE.SAFE_MAIN_VOLUME, 0.76], device.main_writes)
        self.assertEqual(0.0, device.amount)
        self.assertTrue(result["restoration"]["readable_exact"])
        self.assertEqual("UNTOUCHED", result["restoration"]["mixer_routes"])

    def test_capture_failure_still_restores_exact_zero_and_main(self):
        device = _Device()

        def capture(amount):
            if amount == 0.25:
                raise RuntimeError("capture failed")
            return {"amount": amount}

        result = PASSIVE.run_passive_sequence(
            device, capture, settle=lambda _seconds: None)
        self.assertEqual("CAPTURE_FAILED_RESTORED", result["status"])
        self.assertEqual(0.0, device.amount)
        self.assertEqual(0.76, device.main)

    def test_known_highpass_probe_restores_identity_coefficients(self):
        device = _Device()
        result = PASSIVE.run_known_highpass_sequence(
            device, lambda amount: {"amount": amount},
            settle=lambda _seconds: None)
        self.assertEqual("CAPTURED_AND_RESTORED", result["status"])
        self.assertEqual([
            (2, PASSIVE.PROBE_HIGHPASS_HZ, 96000.0),
            (2, PASSIVE.IDENTITY_HIGHPASS_HZ, 96000.0),
        ], device.highpass_writes)
        self.assertEqual("IDENTITY_COEFFICIENTS_SENT",
                         result["controlled_processor"]["restoration"])

    def test_known_eq_probe_restores_band_to_identity(self):
        device = _Device()
        result = PASSIVE.run_known_eq_sequence(
            device, lambda amount: {"amount": amount},
            settle=lambda _seconds: None)
        self.assertEqual("CAPTURED_AND_RESTORED", result["status"])
        self.assertEqual("peaking", device.eq_writes[0][2]["shape"])
        self.assertEqual(PASSIVE.PROBE_EQ_GAIN_DB,
                         device.eq_writes[0][2]["gain_db"])
        self.assertEqual("off", device.eq_writes[-1][2]["shape"])
        self.assertEqual("IDENTITY_COEFFICIENTS_SENT",
                         result["controlled_processor"]["restoration"])


if __name__ == "__main__":
    unittest.main()
