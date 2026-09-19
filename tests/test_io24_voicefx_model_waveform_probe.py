#!/usr/bin/env python3
"""Hardware-free contracts for the remaining VoiceFX model proof."""

import importlib
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _directory in (ROOT, ROOT / "re"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

probe = importlib.import_module("io24_voicefx_model_waveform_probe")


def _spectral_stage(magnitudes, burst=-20.0, gap=-50.0, reference=-22.0):
    magnitudes = np.asarray(magnitudes, dtype=np.float64)
    return {
        "_freqs": np.geomspace(60.0, 12000.0, magnitudes.size),
        "_mags": magnitudes,
        "burst_rms_dbfs": burst,
        "gap_rms_dbfs": gap,
        "reference_burst_rms_dbfs": reference,
        "reference_gap_rms_dbfs": -43.0,
        "reference_bursts_found": 5,
        "dominant_partial": {"hz": 800.0, "dbfs": -20.0},
    }


class ProfileAndSequenceTests(unittest.TestCase):
    def test_profiles_cover_every_model_except_already_proven_delay(self):
        self.assertEqual(tuple(probe.MODEL_PROFILES), (
            "transformer", "detuner", "vocoder", "ringmod", "filters"))
        for model, kwargs in probe.MODEL_PROFILES.items():
            self.assertNotIn("on", kwargs)
            builder = getattr(probe.io24_fx, "set_fx_" + model)
            self.assertTrue(builder(on=False, **kwargs))
            self.assertTrue(builder(on=True, **kwargs))

    def test_sequence_materializes_each_model_then_toggles_it_twice(self):
        class Device:
            def __init__(self):
                self.calls = []

            def set_fx(self, model, **kwargs):
                self.calls.append(("set_fx", model, dict(kwargs)))

            def set_reverb(self, **kwargs):
                self.calls.append(("set_reverb", dict(kwargs)))

        device = Device()
        observed = []

        def capture(label, *_args, **_kwargs):
            observed.append(label)
            return _spectral_stage(np.ones(96))

        stages = probe.run_sequence(
            device, Path("/unused"), Path("/unused/stimulus.wav"), "sink",
            capture=capture, settle=lambda _seconds: None)

        self.assertEqual(set(stages), set(observed))
        for model, profile in probe.MODEL_PROFILES.items():
            calls = [call for call in device.calls
                     if call[0] == "set_fx" and call[1] == model]
            self.assertEqual([call[2]["on"] for call in calls],
                             [False, True, False, True, False])
            for call in calls:
                self.assertEqual({key: call[2][key] for key in profile},
                                 profile)
            self.assertEqual(
                [name for name in observed if name.startswith(model + "_")],
                [model + "_off_0", model + "_on_1", model + "_off_1",
                 model + "_on_2", model + "_off_2"])


class SpectralClassifierTests(unittest.TestCase):
    def test_shape_distance_rejects_gain_only_and_detects_tilt(self):
        base = np.geomspace(1.0, 0.01, 96)
        gain_only = base * 3.0
        tilted = base * np.geomspace(0.08, 8.0, base.size)
        off = _spectral_stage(base)
        gain = _spectral_stage(gain_only)
        changed = _spectral_stage(tilted)
        self.assertLess(probe.spectral_shape_distance(off, gain), 1e-8)
        self.assertGreater(probe.spectral_shape_distance(off, changed), 4.0)

    def test_two_cycle_shape_vote_requires_repeatability_over_off_drift(self):
        base = np.geomspace(1.0, 0.01, 96)
        tiny_drift = base * np.geomspace(0.98, 1.02, base.size)
        changed = base * np.geomspace(0.1, 6.0, base.size)
        result = probe.classify_shape_repeatability(
            [_spectral_stage(base), _spectral_stage(tiny_drift),
             _spectral_stage(base)],
            [_spectral_stage(changed), _spectral_stage(changed * 1.8)])
        self.assertTrue(result["detected"])
        self.assertTrue(result["cycle_1"]["detected"])
        self.assertTrue(result["cycle_2"]["detected"])

        one_cycle = probe.classify_shape_repeatability(
            [_spectral_stage(base), _spectral_stage(tiny_drift),
             _spectral_stage(base)],
            [_spectral_stage(changed), _spectral_stage(base * 2.0)])
        self.assertFalse(one_cycle["detected"])

    def test_detuner_signature_accepts_two_shifted_tones_despite_broadband_rise(self):
        freqs = np.arange(0.0, 2000.25, 0.25)
        off_mags = np.full(freqs.size, 10.0 ** (-70.0 / 20.0))
        on_mags = np.full(freqs.size, 10.0 ** (-52.0 / 20.0))
        for source_hz in probe.shared.STIMULUS_TONES:
            off_mags[np.argmin(np.abs(freqs - source_hz))] = 0.1
            shifted = source_hz * probe.shared.DETUNE_RATIO
            on_mags[np.argmin(np.abs(freqs - shifted))] = 0.08
        off = {"_freqs": freqs, "_mags": off_mags}
        on = {"_freqs": freqs, "_mags": on_mags}
        result = probe.classify_detuner_signature(off, on)
        self.assertTrue(result["detected"])
        self.assertEqual(len(result["tones"]), 2)
        self.assertTrue(all(row["detected"] for row in result["tones"]))

        wrong = dict(on, _mags=on_mags.copy())
        for source_hz in probe.shared.STIMULUS_TONES:
            shifted = source_hz * probe.shared.DETUNE_RATIO
            wrong["_mags"][np.argmin(np.abs(freqs - shifted))] = on_mags[0]
        self.assertFalse(probe.classify_detuner_signature(off, wrong)["detected"])


if __name__ == "__main__":
    unittest.main()
