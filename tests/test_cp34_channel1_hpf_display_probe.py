#!/usr/bin/env python3
"""Hardware-free contract for the Channel-1 HPF display probe."""

import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "re" / "cp34_channel1_hpf_display_probe.py"
SPEC = importlib.util.spec_from_file_location(
    "cp34_channel1_hpf_display_probe_test", SCRIPT)
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class _Identity:
    serial_number = PROBE.EXPECTED_SERIAL
    bcdDevice = PROBE.EXPECTED_FIRMWARE_VERSION


class _FakeDevice:
    def __init__(self, shadow=False, params=None):
        self.dev = _Identity()
        self.calls = []
        self.closed = False
        self.params = params or {
            "flags": 0,
            "input1Gain": 30.0,
            "input2Gain": 24.287769317626953,
            "input1SlotIndex": 0,
            "input2SlotIndex": 2,
            "input1ProcessingChannel": 0,
            "input2ProcessingChannel": 1,
        }

    def read_params(self):
        self.calls.append(("read_params",))
        return copy.deepcopy(self.params)

    def set_highpass_freq(self, channel, hz):
        self.calls.append(("set_highpass_freq", channel, float(hz)))
        return b""

    def close(self):
        self.calls.append(("close",))
        self.closed = True


class Channel1HpfDisplayProbeTests(unittest.TestCase):
    def test_exact_human_paced_sequence_restores_main_without_slot_calls(self):
        device = _FakeDevice()
        ready = []

        result = PROBE.run_probe(
            lambda shadow=False: device,
            100,
            ready_fn=lambda: ready.append(True),
            observe_fn=lambda hz: "%g Hz" % hz,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"], "DISPLAY_OBSERVATIONS_CAPTURED")
        self.assertEqual(ready, [True])
        self.assertEqual(
            [call for call in device.calls if call[0] == "set_highpass_freq"],
            [("set_highpass_freq", 1, 40.0),
             ("set_highpass_freq", 1, 80.0),
             ("set_highpass_freq", 1, 160.0),
             ("set_highpass_freq", 1, 55.0),
             ("set_highpass_freq", 1, 24.0)],
        )
        self.assertFalse(any("preset" in call[0] or "slot" in call[0]
                             for call in device.calls))
        self.assertEqual(result["restore"],
                         "EXACT_24_HZ_BYPASS_WRITE_SENT")
        self.assertTrue(device.closed)

    def test_observer_failure_still_sends_exact_restore(self):
        device = _FakeDevice()

        def fail_observation(_hz):
            raise TimeoutError("no observer")

        result = PROBE.run_probe(
            lambda shadow=False: device,
            100,
            ready_fn=lambda: None,
            observe_fn=fail_observation,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"], "PROBE_FAILED")
        self.assertEqual(result["failed_stage"], "observe_40_hz")
        self.assertEqual(
            [call for call in device.calls if call[0] == "set_highpass_freq"],
            [("set_highpass_freq", 1, 40.0),
             ("set_highpass_freq", 1, 24.0)],
        )

    def test_main_identity_guard_blocks_before_any_write(self):
        for changed, expected in (
            ({"input1SlotIndex": 1}, "not on MAIN slot 0"),
            ({"flags": 1 << 5}, "MAIN is not enabled"),
            ({"flags": 1 << 12}, "stereo link must be off"),
            ({"input1Gain": 29.0}, "no longer matches MAIN"),
        ):
            with self.subTest(changed=changed):
                device = _FakeDevice()
                device.params.update(changed)
                result = PROBE.run_probe(
                    lambda shadow=False: device,
                    100,
                    ready_fn=lambda: self.fail("ready callback must not run"),
                    observe_fn=lambda _hz: self.fail("observer must not run"),
                    sleep_fn=lambda _seconds: None,
                )
                self.assertEqual(result["status"], "PROBE_FAILED")
                self.assertIn(expected, result["error"])
                self.assertFalse(any(call[0] == "set_highpass_freq"
                                     for call in device.calls))

    def test_battery_floor_blocks_before_device_open(self):
        opened = []
        result = PROBE.run_probe(
            lambda shadow=False: opened.append(True),
            10,
            ready_fn=lambda: None,
            observe_fn=lambda _hz: "",
        )

        self.assertEqual(result["status"], "BLOCKED_BATTERY")
        self.assertEqual(opened, [])

    def test_readable_state_change_is_reported_after_restore(self):
        device = _FakeDevice()

        def observe(hz):
            if hz == 55.0:
                device.params["input2SlotIndex"] = 3
            return str(hz)

        result = PROBE.run_probe(
            lambda shadow=False: device,
            100,
            ready_fn=lambda: None,
            observe_fn=observe,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"], "POST_GUARD_FAILED")
        self.assertIn("readable state changed", result["post_guard_error"])
        self.assertEqual(
            [call for call in device.calls if call[0] == "set_highpass_freq"][-1],
            ("set_highpass_freq", 1, 24.0),
        )


if __name__ == "__main__":
    unittest.main()
