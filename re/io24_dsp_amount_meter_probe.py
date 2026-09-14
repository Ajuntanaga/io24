#!/usr/bin/env python3
"""No-cable DSP Amount probe using simultaneous JaSt Input-2/Main meters."""

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RE_DIR = Path(__file__).resolve().parent
for directory in (ROOT, RE_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import io24_dsp_amount_capture as amount_capture  # noqa: E402
import io24_loopback_foundation as foundation  # noqa: E402


SCHEMA = "io24-dsp-amount-meter-probe-v1"
CAPTURE_ORDER = (0.0, 1.0, 0.25, 0.75, 0.5)
SORTED_AMOUNTS = (0.0, 0.25, 0.5, 0.75, 1.0)
SAFE_MAIN_VOLUME = 0.01
PROBE_FREQ_HZ = 1000.0
PROBE_GAIN_DB = 15.0
PROBE_Q = 0.7
RATE_HZ = 96000
SAMPLES_PER_AMOUNT = 240
ENDPOINT_DELTA_MIN = 0.03
POSITION_TOLERANCE = 0.08


class MeterProbeError(RuntimeError):
    pass


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def classify_ratios(amounts, ratios):
    amounts = tuple(float(value) for value in amounts)
    values = [float(value) for value in ratios]
    if amounts != SORTED_AMOUNTS or len(values) != len(SORTED_AMOUNTS):
        raise ValueError("amounts_must_equal_0_25_50_75_100_percent")
    if not all(math.isfinite(value) and value >= 0.0 for value in values):
        raise ValueError("ratios_must_be_finite_and_nonnegative")
    dry, wet = values[0], values[-1]
    delta = wet - dry
    delta_ratio = abs(delta) / max(abs(dry), abs(wet), 1e-15)
    result = {
        "status": "VALID",
        "classification": "INCONCLUSIVE",
        "interpretation": "NO_DEVICE_ARCHITECTURE_CONCLUSION",
        "endpoint_delta_ratio": delta_ratio,
        "amount_measurements": [],
        "reasons": [],
    }
    if delta_ratio < ENDPOINT_DELTA_MIN:
        result.update({
            "status": "INCONCLUSIVE",
            "classification": "ENDPOINT_RATIOS_INDISTINGUISHABLE",
            "reasons": ["endpoint_meter_ratio_delta_below_threshold"],
        })
        return result
    positions = [(value - dry) / delta for value in values]
    result["amount_measurements"] = [
        {"amount": amount, "main_to_input2_ratio": value,
         "endpoint_position": position}
        for amount, value, position in zip(amounts, values, positions)
    ]
    gate_error = max(abs(position - 1.0) for position in positions[1:-1])
    linear_error = max(abs(position - amount)
                       for amount, position in zip(amounts, positions))
    monotonic = (all(right >= left - POSITION_TOLERANCE
                     for left, right in zip(positions, positions[1:])) or
                 all(right <= left + POSITION_TOLERANCE
                     for left, right in zip(positions, positions[1:])))
    if gate_error <= POSITION_TOLERANCE:
        result["classification"] = "ZERO_NONZERO_GATE"
    elif linear_error <= POSITION_TOLERANCE:
        result["classification"] = "LINEAR_METER_ENDPOINT_INTERPOLATION"
        result["interpretation"] = \
            "CONSISTENT_WITH_LINEAR_DRY_WET_NOT_ARCHITECTURE_PROOF"
    elif monotonic:
        result["classification"] = "NONLINEAR_MONOTONIC_METER_BLEND"
    else:
        result["reasons"] = ["meter_ratios_do_not_match_candidate_models"]
    return result


def run_meter_sequence(device, sample_one, settle=time.sleep):
    before = amount_capture._readable_state(device.read_params())
    amount_capture._assert_identity_guards(before)
    if before["input2_processing_enabled"]:
        raise MeterProbeError("Input 2 DSP Amount prestate must be exact zero")
    result = {
        "status": "MEASUREMENT_FAILED_RESTORATION_PENDING",
        "started": _now(),
        "readable_before": before,
        "capture_order": list(CAPTURE_ORDER),
        "measurements": [],
    }
    failure = None
    try:
        device.set_main_volume(SAFE_MAIN_VOLUME)
        device.set_eq_band(
            2, 0, shape="highshelf", freq_hz=PROBE_FREQ_HZ,
            gain_db=PROBE_GAIN_DB, q=PROBE_Q, fs=float(RATE_HZ))
        settle(0.4)
        for amount in CAPTURE_ORDER:
            device.set_fx_mix(2, amount)
            settle(0.4)
            observed = amount_capture._readable_state(device.read_params())
            amount_capture._assert_identity_guards(observed)
            if observed["input2_processing_enabled"] != (amount > 0.0):
                raise MeterProbeError(
                    "DSP Amount zero/nonzero readback mismatch at %.2f" % amount)
            result["measurements"].append(sample_one(amount))
        result["status"] = "MEASURED_RESTORATION_PENDING"
    except BaseException as error:
        failure = error
        result["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        restoration_errors = []
        for action, control in (
                (lambda: device.set_fx_mix(2, 0.0), "dsp_amount"),
                (lambda: device.set_eq_band(
                    2, 0, shape="off", freq_hz=PROBE_FREQ_HZ,
                    gain_db=0.0, q=PROBE_Q, fs=float(RATE_HZ)), "eq_band_0"),
                (lambda: device.set_main_volume(before["main_volume"]),
                 "main_volume")):
            try:
                action()
            except BaseException as error:
                restoration_errors.append({
                    "control": control,
                    "type": type(error).__name__,
                    "message": str(error),
                })
        try:
            settle(0.4)
            after = amount_capture._readable_state(device.read_params())
            amount_capture._assert_identity_guards(after)
            readable_exact = (
                not after["input2_processing_enabled"] and
                math.isclose(after["main_volume"], before["main_volume"],
                             abs_tol=1e-6) and
                after["input1_gain_db"] == before["input1_gain_db"] and
                after["input2_gain_db"] == before["input2_gain_db"])
            result["readable_after"] = after
        except BaseException as error:
            readable_exact = False
            restoration_errors.append({
                "control": "readback",
                "type": type(error).__name__,
                "message": str(error),
            })
        result["restoration"] = {
            "readable_exact": readable_exact,
            "dsp_amount": "EXACT_ZERO_SENT",
            "eq_band_0": "IDENTITY_COEFFICIENTS_SENT",
            "main_volume": "RESTORE_SENT",
            "input_gains": "UNTOUCHED",
            "mixer_routes": "UNTOUCHED",
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


def _summarize_meter(device, amount):
    input2 = []
    main = []
    mixa = []
    ratios = []
    for _ in range(SAMPLES_PER_AMOUNT):
        response = device.read_state()
        if response is None:
            raise MeterProbeError("JaSt read failed during meter sampling")
        values = device.floats(response)
        source = float(values[6])
        main_value = (float(values[12]) + float(values[13])) / 2.0
        mixa_value = (float(values[14]) + float(values[15])) / 2.0
        if source <= 0.0:
            raise MeterProbeError("Input 2 meter reached zero")
        input2.append(source)
        main.append(main_value)
        mixa.append(mixa_value)
        ratios.append(main_value / source)
    ratio_array = np.asarray(ratios)
    median = float(np.median(ratio_array))
    mad = float(np.median(np.abs(ratio_array - median)))
    return {
        "amount": float(amount),
        "samples": SAMPLES_PER_AMOUNT,
        "median_input2": float(np.median(input2)),
        "median_main": float(np.median(main)),
        "median_mixa": float(np.median(mixa)),
        "median_main_to_input2": median,
        "mad_main_to_input2": mad,
        "minimum_main_to_input2": float(np.min(ratio_array)),
        "maximum_main_to_input2": float(np.max(ratio_array)),
    }


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def run_live(output_dir, battery_path):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise MeterProbeError("output directory must exist and be empty")
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": _now(),
        "device": {
            "serial": foundation.EXPECTED_SERIAL,
            "bcd_device": "%04x" % foundation.EXPECTED_BCD_DEVICE,
        },
        "probe": {
            "block": "eq", "band": 0, "channel": 2,
            "shape": "highshelf", "frequency_hz": PROBE_FREQ_HZ,
            "gain_db": PROBE_GAIN_DB, "q": PROBE_Q,
            "observation": "JaSt Input 2 and Main L/R meters",
        },
        "playback": "NONE",
        "mixer_routes": "UNTOUCHED",
        "input_gains": "UNTOUCHED",
    }
    device = None
    try:
        battery = foundation._battery(battery_path)
        report["battery_before"] = battery
        if battery <= foundation.BATTERY_FLOOR:
            report["status"] = "BLOCKED_BATTERY"
            return report
        device = foundation._open_checked()
        report["dsp_amount_prestate"] = amount_capture.resolve_restore_amount(
            {}, device.read_params(), 2)
        sequence = run_meter_sequence(device, lambda amount: _summarize_meter(
            device, amount))
        report["sequence"] = sequence
        report["transport"] = list(device.transport_log)
        if sequence["status"] != "MEASURED_AND_RESTORED":
            report["status"] = sequence["status"]
            return report
        ordered = sorted(sequence["measurements"], key=lambda row: row["amount"])
        analysis = classify_ratios(
            SORTED_AMOUNTS,
            [row["median_main_to_input2"] for row in ordered])
        analysis["ordered_measurements"] = ordered
        report["analysis"] = analysis
        report["status"] = (
            "MEASURED_CLASSIFIED_RESTORED" if analysis["status"] == "VALID"
            else "MEASURED_INCONCLUSIVE_RESTORED")
    except BaseException as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
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
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "DRY_RUN_ONLY",
            "capture_order": list(CAPTURE_ORDER),
            "samples_per_amount": SAMPLES_PER_AMOUNT,
            "writes": ["Main volume", "EQ band 0 coefficients",
                       "Channel 2 DSP Amount"],
            "playback": "NONE",
            "mixer_routes": "UNTOUCHED",
        }, indent=2, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--execute requires --output-dir")
    report = run_live(args.output_dir, args.battery_path)
    _write_json(Path(args.output_dir) / "live-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in (
        "MEASURED_CLASSIFIED_RESTORED",
        "MEASURED_INCONCLUSIVE_RESTORED") else 3


if __name__ == "__main__":
    sys.exit(main())
