#!/usr/bin/env python3
"""Reversible inactive-slot save/recall probe using internal io24 meters.

Slot 1 is used only when it is inactive and its complete original body is in
the identity-scoped Host registry.  The probe writes flat/boosted/flat test
records, recalls each after selecting away, then resends the original body and
restores the original selector and readable controls.
"""

import argparse
from copy import deepcopy
import datetime as dt
import hashlib
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

import io24_presets  # noqa: E402
from io24_preset_record import DeviceSlotRegistry  # noqa: E402
import io24_loopback_foundation as foundation  # noqa: E402
import io24_voicefx_meter_probe as meter  # noqa: E402


SCHEMA = "io24-inactive-slot-recall-meter-probe-v1"
TARGET_CHANNEL = 1
TARGET_SLOT = 1
SAFE_OUTPUT_VOLUME = 0.01
PROBE_INPUT_GAIN_DB = 60.0
SETTLE_SECONDS = 0.5
RECALL_SETTLE_SECONDS = 0.8
EFFECT_DELTA_MIN_DB = 1.0
FLAT_DRIFT_MAX_DB = 0.75


class SlotProbeError(RuntimeError):
    pass


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _record_sha256(record):
    encoded = json.dumps(record, allow_nan=False, ensure_ascii=False,
                         separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _enabled(params, channel):
    bit = 5 if channel == 1 else 6
    return not bool(int(params["flags"]) >> bit & 1)


def _readable_state(params):
    if params is None:
        raise SlotProbeError("JaSt read failed")
    return {
        "flags": int(params["flags"]),
        "input1_gain_db": float(params["input1Gain"]),
        "input2_gain_db": float(params["input2Gain"]),
        "headphone_volume": float(params["hpVolume"]),
        "main_volume": float(params["mainVolume"]),
        "input1_slot": int(params["input1SlotIndex"]),
        "input2_slot": int(params["input2SlotIndex"]),
        "input1_processing_channel": int(params["input1ProcessingChannel"]),
        "input2_processing_channel": int(params["input2ProcessingChannel"]),
        "input1_phantom": bool(params["input1PhantomPower"]),
        "input2_phantom": bool(params["input2PhantomPower"]),
        "input1_processing_enabled": _enabled(params, 1),
        "channel_linked": bool(int(params["flags"]) >> 12 & 1),
    }


def _assert_guards(state):
    if state["input1_phantom"] or state["input2_phantom"]:
        raise SlotProbeError("phantom must be off on both inputs")
    if state["channel_linked"]:
        raise SlotProbeError("stereo link must be off before any test write")
    if (state["input1_processing_channel"],
            state["input2_processing_channel"]) != (0, 1):
        raise SlotProbeError("processing-channel permutation must remain 0/1")
    if not state["input1_processing_enabled"]:
        raise SlotProbeError(
            "Input 1 processing must already be positive; the probe will not "
            "replace its unknown scalar")


def build_test_records(original):
    """Return two complete records differing only in Standard EQ band 4."""
    off_band = {"shape": "off", "freq": 1000.0, "gain": 0.0, "q": 0.7}
    flat_bands = [dict(off_band) for _index in range(4)]
    boosted_bands = deepcopy(flat_bands)
    boosted_bands[3] = {
        "shape": "highshelf", "freq": 1000.0, "gain": 15.0, "q": 0.7}
    common = {
        "hpf_hz": 24.0,
        "eq_first": True,
        "gate": {
            "on": False, "threshold_db": -84.0, "range_db": -84.0,
            "attack_s": 0.005, "release_s": 0.7, "keyfilter_hz": 20.0,
            "keylisten": False, "expander": True,
        },
        "compressor_model": 0,
        "compressor": {
            "on": False, "threshold_db": -24.0, "ratio": 2.0,
            "attack_s": 0.02, "release_s": 0.15, "gain_db": 0.0,
            "softknee": False, "automode": False,
            "keyfilter_hz": 20.0, "keylisten": False,
        },
        "limiter": {"on": False, "threshold_db": -28.0},
        "voicefx_model": "transformer",
        "voicefx": {
            "on": False, "lows": 0.0, "width": 0.5, "mix": 0.0},
    }
    flat = io24_presets.current_slot_record(
        original, "CP34 FLAT RECALL PROBE", bands=flat_bands, **common)
    boosted = io24_presets.current_slot_record(
        original, "CP34 BOOST RECALL PROBE", bands=boosted_bands, **common)
    return flat, boosted


def classify_windows(flat_before, boosted, flat_after):
    def value(window):
        return window["buses"]["main"]["median_to_input1_db"]

    before = value(flat_before)
    active = value(boosted)
    after = value(flat_after)
    drift = after - before
    delta = active - (before + after) / 2.0
    stable = abs(drift) <= FLAT_DRIFT_MAX_DB
    recalled = stable and abs(delta) >= EFFECT_DELTA_MIN_DB
    return {
        "classification": (
            "INACTIVE_SLOT_SAVE_RECALL_EFFECT_DETECTED" if recalled else
            "INCONCLUSIVE_FLAT_BASELINE_DRIFT" if not stable else
            "NO_SAVED_BODY_RECALL_EFFECT_DETECTED"),
        "boost_delta_db": delta,
        "flat_drift_db": drift,
        "stable": stable,
        "saved_body_recall_effect_detected": recalled,
    }


def run_sequence(device, original, flat, boosted, sample_one,
                 settle=time.sleep, progress=lambda _message: None):
    before = _readable_state(device.read_params())
    _assert_guards(before)
    if before["input1_slot"] == TARGET_SLOT:
        raise SlotProbeError("target slot 1 is active; no write was attempted")
    if before["input1_slot"] not in (0, 1):
        raise SlotProbeError("Input 1 selector is outside its physical pair")
    result = {
        "status": "MEASUREMENT_FAILED_RESTORATION_PENDING",
        "started": _now(),
        "readable_before": before,
        "target_channel": TARGET_CHANNEL,
        "target_slot": TARGET_SLOT,
        "original_record_sha256": _record_sha256(original),
        "test_records": {
            "flat_sha256": _record_sha256(flat),
            "boosted_sha256": _record_sha256(boosted),
        },
        "writes": [],
        "windows": [],
    }
    failure = None
    mutation_started = False
    try:
        device.set_main_volume(SAFE_OUTPUT_VOLUME)
        device.set_hp_volume(SAFE_OUTPUT_VOLUME)
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
            raise SlotProbeError("readable safety controls did not latch")
        result["readable_guarded"] = guarded

        sequence = (("flat_before", flat), ("boosted", boosted),
                    ("flat_after", flat))
        for label, record in sequence:
            progress("writing and recalling %s" % label)
            device.set_preset_slot(TARGET_CHANNEL, before["input1_slot"])
            settle(SETTLE_SECONDS)
            mutation_started = True
            transport = device.save_uc_device_slot(TARGET_SLOT, record)
            result["writes"].append({
                "label": label, "record_sha256": _record_sha256(record),
                "transport": transport,
            })
            settle(SETTLE_SECONDS)
            recall = device.recall_device_slot(TARGET_CHANNEL, TARGET_SLOT)
            settle(RECALL_SETTLE_SECONDS)
            observed = _readable_state(device.read_params())
            _assert_guards(observed)
            if observed["input1_slot"] != TARGET_SLOT:
                raise SlotProbeError("Input 1 did not select target slot 1")
            result["windows"].append({
                "label": label,
                "recall": recall,
                "readable": observed,
                "meter": sample_one(label),
            })

        by_label = {entry["label"]: entry["meter"]
                    for entry in result["windows"]}
        result["analysis"] = classify_windows(
            by_label["flat_before"], by_label["boosted"],
            by_label["flat_after"])
        result["status"] = "MEASURED_RESTORATION_PENDING"
    except BaseException as error:
        failure = error
        result["error"] = {"type": type(error).__name__,
                           "message": str(error)}
    finally:
        restoration_errors = []
        restored_controls = []
        actions = []
        if mutation_started:
            actions.extend((
                (lambda: device.set_preset_slot(
                    TARGET_CHANNEL, before["input1_slot"]),
                 "input1_slot_before_original_write"),
                (lambda: device.save_uc_device_slot(TARGET_SLOT, original),
                 "original_slot1_body"),
                (lambda: device.set_preset_slot(
                    TARGET_CHANNEL, before["input1_slot"]),
                 "input1_slot_final"),
            ))
        actions.extend((
            (lambda: device.set_gain(1, before["input1_gain_db"]),
             "input1_gain"),
            (lambda: device.set_main_volume(before["main_volume"]),
             "main_volume"),
            (lambda: device.set_hp_volume(before["headphone_volume"]),
             "headphone_volume"),
        ))
        for action, control in actions:
            try:
                report = action()
                restored_controls.append({"control": control,
                                          "report": report})
            except BaseException as error:
                restoration_errors.append({
                    "control": control, "type": type(error).__name__,
                    "message": str(error),
                })
        try:
            settle(SETTLE_SECONDS)
            after = _readable_state(device.read_params())
            _assert_guards(after)
            readable_exact = (
                after["flags"] == before["flags"] and
                after["input1_slot"] == before["input1_slot"] and
                after["input2_slot"] == before["input2_slot"] and
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
            "mutation_started": mutation_started,
            "readable_exact": readable_exact,
            "original_slot1_body": (
                "RESTORE_SENT" if mutation_started else "NOT_NEEDED"),
            "restored_controls": restored_controls,
            "registry": "UNTOUCHED",
            "mixer_routes": "UNTOUCHED",
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


def run_live(output_dir, battery_path, registry_path):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise SlotProbeError("output directory must exist and be empty")
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": _now(),
        "device": {
            "serial": foundation.EXPECTED_SERIAL,
            "bcd_device": "%04x" % foundation.EXPECTED_BCD_DEVICE,
        },
        "sample_rate_hz": meter.RATE_HZ,
        "stimulus": "INPUT1_PREAMP_SELF_NOISE",
        "observation": "SIMULTANEOUS_JAST_INPUT1_AND_BUS_METERS",
        "playback": "NONE",
        "registry": "READ_ONLY",
        "mixer_routes": "UNTOUCHED",
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
        identity = device._device_slot_identity()
        registry = DeviceSlotRegistry(registry_path)
        entry = registry.get(TARGET_SLOT, device_identity=identity)
        if entry is None:
            raise SlotProbeError(
                "slot 1 has no identity-matched Host-known original body")
        original = entry["record"]
        if _record_sha256(original) != entry["canonical_sha256"]:
            raise SlotProbeError("slot 1 registry record hash differs")
        flat, boosted = build_test_records(original)
        report["registry_original"] = {
            "slot": entry["slot"],
            "preset_name": original["preset_name"],
            "canonical_sha256": entry["canonical_sha256"],
            "provenance": entry["provenance"],
            "status": entry["status"],
        }
        sequence = run_sequence(
            device, original, flat, boosted,
            lambda label: meter.summarize_window(device, label),
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
    parser.add_argument("--registry-path", default=str(
        Path.home() / ".local/state/io24/device-slots.json"))
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "DRY_RUN_ONLY",
            "target_channel": TARGET_CHANNEL,
            "target_slot": TARGET_SLOT,
            "sequence": ["flat", "boosted", "flat", "restore original"],
            "registry": "READ_ONLY",
            "mixer_routes": "UNTOUCHED",
            "dsp_amount": "UNTOUCHED",
            "processing_channel": "UNTOUCHED",
        }, indent=2, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--execute requires --output-dir")
    report = run_live(args.output_dir, args.battery_path, args.registry_path)
    _write_json(Path(args.output_dir) / "live-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "MEASURED_AND_RESTORED" else 3


if __name__ == "__main__":
    sys.exit(main())
