#!/usr/bin/env python3
"""Reversible native Channel-2 gate discriminator for device-slot writes.

This follows the guarded meter and restoration sequence of the Standard-EQ
probe, but uses the firmware's native Channel-2 slot-2 body as its candidate
base and changes only the complete native ``gate`` leaf. It performs no
playback, routing, DSP Amount, processing-channel, firmware, reset, DFU, Wine,
network, or unknown-command operation.
"""

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
RE_DIR = Path(__file__).resolve().parent
for directory in (ROOT, RE_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import io24_dsp  # noqa: E402
import io24_loopback_foundation as foundation  # noqa: E402
import io24_native_standard_slot_probe as common  # noqa: E402
import io24_native_stat as native  # noqa: E402
import io24_native_strip as strip  # noqa: E402


SCHEMA = "io24-native-gate-slot-meter-probe-v1"
FIRMWARE_SHA256 = common.FIRMWARE_SHA256
PIANO_NATIVE_OFFSET = common.PIANO_NATIVE_OFFSET
PIANO_NATIVE_LENGTH = common.PIANO_NATIVE_LENGTH
CHANNEL2_NATIVE_OFFSET = 0x69AB0
CHANNEL2_NATIVE_LENGTH = 0x404
TARGET_SLOT = common.TARGET_SLOT
GATE_THRESHOLD_DB = -40.0
GATE_RANGE_DB = -84.0
GATE_ATTACK_SECONDS = 0.005
GATE_RELEASE_SECONDS = 0.05
GATE_KEYFILTER_HZ = 20.0
GATE_SAMPLE_RATE_HZ = 96000.0


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def record_sha256(record):
    return hashlib.sha256(record).hexdigest()


def _strip_only(record, source_slot):
    decoded = native.decode_native_stat_record(
        native.validate_native_stat_record(record, source_slot))
    channel = tuple(chunk for chunk in decoded.chunks
                    if chunk.key == native.CHANNEL_STRIP_KEY)
    if len(channel) != 1:
        raise common.NativeSlotProbeError(
            "native source lacks exactly one channel strip")
    return native.validate_native_stat_record(
        native.encode_native_stat_record(
            native.NativeStatRecord(decoded.version, channel)),
        TARGET_SLOT,
    )


def _replace_gate(record, enabled):
    decoded = native.decode_native_stat_record(record)
    channel_payload = next(chunk.payload for chunk in decoded.chunks
                           if chunk.key == native.CHANNEL_STRIP_KEY)
    components = {chunk.key: chunk.payload
                  for chunk in native.decode_chunk_group(channel_payload)}
    gate = strip.ComponentState(b"gate", components[b"gate"])
    for index in (0, 1):
        blob = (
            io24_dsp.gate_blob(
                index,
                on=True,
                threshold_db=GATE_THRESHOLD_DB,
                range_db=GATE_RANGE_DB,
                attack_s=GATE_ATTACK_SECONDS,
                release_s=GATE_RELEASE_SECONDS,
                keyfilter_hz=GATE_KEYFILTER_HZ,
                expander=False,
                keylisten=False,
                fs=GATE_SAMPLE_RATE_HZ,
            )
            if enabled else io24_dsp.gate_blob_poweron(index)
        )
        gate.set_gate_blob(blob)
    return native.replace_native_channel_component(
        record, TARGET_SLOT, b"gate", gate.encode())


def build_test_records(firmware):
    firmware = bytes(firmware)
    if hashlib.sha256(firmware).hexdigest() != FIRMWARE_SHA256:
        raise common.NativeSlotProbeError(
            "firmware SHA-256 differs from pinned 1.28 application")

    restore = _strip_only(
        firmware[PIANO_NATIVE_OFFSET:
                 PIANO_NATIVE_OFFSET + PIANO_NATIVE_LENGTH],
        0,
    )
    channel2_base = _strip_only(
        firmware[CHANNEL2_NATIVE_OFFSET:
                 CHANNEL2_NATIVE_OFFSET + CHANNEL2_NATIVE_LENGTH],
        2,
    )
    return {
        "restore": restore,
        # common.run_sequence uses flat/boosted as its neutral A/B/A labels.
        "flat": _replace_gate(channel2_base, False),
        "boosted": _replace_gate(channel2_base, True),
    }


def run_live(output_dir, battery_path, firmware_path, registry_path):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise common.NativeSlotProbeError(
            "output directory must exist and be empty")
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": now(),
        "target_channel": common.TARGET_CHANNEL,
        "target_slot": TARGET_SLOT,
        "sample_rate_hz": int(GATE_SAMPLE_RATE_HZ),
        "stimulus": "INPUT2_PREAMP_SELF_NOISE",
        "observation": "SIMULTANEOUS_JAST_INPUT2_AND_MAIN_METERS",
        "candidate": {
            "base": "PINNED_FIRMWARE_NATIVE_CHANNEL2_SLOT2",
            "only_changed_leaf": "gate",
            "a": "both native gate states disabled",
            "b": "both native gate states enabled",
            "threshold_db": GATE_THRESHOLD_DB,
            "range_db": GATE_RANGE_DB,
            "attack_seconds": GATE_ATTACK_SECONDS,
            "release_seconds": GATE_RELEASE_SECONDS,
        },
        "window_semantics": {
            "flat_before": "gate_off_before",
            "boosted": "gate_on",
            "flat_after": "gate_off_after",
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
            "restore_sha256": record_sha256(records["restore"]),
        }
        report["record_sha256"] = {
            name: record_sha256(record) for name, record in records.items()
        }
        device = foundation._open_checked()
        report["device"] = device._device_slot_identity()
        sequence = common.run_sequence(
            device,
            records,
            lambda label: common.summarize_window(device, label),
            progress=lambda message: print(message, flush=True),
        )
        report["sequence"] = sequence
        report["transport"] = list(device.transport_log)
        report["status"] = sequence["status"]
    except BaseException as error:
        report["error"] = {
            "type": type(error).__name__,
            "message": str(error),
        }
    finally:
        if device is not None:
            report.setdefault("transport", list(device.transport_log))
            try:
                device.close()
            except BaseException as error:
                report["close_error"] = {
                    "type": type(error).__name__,
                    "message": str(error),
                }
                report["status"] = "RESTORATION_FAILED"
        try:
            report["battery_after"] = foundation._battery(battery_path)
        except BaseException as error:
            report["battery_after_error"] = str(error)
        report["finished"] = now()
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
            "target_channel": common.TARGET_CHANNEL,
            "target_slot": TARGET_SLOT,
            "candidate_base": "PINNED_FIRMWARE_NATIVE_CHANNEL2_SLOT2",
            "sequence": ["gate off", "gate on", "gate off",
                         "native Piano restore"],
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
        args.registry_path)
    _write_json(Path(args.output_dir) / "live-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "MEASURED_AND_RESTORED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
