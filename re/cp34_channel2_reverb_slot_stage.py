#!/usr/bin/env python3
"""Stage a factory-derived maximum-wet Reverb in Channel-2 slot 3.

The default invocation is hardware-free.  Live execution requires both
``--execute`` and ``--accept-unreadable-overwrite``.  The bounded live path
selects physical Input 2 for the shared VoiceFX layer, independently controls
physical Channel 2's preset enable and slot layers, writes one complete tagged
``MemP/Stat(3)`` record, recalls it on physical Channel 2, and leaves it
selected for the user's disconnected cold-boot listening check.

This command never targets slot 0, never starts Wine, never changes stereo
link, and never claims that successful transport proves storage or audibility.
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
from io24_preset_record import (  # noqa: E402
    complete_device_slot_record,
    encode_preset_record,
)


TARGET_CHANNEL = 2
TARGET_SLOT = 3
ALTERNATE_SLOT = 2
UC_ASSIGNMENT_PARAMETER_CHANNEL = 1
UC_ASSIGNMENT_VALUE = 1
ASSIGNED_PHYSICAL_INPUT = 2
EXPECTED_SERIAL = "AB7C22200355"
EXPECTED_FIRMWARE_VERSION = 0x0128
TARGET_VOICEFX_MIX = 1.0
EXPECTED_FACTORY_FILE_SHA256 = (
    "89b0572dd760b77831d012e2db0568b4f4eeb158985a4ca86126be28e934c73d"
)
EXPECTED_RECORD_SHA256 = (
    "191a5048c4995355932609e9d5ae225f37c50d8f112966f685a11b3f2a08e79c"
)
EXPECTED_FRAME_SHA256 = (
    "d8ea35050b33484444e48c3d54cf1716bce35265a0b2b92f26939ea7bdf92c1f"
)
OVERWRITE_ACKNOWLEDGEMENT = (
    "current Channel-2 slot 3 content is unreadable and will be replaced"
)


class StageError(RuntimeError):
    """The bounded slot-3 stage is ineligible or did not complete."""


def _battery_result(battery_percent):
    if isinstance(battery_percent, bool) or not isinstance(battery_percent, int):
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if not 0 <= battery_percent <= 100:
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if battery_percent <= 10:
        return {"status": "BLOCKED_BATTERY",
                "battery_percent": battery_percent}
    return None


def load_factory_reverb(path):
    """Load UC Reverb and raise its private Wet/Dry mix to an obvious 100%."""
    path = Path(path)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_FACTORY_FILE_SHA256:
        raise StageError("factory preset collection SHA-256 differs")
    try:
        records = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StageError("factory preset collection is not valid JSON") from error
    if not isinstance(records, list):
        raise StageError("factory preset collection is not a list")
    matches = [record for record in records
               if isinstance(record, dict)
               and record.get("preset_name") == "Reverb"]
    if len(matches) != 1:
        raise StageError("factory preset collection does not contain one Reverb")
    record = complete_device_slot_record(matches[0])
    record["voicefx"] = dict(record["voicefx"])
    record["voicefx"]["mix"] = TARGET_VOICEFX_MIX
    return record


def build_plan(record):
    """Validate and pin the exact no-I/O Channel-2 slot-3 operation."""
    record = complete_device_slot_record(record)
    encoded = encode_preset_record(record)
    digest = hashlib.sha256(encoded).hexdigest()
    if digest != EXPECTED_RECORD_SHA256:
        raise StageError("record is not the pinned maximum-wet Reverb target")
    voicefx = record.get("voicefx")
    if not isinstance(voicefx, dict) or voicefx.get("on") != 1 or \
            voicefx.get("mix") != TARGET_VOICEFX_MIX:
        raise StageError("pinned Reverb Voice FX is not enabled at maximum wet")
    frames = io24._build_uc_slot_json_frames(TARGET_SLOT, record)
    frame_hashes = [hashlib.sha256(frame).hexdigest() for frame in frames]
    if frame_hashes != [EXPECTED_FRAME_SHA256]:
        raise StageError("UC MemP/Stat(3) frame differs from the pinned frame")
    return {
        "schema": "cp34-channel2-reverb-slot-stage-v1",
        "status": "OFFLINE_READY",
        "device": {
            "serial": EXPECTED_SERIAL,
            "bcd_device": "%04x" % EXPECTED_FIRMWARE_VERSION,
        },
        "target_channel": TARGET_CHANNEL,
        "target_slot": TARGET_SLOT,
        "slot_zero_targeted": False,
        "record": {
            "preset_name": record["preset_name"],
            "target_profile": "FACTORY_DERIVED_MAXIMUM_WET",
            "bytes": len(encoded),
            "sha256": digest,
            "wire_prefix_hex": encoded[:1].hex(),
            "voicefx": voicefx,
        },
        "memp_fragments": len(frames),
        "memp_payload_sha256": frame_hashes,
        "uc_voicefx_assignment": {
            "property": "line/ch1/processingChannel",
            "wire_control": "Pari/12 index 0",
            "value": UC_ASSIGNMENT_VALUE,
            "label": "Ch2",
            "assigned_physical_input": ASSIGNED_PHYSICAL_INPUT,
            "preset_control_namespace": "INDEPENDENT_PHYSICAL_CHANNELS",
            "reassert_same_assignment_before_model": True,
            "firmware_slot_side_effect":
                "swap the two active slot indexes when assignment changes",
        },
        "commands_if_executed": [
            "read and validate the exposed baseline",
            "require the independent Voice FX assignment to already be Ch2",
            "reassert Assign Voice FX to Ch2 without remapping preset controls",
            "bypass physical Channel 2 through preset control channel 2",
            "normalize physical Channel 2 to slot 2 before the slot-3 write",
            "write one complete UC tagged MemP/Stat(3) record",
            "set the unit to two visible preset blocks",
            "select slot 3 and enable physical Channel 2 through channel 2",
            "read and verify exposed slot, enable, link, and assignment state",
        ],
        "standalone_preset_button": "CHANNEL_2",
        "slot_content_backup_available": False,
        "restoration_available": "NO_EXACT_CURRENT_SLOT_BODY",
        "stereo_link_change": False,
        "direct_voicefx_parameter_write": False,
        "power_cycle": False,
        "audio_capture": False,
        "physical_commit": "UNPROVED",
        "standalone_audibility": "REQUIRES_USER_LISTENING_AFTER_STAGE",
    }


def _readable_state(params):
    required = {
        "flags", "input1Gain", "input2Gain", "input1SlotIndex",
        "input2SlotIndex", "input1ProcessingChannel",
        "input2ProcessingChannel",
    }
    missing = sorted(required.difference(params))
    if missing:
        raise StageError("readable state lacks %s" % ", ".join(missing))
    flags = int(params["flags"])
    processing = (
        int(params["input1ProcessingChannel"]),
        int(params["input2ProcessingChannel"]),
    )
    if set(processing) != {0, 1}:
        raise StageError("processing-channel state is not a 0/1 permutation")
    return {
        "flags_word": flags,
        "channel_linked": bool(flags >> 12 & 1),
        "input1_gain_db": params["input1Gain"],
        "input2_gain_db": params["input2Gain"],
        "input1_slot_index": int(params["input1SlotIndex"]),
        "input2_slot_index": int(params["input2SlotIndex"]),
        "input1_preset_enabled": not bool(flags >> 5 & 1),
        "input2_preset_enabled": not bool(flags >> 6 & 1),
        "input1_processing_channel": processing[0],
        "input2_processing_channel": processing[1],
        "voicefx_assigned_physical_input": processing[0] + 1,
    }


def _slot_pair_for_physical_input(physical_input):
    if physical_input == 1:
        return (0, 1)
    if physical_input == 2:
        return (2, 3)
    raise StageError("physical input is outside 1/2")


def _validate_physical_slot_alignment(state, channels=(1, 2)):
    """Require each physical channel to select only from its own slot pair."""
    for channel in channels:
        slot = state["input%d_slot_index" % channel]
        if slot not in _slot_pair_for_physical_input(channel):
            raise StageError(
                "physical Channel %d slot %d is outside its slot family" %
                (channel, slot))


def _preserved_channel1_state(state):
    """Physical Channel-1 fields that a Channel-2 stage must not disturb."""
    return {
        "input1_gain_db": state["input1_gain_db"],
        "input1_slot_index": state["input1_slot_index"],
        "input1_preset_enabled": state["input1_preset_enabled"],
    }


def run_stage(device_factory, battery_percent, record,
              overwrite_acknowledgement, sleep_fn=time.sleep,
              expected_serial=EXPECTED_SERIAL,
              expected_firmware=EXPECTED_FIRMWARE_VERSION):
    """Execute only the bounded validate/write/Channel-2 recall sequence."""
    try:
        plan = build_plan(record)
    except (TypeError, ValueError, StageError) as error:
        return {"status": "BLOCKED_TARGET", "target_error": str(error)}

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
    failure_bypass = "NOT_REQUIRED"
    cleanup_channel = None
    baseline = None
    assigned_state = None
    bypass_state = None
    prewrite_state = None
    post = None
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
        if firmware != expected_firmware:
            return {
                "status": "FIRMWARE_MISMATCH",
                "expected_bcd_device": "%04x" % expected_firmware,
                "observed_bcd_device": "%04x" % firmware,
            }

        stage = "baseline"
        baseline_params = device.read_params()
        if baseline_params is None:
            raise StageError("readable baseline unavailable")
        baseline = _readable_state(baseline_params)
        if baseline["channel_linked"]:
            raise StageError("stage must begin with stereo link off")
        if baseline["voicefx_assigned_physical_input"] != \
                ASSIGNED_PHYSICAL_INPUT:
            return {
                **plan,
                "status": "BLOCKED_VOICEFX_ASSIGNMENT",
                "battery_percent": battery_percent,
                "baseline": baseline,
                "required_voicefx_assigned_physical_input":
                    ASSIGNED_PHYSICAL_INPUT,
                "record_write_attempted": False,
            }
        assigned_state = baseline
        preserved_channel1 = _preserved_channel1_state(baseline)
        preserved_gains = {
            "input1_gain_db": baseline["input1_gain_db"],
            "input2_gain_db": baseline["input2_gain_db"],
        }

        # UC's exact host route evaluates processingChannel first and then
        # selects the owning channel's fxmodel. Re-send the already-validated
        # Ch2 assignment so the device route is explicit, but refuse to change
        # assignment here because a real change exchanges active selectors.
        stage = "voicefx_assignment_reassert"
        device.set_processing_channel(
            UC_ASSIGNMENT_PARAMETER_CHANNEL, ASSIGNED_PHYSICAL_INPUT)
        sleep_fn(0.35)
        assigned_params = device.read_params()
        if assigned_params is None:
            raise StageError("Voice FX assignment reassert readback unavailable")
        assigned_state = _readable_state(assigned_params)
        if assigned_state != baseline:
            raise StageError(
                "same-value Voice FX assignment changed exposed device state")

        stage = "physical_channel2_bypass"
        cleanup_channel = TARGET_CHANNEL
        device.set_preset_enabled(TARGET_CHANNEL, False)
        sleep_fn(0.35)
        bypass_params = device.read_params()
        if bypass_params is None:
            raise StageError("physical Channel-2 bypass readback unavailable")
        bypass_state = _readable_state(bypass_params)
        if bypass_state["channel_linked"] or \
                bypass_state["input2_preset_enabled"]:
            raise StageError("physical Channel 2 did not enter bypass")
        if bypass_state["input2_slot_index"] != \
                assigned_state["input2_slot_index"]:
            raise StageError("target slot changed during bypass")
        if _preserved_channel1_state(bypass_state) != preserved_channel1:
            raise StageError("physical Channel 1 changed during Ch2 bypass")
        if {key: bypass_state[key] for key in preserved_gains} != \
                preserved_gains:
            raise StageError("input gain changed during Ch2 bypass")
        if bypass_state["voicefx_assigned_physical_input"] != \
                ASSIGNED_PHYSICAL_INPUT:
            raise StageError("Voice FX assignment changed during Ch2 bypass")

        target_slot_before_normalization = \
            bypass_state["input2_slot_index"]
        target_slot_normalized = \
            target_slot_before_normalization != ALTERNATE_SLOT
        dislodged_from_active_target = \
            target_slot_before_normalization == TARGET_SLOT
        prewrite_state = bypass_state
        if target_slot_normalized:
            stage = "channel2_slot2_normalize"
            device.set_preset_slot(TARGET_CHANNEL, ALTERNATE_SLOT)
            sleep_fn(0.35)
            stage = "channel2_slot2_normalize_verify"
            alternate_params = device.read_params()
            if alternate_params is None:
                raise StageError("Channel-2 slot-2 readback unavailable")
            prewrite_state = _readable_state(alternate_params)
            if prewrite_state["channel_linked"] or \
                    prewrite_state["input2_slot_index"] != ALTERNATE_SLOT or \
                    prewrite_state["input2_preset_enabled"]:
                raise StageError(
                    "physical Channel 2 did not remain bypassed on slot 2")
            if _preserved_channel1_state(prewrite_state) != preserved_channel1:
                raise StageError(
                    "physical Channel 1 changed during Ch2 normalization")
            if {key: prewrite_state[key] for key in preserved_gains} != \
                    preserved_gains:
                raise StageError("input gain changed during Ch2 normalization")
            if prewrite_state["voicefx_assigned_physical_input"] != \
                    ASSIGNED_PHYSICAL_INPUT:
                raise StageError(
                    "Voice FX assignment changed during Ch2 normalization")
        _validate_physical_slot_alignment(prewrite_state, (TARGET_CHANNEL,))

        stage = "uc_tagged_slot3_write"
        record_write_attempted = True
        transport = device.save_uc_device_slot(TARGET_SLOT, record)
        if transport.get("slot") != TARGET_SLOT or \
                transport.get("fragments_sent") != 1:
            raise StageError("slot-3 transport report differs")

        stage = "preset_mode_dual"
        device.set_preset_mode(io24.Io24.PRESET_MODE_DUAL)
        sleep_fn(0.35)
        stage = "channel2_slot3_recall"
        device.set_preset_slot(TARGET_CHANNEL, TARGET_SLOT)
        sleep_fn(0.75)
        stage = "channel2_enable"
        device.set_preset_enabled(TARGET_CHANNEL, True)
        sleep_fn(0.35)

        stage = "post_state"
        post_params = device.read_params()
        if post_params is None:
            raise StageError("post-stage readable state unavailable")
        post = _readable_state(post_params)
        if post["channel_linked"]:
            raise StageError("stereo link changed unexpectedly")
        if post["input2_slot_index"] != TARGET_SLOT:
            raise StageError("physical Channel 2 did not select slot 3")
        if not post["input2_preset_enabled"]:
            raise StageError("physical Channel-2 preset did not enable")
        if post["voicefx_assigned_physical_input"] != ASSIGNED_PHYSICAL_INPUT:
            raise StageError("Voice FX assignment did not remain on Ch2")
        if _preserved_channel1_state(post) != preserved_channel1:
            raise StageError("physical Channel 1 changed after Ch2 recall")
        if {key: post[key] for key in preserved_gains} != preserved_gains:
            raise StageError("input gain changed after Ch2 recall")

        return {
            **plan,
            "status": "STAGED_FOR_STANDALONE_LISTENING",
            "battery_percent": battery_percent,
            "baseline": baseline,
            "assignment_changed": False,
            "assignment_action": "VALIDATED_AND_REASSERTED_SAME_VALUE",
            "prewrite_state": prewrite_state,
            "assigned_state": assigned_state,
            "transport": transport,
            "post_state": post,
            "dislodged_from_active_target": dislodged_from_active_target,
            "target_slot_before_normalization":
                target_slot_before_normalization,
            "target_slot_normalized": target_slot_normalized,
            "preset_mode_command": "DUAL_TWO_BLOCKS",
            "preset_mode_readback": "UNAVAILABLE_CONFIRM_ON_UNIT_SCREEN",
            "target_physical_channel": TARGET_CHANNEL,
            "target_preset_control_channel": TARGET_CHANNEL,
            "physical_commit": "UNPROVED",
            "standalone_recall": "UNPROVED",
            "audibility": "UNPROVED",
            "left_saved_for_standalone_test": True,
        }
    except (Exception, SystemExit) as error:
        if device is not None and cleanup_channel is not None:
            try:
                device.set_preset_enabled(cleanup_channel, False)
                failure_bypass = "WRITE_SENT_NOT_READABLE"
            except Exception as cleanup_error:
                failure_bypass = "%s: %s" % (
                    type(cleanup_error).__name__, cleanup_error)
        return {
            **plan,
            "status": "STAGE_FAILED",
            "failed_stage": stage,
            "record_write_attempted": record_write_attempted,
            "failure_channel2_bypass": failure_bypass,
            "failure_bypass_channel": cleanup_channel,
            "baseline": baseline,
            "assigned_state": assigned_state,
            "bypass_state": bypass_state,
            "prewrite_state": prewrite_state,
            "post_state": post,
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
    parser.add_argument(
        "--factory-presets", type=Path,
        default=ROOT / "re" / "uc_factory_presets.json",
    )
    parser.add_argument(
        "--battery-path", type=Path,
        default=Path("/sys/class/power_supply/BAT0/capacity"),
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--accept-unreadable-overwrite", action="store_true")
    arguments = parser.parse_args(argv)

    try:
        record = load_factory_reverb(arguments.factory_presets)
        plan = build_plan(record)
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
        record,
        OVERWRITE_ACKNOWLEDGEMENT,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == \
        "STAGED_FOR_STANDALONE_LISTENING" else 3


if __name__ == "__main__":
    raise SystemExit(main())
