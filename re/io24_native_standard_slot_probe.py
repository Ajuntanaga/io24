#!/usr/bin/env python3
"""Reversible no-cable probe of a native Standard-EQ device-slot body.

The probe uses inactive Channel-2 slot 3. It writes native flat/boosted/flat
records derived from the pinned Piano firmware strip, measures Input-2/Main
meters, then restores the native Piano body and the exact readable prestate.
It performs no playback, firmware operation, reset, DFU, Wine, routing change,
DSP Amount change, or registry mutation.
"""

import argparse
from copy import deepcopy
import datetime as dt
import hashlib
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
import io24_native_stat as native  # noqa: E402


SCHEMA = "io24-native-standard-slot-meter-probe-v1"
FIRMWARE_SHA256 = (
    "65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a"
    "7679e387952eb1a")
PIANO_NATIVE_OFFSET = 0x69230
PIANO_NATIVE_LENGTH = 0x440
TARGET_CHANNEL = 2
TARGET_SLOT = 3
SAFE_OUTPUT_VOLUME = 0.01
PROBE_INPUT_GAIN_DB = 60.0
SAMPLES_PER_WINDOW = 40
SAMPLE_INTERVAL_SECONDS = 0.05
SETTLE_SECONDS = 0.5
RECALL_SETTLE_SECONDS = 0.8
EFFECT_DELTA_MIN_DB = 1.0
FLAT_DRIFT_MAX_DB = 0.75
EXPECTED_REGISTRY_HASH = (
    "d58136ce09a602d5b291233ba2f2f742023a4bb56459edd771eea20e335bbd8f")


class NativeSlotProbeError(RuntimeError):
    pass


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _record_sha256(record):
    return hashlib.sha256(record).hexdigest()


def build_test_records(firmware, piano_eq):
    """Build the native Piano restore plus isolated flat/boosted EQ bodies."""
    firmware = bytes(firmware)
    digest = hashlib.sha256(firmware).hexdigest()
    if digest != FIRMWARE_SHA256:
        raise NativeSlotProbeError(
            "firmware SHA-256 differs from pinned 1.28 application")
    if not isinstance(piano_eq, dict):
        raise NativeSlotProbeError("Piano Standard EQ state is unavailable")

    source = firmware[
        PIANO_NATIVE_OFFSET:PIANO_NATIVE_OFFSET + PIANO_NATIVE_LENGTH]
    source = native.validate_native_stat_record(source, 0)
    decoded = native.decode_native_stat_record(source)
    channel = tuple(chunk for chunk in decoded.chunks
                    if chunk.key == native.CHANNEL_STRIP_KEY)
    if len(channel) != 1:
        raise NativeSlotProbeError("pinned Piano record lacks one channel strip")
    restore = native.encode_native_stat_record(
        native.NativeStatRecord(decoded.version, channel))
    restore = native.validate_native_stat_record(restore, TARGET_SLOT)

    flat_eq = deepcopy(piano_eq)
    flat_eq["eqallon"] = 0

    boosted_eq = deepcopy(piano_eq)
    boosted_eq["eqallon"] = 1
    for band in range(1, 5):
        boosted_eq["eqbandon%d" % band] = 0
    boosted_eq.update({
        "eqbandon4": 1,
        "eqbandop4": 1,
        "eqfreq4": 1000.0,
        "eqgain4": 15.0,
        "eqq4": 0.7,
    })
    flat = native.build_native_standard_eq_stat_record(
        restore, TARGET_SLOT, flat_eq)
    boosted = native.build_native_standard_eq_stat_record(
        restore, TARGET_SLOT, boosted_eq)
    return {"restore": restore, "flat": flat, "boosted": boosted}


def _enabled(params, channel):
    bit = 5 if channel == 1 else 6
    return not bool(int(params["flags"]) >> bit & 1)


def _readable_state(params):
    if params is None:
        raise NativeSlotProbeError("JaSt read failed")
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
        "input2_processing_enabled": _enabled(params, 2),
        "channel_linked": bool(int(params["flags"]) >> 12 & 1),
    }


def _assert_guards(state):
    if state["input1_phantom"] or state["input2_phantom"]:
        raise NativeSlotProbeError("phantom must be off on both inputs")
    if state["channel_linked"]:
        raise NativeSlotProbeError("stereo link must be off")
    if (state["input1_processing_channel"],
            state["input2_processing_channel"]) != (0, 1):
        raise NativeSlotProbeError(
            "processing-channel permutation must remain 0/1")
    if state["input1_slot"] not in (0, 1) or state["input2_slot"] not in (2, 3):
        raise NativeSlotProbeError("slot selectors are outside physical pairs")
    if not state["input2_processing_enabled"]:
        raise NativeSlotProbeError(
            "Input 2 processing must already be enabled")


def classify_windows(flat_before, boosted, flat_after):
    before = float(flat_before["median_main_to_input2_db"])
    active = float(boosted["median_main_to_input2_db"])
    after = float(flat_after["median_main_to_input2_db"])
    drift = after - before
    delta = active - (before + after) / 2.0
    uncertainty = max(float(window["mad_main_to_input2_db"])
                      for window in (flat_before, boosted, flat_after))
    stable = abs(drift) <= FLAT_DRIFT_MAX_DB
    detected = stable and abs(delta) >= max(
        EFFECT_DELTA_MIN_DB, 6.0 * uncertainty)
    return {
        "classification": (
            "NATIVE_STANDARD_SLOT_RECALL_EFFECT_DETECTED" if detected else
            "INCONCLUSIVE_FLAT_BASELINE_DRIFT" if not stable else
            "NO_NATIVE_SLOT_RECALL_EFFECT_DETECTED"),
        "boost_delta_db": delta,
        "flat_drift_db": drift,
        "maximum_window_mad_db": uncertainty,
        "stable": stable,
        "native_slot_recall_effect_detected": detected,
    }


def run_sequence(device, records, sample_one, settle=time.sleep,
                 progress=lambda _message: None):
    if set(records) != {"restore", "flat", "boosted"}:
        raise NativeSlotProbeError("native record set is incomplete")
    for record in records.values():
        native.validate_native_stat_record(record, TARGET_SLOT)
    before = _readable_state(device.read_params())
    _assert_guards(before)
    if before["input2_slot"] == TARGET_SLOT:
        raise NativeSlotProbeError(
            "target slot 3 is active; no write was attempted")

    result = {
        "status": "MEASUREMENT_FAILED_RESTORATION_PENDING",
        "started": _now(),
        "target_channel": TARGET_CHANNEL,
        "target_slot": TARGET_SLOT,
        "readable_before": before,
        "record_sha256": {name: _record_sha256(record)
                          for name, record in records.items()},
        "writes": [],
        "windows": [],
    }
    failure = None
    mutation_started = False
    try:
        device.set_main_volume(SAFE_OUTPUT_VOLUME)
        device.set_hp_volume(SAFE_OUTPUT_VOLUME)
        device.set_gain(TARGET_CHANNEL, PROBE_INPUT_GAIN_DB)
        settle(SETTLE_SECONDS)
        guarded = _readable_state(device.read_params())
        _assert_guards(guarded)
        if not math.isclose(guarded["main_volume"], SAFE_OUTPUT_VOLUME,
                            abs_tol=1e-6) or not math.isclose(
                                guarded["headphone_volume"],
                                SAFE_OUTPUT_VOLUME, abs_tol=1e-6) or not math.isclose(
                                    guarded["input2_gain_db"],
                                    PROBE_INPUT_GAIN_DB, abs_tol=1e-6):
            raise NativeSlotProbeError("readable safety controls did not latch")
        result["readable_guarded"] = guarded

        for label, record in (("flat_before", records["flat"]),
                              ("boosted", records["boosted"]),
                              ("flat_after", records["flat"])):
            progress("writing and recalling native %s" % label)
            device.set_preset_slot(TARGET_CHANNEL, before["input2_slot"])
            settle(SETTLE_SECONDS)
            mutation_started = True
            transport = device.save_device_slot(TARGET_SLOT, record)
            result["writes"].append({
                "label": label,
                "record_sha256": _record_sha256(record),
                "transport": transport,
            })
            settle(SETTLE_SECONDS)
            recall = device.recall_device_slot(TARGET_CHANNEL, TARGET_SLOT)
            settle(RECALL_SETTLE_SECONDS)
            observed = _readable_state(device.read_params())
            _assert_guards(observed)
            if observed["input2_slot"] != TARGET_SLOT:
                raise NativeSlotProbeError("Input 2 did not select slot 3")
            result["windows"].append({
                "label": label,
                "recall": recall,
                "readable": observed,
                "meter": sample_one(label),
            })

        windows = {row["label"]: row["meter"] for row in result["windows"]}
        result["analysis"] = classify_windows(
            windows["flat_before"], windows["boosted"], windows["flat_after"])
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
                    TARGET_CHANNEL, before["input2_slot"]),
                 "input2_slot_before_restore_write"),
                (lambda: device.save_device_slot(
                    TARGET_SLOT, records["restore"]),
                 "native_piano_slot3_body"),
                (lambda: device.set_preset_slot(
                    TARGET_CHANNEL, before["input2_slot"]),
                 "input2_slot_final"),
            ))
        actions.extend((
            (lambda: device.set_gain(TARGET_CHANNEL, before["input2_gain_db"]),
             "input2_gain"),
            (lambda: device.set_main_volume(before["main_volume"]),
             "main_volume"),
            (lambda: device.set_hp_volume(before["headphone_volume"]),
             "headphone_volume"),
        ))
        for action, control in actions:
            try:
                report = action()
                restored_controls.append({"control": control, "report": report})
            except BaseException as error:
                restoration_errors.append({
                    "control": control, "type": type(error).__name__,
                    "message": str(error),
                })
        try:
            settle(SETTLE_SECONDS)
            after = _readable_state(device.read_params())
            _assert_guards(after)
            readable_exact = all(after[key] == before[key] for key in (
                "flags", "input1_gain_db", "input2_gain_db",
                "headphone_volume", "main_volume", "input1_slot",
                "input2_slot", "input1_processing_channel",
                "input2_processing_channel"))
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
            "slot3_body": (
                "NATIVE_PIANO_RESTORE_SENT" if mutation_started else
                "NOT_NEEDED"),
            "slot_body_readback": "UNAVAILABLE",
            "restored_controls": restored_controls,
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


def summarize_window(device, label):
    ratios = []
    sources = []
    outputs = []
    for _ in range(SAMPLES_PER_WINDOW):
        response = device.read_state()
        if response is None:
            raise NativeSlotProbeError("JaSt read failed during meter window")
        values = device.floats(response)
        source = float(values[6])
        output = (float(values[12]) + float(values[13])) / 2.0
        if source <= 0.0 or output <= 0.0:
            raise NativeSlotProbeError("Input 2 or Main meter reached zero")
        sources.append(source)
        outputs.append(output)
        ratios.append(20.0 * math.log10(output / source))
        time.sleep(SAMPLE_INTERVAL_SECONDS)
    median = statistics.median(ratios)
    return {
        "label": label,
        "samples": SAMPLES_PER_WINDOW,
        "median_input2": statistics.median(sources),
        "median_main": statistics.median(outputs),
        "median_main_to_input2_db": median,
        "mad_main_to_input2_db": statistics.median(
            abs(value - median) for value in ratios),
        "minimum_main_to_input2_db": min(ratios),
        "maximum_main_to_input2_db": max(ratios),
    }


def _load_piano_eq(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return data["line"]["ch2"]["eq"]


def _validate_registry(path):
    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    entry = registry.get("slots", {}).get(str(TARGET_SLOT))
    if not isinstance(entry, dict) or entry.get("canonical_sha256") != \
            EXPECTED_REGISTRY_HASH:
        raise NativeSlotProbeError(
            "slot 3 registry is not the pinned Piano record")
    record = entry.get("record")
    if not isinstance(record, dict) or record.get("preset_name") != \
            "Piano Accomany":
        raise NativeSlotProbeError("slot 3 registry does not name Piano Accomany")
    return {
        "slot": TARGET_SLOT,
        "preset_name": record["preset_name"],
        "canonical_sha256": entry["canonical_sha256"],
        "provenance": entry.get("provenance"),
        "status": entry.get("status"),
    }


def run_live(output_dir, battery_path, firmware_path, scene_path, registry_path):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise NativeSlotProbeError("output directory must exist and be empty")
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": _now(),
        "target_channel": TARGET_CHANNEL,
        "target_slot": TARGET_SLOT,
        "sample_rate_hz": 96000,
        "stimulus": "INPUT2_PREAMP_SELF_NOISE",
        "observation": "SIMULTANEOUS_JAST_INPUT2_AND_MAIN_METERS",
        "playback": "NONE",
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
        report["registry_precondition"] = _validate_registry(registry_path)
        records = build_test_records(
            Path(firmware_path).read_bytes(), _load_piano_eq(scene_path))
        report["restore_basis"] = {
            "body": "PINNED_FIRMWARE_NATIVE_PIANO_CHANNEL_STRIP",
            "current_slot_body_readback": "UNAVAILABLE",
            "semantic_match_to_registry": True,
            "restore_sha256": _record_sha256(records["restore"]),
        }
        device = foundation._open_checked()
        report["device"] = device._device_slot_identity()
        sequence = run_sequence(
            device, records, lambda label: summarize_window(device, label),
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


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main(argv=None):
    default_scene = (ROOT / ".superpowers" / "sdd" /
                     "2026-08-28-cp34-preset-effect-control" / "runs" /
                     "20260914T031459-0700-native-slot-builder" / "backup" /
                     "Piano Accomany.scene")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    parser.add_argument("--firmware-path",
                        default="/home/ajuntanaga/.cache/io24/re/io24_fw.bin")
    parser.add_argument("--scene-path", default=str(default_scene))
    parser.add_argument("--registry-path", default=(
        "/home/ajuntanaga/.local/state/io24/device-slots.json"))
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "DRY_RUN_ONLY",
            "target_channel": TARGET_CHANNEL,
            "target_slot": TARGET_SLOT,
            "sequence": ["flat", "boosted", "flat", "native Piano restore"],
            "playback": "NONE",
            "mixer_routes": "UNTOUCHED",
            "dsp_amount": "UNTOUCHED",
            "processing_channel": "UNTOUCHED",
        }, indent=2, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--execute requires --output-dir")
    report = run_live(
        args.output_dir, args.battery_path, args.firmware_path,
        args.scene_path, args.registry_path)
    _write_json(Path(args.output_dir) / "live-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "MEASURED_AND_RESTORED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
