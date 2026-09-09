#!/usr/bin/env python3
"""Execute one serial-pinned CP34 linked gate-transition capture."""

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import io24


DEFAULT_ENDPOINT = "hw:CARD=R24,DEV=0"
DEFAULT_DURATION = 14


def build_dry_run(expected_serial, capture_endpoint, duration_seconds):
    return {
        "schema": "cp34-gate-transition-live-trial-v1",
        "status": "DRY_RUN_ONLY",
        "expected_serial": expected_serial,
        "capture": {
            "endpoint": capture_endpoint,
            "duration_seconds": duration_seconds,
            "channels": 6,
            "format": "S32_LE",
            "rate_hz": 48000,
            "playback": False,
        },
        "usb_opened": False,
        "capture_opened": False,
        "permitted_action": "linked Channel-2 slot-3 factory gate transition",
    }


def _battery_block(battery_percent):
    if isinstance(battery_percent, bool) or not isinstance(battery_percent, int) \
            or not 0 <= battery_percent <= 100:
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if battery_percent <= 10:
        return {"status": "BLOCKED_BATTERY",
                "battery_percent": battery_percent}
    return None


def _real_recorder(argv, _capture_path):
    return subprocess.Popen(argv, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, text=True)


def _error(error):
    return {"type": type(error).__name__, "message": str(error)}


def run_live_trial(*, expected_serial, battery_percent, capture_endpoint,
                   capture_path, duration_seconds,
                   device_factory=lambda: io24.Io24(shadow=False),
                   recorder_factory=_real_recorder,
                   action=io24.probe_channel2_slot3_with_gate_transition,
                   sleep_fn=time.sleep, monotonic_fn=time.monotonic):
    """Run exactly once with injectable hardware boundaries for tests."""
    blocked = _battery_block(battery_percent)
    if blocked is not None:
        return blocked
    if not capture_path or os.path.exists(capture_path):
        return {"status": "BLOCKED_CAPTURE_PATH",
                "capture_path": capture_path,
                "reason": "capture path is missing or already exists"}

    device = None
    recorder = None
    capture_start = None
    events = []
    action_result = None
    action_error = None
    capture_stderr = ""
    try:
        try:
            device = device_factory()
        except BaseException as error:
            return {"status": "DEVICE_OPEN_FAILED", "error": _error(error)}

        try:
            observed_serial = device.dev.serial_number
        except BaseException as error:
            return {"status": "IDENTITY_UNAVAILABLE", "error": _error(error)}
        if observed_serial != expected_serial:
            return {
                "status": "IDENTITY_MISMATCH",
                "expected_serial": expected_serial,
                "observed_serial": observed_serial,
            }

        command = [
            "arecord", "-q", "-D", capture_endpoint, "-t", "wav",
            "-f", "S32_LE", "-r", "48000", "-c", "6", "-d",
            str(duration_seconds), capture_path,
        ]
        try:
            recorder = recorder_factory(command, capture_path)
        except BaseException as error:
            return {"status": "CAPTURE_START_FAILED", "error": _error(error)}
        capture_start = monotonic_fn()
        sleep_fn(0.5)
        if recorder.poll() is not None:
            _, capture_stderr = recorder.communicate(timeout=5)
            return {
                "status": "CAPTURE_START_FAILED",
                "capture": {"returncode": recorder.returncode,
                            "stderr": capture_stderr.strip()},
            }

        def event(name):
            events.append({
                "event": name,
                "capture_offset_seconds": round(monotonic_fn() - capture_start, 6),
                "wall_time": datetime.datetime.now().astimezone().isoformat(
                    timespec="milliseconds"),
            })

        try:
            action_result = action(device, sleep_fn=sleep_fn, event_fn=event)
        except BaseException as error:
            action_error = _error(error)
    finally:
        if device is not None:
            try:
                device.close()
            except BaseException as error:
                if action_error is None:
                    action_error = _error(error)
        if recorder is not None and not getattr(
                recorder, "communicated", False):
            try:
                _, capture_stderr = recorder.communicate(
                    timeout=duration_seconds + 8)
            except subprocess.TimeoutExpired:
                recorder.terminate()
                _, capture_stderr = recorder.communicate(timeout=5)
                if action_error is None:
                    action_error = {"type": "CaptureTimeout",
                                    "message": "arecord exceeded fixed duration"}

    capture = {
        "path": capture_path,
        "endpoint": capture_endpoint,
        "duration_seconds": duration_seconds,
        "format": "S32_LE",
        "rate_hz": 48000,
        "channels": 6,
        "returncode": None if recorder is None else recorder.returncode,
        "stderr": capture_stderr.strip(),
    }
    if os.path.isfile(capture_path):
        with open(capture_path, "rb") as handle:
            capture["sha256"] = hashlib.sha256(handle.read()).hexdigest()
        capture["bytes"] = os.path.getsize(capture_path)
    else:
        if action_error is None:
            action_error = {"type": "CaptureMissing",
                            "message": "capture file was not produced"}
    if recorder is not None and recorder.returncode != 0 and action_error is None:
        action_error = {"type": "CaptureFailed",
                        "message": "arecord exit %s" % recorder.returncode}

    return {
        "schema": "cp34-gate-transition-live-trial-v1",
        "status": (action_result["status"] if action_error is None
                   else "LIVE_TRIAL_FAILED"),
        "battery_percent": battery_percent,
        "device": {"serial": expected_serial},
        "scope": "passive capture plus bounded linked Channel-2 gate transition",
        "events": events,
        "capture": capture,
        "device_result": action_result,
        "error": action_error,
    }


def _read_battery(path):
    try:
        with open(path, encoding="ascii") as handle:
            value = int(handle.read().strip())
    except (OSError, ValueError):
        return None
    return value


def _write_report(path, report):
    parent = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(parent):
        raise OSError("report parent does not exist: %s" % parent)
    with open(path, "x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    parser.add_argument("--capture-endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--capture-path")
    parser.add_argument("--report")
    parser.add_argument("--execute", action="store_true")
    arguments = parser.parse_args(argv)

    if not arguments.execute:
        report = build_dry_run(arguments.serial, arguments.capture_endpoint,
                               DEFAULT_DURATION)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if not arguments.capture_path or not arguments.report:
        print(json.dumps({"status": "BLOCKED_ARGUMENTS",
                          "reason": "--capture-path and --report are required"},
                         indent=2, sort_keys=True))
        return 3

    battery = _read_battery(arguments.battery_path)
    report = run_live_trial(
        expected_serial=arguments.serial,
        battery_percent=battery,
        capture_endpoint=arguments.capture_endpoint,
        capture_path=arguments.capture_path,
        duration_seconds=DEFAULT_DURATION,
    )
    try:
        _write_report(arguments.report, report)
    except OSError as error:
        print(json.dumps({"status": "REPORT_WRITE_FAILED", "error": _error(error)},
                         indent=2, sort_keys=True))
        return 3
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == \
        "LINKED_CHANNEL2_GATE_TRANSITION_COMPLETED" else 3


if __name__ == "__main__":
    sys.exit(main())
