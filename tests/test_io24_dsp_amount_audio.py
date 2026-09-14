import importlib.util
import json
import os
import tempfile
import unittest
import wave

import numpy as np


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "io24_dsp_amount_audio.py")
SPEC = importlib.util.spec_from_file_location("io24_dsp_amount_audio", SCRIPT)
ANALYZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYZER)


AMOUNTS = (0.0, 0.25, 0.5, 0.75, 1.0)


def _write_wav(path, audio, rate=96000):
    pcm = np.rint(np.clip(audio, -1.0, 1.0) * (2**31 - 1)).astype("<i4")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(audio.shape[1])
        handle.setsampwidth(4)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())


def _fixture(directory, mode="dry_wet", rate=96000, clipped=False,
             endpoint_difference=True):
    rng = np.random.default_rng(0xD5A024)
    frames = rate * 3
    active_start = int(0.45 * rate)
    active_frames = int(1.8 * rate)
    source = rng.normal(0.0, 10 ** (-30 / 20), active_frames)
    fade = int(0.02 * rate)
    source[:fade] *= np.linspace(0.0, 1.0, fade, endpoint=False)
    source[-fade:] *= np.linspace(1.0, 0.0, fade, endpoint=False)

    reference = np.zeros(frames)
    reference[active_start:active_start + active_frames] = source
    dry = np.zeros(frames)
    wet = np.zeros(frames)
    dry_delay = 31
    wet_delay = 173
    dry[dry_delay:] = 0.72 * reference[:-dry_delay]
    wet[:] = dry
    if endpoint_difference:
        wet[wet_delay:] += 0.24 * reference[:-wet_delay]

    captures = []
    shifts = (0, 37, -23, 61, -41)
    gains = (1.0, 0.93, 1.04, 0.97, 1.02)
    for amount, shift, gain in zip(AMOUNTS, shifts, gains):
        if mode == "dry_wet":
            monitor = (1.0 - amount) * dry + amount * wet
        elif mode == "gate":
            monitor = dry if amount == 0.0 else wet
        elif mode == "level":
            monitor = amount * wet
        elif mode == "curved":
            mix = amount * amount
            monitor = (1.0 - mix) * dry + mix * wet
        else:
            raise ValueError(mode)
        audio = np.zeros((frames, 6), dtype=np.float64)
        audio[:, 1] = reference
        audio[:, 2] = monitor
        audio = np.roll(audio, shift, axis=0) * gain
        if shift > 0:
            audio[:shift] = 0.0
        elif shift < 0:
            audio[shift:] = 0.0
        if clipped and amount == 0.5:
            audio[100, 0] = 0.7
        path = os.path.join(directory, "amount-%03d.wav" % round(amount * 100))
        _write_wav(path, audio, rate=rate)
        captures.append({"amount": amount, "path": path})

    manifest = {
        "schema": "io24-dsp-amount-captures-v1",
        "rate_hz": rate,
        "channels": 6,
        "sample_width_bytes": 4,
        "reference_channel": 2,
        "monitor_channel": 3,
        "captures": captures,
    }
    path = os.path.join(directory, "manifest.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle)
    return path


class DspAmountAudioTests(unittest.TestCase):
    def test_classifies_linear_parallel_dry_wet(self):
        with tempfile.TemporaryDirectory() as temp:
            result = ANALYZER.analyze_manifest(_fixture(temp, "dry_wet"))

        self.assertEqual("VALID", result["status"])
        self.assertEqual("LINEAR_ENDPOINT_INTERPOLATION",
                         result["classification"])
        self.assertEqual("CONSISTENT_WITH_DRY_WET_NOT_ARCHITECTURE_PROOF",
                         result["interpretation"])
        self.assertGreater(result["endpoint_delta_ratio"], 0.1)
        for row in result["amount_measurements"]:
            self.assertAlmostEqual(row["amount"], row["endpoint_position"], places=2)
            self.assertLess(row["affine_residual_ratio"], 0.02)

    def test_classifies_zero_nonzero_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            result = ANALYZER.analyze_manifest(_fixture(temp, "gate"))

        self.assertEqual("VALID", result["status"])
        self.assertEqual("ZERO_NONZERO_GATE", result["classification"])
        positive = [row for row in result["amount_measurements"]
                    if 0.0 < row["amount"] < 1.0]
        self.assertTrue(all(row["distance_to_wet_ratio"] < 0.02
                            for row in positive))

    def test_classifies_output_level_scaling_separately(self):
        with tempfile.TemporaryDirectory() as temp:
            result = ANALYZER.analyze_manifest(_fixture(temp, "level"))

        self.assertEqual("VALID", result["status"])
        self.assertEqual("ZERO_ANCHORED_OUTPUT_LEVEL_SCALING",
                         result["classification"])

    def test_reports_nonlinear_endpoint_blend_without_calling_it_linear(self):
        with tempfile.TemporaryDirectory() as temp:
            result = ANALYZER.analyze_manifest(_fixture(temp, "curved"))

        self.assertEqual("VALID", result["status"])
        self.assertEqual("NONLINEAR_ENDPOINT_BLEND", result["classification"])
        midpoint = next(row for row in result["amount_measurements"]
                        if row["amount"] == 0.5)
        self.assertAlmostEqual(0.25, midpoint["endpoint_position"], places=2)

    def test_indistinguishable_endpoints_are_inconclusive(self):
        with tempfile.TemporaryDirectory() as temp:
            result = ANALYZER.analyze_manifest(
                _fixture(temp, "dry_wet", endpoint_difference=False))

        self.assertEqual("INCONCLUSIVE", result["status"])
        self.assertEqual("ENDPOINTS_INDISTINGUISHABLE", result["classification"])
        self.assertIn("endpoint_delta_below_threshold", result["reasons"])

    def test_wrong_rate_missing_amount_and_clipping_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            wrong_rate = ANALYZER.analyze_manifest(_fixture(temp, rate=48000))
        with tempfile.TemporaryDirectory() as temp:
            clipped = ANALYZER.analyze_manifest(_fixture(temp, clipped=True))
        with tempfile.TemporaryDirectory() as temp:
            manifest_path = _fixture(temp)
            with open(manifest_path, encoding="utf-8") as handle:
                manifest = json.load(handle)
            manifest["captures"] = manifest["captures"][:-1]
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(manifest, handle)
            missing = ANALYZER.analyze_manifest(manifest_path)

        for result in (wrong_rate, clipped, missing):
            self.assertEqual("INVALID_CAPTURE_SET", result["status"])
            self.assertEqual("UNPROVED", result["classification"])
            self.assertTrue(result["reasons"])


if __name__ == "__main__":
    unittest.main()
