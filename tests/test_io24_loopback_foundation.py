import importlib.util
import math
import os
import tempfile
import unittest
import wave
import struct

import numpy as np


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "io24_loopback_foundation.py")
SPEC = importlib.util.spec_from_file_location("io24_loopback_foundation", SCRIPT)
FOUNDATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FOUNDATION)


def _state(**overrides):
    value = {
        "flags_word": 0x181,
        "input1_muted": False,
        "input2_muted": False,
        "input1_preset_enabled": True,
        "input2_preset_enabled": True,
        "channel_linked": False,
        "input1_slot_index": 0,
        "input2_slot_index": 2,
        "input1_processing_channel": 0,
        "input2_processing_channel": 1,
        "input1_gain_db": 35.0,
        "input2_gain_db": 20.0,
        "input1_phantom": False,
        "input2_phantom": False,
        "hp_volume": 0.5,
        "main_volume": 0.05,
        "monitor_mix": 0.0,
    }
    value.update(overrides)
    return value


def _write_capture(path, *, clipped=False, correlated=True,
                   routed_channel=3, leakage_channel=None):
    rng = np.random.default_rng(24)
    frames = FOUNDATION.RATE * FOUNDATION.CAPTURE_SECONDS
    audio = np.zeros((frames, FOUNDATION.CHANNELS), dtype=np.float64)
    start, stop, lag = 48000, 144000, 17
    source = rng.normal(0.0, 10 ** (-30 / 20), stop - start)
    audio[start:stop, 1] = source
    if correlated:
        audio[start + lag:stop + lag, routed_channel] = source * 0.7
        if leakage_channel is not None:
            audio[start + lag:stop + lag, leakage_channel] = source * 0.35
    else:
        audio[start:stop, routed_channel] = rng.normal(
            0.0, 10 ** (-30 / 20), stop - start)
    if clipped:
        audio[100, 0] = 0.51
    pcm = np.rint(audio * (2**31 - 1)).astype("<i4")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(FOUNDATION.CHANNELS)
        handle.setsampwidth(4)
        handle.setframerate(FOUNDATION.RATE)
        handle.writeframes(pcm.tobytes())


class LoopbackFoundationTests(unittest.TestCase):
    def test_audited_setp_services_input_endpoint_after_exact_write(self):
        class Output:
            def __init__(self):
                self.frames = []

            def write(self, frame, timeout):
                self.frames.append((bytes(frame), timeout))
                return len(frame)

        class Input:
            def __init__(self):
                self.reads = 0

            def read(self, _size, timeout):
                self.reads += 1
                self.timeout = timeout
                return struct.pack("<H", 12) + b"\x01\x01\x01\0\0\0" + b"done"

        device = object.__new__(FOUNDATION.AuditedIo24)
        device._uid = 0
        device.transport_log = []
        device.ep_out = Output()
        device.ep_in = Input()
        payload = struct.pack("<IIII", FOUNDATION.io24.SETP,
                              FOUNDATION.io24.APPL, 0, 0x50617269)

        result = device._exec(payload, wait=0.01)

        self.assertEqual(result, b"done")
        self.assertEqual(device.ep_in.reads, 1)
        self.assertEqual(device.ep_in.timeout, 400)
        self.assertEqual(device.ep_out.frames[0][1], 2000)
        self.assertEqual(device.transport_log[0]["transport"],
                         "USB_WRITE_EXACT_LENGTH")
        self.assertEqual(device.transport_log[0]["response_frame_bytes"], 12)

    def test_audited_setp_rejects_short_usb_write(self):
        class Output:
            @staticmethod
            def write(frame, timeout):
                return len(frame) - 1

        device = object.__new__(FOUNDATION.AuditedIo24)
        device._uid = 0
        device.transport_log = []
        device.ep_out = Output()
        payload = struct.pack("<IIII", FOUNDATION.io24.SETP,
                              FOUNDATION.io24.APPL, 0, 0x50617269)
        with self.assertRaisesRegex(FOUNDATION.FoundationError, "short USB write"):
            device._exec(payload, wait=0.01)

    def test_correlated_input2_to_mix_a_capture_is_calibrated(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "capture.wav")
            _write_capture(path)

            result = FOUNDATION.analyze_capture(FOUNDATION.Path(path))

        self.assertEqual(result["status"], "CALIBRATED")
        self.assertEqual(result["frozen_mix_a_capture_channel"], 4)
        self.assertEqual(
            [row["capture_channel"]
             for row in result["capture_channel_correlations"]],
            [1, 2, 3, 4, 5, 6],
        )
        reference = result["capture_channel_correlations"][1]
        self.assertEqual(reference["role"], "physical_input2_reference")
        best = max(result["mix_a_candidates"],
                   key=lambda item: item["absolute_correlation"])
        self.assertGreater(best["absolute_correlation"], 0.99)
        self.assertEqual(best["lag_samples"], 17)
        self.assertLess(result["maximum_peak_dbfs"], -6.0)

    def test_uncorrelated_mix_a_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "capture.wav")
            _write_capture(path, correlated=False)

            result = FOUNDATION.analyze_capture(FOUNDATION.Path(path))

        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertIn("no_correlated_mix_a_channel", result["reasons"])

    def test_correlated_route_outside_usb_3_4_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "capture.wav")
            _write_capture(path, routed_channel=5)

            result = FOUNDATION.analyze_capture(FOUNDATION.Path(path))

        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertIn("mix_a_channel_outside_expected_pair", result["reasons"])
        self.assertIsNone(result["frozen_mix_a_capture_channel"])

    def test_correlated_leakage_outside_usb_3_4_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "capture.wav")
            _write_capture(path, routed_channel=3, leakage_channel=5)

            result = FOUNDATION.analyze_capture(FOUNDATION.Path(path))

        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertIn("mix_a_leakage_outside_expected_pair", result["reasons"])

    def test_minus_six_dbfs_peak_limit_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "capture.wav")
            _write_capture(path, clipped=True)

            with self.assertRaisesRegex(FOUNDATION.FoundationError, "-6 dBFS"):
                FOUNDATION.analyze_capture(FOUNDATION.Path(path))

    def test_configuration_guard_requires_both_mutes_zero_gain_and_bypass(self):
        before = _state()
        valid = _state(input1_muted=True, input2_muted=True,
                       input2_gain_db=0.0, input2_preset_enabled=False)
        FOUNDATION._guard_configuration(before, valid)
        for invalid in (
            _state(input1_muted=False, input2_muted=True,
                   input2_gain_db=0.0, input2_preset_enabled=False),
            _state(input1_muted=True, input2_muted=True,
                   input2_gain_db=1.0, input2_preset_enabled=False),
            _state(input1_muted=True, input2_muted=True,
                   input2_gain_db=0.0, input2_preset_enabled=True),
        ):
            with self.assertRaises(FOUNDATION.FoundationError):
                FOUNDATION._guard_configuration(before, invalid)

    def test_ready_guard_protects_slot_and_processing_namespace(self):
        before = _state()
        valid = _state(input1_muted=True, input2_muted=False,
                       input2_gain_db=0.0, input2_preset_enabled=False)
        FOUNDATION._guard_ready(before, valid)
        with self.assertRaisesRegex(FOUNDATION.FoundationError,
                                    "protected field input2_slot_index"):
            FOUNDATION._guard_ready(
                before, dict(valid, input2_slot_index=3))

    def test_restoration_comparison_is_exact_not_tolerant(self):
        before = _state()
        exact = FOUNDATION._guard_restored(before, dict(before))
        self.assertTrue(all(item["equal"] for item in exact.values()))
        changed = FOUNDATION._guard_restored(
            before, dict(before, input2_gain_db=math.nextafter(20.0, 21.0)))
        self.assertFalse(changed["input2_gain_db"]["equal"])


if __name__ == "__main__":
    unittest.main()
