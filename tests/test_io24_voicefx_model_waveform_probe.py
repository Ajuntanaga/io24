#!/usr/bin/env python3
"""Hardware-free contracts for the remaining VoiceFX model proof."""

import importlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

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
        self.assertFalse(any(call[0] == "set_fx" and call[1] == "delay"
                             for call in device.calls))
        self.assertEqual(device.calls[0], (
            "set_fx", "filters",
            dict(on=False, **probe.MODEL_PROFILES["filters"])))
        self.assertEqual(device.calls[1], (
            "set_fx", "transformer",
            dict(on=False, **probe.MODEL_PROFILES["transformer"])))
        for model, profile in probe.MODEL_PROFILES.items():
            calls = [call for call in device.calls
                     if call[0] == "set_fx" and call[1] == model]
            expected_power = [False, True, False, True, False]
            if model == "filters":
                expected_power.insert(0, False)
            self.assertEqual([call[2]["on"] for call in calls],
                             expected_power)
            for call in calls:
                self.assertEqual({key: call[2][key] for key in profile},
                                 profile)
            self.assertEqual(
                [name for name in observed if name.startswith(model + "_")],
                [model + "_off_0", model + "_on_1", model + "_off_1",
                 model + "_on_2", model + "_off_2"])

    def test_transformer_handoff_arms_source_before_each_target_assignment(self):
        class Device:
            def __init__(self):
                self.channel = 1
                self.calls = []

            def set_voicefx_channel(self, channel):
                self.channel = channel
                self.calls.append(("assign", channel))

            def set_fx(self, model, **kwargs):
                self.calls.append(("set_fx", model, dict(kwargs)))

            def set_reverb(self, **kwargs):
                self.calls.append(("set_reverb", dict(kwargs)))

            def read_params(self):
                return {
                    "flags": 0,
                    "input1SlotIndex": 0, "input2SlotIndex": 2,
                    "input1ProcessingChannel": (
                        0 if self.channel == 1 else 1),
                    "input2ProcessingChannel": (
                        1 if self.channel == 1 else 0),
                    "input1Gain": 0.0, "input2Gain": 0.0,
                    "input1PhantomPower": False,
                    "input2PhantomPower": False,
                    "hpVolume": 0.5, "mainVolume": 0.5,
                    "monitorMix": 0.0,
                }

        device = Device()
        observed = []

        def capture(label, *_args, **_kwargs):
            observed.append(label)
            return _spectral_stage(np.ones(96))

        probe.run_transformer_handoff_sequence(
            device, Path("/unused"), Path("/unused/stimulus.wav"), "sink",
            input_channel=2, capture=capture, settle=lambda _seconds: None)

        self.assertEqual(
            [call for call in device.calls if call[0] == "assign"],
            [("assign", 2), ("assign", 1), ("assign", 2),
             ("assign", 1), ("assign", 2)])
        armed = [call for call in device.calls
                 if call[0] == "set_fx" and call[2]["on"]]
        self.assertEqual(len(armed), 2)
        self.assertEqual(observed, [
            "control_off", "control_reverb", "control_off_after",
            "transformer_handoff_on_1", "transformer_handoff_off_1",
            "transformer_handoff_on_2", "transformer_handoff_off_2",
        ])
        self.assertEqual(
            probe.plan(2, transformer_handoff=True)["mode"],
            "transformer_model_before_assignment")

    def test_assigned_delay_always_supplies_the_verified_safe_rate(self):
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

        probe.run_assigned_delay_sequence(
            device, Path("/unused"), Path("/unused/stimulus.wav"), "sink",
            input_channel=2, capture=capture, settle=lambda _seconds: None)

        delay_calls = [call for call in device.calls
                       if call[0] == "set_fx"]
        self.assertEqual([call[2]["on"] for call in delay_calls],
                         [False, True, False, True, False])
        self.assertTrue(all(call[1] == "delay" for call in delay_calls))
        self.assertTrue(all(call[2]["fs"] == 48000.0
                            for call in delay_calls))
        self.assertEqual(
            probe.plan(2, delay_only=True)["mode"], "assigned_delay_48khz")
        with self.assertRaises(probe.ModelProbeError):
            probe.plan(2, transformer_handoff=True, delay_only=True)

    def test_transformer_selector_replay_uses_firmware_deferred_order(self):
        class Device:
            def __init__(self):
                self.calls = []

            def send_fx(self, frames):
                if isinstance(frames, (bytes, bytearray)):
                    frames = [frames]
                frames = tuple(bytes(frame) for frame in frames)
                self.calls.append(frames)
                return len(frames)

        device = Device()
        sleeps = []
        profile = probe.MODEL_PROFILES["transformer"]
        written = probe.materialize_transformer_with_selector_replay(
            device, on=True, profile=profile, settle=sleeps.append)

        expected = tuple(probe.io24_fx.set_fx_transformer(
            on=True, **profile))
        self.assertEqual(device.calls, [expected[:1], expected])
        self.assertEqual(sleeps, [probe.TRANSFORMER_REBUILD_SETTLE_S])
        self.assertEqual(written, len(expected) + 1)
        self.assertEqual(device._voicefx_selected_model, "transformer")
        self.assertEqual(device._voicefx_selected_state,
                         dict(on=True, **profile))

    def test_selector_replay_sequence_rebuilds_twice_and_turns_off(self):
        class Device:
            def __init__(self):
                self.calls = []

            def set_fx(self, model, **kwargs):
                self.calls.append(("set_fx", model, dict(kwargs)))

            def send_fx(self, frames):
                if isinstance(frames, (bytes, bytearray)):
                    frames = [frames]
                frames = tuple(bytes(frame) for frame in frames)
                self.calls.append(("send_fx", frames))
                return len(frames)

            def set_reverb(self, **kwargs):
                self.calls.append(("set_reverb", dict(kwargs)))

        device = Device()
        observed = []
        sleeps = []

        def capture(label, *_args, **_kwargs):
            observed.append(label)
            return _spectral_stage(np.ones(96))

        probe.run_transformer_selector_replay_sequence(
            device, Path("/unused"), Path("/unused/stimulus.wav"), "sink",
            input_channel=2, capture=capture,
            settle=lambda _seconds: None,
            rebuild_settle=sleeps.append)

        full = tuple(probe.io24_fx.set_fx_transformer(
            on=True, **probe.MODEL_PROFILES["transformer"]))
        replay_sends = [call[1] for call in device.calls
                        if call[0] == "send_fx"]
        self.assertEqual(replay_sends, [full[:1], full, full[:1], full])
        self.assertEqual(sleeps, [probe.TRANSFORMER_REBUILD_SETTLE_S] * 2)
        self.assertEqual(observed, [
            "control_off", "control_reverb", "control_off_after",
            "transformer_selector_replay_on_1",
            "transformer_selector_replay_off_1",
            "transformer_selector_replay_on_2",
            "transformer_selector_replay_off_2",
        ])
        self.assertEqual(
            probe.plan(2, selector_replay=True)["mode"],
            "transformer_deferred_selector_replay")


class AssignmentSafetyTests(unittest.TestCase):
    def test_processing_permutation_decodes_both_physical_inputs(self):
        self.assertEqual(probe.voicefx_assignment({
            "input1_processing_channel": 0,
            "input2_processing_channel": 1,
        }), 1)
        self.assertEqual(probe.voicefx_assignment({
            "input1_processing_channel": 1,
            "input2_processing_channel": 0,
        }), 2)
        with self.assertRaises(probe.ModelProbeError):
            probe.voicefx_assignment({
                "input1_processing_channel": 1,
                "input2_processing_channel": 1,
            })

    def test_assignment_guards_accept_input2_without_requiring_identity(self):
        state = {
            "input1_phantom": False, "input2_phantom": False,
            "channel_linked": False,
            "input1_processing_channel": 1,
            "input2_processing_channel": 0,
            "input2_processing_enabled": True,
        }
        probe.assert_assignment_guards(state, 2)
        plan = probe.plan(input_channel=2)
        self.assertNotIn("processingChannel", plan["never_written"])
        self.assertIn("assign Voice FX to Input 2 before model state",
                      plan["processing_assignment"])

    def test_pipewire_rate_is_parsed_and_missing_rate_fails_closed(self):
        def runner(_argv, **_kwargs):
            return SimpleNamespace(
                returncode=0,
                stdout="update: id:0 key:'clock.rate' value:'48000' type:''\n",
                stderr="")

        self.assertEqual(probe.pipewire_rate(runner=runner), 48000)

        def missing(_argv, **_kwargs):
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with self.assertRaises(probe.ModelProbeError):
            probe.pipewire_rate(runner=missing)

    def test_assignment_uses_production_method_and_checks_readback(self):
        class Device:
            def __init__(self):
                self.channel = 1

            def set_voicefx_channel(self, channel):
                self.channel = channel

            def read_params(self):
                return {
                    "flags": 0,
                    "input1SlotIndex": 0, "input2SlotIndex": 2,
                    "input1ProcessingChannel": 0 if self.channel == 1 else 1,
                    "input2ProcessingChannel": 1 if self.channel == 1 else 0,
                    "input1Gain": 0.0, "input2Gain": 0.0,
                    "input1PhantomPower": False,
                    "input2PhantomPower": False,
                    "hpVolume": 0.5, "mainVolume": 0.5,
                    "monitorMix": 0.0,
                }

        device = Device()
        state = probe.assign_and_verify(device, 2)
        self.assertEqual(probe.voicefx_assignment(state), 2)


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

    def test_transformer_handoff_classifier_requires_repeatable_shape(self):
        base = np.geomspace(1.0, 0.01, 96)
        changed = base * np.geomspace(0.1, 6.0, base.size)
        off = _spectral_stage(base)
        reverb = _spectral_stage(base, gap=-35.0)
        stages = {
            "control_off": off,
            "control_reverb": reverb,
            "control_off_after": _spectral_stage(base),
            "transformer_handoff_on_1": _spectral_stage(changed),
            "transformer_handoff_off_1": _spectral_stage(base),
            "transformer_handoff_on_2": _spectral_stage(changed * 1.5),
            "transformer_handoff_off_2": _spectral_stage(base),
        }
        result = probe.classify_transformer_handoff(stages, input_channel=2)
        self.assertTrue(result["run_valid"])
        self.assertEqual(result["status"],
                         "TRANSFORMER_HANDOFF_PROCESSING_DETECTED")
        self.assertTrue(result["transformer"]["processing_detected"])


if __name__ == "__main__":
    unittest.main()
