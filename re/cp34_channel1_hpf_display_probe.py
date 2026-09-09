#!/usr/bin/env python3
"""Human-paced Channel-1 Fat Channel HPF physical-display correlation probe.

Live execution is deliberately narrow: after exact battery, identity, and
readable-state guards, it sends only Channel-1 ``set_highpass_freq`` calls for
40, 80, 160, and 55 Hz.  It never saves, selects, enables, disables, or changes
a device preset.  The exact MAIN 24 Hz bypass call is always attempted in the
cleanup path.  The DSP value is write-only, so restoration means that the
identical bypass command was sent, not that the device reported it back.
"""

import argparse
import json
from pathlib import Path
import signal
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import io24  # noqa: E402


EXPECTED_SERIAL = "AB7C22200355"
EXPECTED_FIRMWARE_VERSION = 0x0128
TARGET_CHANNEL = 1
TARGET_SLOT = 0
EXPECTED_GAIN_DB = 30.0
PROBE_VALUES_HZ = (40.0, 80.0, 160.0, 55.0)
RESTORE_HZ = 24.0
BATTERY_FLOOR = 10
PROMPT_TIMEOUT_SECONDS = 300


class ProbeError(RuntimeError):
    """The bounded display probe was ineligible or failed."""


def _battery_result(battery_percent):
    if isinstance(battery_percent, bool) or not isinstance(battery_percent, int):
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if not 0 <= battery_percent <= 100:
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if battery_percent <= BATTERY_FLOOR:
        return {"status": "BLOCKED_BATTERY",
                "battery_percent": battery_percent}
    return None


def _readable_state(params):
    required = {
        "flags", "input1Gain", "input2Gain", "input1SlotIndex",
        "input2SlotIndex", "input1ProcessingChannel",
        "input2ProcessingChannel",
    }
    missing = sorted(required.difference(params or {}))
    if missing:
        raise ProbeError("readable state lacks %s" % ", ".join(missing))
    flags = int(params["flags"])
    processing = (
        int(params["input1ProcessingChannel"]),
        int(params["input2ProcessingChannel"]),
    )
    if set(processing) != {0, 1}:
        raise ProbeError("processing-channel state is not a 0/1 permutation")
    return {
        "flags_word": flags,
        "channel_linked": bool(flags >> 12 & 1),
        "input1_gain_db": float(params["input1Gain"]),
        "input2_gain_db": float(params["input2Gain"]),
        "input1_slot_index": int(params["input1SlotIndex"]),
        "input2_slot_index": int(params["input2SlotIndex"]),
        "input1_preset_enabled": not bool(flags >> 5 & 1),
        "input2_preset_enabled": not bool(flags >> 6 & 1),
        "input1_processing_channel": processing[0],
        "input2_processing_channel": processing[1],
    }


def _guard_main(state):
    if state["channel_linked"]:
        raise ProbeError("stereo link must be off")
    if state["input1_slot_index"] != TARGET_SLOT:
        raise ProbeError("Channel 1 is not on MAIN slot 0")
    if not state["input1_preset_enabled"]:
        raise ProbeError("Channel-1 MAIN is not enabled")
    if abs(state["input1_gain_db"] - EXPECTED_GAIN_DB) > 0.001:
        raise ProbeError("Channel-1 gain no longer matches MAIN's 30 dB guard")


def _readable_guard_projection(state):
    return {
        "channel_linked": state["channel_linked"],
        "input1_gain_db": state["input1_gain_db"],
        "input2_gain_db": state["input2_gain_db"],
        "input1_slot_index": state["input1_slot_index"],
        "input2_slot_index": state["input2_slot_index"],
        "input1_preset_enabled": state["input1_preset_enabled"],
        "input2_preset_enabled": state["input2_preset_enabled"],
        "input1_processing_channel": state["input1_processing_channel"],
        "input2_processing_channel": state["input2_processing_channel"],
    }


def run_probe(device_factory, battery_percent, ready_fn, observe_fn,
              sleep_fn=time.sleep, expected_serial=EXPECTED_SERIAL,
              expected_firmware=EXPECTED_FIRMWARE_VERSION):
    """Run the authorized probe; callbacks provide explicit human pacing."""
    blocked = _battery_result(battery_percent)
    if blocked is not None:
        return blocked

    device = None
    baseline = None
    post_state = None
    observations = []
    write_attempted = False
    restore_status = "NOT_REQUIRED"
    result = None
    stage = "open"
    try:
        device = device_factory(shadow=False)
        stage = "identity"
        serial = device.dev.serial_number
        firmware = int(getattr(device.dev, "bcdDevice", 0))
        if serial != expected_serial:
            raise ProbeError("serial mismatch: %r" % serial)
        if firmware != expected_firmware:
            raise ProbeError("bcdDevice mismatch: %04x" % firmware)

        stage = "baseline"
        baseline = _readable_state(device.read_params())
        _guard_main(baseline)
        baseline_projection = _readable_guard_projection(baseline)

        stage = "human_ready"
        ready_fn()

        for hz in PROBE_VALUES_HZ:
            stage = "write_%g_hz" % hz
            write_attempted = True
            transport = device.set_highpass_freq(TARGET_CHANNEL, hz)
            sleep_fn(0.35)
            stage = "observe_%g_hz" % hz
            observations.append({
                "requested_hz": hz,
                "physical_display": str(observe_fn(hz)),
                "transport_reply_bytes": len(transport or b""),
            })

        result = {
            "schema": "cp34-channel1-hpf-display-probe-v1",
            "status": "DISPLAY_OBSERVATIONS_CAPTURED",
            "battery_percent": battery_percent,
            "device": {"serial": serial, "bcd_device": "%04x" % firmware},
            "baseline": baseline,
            "probe_values_hz": list(PROBE_VALUES_HZ),
            "observations": observations,
            "slot_operations": 0,
            "digital_hpf_readback": "UNAVAILABLE",
        }
    except (Exception, SystemExit) as error:
        result = {
            "schema": "cp34-channel1-hpf-display-probe-v1",
            "status": "PROBE_FAILED",
            "failed_stage": stage,
            "battery_percent": battery_percent,
            "baseline": baseline,
            "observations": observations,
            "slot_operations": 0,
            "error": "%s: %s" % (type(error).__name__, error),
        }
    finally:
        if device is not None and write_attempted:
            try:
                device.set_highpass_freq(TARGET_CHANNEL, RESTORE_HZ)
                sleep_fn(0.35)
                restore_status = "EXACT_24_HZ_BYPASS_WRITE_SENT"
            except Exception as error:
                restore_status = "RESTORE_FAILED: %s: %s" % (
                    type(error).__name__, error)
            try:
                post_state = _readable_state(device.read_params())
                if baseline is not None and _readable_guard_projection(post_state) != \
                        _readable_guard_projection(baseline):
                    raise ProbeError("readable state changed during display probe")
            except Exception as error:
                if result is not None and result.get("status") != "PROBE_FAILED":
                    result["status"] = "POST_GUARD_FAILED"
                    result["post_guard_error"] = "%s: %s" % (
                        type(error).__name__, error)
        if device is not None:
            try:
                device.close()
            except Exception:
                pass

    if result is None:
        result = {"status": "PROBE_FAILED", "failed_stage": stage}
    result["restore"] = restore_status
    result["post_state"] = post_state
    if restore_status.startswith("RESTORE_FAILED"):
        result["status"] = "RESTORE_FAILED"
    return result


def _read_battery(path):
    try:
        return int(path.read_text(encoding="ascii").strip())
    except (OSError, ValueError) as error:
        raise ProbeError("battery unavailable: %s" % error) from error


def _timed_input(prompt):
    def expired(_signum, _frame):
        raise TimeoutError("human observation timed out")

    previous = signal.signal(signal.SIGALRM, expired)
    signal.alarm(PROMPT_TIMEOUT_SECONDS)
    try:
        return input(prompt)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--battery-path", type=Path,
        default=Path("/sys/class/power_supply/BAT0/capacity"),
    )
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args(argv)

    plan = {
        "schema": "cp34-channel1-hpf-display-probe-v1",
        "status": "OFFLINE_READY",
        "target_channel": TARGET_CHANNEL,
        "probe_values_hz": list(PROBE_VALUES_HZ),
        "restore_hz": RESTORE_HZ,
        "slot_operations": 0,
        "human_paced": True,
    }
    if not arguments.execute:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    try:
        battery_percent = _read_battery(arguments.battery_path)
    except ProbeError as error:
        result = {"status": "BLOCKED_BATTERY_UNAVAILABLE",
                  "battery_error": str(error)}
    else:
        result = run_probe(
            io24.Io24,
            battery_percent,
            ready_fn=lambda: _timed_input(
                "Open Channel 1 detail on the io24 display, then press Enter: "),
            observe_fn=lambda hz: _timed_input(
                "%.0f Hz sent. Type exactly what the physical display shows: " % hz),
        )

    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.report:
        arguments.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result.get("status") == "DISPLAY_OBSERVATIONS_CAPTURED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
