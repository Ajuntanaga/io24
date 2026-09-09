import importlib.util
import os
import tempfile
import unittest
import wave

import numpy as np


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "cp34_gate_transition_audio.py")
ANALYZER = None
if os.path.isfile(SCRIPT):
    SPEC = importlib.util.spec_from_file_location("cp34_gate_transition_audio", SCRIPT)
    ANALYZER = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(ANALYZER)


EVENTS = [
    {"event": "baseline_confirmed", "capture_offset_seconds": 0.5},
    {"event": "channel2_slot2_confirmed", "capture_offset_seconds": 1.0},
    {"event": "link_on_confirmed", "capture_offset_seconds": 2.5},
    {"event": "channel2_slot3_confirmed", "capture_offset_seconds": 3.0},
    {"event": "factory_gate_on_sent", "capture_offset_seconds": 3.2},
    {"event": "factory_gate_off_sent", "capture_offset_seconds": 5.0},
    {"event": "factory_gate_restored", "capture_offset_seconds": 9.0},
    {"event": "link_off_confirmed", "capture_offset_seconds": 10.0},
]


def _write_capture(path, *, mode="echo150", rate=48000, channels=6):
    duration = 11.0
    frame_count = int(rate * duration)
    rng = np.random.default_rng(240904)
    source = rng.normal(0.0, 0.002, frame_count)
    audio = np.zeros((frame_count, channels), dtype=np.float64)
    if channels >= 2:
        audio[:, 1] = source

    if channels >= 6:
        on = slice(int(3.2 * rate), int(5.0 * rate))
        off = slice(int(5.0 * rate), int(9.0 * rate))
        output = 0.5 * source
        if mode == "echo150":
            lag = int(round(0.150 * rate))
            output[lag:] += 0.25 * source[:-lag]
            output[2 * lag:] += 0.0625 * source[:-2 * lag]
        elif mode == "echo173":
            lag = int(round(0.173 * rate))
            output[lag:] += 0.25 * source[:-lag]
        elif mode not in ("direct", "pregate", "clipped"):
            raise ValueError(mode)
        for channel in range(2, 6):
            audio[on, channel] = 0.005 * source[on]
            audio[off, channel] = output[off]
            if mode == "pregate":
                audio[on, channel] = output[on]
        if mode == "clipped":
            audio[int(6.0 * rate), 2] = 1.0

    pcm = np.round(np.clip(audio, -1.0, 1.0) * (2**31 - 1)).astype("<i4")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(4)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())


class GateTransitionAudioTests(unittest.TestCase):
    def _analyze(self, path, events=EVENTS):
        self.assertIsNotNone(ANALYZER, "gate-transition analyzer is missing")
        return ANALYZER.analyze_capture(path, events)

    def test_detects_repeatable_150ms_transfer_after_observable_gate_open(self):
        """Catches an analyzer that misses the exact Slap Echo cadence."""
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "positive.wav")
            _write_capture(path, mode="echo150")

            result = self._analyze(path)

        self.assertEqual("VALID", result["status"])
        self.assertEqual("DOWNSTREAM_GATE_OBSERVABLE", result["capture_tap"])
        self.assertEqual("REPEAT_150MS_SIGNATURE", result["repeat_result"])
        self.assertEqual("WAVEFORM_EVIDENCE_MODEL_IDENTITY_UNRESOLVED",
                         result["effect_conclusion"])
        for channel in result["monitor_channels"]:
            self.assertGreater(channel["gate_delta_db"], 12.0)
            self.assertGreater(channel["model_correlation"], 0.95)
            self.assertAlmostEqual(0.5, channel["lag150_over_direct"], places=2)

    def test_reports_no_repeat_for_direct_only_downstream_gate_path(self):
        """Catches a classifier that calls any gate delta a delay."""
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "direct.wav")
            _write_capture(path, mode="direct")

            result = self._analyze(path)

        self.assertEqual("DOWNSTREAM_GATE_OBSERVABLE", result["capture_tap"])
        self.assertEqual("NO_REPEAT_DOWNSTREAM_GATE_OFF", result["repeat_result"])
        self.assertEqual("LINKED_PATH_NEGATIVE_STORAGE_UNRESOLVED",
                         result["effect_conclusion"])

    def test_refuses_effect_conclusion_when_capture_tap_is_pre_gate(self):
        """Catches a negative verdict from a bus that cannot observe the gate."""
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "pregate.wav")
            _write_capture(path, mode="pregate")

            result = self._analyze(path)

        self.assertEqual("CAPTURE_TAP_NOT_GATE_OBSERVABLE", result["capture_tap"])
        self.assertEqual("UNPROVED", result["repeat_result"])
        self.assertEqual("UNPROVED_CAPTURE_TAP", result["effect_conclusion"])

    def test_173ms_echo_does_not_satisfy_150ms_signature(self):
        """Catches cadence tolerance wide enough to mislabel another delay."""
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "echo173.wav")
            _write_capture(path, mode="echo173")

            result = self._analyze(path)

        self.assertEqual("DOWNSTREAM_GATE_OBSERVABLE", result["capture_tap"])
        self.assertEqual("NO_REPEAT_DOWNSTREAM_GATE_OFF", result["repeat_result"])

    def test_invalid_format_events_and_clipping_fail_closed(self):
        """Catches analysis of malformed, mistimed, or clipped evidence."""
        cases = []
        with tempfile.TemporaryDirectory() as temp:
            wrong_channels = os.path.join(temp, "two.wav")
            wrong_rate = os.path.join(temp, "44100.wav")
            clipped = os.path.join(temp, "clipped.wav")
            valid = os.path.join(temp, "valid.wav")
            _write_capture(wrong_channels, channels=2)
            _write_capture(wrong_rate, rate=44100)
            _write_capture(clipped, mode="clipped")
            _write_capture(valid, mode="direct")
            cases.extend([
                self._analyze(wrong_channels),
                self._analyze(wrong_rate),
                self._analyze(clipped),
                self._analyze(valid, EVENTS[:-1]),
                self._analyze(valid, list(reversed(EVENTS))),
            ])

        self.assertTrue(all(case["status"] == "INVALID_CAPTURE" for case in cases))
        self.assertTrue(all(case["repeat_result"] == "UNPROVED" for case in cases))
        self.assertTrue(all(case["reasons"] for case in cases))


if __name__ == "__main__":
    unittest.main()
