#!/usr/bin/env python3
"""Validate the corrected block-201 rebuild sequence on one live io24.

The measurement is deliberately narrow: one Delay off/on/off A/B/A and one
Channel-1 gate off/on/off positive control, both observed with the simultaneous
JaSt Input-1 and Main meters.  Input gain and output volumes are made safe for
the measurement, while routing, slots, processingChannel, and DSP Amount are
left untouched.  Complete Host-known Voice FX and gate calls are resent during
restoration because those controls are write-only.

Live execution requires ``--execute`` and an existing empty output directory.
"""

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import statistics
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RE_DIR = Path(__file__).resolve().parent
for directory in (ROOT, RE_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import io24_loopback_foundation as foundation  # noqa: E402
import io24_voicefx_meter_probe as prior  # noqa: E402


SCHEMA = "io24-corrected-fx-rebuild-probe-v1"
SAFE_OUTPUT_VOLUME = 0.01
PROBE_INPUT_GAIN_DB = 60.0
SAMPLES_PER_WINDOW = 40
SAMPLE_INTERVAL_SECONDS = 0.05
SETTLE_SECONDS = 0.6
DRIFT_MAX_DB = 0.75
EFFECT_MIN_DB = 1.0
RATE_HZ = 96000.0
DELAY_PARAMETERS = {
    "time_s": 0.25,
    "feedback": 1.0,
    "mix": 1.0,
}


class ProbeError(RuntimeError):
    """A guard failed; no further test mutation should be attempted."""


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _state(device):
    params = device.read_params()
    if not params:
        raise ProbeError("JaSt state is unreadable")
    flags = int(params["flags"])
    return {
        "flags": flags,
        "input1_gain_db": float(params["input1Gain"]),
        "input2_gain_db": float(params["input2Gain"]),
        "input1_slot": int(params["input1SlotIndex"]),
        "input2_slot": int(params["input2SlotIndex"]),
        "input1_processing_channel": int(params["input1ProcessingChannel"]),
        "input2_processing_channel": int(params["input2ProcessingChannel"]),
        "input1_processing_enabled": not bool(flags >> 5 & 1),
        "input2_processing_enabled": not bool(flags >> 6 & 1),
        "channel_linked": bool(flags >> 12 & 1),
        "input1_phantom": bool(params["input1PhantomPower"]),
        "input2_phantom": bool(params["input2PhantomPower"]),
        "main_volume": float(params["mainVolume"]),
        "headphone_volume": float(params["hpVolume"]),
    }


def _assert_guards(state):
    if state["input1_phantom"] or state["input2_phantom"]:
        raise ProbeError("phantom must be off on both inputs")
    if state["channel_linked"]:
        raise ProbeError("stereo link must be off")
    if (state["input1_processing_channel"],
            state["input2_processing_channel"]) != (0, 1):
        raise ProbeError("Voice FX owner must remain Input 1 (0/1 permutation)")
    if not state["input1_processing_enabled"]:
        raise ProbeError("Input 1 processing must already be enabled")


def window(device, label):
    ratios = []
    sources = []
    outputs = []
    for _ in range(SAMPLES_PER_WINDOW):
        response = device.read_state()
        if response is None:
            raise ProbeError("JaSt read failed during %s" % label)
        values = device.floats(response)
        source = float(values[4])
        output = (float(values[12]) + float(values[13])) / 2.0
        if source <= 0.0 or output <= 0.0:
            raise ProbeError("a meter reached zero during %s" % label)
        sources.append(source)
        outputs.append(output)
        ratios.append(20.0 * math.log10(output / source))
        time.sleep(SAMPLE_INTERVAL_SECONDS)
    median = statistics.median(ratios)
    return {
        "label": label,
        "samples": SAMPLES_PER_WINDOW,
        "median_input1": statistics.median(sources),
        "median_main": statistics.median(outputs),
        "median_main_to_input1_db": median,
        "mad_db": statistics.median(abs(value - median) for value in ratios),
        "minimum_db": min(ratios),
        "maximum_db": max(ratios),
    }


def classify(windows, detected_label, null_label):
    before, active, after = windows
    baseline = (float(before["median_main_to_input1_db"]) +
                float(after["median_main_to_input1_db"])) / 2.0
    delta = float(active["median_main_to_input1_db"]) - baseline
    drift = (float(after["median_main_to_input1_db"]) -
             float(before["median_main_to_input1_db"]))
    uncertainty = max(float(item["mad_db"]) for item in windows)
    threshold = max(EFFECT_MIN_DB, 6.0 * uncertainty)
    stable = abs(drift) <= DRIFT_MAX_DB
    detected = stable and abs(delta) >= threshold
    return {
        "classification": (detected_label if detected else
                           "INCONCLUSIVE_BASELINE_DRIFT" if not stable else
                           null_label),
        "effect_delta_db": delta,
        "off_drift_db": drift,
        "maximum_window_mad_db": uncertainty,
        "detection_threshold_db": threshold,
        "stable": stable,
        "effect_detected": detected,
    }


def run_sequence(device, restore_fx, restore_gate,
                 sample_one=None, settle=time.sleep,
                 progress=lambda _message: None):
    """Perform both measurements and always attempt the full restoration."""
    if sample_one is None:
        sample_one = lambda label: window(device, label)
    before = _state(device)
    _assert_guards(before)
    result = {
        "status": "MEASUREMENT_FAILED_RESTORATION_PENDING",
        "started": _now(),
        "readable_before": before,
        "restore_fx": restore_fx,
        "restore_gate": restore_gate,
    }
    failure = None
    try:
        device.set_main_volume(SAFE_OUTPUT_VOLUME)
        device.set_hp_volume(SAFE_OUTPUT_VOLUME)
        device.set_gain(1, PROBE_INPUT_GAIN_DB)
        device.gate_off(1)
        settle(SETTLE_SECONDS)
        guarded = _state(device)
        _assert_guards(guarded)
        if not math.isclose(guarded["main_volume"], SAFE_OUTPUT_VOLUME,
                            abs_tol=1e-6) or not math.isclose(
                                guarded["headphone_volume"],
                                SAFE_OUTPUT_VOLUME, abs_tol=1e-6) or not \
                math.isclose(guarded["input1_gain_db"], PROBE_INPUT_GAIN_DB,
                             abs_tol=1e-6):
            raise ProbeError("readable safety controls did not latch")
        result["readable_guarded"] = guarded

        progress("measuring Channel-1 gate positive control")
        gate_windows = [sample_one("gate_off_before")]
        device.set_gate(**restore_gate)
        settle(SETTLE_SECONDS)
        gate_windows.append(sample_one("gate_on"))
        device.gate_off(1)
        settle(SETTLE_SECONDS)
        gate_windows.append(sample_one("gate_off_after"))
        result["gate_positive_control"] = {
            "windows": gate_windows,
            "analysis": classify(
                gate_windows, "DIRECT_GATE_EFFECT_DETECTED",
                "NO_DIRECT_GATE_EFFECT_DETECTED"),
        }

        progress("measuring corrected Delay rebuild sequence")
        off = dict(DELAY_PARAMETERS, on=False)
        on = dict(DELAY_PARAMETERS, on=True)
        device.set_fx("delay", **off)
        settle(SETTLE_SECONDS)
        fx_windows = [sample_one("delay_off_before")]
        device.set_fx("delay", **on)
        settle(SETTLE_SECONDS)
        fx_windows.append(sample_one("delay_on"))
        device.set_fx("delay", **off)
        settle(SETTLE_SECONDS)
        fx_windows.append(sample_one("delay_off_after"))
        result["delay"] = {
            "parameters": DELAY_PARAMETERS,
            "sequence": "SELECT_WAIT_SELECTOR_REPLAY_STATE",
            "windows": fx_windows,
            "analysis": classify(
                fx_windows, "CORRECTED_DELAY_SCALAR_LEVEL_EFFECT_DETECTED",
                "NO_CORRECTED_DELAY_SCALAR_LEVEL_EFFECT_DETECTED"),
        }
        control_ok = result["gate_positive_control"]["analysis"][
            "effect_detected"]
        delay_detected = result["delay"]["analysis"]["effect_detected"]
        # The API's feedback 1.0 becomes coefficient 0.5 on the wire. For
        # uncorrelated stationary noise, y[n]=x[n]+0.5*y[n-D] has power gain
        # 1/(1-0.5^2), only +1.249 dB. A threshold above that makes a scalar
        # null inconclusive even when a gross gate control is easily seen.
        expected_noise_gain_db = 10.0 * math.log10(1.0 / (1.0 - 0.5 ** 2))
        result["delay"]["expected_stationary_noise_gain_db"] = \
            expected_noise_gain_db
        result["delay"]["measurement_interpretation"] = (
            "INCONCLUSIVE_EXPECTED_LEVEL_SIGNATURE_BELOW_THRESHOLD" if
            not delay_detected and expected_noise_gain_db <
            result["delay"]["analysis"]["detection_threshold_db"] else
            "SCALAR_LEVEL_EFFECT_DETECTED" if delay_detected else
            "NO_EXPECTED_SCALAR_LEVEL_EFFECT_DETECTED")
        result["conclusion"] = (
            "CORRECTED_DELAY_AUDIBLE_BY_METER" if
            control_ok and delay_detected else
            "INCONCLUSIVE_POSITIVE_CONTROL_FAILED" if not control_ok else
            result["delay"]["measurement_interpretation"])
        result["status"] = "MEASURED_RESTORATION_PENDING"
    except BaseException as error:
        failure = error
        result["error"] = {"type": type(error).__name__,
                           "message": str(error)}
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
            settle(SETTLE_SECONDS)
            after = _state(device)
            _assert_guards(after)
            readable_exact = after == before
            result["readable_after"] = after
        except BaseException as error:
            restoration_errors.append({
                "control": "readback",
                "type": type(error).__name__,
                "message": str(error),
            })
        result["restoration"] = {
            "readable_exact": readable_exact,
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
        result["finished"] = _now()
    return result


def run_live(output_dir, battery_path, shadow_path):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise ProbeError("output directory must exist and be empty")
    restore_fx = prior.restore_fx_from_shadow(shadow_path)
    restore_gate = prior.restore_gate_from_shadow(shadow_path)
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": _now(),
        "host_configured_sample_rate_hz": int(RATE_HZ),
        "host_configured_quantum_frames": 512,
        "stimulus": "INPUT1_PREAMP_SELF_NOISE",
        "observation": "SIMULTANEOUS_JAST_INPUT1_AND_MAIN_LR_METERS",
        "playback": "NONE",
        "mixer_routes_preset_slots_dsp_amount_processing_channel": "UNTOUCHED",
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
        report["error"] = {"type": type(error).__name__,
                           "message": str(error)}
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
        report["finished"] = _now()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    parser.add_argument("--shadow-path",
                        default=str(Path.home() / ".cache/io24/shadow.json"))
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "DRY_RUN_ONLY",
            "model": "delay",
            "model_parameters": DELAY_PARAMETERS,
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
