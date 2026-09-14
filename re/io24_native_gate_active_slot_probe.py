#!/usr/bin/env python3
"""Reversible native gate probe matching UC's active-slot write condition.

The earlier A/B/A tests wrote inactive Channel-2 slot 3. Exact UC 4.7.2 code
writes only the currently selected slot after a settled edit. This probe makes
slot 3 active before each native ``MemP/Stat(3)`` write, forces a 2 -> 3 recall
edge, and measures Input-2/Main meters. It changes no routing, DSP Amount,
processing-channel assignment, playback, firmware, reset, DFU, Wine, network,
or unknown command.
"""

import argparse
import datetime as dt
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

import io24_loopback_foundation as foundation  # noqa: E402
import io24_native_gate_slot_probe as gate  # noqa: E402
import io24_native_standard_slot_probe as common  # noqa: E402
import io24_native_stat as native  # noqa: E402


SCHEMA = "io24-native-gate-active-slot-meter-probe-v1"
TARGET_CHANNEL = common.TARGET_CHANNEL
TARGET_SLOT = common.TARGET_SLOT
SAFE_OUTPUT_VOLUME = common.SAFE_OUTPUT_VOLUME
PROBE_INPUT_GAIN_DB = common.PROBE_INPUT_GAIN_DB
SETTLE_SECONDS = common.SETTLE_SECONDS
RECALL_SETTLE_SECONDS = common.RECALL_SETTLE_SECONDS
FLAT_DRIFT_MAX_DB = common.FLAT_DRIFT_MAX_DB
EFFECT_DELTA_MIN_DB = common.EFFECT_DELTA_MIN_DB

build_test_records = gate.build_test_records


class NativeActiveSlotProbeError(RuntimeError):
    pass


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _classify(off_before, active, off_after):
    before = float(off_before["median_main_to_input2_db"])
    effect = float(active["median_main_to_input2_db"])
    after = float(off_after["median_main_to_input2_db"])
    drift = after - before
    delta = effect - (before + after) / 2.0
    uncertainty = max(float(window["mad_main_to_input2_db"])
                      for window in (off_before, active, off_after))
    stable = abs(drift) <= FLAT_DRIFT_MAX_DB
    detected = stable and abs(delta) >= max(
        EFFECT_DELTA_MIN_DB, 6.0 * uncertainty)
    return {
        "classification": (
            "NATIVE_ACTIVE_SLOT_GATE_EFFECT_DETECTED" if detected else
            "INCONCLUSIVE_GATE_OFF_BASELINE_DRIFT" if not stable else
            "NO_NATIVE_ACTIVE_SLOT_GATE_EFFECT_DETECTED"
        ),
        "effect_delta_db": delta,
        "gate_off_drift_db": drift,
        "maximum_window_mad_db": uncertainty,
        "stable": stable,
        "effect_detected": detected,
    }


def run_active_sequence(device, records, sample_one, settle=time.sleep,
                        progress=lambda _message: None):
    """Write each body while slot 3 is selected, then force its recall."""
    if set(records) != {"restore", "flat", "boosted"}:
        raise NativeActiveSlotProbeError("native record set is incomplete")
    for record in records.values():
        native.validate_native_stat_record(record, TARGET_SLOT)

    before = common._readable_state(device.read_params())
    common._assert_guards(before)
    if before["input2_slot"] == TARGET_SLOT:
        raise NativeActiveSlotProbeError(
            "target slot 3 is active at preflight; no write was attempted")

    result = {
        "status": "MEASUREMENT_FAILED_RESTORATION_PENDING",
        "started": _now(),
        "target_channel": TARGET_CHANNEL,
        "target_slot": TARGET_SLOT,
        "readable_before": before,
        "record_sha256": {
            name: gate.record_sha256(record)
            for name, record in records.items()
        },
        "write_condition": "TARGET_SLOT_SELECTED_BEFORE_EVERY_WRITE",
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
        guarded = common._readable_state(device.read_params())
        common._assert_guards(guarded)
        if not math.isclose(guarded["main_volume"], SAFE_OUTPUT_VOLUME,
                            abs_tol=1e-6) or not math.isclose(
                                guarded["headphone_volume"],
                                SAFE_OUTPUT_VOLUME, abs_tol=1e-6) or not math.isclose(
                                    guarded["input2_gain_db"],
                                    PROBE_INPUT_GAIN_DB, abs_tol=1e-6):
            raise NativeActiveSlotProbeError(
                "readable safety controls did not latch")
        result["readable_guarded"] = guarded

        candidates = (
            ("gate_off_before", records["flat"]),
            ("gate_on", records["boosted"]),
            ("gate_off_after", records["flat"]),
        )
        for label, record in candidates:
            progress("selecting slot 3 before native %s write" % label)
            device.set_preset_slot(TARGET_CHANNEL, before["input2_slot"])
            settle(SETTLE_SECONDS)
            mutation_started = True
            device.recall_device_slot(TARGET_CHANNEL, TARGET_SLOT)
            settle(RECALL_SETTLE_SECONDS)
            active = common._readable_state(device.read_params())
            common._assert_guards(active)
            if active["input2_slot"] != TARGET_SLOT:
                raise NativeActiveSlotProbeError(
                    "Input 2 did not select slot 3 before write")

            transport = device.save_device_slot(TARGET_SLOT, record)
            result["writes"].append({
                "label": label,
                "record_sha256": gate.record_sha256(record),
                "slot_active_before_write": True,
                "transport": transport,
            })
            settle(SETTLE_SECONDS)

            device.set_preset_slot(TARGET_CHANNEL, before["input2_slot"])
            settle(SETTLE_SECONDS)
            recall = device.recall_device_slot(TARGET_CHANNEL, TARGET_SLOT)
            settle(RECALL_SETTLE_SECONDS)
            observed = common._readable_state(device.read_params())
            common._assert_guards(observed)
            if observed["input2_slot"] != TARGET_SLOT:
                raise NativeActiveSlotProbeError(
                    "Input 2 did not reselect slot 3 after write")
            result["windows"].append({
                "label": label,
                "recall": recall,
                "readable": observed,
                "meter": sample_one(label),
            })

        windows = {row["label"]: row["meter"]
                   for row in result["windows"]}
        result["analysis"] = _classify(
            windows["gate_off_before"], windows["gate_on"],
            windows["gate_off_after"])
        result["status"] = "MEASURED_RESTORATION_PENDING"
    except BaseException as error:
        failure = error
        result["error"] = {
            "type": type(error).__name__, "message": str(error)}
    finally:
        restoration_errors = []
        restored_controls = []
        actions = []
        if mutation_started:
            actions.extend((
                (lambda: device.recall_device_slot(
                    TARGET_CHANNEL, TARGET_SLOT),
                 "slot3_active_before_restore_write"),
                (lambda: device.save_device_slot(
                    TARGET_SLOT, records["restore"]),
                 "native_piano_slot3_body_active_write"),
                (lambda: device.set_preset_slot(
                    TARGET_CHANNEL, before["input2_slot"]),
                 "input2_slot_final"),
            ))
        actions.extend((
            (lambda: device.set_gain(
                TARGET_CHANNEL, before["input2_gain_db"]), "input2_gain"),
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
                    "control": control,
                    "type": type(error).__name__,
                    "message": str(error),
                })
        try:
            settle(SETTLE_SECONDS)
            after = common._readable_state(device.read_params())
            common._assert_guards(after)
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
                "NATIVE_PIANO_RESTORE_WRITTEN_WHILE_ACTIVE"
                if mutation_started else "NOT_NEEDED"),
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


def run_live(output_dir, battery_path, firmware_path, registry_path):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise NativeActiveSlotProbeError(
            "output directory must exist and be empty")
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": _now(),
        "target_channel": TARGET_CHANNEL,
        "target_slot": TARGET_SLOT,
        "sample_rate_hz": int(gate.GATE_SAMPLE_RATE_HZ),
        "stimulus": "INPUT2_PREAMP_SELF_NOISE",
        "observation": "SIMULTANEOUS_JAST_INPUT2_AND_MAIN_METERS",
        "candidate": {
            "base": "PINNED_FIRMWARE_NATIVE_CHANNEL2_SLOT2",
            "only_changed_leaf": "gate",
            "a": "both native gate states disabled",
            "b": "both native gate states enabled",
            "write_condition": "slot 3 active before every MemP/Stat(3)",
            "threshold_db": gate.GATE_THRESHOLD_DB,
            "range_db": gate.GATE_RANGE_DB,
            "attack_seconds": gate.GATE_ATTACK_SECONDS,
            "release_seconds": gate.GATE_RELEASE_SECONDS,
        },
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
        report["registry_precondition"] = common._validate_registry(
            registry_path)
        records = build_test_records(Path(firmware_path).read_bytes())
        report["restore_basis"] = {
            "body": "PINNED_FIRMWARE_NATIVE_PIANO_CHANNEL_STRIP",
            "current_slot_body_readback": "UNAVAILABLE",
            "semantic_match_to_registry": True,
            "restore_sha256": gate.record_sha256(records["restore"]),
        }
        report["record_sha256"] = {
            name: gate.record_sha256(record)
            for name, record in records.items()
        }
        device = foundation._open_checked()
        report["device"] = device._device_slot_identity()
        sequence = run_active_sequence(
            device, records,
            lambda label: common.summarize_window(device, label),
            progress=lambda message: print(message, flush=True),
        )
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
        report["finished"] = _now()
    return report


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument(
        "--battery-path", default="/sys/class/power_supply/BAT0/capacity")
    parser.add_argument(
        "--firmware-path",
        default="/home/ajuntanaga/.cache/io24/re/io24_fw.bin")
    parser.add_argument(
        "--registry-path",
        default="/home/ajuntanaga/.local/state/io24/device-slots.json")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "DRY_RUN_ONLY",
            "target_channel": TARGET_CHANNEL,
            "target_slot": TARGET_SLOT,
            "write_condition": "slot 3 active before every write",
            "sequence": ["gate off", "gate on", "gate off",
                         "native Piano restore"],
            "playback": "NONE",
            "mixer_routes": "UNTOUCHED",
            "dsp_amount": "UNTOUCHED",
            "processing_channel": "UNTOUCHED",
        }, indent=2, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--output-dir is required with --execute")
    report = run_live(
        args.output_dir, args.battery_path, args.firmware_path,
        args.registry_path)
    _write_json(Path(args.output_dir) / "live-report.json", report)
    print(json.dumps({
        "status": report["status"],
        "output": str(Path(args.output_dir) / "live-report.json"),
    }, sort_keys=True))
    return 0 if report["status"] == "MEASURED_AND_RESTORED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
