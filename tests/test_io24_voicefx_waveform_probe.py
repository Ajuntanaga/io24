#!/usr/bin/env python3
"""Hardware-free contracts for the Main-L -> Input-2 VoiceFX proof."""

import importlib
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _directory in (ROOT, ROOT / "re"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

probe = importlib.import_module("io24_voicefx_waveform_probe")


def _shadow(path):
    calls = {}
    for source, bus, gain in (
            ("line/ch1", "main", 0.0),
            ("line/ch2", "main", 0.0),
            ("fxreturn/ch1", "main", 0.0),
            ("return/ch1", "main", 0.0),
            ("return/ch1", "mixa", 0.0),
            ("fxreturn/ch1", "mixa", -60.0)):
        key = "set_send_db#source=%s,bus=%s" % (source, bus)
        calls[key] = {"fn": "set_send_db", "kwargs": {
            "source": source, "bus": bus, "gain_db": gain}}
    calls["set_fx"] = {"fn": "set_fx", "kwargs": {
        "model": "delay", "on": True, "time_s": 0.25,
        "feedback": 1.0, "mix": 1.0}}
    calls["set_reverb"] = {"fn": "set_reverb", "kwargs": {
        "on": False, "size": 0.1, "mix": 0.0, "predelay": 0.02,
        "hp_freq": 200.0, "fs": 48000.0}}
    path.write_text(json.dumps(calls), encoding="utf-8")
    return path


class FakeDevice:
    def __init__(self):
        self.calls = []

    def set_mute(self, channel, on):
        self.calls.append(("set_mute", channel, on))

    def set_send_db(self, source, bus, gain_db):
        self.calls.append(("set_send_db", source, bus, gain_db))

    def set_gain(self, channel, gain_db):
        self.calls.append(("set_gain", channel, gain_db))

    def set_fx(self, model, **kwargs):
        self.calls.append(("set_fx", model, dict(kwargs)))

    def set_reverb(self, **kwargs):
        self.calls.append(("set_reverb", dict(kwargs)))


class ShadowAndSafetyTests(unittest.TestCase):
    def test_exact_prior_state_requires_every_route_that_will_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _shadow(Path(tmp) / "shadow.json")
            state = probe.load_exact_prior_state(path)
            self.assertEqual(state["routes"][("line/ch2", "main")], 0.0)
            data = json.loads(path.read_text(encoding="utf-8"))
            del data["set_send_db#source=fxreturn/ch1,bus=mixa"]
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(probe.WaveformProbeError):
                probe.load_exact_prior_state(path)

    def test_safe_path_mutes_input2_before_breaking_feedback(self):
        device = FakeDevice()
        probe.configure_safe_path(device, input_was_muted=False)
        self.assertEqual(device.calls[0], ("set_mute", 2, True))
        self.assertEqual(device.calls[1:3], [
            ("set_send_db", "line/ch2", "main", None),
            ("set_send_db", "fxreturn/ch1", "main", None),
        ])
        self.assertIn(("set_gain", 2, probe.TEST_INPUT2_GAIN_DB),
                      device.calls)
        self.assertEqual(device.calls[-1], ("set_mute", 2, False))
        self.assertLess(
            device.calls.index(("set_send_db", "line/ch2", "main", None)),
            device.calls.index(("set_send_db", "return/ch1", "main", 0.0)))

    def test_restoration_reopens_feedback_routes_only_while_input2_is_muted(self):
        with tempfile.TemporaryDirectory() as tmp:
            prior = probe.load_exact_prior_state(
                _shadow(Path(tmp) / "shadow.json"))
        device = FakeDevice()
        probe.restore_exact_state(device, prior, input_was_muted=False,
                                  input_gain_db=0.0)
        self.assertEqual(device.calls[0], ("set_mute", 2, True))
        self.assertEqual(device.calls[-1], ("set_mute", 2, False))
        unmute = len(device.calls) - 1
        for route in (("line/ch2", "main"), ("fxreturn/ch1", "main")):
            call = ("set_send_db", route[0], route[1], 0.0)
            self.assertLess(device.calls.index(call), unmute)
        gain_restore = device.calls.index(("set_gain", 2, 0.0))
        self.assertLess(gain_restore, device.calls.index(
            ("set_send_db", "fxreturn/ch1", "main", 0.0)))
        self.assertLess(gain_restore, device.calls.index(
            ("set_send_db", "line/ch2", "main", 0.0)))
        self.assertIn(("set_fx", "delay", {
            "on": True, "time_s": 0.25, "feedback": 1.0, "mix": 1.0}),
            device.calls)

    def test_guards_require_input2_processing_without_changing_it(self):
        good = {
            "input1_phantom": False, "input2_phantom": False,
            "channel_linked": False, "input1_processing_channel": 0,
            "input2_processing_channel": 1,
            "input2_processing_enabled": True,
        }
        probe.assert_input2_guards(good)
        bad = dict(good, input2_processing_enabled=False)
        with self.assertRaises(probe.WaveformProbeError):
            probe.assert_input2_guards(bad)

    def test_input1_path_changes_only_input1_gain_mute_and_feedback_leg(self):
        device = FakeDevice()
        probe.configure_safe_path(
            device, input_was_muted=False, input_channel=1)
        self.assertEqual(device.calls[0], ("set_mute", 1, True))
        self.assertEqual(device.calls[1],
                         ("set_send_db", "line/ch1", "main", None))
        self.assertIn(("set_gain", 1, probe.TEST_INPUT_GAIN_DB),
                      device.calls)
        self.assertEqual(device.calls[-1], ("set_mute", 1, False))
        self.assertNotIn(("set_gain", 2, probe.TEST_INPUT_GAIN_DB),
                         device.calls)
        self.assertNotIn(("set_send_db", "line/ch2", "main", None),
                         device.calls)

    def test_input1_shadow_and_plan_are_channel_specific(self):
        with tempfile.TemporaryDirectory() as tmp:
            prior = probe.load_exact_prior_state(
                _shadow(Path(tmp) / "shadow.json"), input_channel=1)
        self.assertIn(("line/ch1", "main"), prior["routes"])
        self.assertNotIn(("line/ch2", "main"), prior["routes"])
        plan = probe.plan(input_channel=1)
        self.assertEqual(plan["rig"], "Main Out L -> Input 1")
        self.assertIn("line/ch1 -> Main off", plan["pre_playback_order"])
        self.assertNotIn("line/ch2 -> Main off", plan["pre_playback_order"])

    def test_pipewire_sink_mute_is_detected_and_restored_by_exact_name(self):
        name = "alsa_output.usb-PreSonus_Revelator_IO_24_AB7C22200355-00.test"
        state = {"muted": True}
        calls = []

        def dump():
            return json.dumps([{
                "id": 151,
                "info": {
                    "props": {"node.name": name,
                              "media.class": "Audio/Sink"},
                    "params": {"Props": [{"mute": state["muted"],
                                            "softMute": state["muted"],
                                            "channelVolumes": [0.064] * 3}]},
                },
            }])

        def runner(argv, **_kwargs):
            calls.append(list(argv))
            if argv[0] == "pw-dump":
                return SimpleNamespace(returncode=0, stdout=dump(), stderr="")
            self.assertEqual(argv[:3], ["wpctl", "set-mute", "151"])
            state["muted"] = argv[3] == "1"
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        before = probe.resolve_playback_sink_state(runner=runner)
        self.assertTrue(before["muted"])
        unmuted = probe.set_playback_sink_mute(name, False, runner=runner)
        self.assertFalse(unmuted["muted"])
        restored = probe.set_playback_sink_mute(name, True, runner=runner)
        self.assertTrue(restored["muted"])
        self.assertIn(["wpctl", "set-mute", "151", "0"], calls)
        self.assertIn(["wpctl", "set-mute", "151", "1"], calls)


class AnalysisTests(unittest.TestCase):
    def _write_capture(self, path, reference, mixa):
        frames = np.zeros((reference.size, probe.CHANNELS), dtype=np.float64)
        frames[:, probe.INPUT2_REFERENCE_CHANNEL] = reference
        for channel in probe.MIX_A_CHANNELS:
            frames[:, channel] = mixa
        pcm = np.rint(np.clip(frames, -1.0, 1.0) * (2 ** 31 - 1)).astype("<i4")
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(probe.CHANNELS)
            handle.setsampwidth(4)
            handle.setframerate(probe.RATE)
            handle.writeframes(pcm.tobytes())
        return path

    def test_alignment_comes_from_input2_when_the_return_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            stimulus = probe.build_stimulus(tmp / "stimulus.wav")
            _rate, frames = probe.shared.read_capture(stimulus)
            reference = frames[:, 0]
            stage = probe.analyse_stage_from_input2(
                self._write_capture(tmp / "off.wav", reference,
                                    np.zeros(reference.size)))
        self.assertEqual(stage["reference_bursts_found"], probe.shared.CYCLES)
        self.assertLess(stage["gap_rms_dbfs"], -120.0)

    def test_post_dsp_reference_change_during_delay_is_a_voicefx_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            stimulus = probe.build_stimulus(tmp / "stimulus.wav")
            _rate, frames = probe.shared.read_capture(stimulus)
            reference = frames[:, 0]
            quiet = np.zeros(reference.size)

            def tailed(lag_s, gain, repeats):
                result = quiet.copy()
                for tap in range(1, repeats + 1):
                    lag = int(round(tap * lag_s * probe.RATE))
                    result[lag:] += reference[:-lag] * (gain ** tap)
                return result

            stages = {}
            for name, mixa in {
                    "control_off": quiet,
                    "control_reverb": tailed(0.013, 0.85, 60),
                    "control_off_after": quiet,
                    "delay_on_1": tailed(0.25, 0.7, 3),
                    "delay_off_1": quiet,
                    "delay_on_2": tailed(0.25, 0.7, 3),
                    "delay_off_2": quiet,
            }.items():
                path = self._write_capture(tmp / (name + ".wav"),
                                           reference, mixa)
                stages[name] = probe.analyse_stage_from_input2(path)
            # The io24 USB input send can be post-DSP.  Insert Delay then
            # changes the captured reference by design; only effect-off
            # reference stages can diagnose physical-source drift.
            for name in ("delay_on_1", "delay_on_2"):
                stages[name]["reference_burst_rms_dbfs"] -= 3.1
            verdict = probe.classify(stages)
        self.assertEqual(verdict["status"],
                         "VOICEFX_DELAY_PROCESSING_DETECTED")
        self.assertTrue(verdict["run_valid"])
        self.assertTrue(verdict["delay_repeatability"]["cycle_1"]["detected"])
        self.assertTrue(verdict["delay_repeatability"]["cycle_2"]["detected"])


if __name__ == "__main__":
    unittest.main()
