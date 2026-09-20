#!/usr/bin/env python3
"""Hardware-free contracts for the guarded UC Multiband live probe."""

import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
import wave

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "re" / "io24_uc_multiband_live_probe.py"
SPEC = importlib.util.spec_from_file_location(
    "io24_uc_multiband_live_probe", SCRIPT)
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def _write_capture(path, tone_dbfs, peak_dbfs=None, input_channel=2):
    frames = PROBE.RATE * PROBE.CAPTURE_SECONDS
    audio = np.zeros((frames, PROBE.CAPTURE_CHANNELS), dtype=np.float64)
    start, stop = int(1.1 * PROBE.RATE), int(3.6 * PROBE.RATE)
    amplitude = math.sqrt(2.0) * 10.0 ** (tone_dbfs / 20.0)
    phase = np.arange(stop - start, dtype=np.float64)
    index = PROBE.INPUT_CHANNELS[input_channel]
    audio[start:stop, index] = (
        amplitude * np.sin(2.0 * math.pi * PROBE.TONE_HZ * phase / PROBE.RATE))
    if peak_dbfs is not None:
        audio[10, index] = 10.0 ** (peak_dbfs / 20.0)
    pcm = np.rint(np.clip(audio, -1.0, 1.0) * (2**31 - 1)).astype("<i4")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(PROBE.CAPTURE_CHANNELS)
        handle.setsampwidth(4)
        handle.setframerate(PROBE.RATE)
        handle.writeframes(pcm.tobytes())


def _shadow():
    def entry(fn, **kwargs):
        return {"fn": fn, "kwargs": kwargs}

    return {
        "set_send_db#source=line/ch1,bus=main":
            entry("set_send_db", source="line/ch1", bus="main", gain_db=-2.0),
        "set_send_assigned#source=line/ch1,bus=main":
            entry("set_send_assigned", source="line/ch1", bus="main", on=True),
        "set_send_db#source=line/ch2,bus=main":
            entry("set_send_db", source="line/ch2", bus="main", gain_db=0.0),
        "set_send_assigned#source=line/ch2,bus=main":
            entry("set_send_assigned", source="line/ch2", bus="main", on=True),
        "set_send_db#source=fxreturn/ch1,bus=main":
            entry("set_send_db", source="fxreturn/ch1", bus="main", gain_db=-3.0),
        "set_send_assigned#source=fxreturn/ch1,bus=main":
            entry("set_send_assigned", source="fxreturn/ch1", bus="main", on=False),
        "set_send_db#source=return/ch1,bus=main":
            entry("set_send_db", source="return/ch1", bus="main", gain_db=-1.0),
    }


class UcMultibandLiveProbeTests(unittest.TestCase):
    def test_three_channel_raw_capture_is_wrapped_after_exact_byte_count(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            raw = directory / "capture.wav.raw"
            target = directory / "capture.wav"
            frames = PROBE.RATE * PROBE.CAPTURE_SECONDS
            samples = np.arange(
                frames * PROBE.CAPTURE_CHANNELS, dtype="<i4")
            raw.write_bytes(samples.tobytes())

            PROBE._wrap_raw_capture(raw, target)

            self.assertFalse(raw.exists())
            with wave.open(str(target), "rb") as handle:
                self.assertEqual(handle.getnchannels(), PROBE.CAPTURE_CHANNELS)
                self.assertEqual(handle.getsampwidth(), 4)
                self.assertEqual(handle.getframerate(), PROBE.RATE)
                self.assertEqual(handle.getnframes(), frames)

    def test_each_treatment_selects_one_exact_model_on_all_four_bands(self):
        for model in PROBE.MODELS:
            with self.subTest(model=model):
                state = PROBE.model_state(model)
                self.assertEqual(
                    [state["bands"][band]["type"] for band in PROBE.io24_mbc.BANDS],
                    [model] * 4)
                graph = PROBE.io24_mbc.build_graph(
                    state["xovers"], True, state=state,
                    sample_rate=PROBE.RATE, plugin="/tmp/probe")
                compressors = [node for node in graph["nodes"]
                               if node.get("label") == "io24_uc_comp"]
                self.assertEqual(len(compressors), 4)

    def test_route_prestate_requires_every_touched_write_only_control(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shadow.json"
            path.write_text(json.dumps(_shadow()), encoding="utf-8")
            state = PROBE.load_route_prestate(path)
            self.assertEqual(state["line_ch1_main"],
                             {"gain_db": -2.0, "assigned": True})
            self.assertEqual(state["line_ch2_main"],
                             {"gain_db": 0.0, "assigned": True})
            self.assertEqual(state["fxreturn_ch1_main"],
                             {"gain_db": -3.0, "assigned": False})
            self.assertEqual(state["return_ch1_main"], {"gain_db": -1.0})

            broken = _shadow()
            broken.pop("set_send_assigned#source=line/ch2,bus=main")
            path.write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaisesRegex(PROBE.ProbeError, "missing route prestate"):
                PROBE.load_route_prestate(path)

    def test_direct_positive_control_selects_the_input_with_the_tone(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "direct.wav"
            _write_capture(path, -30.0, input_channel=1)

            result = PROBE.select_loopback_input(path)

        self.assertEqual(result["selected_input"], 1)
        self.assertGreater(
            result["channels"]["1"]["input_tone_rms_dbfs"], -31.0)
        self.assertIsNone(
            result["channels"]["2"]["input_tone_rms_dbfs"])

    def test_expected_signed_tone_deltas_accept_all_three_models(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            levels = {"baseline_before": -30.0, "standard": -37.0,
                      "tube": -40.0, "fet": -22.0,
                      "baseline_after": -30.2}
            paths = {}
            for name, level in levels.items():
                paths[name] = directory / (name + ".wav")
                _write_capture(paths[name], level)

            result = PROBE.analyze_captures(paths)

        self.assertEqual(result["status"], "MULTIBAND_AUDIBLE_ALL_MODELS")
        self.assertEqual(set(result["models_passed"]), set(PROBE.MODELS))
        for model in PROBE.MODELS:
            delta = result["cases"][model]["delta_db"]
            self.assertGreaterEqual(abs(delta), PROBE.MIN_MODEL_CHANGE_DB)
            self.assertGreater(
                delta * PROBE.EXPECTED_MODEL_DELTA_SIGN[model], 0.0)

    def test_fet_change_in_the_wrong_direction_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            levels = {"baseline_before": -30.0, "standard": -37.0,
                      "tube": -40.0, "fet": -38.0,
                      "baseline_after": -30.2}
            paths = {}
            for name, level in levels.items():
                paths[name] = directory / (name + ".wav")
                _write_capture(paths[name], level)

            result = PROBE.analyze_captures(paths)

        self.assertEqual(result["status"],
                         "MULTIBAND_AUDIBILITY_INCONCLUSIVE")
        self.assertIn("fet_delta_wrong_direction", result["reasons"])

    def test_uc_expected_signed_changes_accept_attempt_six_transfer(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            levels = {
                "baseline_before": -23.84096389216709,
                "standard": -24.71403739947987,
                "tube": -28.813114906947025,
                "fet": -22.336950097840486,
                "baseline_after": -23.79713158847068,
            }
            paths = {}
            for name, level in levels.items():
                paths[name] = directory / (name + ".wav")
                _write_capture(paths[name], level, input_channel=1)

            result = PROBE.analyze_captures(paths, input_channel=1)

        self.assertEqual(result["status"], "MULTIBAND_AUDIBLE_ALL_MODELS")
        self.assertEqual(set(result["models_passed"]), set(PROBE.MODELS))
        self.assertEqual(result["reasons"], [])

    def test_missing_physical_loopback_signal_blocks_classification(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            paths = {}
            for name in PROBE.CASES:
                paths[name] = directory / (name + ".wav")
                _write_capture(paths[name], -100.0)

            result = PROBE.analyze_captures(paths)

        self.assertEqual(result["status"], "BLOCKED_NO_LOOPBACK_SIGNAL")
        self.assertIn("baseline_below_detection_floor", result["reasons"])

    def test_capture_at_minus_six_dbfs_or_hotter_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            paths = {}
            for name in PROBE.CASES:
                paths[name] = directory / (name + ".wav")
                _write_capture(paths[name], -30.0,
                               peak_dbfs=(
                                   -5.0 if name == "baseline_before" else None))

            with self.assertRaisesRegex(PROBE.ProbeError, "-6 dBFS"):
                PROBE.analyze_captures(paths)


if __name__ == "__main__":
    unittest.main()
