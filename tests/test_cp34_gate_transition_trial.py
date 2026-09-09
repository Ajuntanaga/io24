import importlib.util
import os
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "cp34_gate_transition_trial.py")
RUNNER = None
if os.path.isfile(SCRIPT):
    SPEC = importlib.util.spec_from_file_location("cp34_gate_transition_trial", SCRIPT)
    RUNNER = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(RUNNER)


class _UsbDevice:
    def __init__(self, serial):
        self.serial_number = serial
        self.bcdDevice = 0x0128


class _Device:
    def __init__(self, serial="AB7C22200355"):
        self.dev = _UsbDevice(serial)
        self.closed = False

    def close(self):
        self.closed = True


class _Recorder:
    def __init__(self, path, *, early_exit=False, returncode=0):
        self.path = path
        self.early_exit = early_exit
        self.returncode = returncode if early_exit else None
        self.communicated = False

    def start(self):
        if not self.early_exit:
            with open(self.path, "wb") as handle:
                handle.write(b"capture fixture")
        return self

    def poll(self):
        return self.returncode if self.early_exit else None

    def communicate(self, timeout=None):
        self.communicated = True
        if self.returncode is None:
            self.returncode = 0
        return ("", "" if self.returncode == 0 else "capture failed")

    def terminate(self):
        self.returncode = -15


class GateTransitionTrialTests(unittest.TestCase):
    def _runner(self):
        self.assertIsNotNone(RUNNER, "gate-transition live runner is missing")
        return RUNNER

    def test_default_plan_is_nonmutating_dry_run(self):
        """Catches a command that treats omission of --execute as authority."""
        result = self._runner().build_dry_run(
            "AB7C22200355", "hw:CARD=R24,DEV=0", 14)

        self.assertEqual("DRY_RUN_ONLY", result["status"])
        self.assertFalse(result["usb_opened"])
        self.assertFalse(result["capture_opened"])
        self.assertEqual("AB7C22200355", result["expected_serial"])

    def test_battery_floor_blocks_before_device_or_capture_factory(self):
        """Catches any hardware access at or below the 10-percent floor."""
        calls = []

        result = self._runner().run_live_trial(
            expected_serial="AB7C22200355", battery_percent=10,
            capture_endpoint="hw:CARD=R24,DEV=0", capture_path="unused.wav",
            duration_seconds=14,
            device_factory=lambda: calls.append("device"),
            recorder_factory=lambda _argv, _path: calls.append("capture"),
            action=lambda *_args, **_kwargs: calls.append("action"),
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual("BLOCKED_BATTERY", result["status"])
        self.assertEqual([], calls)

    def test_identity_mismatch_closes_device_without_opening_capture(self):
        """Catches capture or mutation against a same-model wrong serial."""
        device = _Device("WRONG")
        calls = []

        result = self._runner().run_live_trial(
            expected_serial="AB7C22200355", battery_percent=75,
            capture_endpoint="hw:CARD=R24,DEV=0", capture_path="unused.wav",
            duration_seconds=14, device_factory=lambda: device,
            recorder_factory=lambda _argv, _path: calls.append("capture"),
            action=lambda *_args, **_kwargs: calls.append("action"),
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual("IDENTITY_MISMATCH", result["status"])
        self.assertEqual([], calls)
        self.assertTrue(device.closed)

    def test_capture_start_failure_closes_without_calling_action(self):
        """Catches a live write after ALSA failed to provide evidence."""
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "failed.wav")
            device = _Device()
            recorder = _Recorder(path, early_exit=True, returncode=1)
            action_calls = []

            result = self._runner().run_live_trial(
                expected_serial="AB7C22200355", battery_percent=75,
                capture_endpoint="hw:CARD=R24,DEV=0", capture_path=path,
                duration_seconds=14, device_factory=lambda: device,
                recorder_factory=lambda _argv, _path: recorder.start(),
                action=lambda *_args, **_kwargs: action_calls.append(True),
                sleep_fn=lambda _seconds: None,
            )

        self.assertEqual("CAPTURE_START_FAILED", result["status"])
        self.assertEqual([], action_calls)
        self.assertTrue(device.closed)
        self.assertTrue(recorder.communicated)

    def test_success_runs_action_once_and_hashes_completed_capture(self):
        """Catches duplicate action execution or unbound capture evidence."""
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "capture.wav")
            device = _Device()
            recorder = _Recorder(path)
            action_calls = []

            def action(dev, sleep_fn, event_fn):
                action_calls.append(dev)
                event_fn("baseline_confirmed")
                event_fn("link_off_confirmed")
                return {"status": "LINKED_CHANNEL2_GATE_TRANSITION_COMPLETED"}

            result = self._runner().run_live_trial(
                expected_serial="AB7C22200355", battery_percent=75,
                capture_endpoint="hw:CARD=R24,DEV=0", capture_path=path,
                duration_seconds=14, device_factory=lambda: device,
                recorder_factory=lambda _argv, _path: recorder.start(),
                action=action, sleep_fn=lambda _seconds: None,
                monotonic_fn=iter((10.0, 10.25, 10.5)).__next__,
            )

        self.assertEqual("LINKED_CHANNEL2_GATE_TRANSITION_COMPLETED",
                         result["status"])
        self.assertEqual([device], action_calls)
        self.assertTrue(device.closed)
        self.assertTrue(recorder.communicated)
        self.assertEqual(64, len(result["capture"]["sha256"]))
        self.assertEqual(0, result["capture"]["returncode"])
        self.assertEqual([0.25, 0.5],
                         [event["capture_offset_seconds"]
                          for event in result["events"]])

    def test_action_failure_is_recorded_after_device_and_capture_cleanup(self):
        """Catches an exception path that drops cleanup evidence."""
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "capture.wav")
            device = _Device()
            recorder = _Recorder(path)

            def fail(_dev, sleep_fn, event_fn):
                raise RuntimeError("injected action failure")

            result = self._runner().run_live_trial(
                expected_serial="AB7C22200355", battery_percent=75,
                capture_endpoint="hw:CARD=R24,DEV=0", capture_path=path,
                duration_seconds=14, device_factory=lambda: device,
                recorder_factory=lambda _argv, _path: recorder.start(),
                action=fail, sleep_fn=lambda _seconds: None,
            )

        self.assertEqual("LIVE_TRIAL_FAILED", result["status"])
        self.assertEqual("RuntimeError", result["error"]["type"])
        self.assertTrue(device.closed)
        self.assertTrue(recorder.communicated)


if __name__ == "__main__":
    unittest.main()
