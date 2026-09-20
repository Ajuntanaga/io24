#!/usr/bin/env python3
"""Prepare one decisive corrected Ring-Mod meter test for the io24.

The live path performs one Channel-1 gate positive control followed by one
Ring-Mod off/on/off A/B/A.  Ring Mod is fully wet and its output-volume field
is zero, so the firmware's active dry and wet output gains are both zero.  A
flat result with a valid control is therefore a resolved negative for the
selector sequence used by that run rather than another underpowered Delay
measurement.  The retained live run used the superseded selector/state-replay
sequence; current Host code replays the selector after bypass instead.

Live execution requires ``--execute`` and an existing empty output directory.
Routing, slots, processingChannel, and DSP Amount remain untouched.
"""

import argparse
import json
import math
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RE_DIR = Path(__file__).resolve().parent
for directory in (ROOT, RE_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import io24_corrected_fx_rebuild_probe as common  # noqa: E402
import io24_loopback_foundation as foundation  # noqa: E402
import io24_voicefx_meter_probe as prior  # noqa: E402


SCHEMA = "io24-corrected-ringmod-probe-v2"
SESSION_STREAM_FLAG_MASK = 1 << 9
RINGMOD_PARAMETERS = {
    "carrier_hz": 1000.0,
    "dist": 0.0,
    "vol": 0.0,
    "carrier2": False,
    "carrier2_hz": 50.0,
    "mix": 1.0,
}


def ringmod_output_gains(parameters):
    """Return the two source-bound final gains used by model-3 process."""
    volume = float(parameters["vol"])
    mix = float(parameters["mix"])
    return {
        "dry": volume * (1.0 - mix),
        "wet": 2.0 * volume * mix,
    }


def restoration_matches(before, after):
    """Compare user state while ignoring documented session/stream bit 9."""
    expected = dict(before)
    observed = dict(after)
    expected["flags"] = int(expected["flags"]) & ~SESSION_STREAM_FLAG_MASK
    observed["flags"] = int(observed["flags"]) & ~SESSION_STREAM_FLAG_MASK
    return observed == expected


def run_sequence(device, restore_fx, restore_gate,
                 sample_one=None, settle=time.sleep,
                 progress=lambda _message: None):
    """Perform the gate and Ring-Mod measurements, always restoring state."""
    if sample_one is None:
        sample_one = lambda label: common.window(device, label)
    before = common._state(device)
    common._assert_guards(before)
    result = {
        "status": "MEASUREMENT_FAILED_RESTORATION_PENDING",
        "started": common._now(),
        "readable_before": before,
        "restore_fx": restore_fx,
        "restore_gate": restore_gate,
    }
    failure = None
    try:
        device.set_main_volume(common.SAFE_OUTPUT_VOLUME)
        device.set_hp_volume(common.SAFE_OUTPUT_VOLUME)
        device.set_gain(1, common.PROBE_INPUT_GAIN_DB)
        device.gate_off(1)
        settle(common.SETTLE_SECONDS)
        guarded = common._state(device)
        common._assert_guards(guarded)
        if not math.isclose(
                guarded["main_volume"], common.SAFE_OUTPUT_VOLUME,
                abs_tol=1e-6) or not math.isclose(
                    guarded["headphone_volume"], common.SAFE_OUTPUT_VOLUME,
                    abs_tol=1e-6) or not math.isclose(
                        guarded["input1_gain_db"], common.PROBE_INPUT_GAIN_DB,
                        abs_tol=1e-6):
            raise common.ProbeError("readable safety controls did not latch")
        result["readable_guarded"] = guarded

        progress("measuring Channel-1 gate positive control")
        gate_windows = [sample_one("gate_off_before")]
        device.set_gate(**restore_gate)
        settle(common.SETTLE_SECONDS)
        gate_windows.append(sample_one("gate_on"))
        device.gate_off(1)
        settle(common.SETTLE_SECONDS)
        gate_windows.append(sample_one("gate_off_after"))
        result["gate_positive_control"] = {
            "windows": gate_windows,
            "analysis": common.classify(
                gate_windows, "DIRECT_GATE_EFFECT_DETECTED",
                "NO_DIRECT_GATE_EFFECT_DETECTED"),
        }

        progress("measuring corrected zero-output Ring-Mod sequence")
        off = dict(RINGMOD_PARAMETERS, on=False)
        on = dict(RINGMOD_PARAMETERS, on=True)
        device.set_fx("ringmod", **off)
        settle(common.SETTLE_SECONDS)
        fx_windows = [sample_one("ringmod_off_before")]
        device.set_fx("ringmod", **on)
        settle(common.SETTLE_SECONDS)
        fx_windows.append(sample_one("ringmod_on"))
        device.set_fx("ringmod", **off)
        settle(common.SETTLE_SECONDS)
        fx_windows.append(sample_one("ringmod_off_after"))
        analysis = common.classify(
            fx_windows,
            "CORRECTED_RINGMOD_ZERO_OUTPUT_EFFECT_DETECTED",
            "NO_CORRECTED_RINGMOD_ZERO_OUTPUT_EFFECT_DETECTED")
        result["ringmod"] = {
            "parameters": RINGMOD_PARAMETERS,
            "predicted_output_gains": ringmod_output_gains(
                RINGMOD_PARAMETERS),
            "firmware_process_fields": {
                "on": "model+0x14",
                "volume": "model+0x20",
                "mix": "model+0x2c",
                "dry_gain": "volume * (1 - mix)",
                "wet_gain": "2 * volume * mix",
            },
            "sequence": "SELECT_WAIT_SELECTOR_REPLAY_STATE",
            "windows": fx_windows,
            "analysis": analysis,
        }
        control_ok = result["gate_positive_control"]["analysis"][
            "effect_detected"]
        if not control_ok:
            conclusion = "INCONCLUSIVE_POSITIVE_CONTROL_FAILED"
        elif analysis["effect_detected"]:
            conclusion = "CORRECTED_RINGMOD_ZERO_OUTPUT_EFFECT_DETECTED"
        elif not analysis["stable"]:
            conclusion = "INCONCLUSIVE_RINGMOD_BASELINE_DRIFT"
        else:
            conclusion = "NO_CORRECTED_RINGMOD_ZERO_OUTPUT_EFFECT_DETECTED"
        result["conclusion"] = conclusion
        result["status"] = "MEASURED_RESTORATION_PENDING"
    except BaseException as error:
        failure = error
        result["error"] = {
            "type": type(error).__name__, "message": str(error)}
    finally:
        restoration_errors = []
        restored_controls = []
        actions = (
            (lambda: device.set_fx(restore_fx["model"],
                                   **restore_fx["kwargs"]),
             "voicefx_host_known_intent"),
            (lambda: device.set_gate(**restore_gate),
             "channel1_gate_host_known_intent"),
            (lambda: device.set_gain(1, before["input1_gain_db"]),
             "input1_gain"),
            (lambda: device.set_main_volume(before["main_volume"]),
             "main_volume"),
            (lambda: device.set_hp_volume(before["headphone_volume"]),
             "headphone_volume"),
        )
        for action, control in actions:
            try:
                action()
                restored_controls.append(control)
            except BaseException as error:
                restoration_errors.append({
                    "control": control,
                    "type": type(error).__name__,
                    "message": str(error),
                })
        readable_exact = False
        try:
            settle(common.SETTLE_SECONDS)
            after = common._state(device)
            common._assert_guards(after)
            raw_readable_exact = after == before
            readable_exact = restoration_matches(before, after)
            result["readable_after"] = after
        except BaseException as error:
            restoration_errors.append({
                "control": "readback",
                "type": type(error).__name__,
                "message": str(error),
            })
        result["restoration"] = {
            "readable_exact": readable_exact,
            "raw_readable_exact": raw_readable_exact if
                "raw_readable_exact" in locals() else False,
            "ignored_session_stream_flag_mask":
                SESSION_STREAM_FLAG_MASK,
            "restored_controls": restored_controls,
            "voicefx": "HOST_KNOWN_WRITE_ONLY_INTENT_RESENT",
            "channel1_gate": "HOST_KNOWN_WRITE_ONLY_INTENT_RESENT",
            "routing_slots_dsp_amount_processing_channel": "UNTOUCHED",
            "errors": restoration_errors,
        }
        if restoration_errors or not readable_exact:
            result["status"] = "RESTORATION_FAILED"
        elif failure is not None:
            result["status"] = "MEASUREMENT_FAILED_RESTORED"
        else:
            result["status"] = "MEASURED_AND_RESTORED"
        result["finished"] = common._now()
    return result


def run_live(output_dir, battery_path, shadow_path):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise common.ProbeError("output directory must exist and be empty")
    restore_fx = prior.restore_fx_from_shadow(shadow_path)
    restore_gate = prior.restore_gate_from_shadow(shadow_path)
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": common._now(),
        "audio_stream_timing": common.meter_only_audio_stream_timing(),
        "stimulus": "INPUT1_PREAMP_SELF_NOISE",
        "observation": "SIMULTANEOUS_JAST_INPUT1_AND_MAIN_LR_METERS",
        "playback": "NONE",
        "mixer_routes_preset_slots_dsp_amount_processing_channel":
            "UNTOUCHED",
    }
    device = None
    try:
        battery = foundation._battery(battery_path)
        report["battery_before"] = battery
        if battery <= foundation.BATTERY_FLOOR:
            report["status"] = "BLOCKED_BATTERY"
            return report
        device = foundation._open_checked()
        report["device"] = {
            "serial": device.dev.serial_number,
            "bcd_device": "%04x" % int(device.dev.bcdDevice),
        }
        sequence = run_sequence(
            device, restore_fx, restore_gate,
            progress=lambda message: print(message, flush=True))
        report["sequence"] = sequence
        report["transport"] = list(device.transport_log)
        report["status"] = sequence["status"]
    except BaseException as error:
        report["error"] = {
            "type": type(error).__name__, "message": str(error)}
    finally:
        if device is not None:
            report.setdefault("transport", list(device.transport_log))
            try:
                device.close()
            except BaseException as error:
                report["close_error"] = {
                    "type": type(error).__name__, "message": str(error)}
                report["status"] = "RESTORATION_FAILED"
        try:
            report["battery_after"] = foundation._battery(battery_path)
        except BaseException as error:
            report["battery_after_error"] = str(error)
        report["finished"] = common._now()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument(
        "--battery-path", default="/sys/class/power_supply/BAT0/capacity")
    parser.add_argument(
        "--shadow-path",
        default=str(Path.home() / ".cache/io24/shadow.json"))
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "DRY_RUN_ONLY",
            "model": "ringmod",
            "model_parameters": RINGMOD_PARAMETERS,
            "predicted_output_gains": ringmod_output_gains(
                RINGMOD_PARAMETERS),
            "positive_control": "Channel-1 direct gate off/on/off",
            "restoration": "Host-known Voice FX and gate plus readable state",
            "untouched": ["mixer routes", "preset slots", "DSP Amount",
                          "processingChannel"],
        }, indent=2, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--execute requires --output-dir")
    report = run_live(args.output_dir, args.battery_path, args.shadow_path)
    path = Path(args.output_dir) / "live-report.json"
    with path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "MEASURED_AND_RESTORED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
