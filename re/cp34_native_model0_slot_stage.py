#!/usr/bin/env python3
"""Stage one pinned native model-0 record for standalone listening.

The default invocation is hardware-free and prints the validated plan. Live
execution requires both ``--execute`` and ``--accept-unreadable-overwrite``.
It writes one component-201-owning slot, routes the Voice FX chain to the
chosen physical input, enables that preset family, and recalls the newly
written slot. It does not capture audio, change stereo link, power-cycle the
unit, restore the slot, or claim that transport proves storage or audibility.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import io24  # noqa: E402
from io24_native_stat import validate_native_stat_record  # noqa: E402


EXPECTED_CANDIDATE_SHA256 = {
    0: "da1b3e00463ed6e51139119611ef18ba8b8286d4db41f7d6dac7290e2f041c57",
    1: "b968619645be68441f23ff795745ab24570977213121fb4d6ed3fc3e48f3e564",
}
EXPECTED_FIRMWARE_VERSION = 0x0128
# The user rejected both Channel-1 storage slots and requires an actual
# Channel-2 slot. Stock slots 2/3 cannot carry component 201, so no live target
# is eligible until the user chooses a different stock boundary or the later
# private-firmware lane supplies one.
USER_PROHIBITED_LIVE_SLOTS = frozenset((0, 1))
OVERWRITE_ACKNOWLEDGEMENT = (
    "current slot content is unreadable; restore is firmware default"
)


class StageError(RuntimeError):
    """The bounded native-slot stage is ineligible or did not complete."""


def _battery_result(battery_percent):
    if isinstance(battery_percent, bool) or not isinstance(battery_percent, int):
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if not 0 <= battery_percent <= 100:
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if battery_percent <= 10:
        return {"status": "BLOCKED_BATTERY",
                "battery_percent": battery_percent}
    return None


def build_plan(slot_index, record, processing_input,
               allowed_hashes=EXPECTED_CANDIDATE_SHA256):
    """Validate the exact record and return a no-I/O execution plan."""
    if isinstance(slot_index, bool) or slot_index not in (0, 1):
        raise StageError("native Voice FX storage target must be slot 0 or 1")
    if isinstance(processing_input, bool) or processing_input not in (1, 2):
        raise StageError("processing input must be 1 or 2")
    record = validate_native_stat_record(record, slot_index=slot_index)
    digest = hashlib.sha256(record).hexdigest()
    if digest != allowed_hashes.get(slot_index):
        raise StageError(
            "record SHA-256 is not the pinned model-0 candidate for slot %d" %
            slot_index)
    frames = io24._build_native_slot_memp_frames(slot_index, record)
    return {
        "schema": "cp34-native-model0-slot-stage-v1",
        "status": "OFFLINE_READY",
        "slot_index": slot_index,
        "processing_input": processing_input,
        "record_bytes": len(record),
        "record_sha256": digest,
        "memp_fragments": len(frames),
        "memp_payload_sha256": [
            hashlib.sha256(frame).hexdigest() for frame in frames
        ],
        "commands_if_executed": [
            "bypass the Channel-1 preset family during staging",
            "if needed, select the other Channel-1 slot before overwriting the active target",
            "write native MemP/Stat(%d)" % slot_index,
            "route Voice FX processing chain to physical Input %d" %
            processing_input,
            "set the unit to two visible preset blocks",
            "select Stat(%d) to produce a host-side recall/application edge" %
            slot_index,
            "enable the Channel-1 preset family",
            "read and verify the exposed selector/routing state",
        ],
        "standalone_preset_button": "CHANNEL_1",
        "slot_content_backup_available": False,
        "restoration_available": "EXACT_FIRMWARE_DEFAULT_ONLY",
        "stereo_link_change": False,
        "power_cycle": False,
        "audio_capture": False,
        "standalone_audibility": "REQUIRES_USER_LISTENING_AFTER_STAGE",
    }


def _readable_state(params):
    flags = int(params["flags"])
    input1_processing_raw = int(params["input1ProcessingChannel"])
    input2_processing_raw = int(params["input2ProcessingChannel"])
    if input1_processing_raw not in (0, 1) or \
            input2_processing_raw not in (0, 1):
        raise StageError("processing-channel readback is outside 0..1")
    return {
        "flags_word": flags,
        "channel_linked": bool(flags >> 12 & 1),
        "voicefx_storage_slot": int(params["input1SlotIndex"]),
        "voicefx_storage_enabled": not bool(flags >> 5 & 1),
        # read_params() normalizes JaSt's mixer ids 3/4 to zero-based 0/1,
        # while the public control and operator language use physical Inputs
        # 1/2.  Keep both representations explicit so they cannot be confused.
        "voicefx_chain_processing_raw": input1_processing_raw,
        "voicefx_chain_physical_input": input1_processing_raw + 1,
        "other_chain_processing_raw": input2_processing_raw,
        "other_chain_physical_input": input2_processing_raw + 1,
    }


def run_stage(device_factory, battery_percent, expected_serial, slot_index,
              record, processing_input, overwrite_acknowledgement,
              sleep_fn=time.sleep, allowed_hashes=EXPECTED_CANDIDATE_SHA256,
              prohibited_live_slots=USER_PROHIBITED_LIVE_SLOTS):
    """Execute only the bounded write/route/recall sequence.

    ``device_factory`` is injected for hardware-free command-order tests. The
    caller remains responsible for separately authorized physical listening
    and the computer-to-standalone power transition.
    """
    try:
        plan = build_plan(
            slot_index, record, processing_input,
            allowed_hashes=allowed_hashes)
    except (TypeError, ValueError, StageError) as error:
        return {"status": "BLOCKED_TARGET", "target_error": str(error)}

    if slot_index in prohibited_live_slots:
        return {
            **plan,
            "status": "BLOCKED_USER_REQUIRES_CHANNEL2_STORAGE",
            "reason": (
                "slots 0/1 are the Channel-1 owning pair; the user prohibited "
                "them, while stock Channel-2 slots 2/3 cannot carry component "
                "201"
            ),
        }

    blocked = _battery_result(battery_percent)
    if blocked is not None:
        return blocked
    if overwrite_acknowledgement != OVERWRITE_ACKNOWLEDGEMENT:
        return {
            "status": "BLOCKED_UNREADABLE_OVERWRITE_NOT_ACCEPTED",
            "required_acknowledgement": OVERWRITE_ACKNOWLEDGEMENT,
        }

    device = None
    stage = "open"
    record_write_attempted = False
    try:
        device = device_factory(shadow=False)
        stage = "identity"
        serial = device.dev.serial_number
        firmware = int(getattr(device.dev, "bcdDevice", 0))
        if serial != expected_serial:
            return {
                "status": "IDENTITY_MISMATCH",
                "expected_serial": expected_serial,
                "observed_serial": serial,
            }
        if firmware != EXPECTED_FIRMWARE_VERSION:
            return {
                "status": "FIRMWARE_MISMATCH",
                "expected_bcd_device": "%04x" % EXPECTED_FIRMWARE_VERSION,
                "observed_bcd_device": "%04x" % firmware,
            }

        stage = "baseline"
        baseline_params = device.read_params()
        if baseline_params is None:
            raise StageError("readable baseline unavailable")
        baseline = _readable_state(baseline_params)
        if baseline["channel_linked"]:
            raise StageError("stage must begin with stereo link off")
        if baseline["voicefx_storage_slot"] not in (0, 1):
            raise StageError(
                "Channel-1 selector is outside its owning slot pair 0/1")

        # Keep unknown or newly written processing out of the listening path
        # until the exact target has been recalled and routing is settled.
        stage = "preset_bypass_for_stage"
        device.set_preset_enabled(1, False)
        sleep_fn(0.35)

        dislodged_from_active_target = False
        prewrite_state = baseline
        if baseline["voicefx_storage_slot"] == slot_index:
            stage = "alternate_slot_select"
            device.set_preset_slot(1, 1 - slot_index)
            sleep_fn(0.35)
            stage = "alternate_slot_verify"
            alternate_params = device.read_params()
            if alternate_params is None:
                raise StageError("alternate-slot readback unavailable")
            prewrite_state = _readable_state(alternate_params)
            if prewrite_state["channel_linked"]:
                raise StageError("stereo link changed during target dislodge")
            if prewrite_state["voicefx_storage_slot"] != 1 - slot_index:
                raise StageError("target slot remained active before write")
            if prewrite_state["voicefx_storage_enabled"]:
                raise StageError("Channel-1 preset did not remain bypassed")
            dislodged_from_active_target = True

        stage = "native_slot_write"
        record_write_attempted = True
        transport = device.save_device_slot(slot_index, record)

        stage = "processing_route"
        device.set_processing_channel(1, processing_input)
        sleep_fn(0.35)
        stage = "preset_mode_dual"
        device.set_preset_mode(io24.Io24.PRESET_MODE_DUAL)
        sleep_fn(0.35)
        stage = "slot_recall"
        device.set_preset_slot(1, slot_index)
        sleep_fn(0.75)
        stage = "preset_enable"
        device.set_preset_enabled(1, True)
        sleep_fn(0.35)

        stage = "post_state"
        post_params = device.read_params()
        if post_params is None:
            raise StageError("post-stage readable state unavailable")
        post = _readable_state(post_params)
        if post["channel_linked"]:
            raise StageError("stereo link changed unexpectedly")
        if post["voicefx_storage_slot"] != slot_index:
            raise StageError("target slot selection did not read back")
        if not post["voicefx_storage_enabled"]:
            raise StageError("Voice FX owning preset family did not enable")
        if post["voicefx_chain_physical_input"] != processing_input:
            raise StageError("Voice FX processing input did not read back")

        return {
            **plan,
            "status": "STAGED_FOR_STANDALONE_LISTENING",
            "battery_percent": battery_percent,
            "device": {
                "serial": serial,
                "bcd_device": "%04x" % firmware,
            },
            "baseline": baseline,
            "prewrite_state": prewrite_state,
            "transport": transport,
            "post_state": post,
            "dislodged_from_active_target": dislodged_from_active_target,
            "preset_mode_command": "DUAL_TWO_BLOCKS",
            "preset_mode_readback": "UNAVAILABLE_CONFIRM_ON_UNIT_SCREEN",
            "physical_commit": "UNPROVED",
            "standalone_recall": "UNPROVED",
            "audibility": "UNPROVED",
            "left_saved_for_standalone_test": True,
        }
    except (Exception, SystemExit) as error:
        return {
            **plan,
            "status": "STAGE_FAILED",
            "failed_stage": stage,
            "record_write_attempted": record_write_attempted,
            "error": "%s: %s" % (type(error).__name__, error),
        }
    finally:
        if device is not None:
            try:
                device.close()
            except Exception:
                pass


def _read_battery(path):
    try:
        return int(path.read_text(encoding="ascii").strip())
    except (OSError, ValueError) as error:
        raise StageError("battery unavailable: %s" % error) from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--slot", required=True, type=int, choices=(0, 1))
    parser.add_argument("--processing-input", required=True, type=int,
                        choices=(1, 2))
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument(
        "--battery-path", type=Path,
        default=Path("/sys/class/power_supply/BAT0/capacity"),
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--accept-unreadable-overwrite", action="store_true")
    arguments = parser.parse_args(argv)

    try:
        record = arguments.record.read_bytes()
        plan = build_plan(
            arguments.slot, record, arguments.processing_input)
    except (OSError, TypeError, ValueError, StageError) as error:
        print(json.dumps({"status": "BLOCKED_TARGET",
                          "target_error": str(error)}, sort_keys=True))
        return 3

    if not arguments.execute:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    if not arguments.accept_unreadable_overwrite:
        print(json.dumps({
            "status": "BLOCKED_UNREADABLE_OVERWRITE_NOT_ACCEPTED",
            "required_flag": "--accept-unreadable-overwrite",
            "required_acknowledgement": OVERWRITE_ACKNOWLEDGEMENT,
        }, indent=2, sort_keys=True))
        return 3
    try:
        battery_percent = _read_battery(arguments.battery_path)
    except StageError as error:
        print(json.dumps({"status": "BLOCKED_BATTERY_UNAVAILABLE",
                          "battery_error": str(error)}, sort_keys=True))
        return 3

    result = run_stage(
        io24.Io24,
        battery_percent,
        arguments.serial,
        arguments.slot,
        record,
        arguments.processing_input,
        OVERWRITE_ACKNOWLEDGEMENT,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "STAGED_FOR_STANDALONE_LISTENING" else 3


if __name__ == "__main__":
    raise SystemExit(main())
