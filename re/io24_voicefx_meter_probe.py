#!/usr/bin/env python3
"""No-cable Voice FX A/B probe using simultaneous JaSt input/Main meters.

The probe uses Input 1 preamp self-noise as a broadband source.  It never
changes mixer routing, preset content, DSP Amount, or processingChannel.  The
current Host shadow supplies the complete write-only Voice FX intent that is
resent during restoration.
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

import io24_fx  # noqa: E402
import io24_loopback_foundation as foundation  # noqa: E402


SCHEMA = "io24-voicefx-meter-probe-v1"
RATE_HZ = 96000
SAFE_OUTPUT_VOLUME = 0.01
PROBE_INPUT_GAIN_DB = 60.0
SAMPLES_PER_WINDOW = 40
SAMPLE_INTERVAL_SECONDS = 0.05
SETTLE_SECONDS = 0.5
EFFECT_DELTA_MIN_DB = 0.5
OFF_DRIFT_MAX_DB = 0.5
CONTROL_INPUT_DELTA_MIN_DB = 20.0
CONTROL_MAIN_DELTA_MIN_DB = 10.0

MODEL_PROFILES = (
    ("transformer", {"lows": 1.0, "width": 1.0, "mix": 1.0,
                     "fs": float(RATE_HZ)}),
    ("detuner", {"detune": 0, "mix": 0.5, "fs": float(RATE_HZ)}),
    ("vocoder", {"carrier_type": 1, "carrier_freq": 110.0,
                 "vol": 1.0, "mix": 1.0, "fs": float(RATE_HZ)}),
    ("ringmod", {"carrier_hz": 1000.0, "dist": 1.0, "vol": 1.0,
                 "carrier2": True, "carrier2_hz": 50.0, "mix": 1.0}),
    ("filters", {"pitch": 0.0, "regeneration": 1.0, "damping": 0.0,
                 "distortion": 1.0, "volume": 1.0, "mix": 1.0}),
    ("delay", {"time_s": 0.125, "feedback": 0.9, "mix": 0.5}),
)


class VoiceFxProbeError(RuntimeError):
    pass


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _db(value):
    return 20.0 * math.log10(max(float(value), 1e-15))


def _enabled(params, channel):
    bit = 5 if channel == 1 else 6
    return not bool(int(params["flags"]) >> bit & 1)


def _readable_state(params):
    if params is None:
        raise VoiceFxProbeError("JaSt read failed")
    return {
        "flags": int(params["flags"]),
        "input1_gain_db": float(params["input1Gain"]),
        "input2_gain_db": float(params["input2Gain"]),
        "headphone_volume": float(params["hpVolume"]),
        "main_volume": float(params["mainVolume"]),
        "input1_processing_channel": int(params["input1ProcessingChannel"]),
        "input2_processing_channel": int(params["input2ProcessingChannel"]),
        "input1_phantom": bool(params["input1PhantomPower"]),
        "input2_phantom": bool(params["input2PhantomPower"]),
        "input1_processing_enabled": _enabled(params, 1),
        "channel_linked": bool(int(params["flags"]) >> 12 & 1),
    }


def _assert_guards(state):
    if state["input1_phantom"] or state["input2_phantom"]:
        raise VoiceFxProbeError("phantom must be off on both inputs")
    if state["channel_linked"]:
        raise VoiceFxProbeError("stereo link must be off before any test write")
    if (state["input1_processing_channel"],
            state["input2_processing_channel"]) != (0, 1):
        raise VoiceFxProbeError(
            "processing-channel permutation must remain 0/1")
    if not state["input1_processing_enabled"]:
        raise VoiceFxProbeError(
            "Input 1 DSP Amount must already be positive; the probe will not "
            "change its write-only value")


def restore_fx_from_shadow(path):
    """Load and validate one complete Host-known set_fx call without I/O."""
    with Path(path).open(encoding="utf-8") as handle:
        shadow = json.load(handle)
    entry = shadow.get("set_fx")
    if not isinstance(entry, dict) or entry.get("fn") != "set_fx":
        raise VoiceFxProbeError("Host shadow has no complete set_fx entry")
    kwargs = entry.get("kwargs")
    if not isinstance(kwargs, dict):
        raise VoiceFxProbeError("Host shadow set_fx kwargs are missing")
    restore = dict(kwargs)
    model = str(restore.pop("model", "")).lower()
    if model not in dict(MODEL_PROFILES):
        raise VoiceFxProbeError("Host shadow has an unknown Voice FX model")
    # Builders are pure: this validates the exact call before USB is opened.
    getattr(io24_fx, "set_fx_" + model)(**restore)
    return {"model": model, "kwargs": restore}


def restore_gate_from_shadow(path):
    """Load the complete Host-known Channel 1 gate call without device I/O."""
    with Path(path).open(encoding="utf-8") as handle:
        shadow = json.load(handle)
    entry = shadow.get("set_gate#channel=1,instance=None")
    if not isinstance(entry, dict) or entry.get("fn") != "set_gate":
        raise VoiceFxProbeError("Host shadow has no complete Channel 1 gate entry")
    kwargs = entry.get("kwargs")
    if not isinstance(kwargs, dict) or kwargs.get("channel") != 1:
        raise VoiceFxProbeError("Host shadow Channel 1 gate kwargs are missing")
    required = {
        "channel", "on", "threshold_db", "range_db", "attack_s",
        "release_s", "keyfilter_hz", "expander", "keylisten", "instance",
        "fs",
    }
    if set(kwargs) != required:
        raise VoiceFxProbeError("Host shadow Channel 1 gate state is incomplete")
    return dict(kwargs)


def _meter_metric(values):
    median = statistics.median(values)
    db_values = [_db(value) for value in values]
    median_db = statistics.median(db_values)
    return {
        "median": median,
        "median_to_input1_db": median_db,
        "mad_to_input1_db": statistics.median(
            abs(value - median_db) for value in db_values),
        "minimum_to_input1_db": min(db_values),
        "maximum_to_input1_db": max(db_values),
    }


def summarize_window(device, label):
    sources = []
    buses = {"main": [], "mixa": [], "mixb": []}
    ratios = {"main": [], "mixa": [], "mixb": []}
    for _ in range(SAMPLES_PER_WINDOW):
        response = device.read_state()
        if response is None:
            raise VoiceFxProbeError("JaSt read failed during meter sampling")
        values = device.floats(response)
        source = float(values[4])
        observed = {
            "main": (float(values[12]) + float(values[13])) / 2.0,
            "mixa": (float(values[14]) + float(values[15])) / 2.0,
            "mixb": (float(values[16]) + float(values[17])) / 2.0,
        }
        if source <= 0.0:
            raise VoiceFxProbeError("Input 1 meter reached zero")
        sources.append(source)
        for bus, value in observed.items():
            buses[bus].append(value)
            ratios[bus].append(value / source)
        time.sleep(SAMPLE_INTERVAL_SECONDS)
    metrics = {bus: _meter_metric(values)
               for bus, values in ratios.items()}
    return {
        "label": label,
        "samples": SAMPLES_PER_WINDOW,
        "median_input1": statistics.median(sources),
        "buses": {
            bus: dict(metric, median_output=statistics.median(buses[bus]))
            for bus, metric in metrics.items()
        },
    }


def _window_bus(window, bus):
    if "buses" in window:
        return window["buses"][bus]
    if bus != "main":
        raise KeyError(bus)
    # Compatibility for focused unit-test fixtures and v1 attempt inspection.
    return {
        "median_output": window["median_main"],
        "median_to_input1_db": window["median_main_to_input1_db"],
        "mad_to_input1_db": window["mad_main_to_input1_db"],
    }


def classify_measurements(control_low, control_high, trials):
    source_delta = _db(control_high["median_input1"] /
                       control_low["median_input1"])
    available_buses = ("main",) if "buses" not in control_low else \
        ("main", "mixa", "mixb")
    output_deltas = {
        bus: _db(_window_bus(control_high, bus)["median_output"] /
                 _window_bus(control_low, bus)["median_output"])
        for bus in available_buses
    }
    selected_bus = max(output_deltas, key=output_deltas.get)
    selected_delta = output_deltas[selected_bus]
    control_valid = (source_delta >= CONTROL_INPUT_DELTA_MIN_DB and
                     selected_delta >= CONTROL_MAIN_DELTA_MIN_DB)
    models = []
    for trial in trials:
        before = _window_bus(trial["off_before"], selected_bus)
        active = _window_bus(trial["on"], selected_bus)
        after = _window_bus(trial["off_after"], selected_bus)
        off_midpoint = (before["median_to_input1_db"] +
                        after["median_to_input1_db"]) / 2.0
        delta = active["median_to_input1_db"] - off_midpoint
        drift = after["median_to_input1_db"] - before["median_to_input1_db"]
        uncertainty = max(before["mad_to_input1_db"],
                          active["mad_to_input1_db"],
                          after["mad_to_input1_db"], 1e-6)
        stable = abs(drift) <= OFF_DRIFT_MAX_DB
        detected = (control_valid and stable and
                    abs(delta) >= max(EFFECT_DELTA_MIN_DB, 6.0 * uncertainty))
        models.append({
            "model": trial["model"],
            "active_delta_db": delta,
            "off_drift_db": drift,
            "maximum_window_mad_db": uncertainty,
            "stable": stable,
            "meter_effect_detected": detected,
        })
    if not control_valid:
        classification = "INCONCLUSIVE_METER_ROUTE_CONTROL_FAILED"
    elif any(not row["stable"] for row in models):
        classification = "INCONCLUSIVE_OFF_BASELINE_DRIFT"
    elif any(row["meter_effect_detected"] for row in models):
        classification = "DIRECT_BLOCK201_METER_EFFECT_DETECTED"
    else:
        classification = "NO_DIRECT_BLOCK201_METER_EFFECT_DETECTED"
    return {
        "classification": classification,
        "scope": "DIRECT_MODEL_SELECT_AND_PARAMETER_WRITES_ONLY",
        "control": {
            "valid": control_valid,
            "input1_gain_response_db": source_delta,
            "selected_bus": selected_bus,
            "selected_bus_gain_response_db": selected_delta,
            "bus_gain_responses_db": output_deltas,
        },
        "models": models,
    }


def run_sequence(device, restore_fx, restore_gate, sample_one, settle=time.sleep,
                 progress=lambda _message: None):
    before = _readable_state(device.read_params())
    _assert_guards(before)
    result = {
        "status": "MEASUREMENT_FAILED_RESTORATION_PENDING",
        "started": _now(),
        "readable_before": before,
        "restore_fx": restore_fx,
        "restore_gate": restore_gate,
        "trials": [],
    }
    failure = None
    try:
        device.set_main_volume(SAFE_OUTPUT_VOLUME)
        device.set_hp_volume(SAFE_OUTPUT_VOLUME)
        device.gate_off(1)
        settle(SETTLE_SECONDS)
        low = sample_one("gain_control_low")
        device.set_gain(1, PROBE_INPUT_GAIN_DB)
        settle(SETTLE_SECONDS)
        guarded = _readable_state(device.read_params())
        _assert_guards(guarded)
        if not math.isclose(guarded["main_volume"], SAFE_OUTPUT_VOLUME,
                            abs_tol=1e-6) or \
                not math.isclose(guarded["headphone_volume"],
                                 SAFE_OUTPUT_VOLUME, abs_tol=1e-6) or \
                not math.isclose(guarded["input1_gain_db"],
                                 PROBE_INPUT_GAIN_DB, abs_tol=1e-6):
            raise VoiceFxProbeError("readable safety controls did not latch")
        result["readable_guarded"] = guarded
        high = sample_one("gain_control_high")
        result["gain_control"] = {"low": low, "high": high}

        for model, parameters in MODEL_PROFILES:
            progress("measuring %s" % model)
            off = dict(parameters, on=False)
            on = dict(parameters, on=True)
            device.set_fx(model, **off)
            settle(SETTLE_SECONDS)
            off_before = sample_one(model + "_off_before")
            device.set_fx(model, **on)
            settle(SETTLE_SECONDS)
            active = sample_one(model + "_on")
            device.set_fx(model, **off)
            settle(SETTLE_SECONDS)
            off_after = sample_one(model + "_off_after")
            result["trials"].append({
                "model": model,
                "parameters": parameters,
                "off_before": off_before,
                "on": active,
                "off_after": off_after,
            })
        result["analysis"] = classify_measurements(
            low, high, result["trials"])
        result["status"] = "MEASURED_RESTORATION_PENDING"
    except BaseException as error:
        failure = error
        result["error"] = {"type": type(error).__name__,
                           "message": str(error)}
    finally:
        restoration_errors = []
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
        restored_controls = []
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
        try:
            settle(SETTLE_SECONDS)
            after = _readable_state(device.read_params())
            _assert_guards(after)
            readable_exact = (
                after["flags"] == before["flags"] and
                after["input1_gain_db"] == before["input1_gain_db"] and
                after["input2_gain_db"] == before["input2_gain_db"] and
                after["main_volume"] == before["main_volume"] and
                after["headphone_volume"] == before["headphone_volume"])
            result["readable_after"] = after
        except BaseException as error:
            readable_exact = False
            restoration_errors.append({
                "control": "readback", "type": type(error).__name__,
                "message": str(error),
            })
        result["restoration"] = {
            "readable_exact": readable_exact,
            "restored_controls": restored_controls,
            "voicefx": "HOST_KNOWN_WRITE_ONLY_INTENT_RESENT",
            "channel1_gate": "HOST_KNOWN_WRITE_ONLY_INTENT_RESENT",
            "mixer_routes": "UNTOUCHED",
            "preset_slots": "UNTOUCHED",
            "dsp_amount": "UNTOUCHED",
            "processing_channel": "UNTOUCHED",
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


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def run_live(output_dir, battery_path, shadow_path):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise VoiceFxProbeError("output directory must exist and be empty")
    restore_fx = restore_fx_from_shadow(shadow_path)
    restore_gate = restore_gate_from_shadow(shadow_path)
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": _now(),
        "device": {
            "serial": foundation.EXPECTED_SERIAL,
            "bcd_device": "%04x" % foundation.EXPECTED_BCD_DEVICE,
        },
        "sample_rate_hz": RATE_HZ,
        "stimulus": "INPUT1_PREAMP_SELF_NOISE",
        "observation": "SIMULTANEOUS_JAST_INPUT1_AND_MAIN_LR_METERS",
        "playback": "NONE",
        "mixer_routes": "UNTOUCHED",
        "preset_slots": "UNTOUCHED",
        "dsp_amount": "UNTOUCHED",
        "processing_channel": "UNTOUCHED",
    }
    device = None
    try:
        battery = foundation._battery(battery_path)
        report["battery_before"] = battery
        if battery <= foundation.BATTERY_FLOOR:
            report["status"] = "BLOCKED_BATTERY"
            return report
        device = foundation._open_checked()
        sequence = run_sequence(
            device, restore_fx, restore_gate,
            lambda label: summarize_window(device, label),
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
            "models": [model for model, _parameters in MODEL_PROFILES],
            "samples_per_window": SAMPLES_PER_WINDOW,
            "sample_interval_seconds": SAMPLE_INTERVAL_SECONDS,
            "writes": ["Main volume", "Headphone volume", "Input 1 gain",
                       "Channel 1 gate bypass/restore",
                       "Voice FX block 201 model/parameters"],
            "mixer_routes": "UNTOUCHED",
            "preset_slots": "UNTOUCHED",
            "dsp_amount": "UNTOUCHED",
            "processing_channel": "UNTOUCHED",
        }, indent=2, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--execute requires --output-dir")
    report = run_live(args.output_dir, args.battery_path, args.shadow_path)
    _write_json(Path(args.output_dir) / "live-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "MEASURED_AND_RESTORED" else 3


if __name__ == "__main__":
    sys.exit(main())
