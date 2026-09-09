#!/usr/bin/env python3
"""Write and activate the user-requested MAIN profile in Channel-1 slot 0.

The default invocation is hardware-free. Live execution requires both
``--execute`` and ``--accept-slot0-overwrite``. The live path preserves the
readable Channel-2 state, never changes preset mode or Voice FX assignment,
writes one complete ``MemP/Stat(0)`` record, selects it for physical Channel 1,
and directly applies the identical Fat Channel values so the requested sound
does not depend on unproved device-slot recall semantics.

Transport success does not prove nonvolatile storage. A later disconnected
recall/power-cycle check and user listening check remain necessary.
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
import io24_presets  # noqa: E402
from io24_preset_record import (  # noqa: E402
    complete_device_slot_record,
    encode_preset_record,
)


TARGET_CHANNEL = 1
TARGET_SLOT = 0
ALTERNATE_SLOT = 1
PRESERVED_CHANNEL = 2
EXPECTED_SERIAL = "AB7C22200355"
EXPECTED_FIRMWARE_VERSION = 0x0128
EXPECTED_RECORD_SHA256 = (
    "fdd1c3def78bd774f49eccb34ae85c1f1e60906337723b06e847aee6e63b2404"
)
EXPECTED_FRAME_SHA256 = (
    "aec4841d0f3d5bbc7e9b5a9e59623a24c680b7d376bdf11081d354bab12fa1c5"
)
OVERWRITE_ACKNOWLEDGEMENT = (
    "Channel-1 first device slot will be replaced by MAIN"
)


class StageError(RuntimeError):
    """The bounded MAIN write is ineligible or did not complete."""


def build_main_record():
    """Return the complete, exact profile authorized for MAIN."""
    return complete_device_slot_record({
        "preset_name": "MAIN",
        "icon_id": "electricguitar",
        "opt": {"swapcompeq": 0},
        # The recovered direct-live implementation defines 24 Hz as bypass.
        "filter": {"hpf": 24.0},
        "gate": {
            "on": 0,
            "keylisten": 0,
            "expander": 1,
            "keyfilter": 40.0,
            "threshold": -84.0,
            "range": -60.0,
            "attack": 0.005,
            "release": 0.3,
        },
        "limit": {"limiteron": 1, "threshold": -0.6},
        "voicefxopt": {" ": " "},
        "eq": {
            "__classid": "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}",
            "eqallon": 1,
            "eqgain1": 1.0,
            "eqq1": 0.7,
            "eqfreq1": 90.0,
            "eqbandon1": 1,
            "eqbandop1": 1,
            "eqgain2": -2.0,
            "eqq2": 1.1,
            "eqfreq2": 300.0,
            "eqbandon2": 1,
            "eqgain3": 1.25,
            "eqq3": 0.9,
            "eqfreq3": 1800.0,
            "eqbandon3": 1,
            "eqgain4": 1.0,
            "eqq4": 0.7,
            "eqfreq4": 7000.0,
            "eqbandon4": 1,
            "eqbandop4": 1,
        },
        "comp": {
            "__classid": "{870D04F7-212E-4F9C-ADBB-39A97216433F}",
            "on": 1,
            "softknee": 1,
            "automode": 0,
            "threshold": -24.0,
            "ratio": 2.0,
            "attack": 0.03,
            "release": 0.12,
            "gain": 2.0,
            "keyfilter": 20.0,
            "keylisten": 0,
        },
        "voicefx": {
            "on": 0,
            "__classid": "{98A527BA-2D6E-4B35-BB26-251EC081A067}",
            "feedback": 0.2,
            "mix": 0.5,
            "time": 0.19,
        },
    })


def _canonical_json(record):
    return json.dumps(record, allow_nan=False, ensure_ascii=False,
                      separators=(",", ":"), sort_keys=True).encode("utf-8")


def build_plan(record):
    """Validate that *record* is exactly MAIN and describe the bounded write."""
    record = complete_device_slot_record(record)
    if _canonical_json(record) != _canonical_json(build_main_record()):
        raise StageError("record is not the exact authorized MAIN profile")
    encoded = encode_preset_record(record)
    record_digest = hashlib.sha256(encoded).hexdigest()
    if record_digest != EXPECTED_RECORD_SHA256:
        raise StageError("MAIN archive bytes differ from the pinned target")
    frames = io24._build_uc_slot_json_frames(TARGET_SLOT, record)
    frame_hashes = [hashlib.sha256(frame).hexdigest() for frame in frames]
    if frame_hashes != [EXPECTED_FRAME_SHA256]:
        raise StageError("MAIN MemP frame differs from the pinned target")
    return {
        "schema": "cp34-channel1-main-slot-stage-v1",
        "status": "OFFLINE_READY",
        "device": {
            "serial": EXPECTED_SERIAL,
            "bcd_device": "%04x" % EXPECTED_FIRMWARE_VERSION,
        },
        "preset_name": record["preset_name"],
        "target_channel": TARGET_CHANNEL,
        "target_slot": TARGET_SLOT,
        "preserved_channel": PRESERVED_CHANNEL,
        "changes_preset_mode": False,
        "changes_voicefx_assignment": False,
        "record_bytes": len(encoded),
        "record_sha256": record_digest,
        "memp_fragments": len(frames),
        "memp_payload_sha256": frame_hashes,
        "profile": {
            "compressor": "Standard, active, 2:1, soft knee",
            "limiter": "active at -0.6 dBFS",
            "eq": "four-band Strandberg Boden 8 starting curve",
            "hpf": "bypassed",
            "gate": "off",
            "voicefx": "off",
        },
        "physical_commit": "UNPROVED",
        "audibility": "REQUIRES_USER_LISTENING",
    }


def _battery_result(battery_percent):
    if isinstance(battery_percent, bool) or not isinstance(battery_percent, int):
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if not 0 <= battery_percent <= 100:
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if battery_percent <= 10:
        return {"status": "BLOCKED_BATTERY",
                "battery_percent": battery_percent}
    return None


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
    }


def _preserved_channel2_state(state):
    return {
        "input2_gain_db": state["input2_gain_db"],
        "input2_slot_index": state["input2_slot_index"],
        "input2_preset_enabled": state["input2_preset_enabled"],
        "input2_processing_channel": state["input2_processing_channel"],
    }


def _verify_untouched_state(observed, preserved_channel2, preserved_gains,
                            processing_pair):
    if observed["channel_linked"]:
        raise StageError("stereo link changed unexpectedly")
    if _preserved_channel2_state(observed) != preserved_channel2:
        raise StageError("physical Channel 2 changed unexpectedly")
    if {key: observed[key] for key in preserved_gains} != preserved_gains:
        raise StageError("input gain changed unexpectedly")
    if (observed["input1_processing_channel"],
            observed["input2_processing_channel"]) != processing_pair:
        raise StageError("Voice FX assignment changed unexpectedly")


def run_stage(device_factory, battery_percent, record,
              overwrite_acknowledgement, sleep_fn=time.sleep,
              expected_serial=EXPECTED_SERIAL,
              expected_firmware=EXPECTED_FIRMWARE_VERSION):
    """Execute the exact MAIN slot-0 write and direct Channel-1 apply."""
    try:
        plan = build_plan(record)
    except (TypeError, ValueError, StageError) as error:
        return {"status": "BLOCKED_TARGET", "target_error": str(error)}

    blocked = _battery_result(battery_percent)
    if blocked is not None:
        return blocked
    if overwrite_acknowledgement != OVERWRITE_ACKNOWLEDGEMENT:
        return {
            "status": "BLOCKED_SLOT0_OVERWRITE_NOT_ACCEPTED",
            "required_acknowledgement": OVERWRITE_ACKNOWLEDGEMENT,
        }

    device = None
    stage = "open"
    record_write_attempted = False
    baseline = None
    bypass_state = None
    prewrite_state = None
    post = None
    cleanup = "NOT_REQUIRED"
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
        params = device.read_params()
        if params is None:
            raise StageError("readable baseline unavailable")
        baseline = _readable_state(params)
        if baseline["channel_linked"]:
            raise StageError("stage must begin with stereo link off")
        preserved_channel2 = _preserved_channel2_state(baseline)
        preserved_gains = {
            "input1_gain_db": baseline["input1_gain_db"],
            "input2_gain_db": baseline["input2_gain_db"],
        }
        processing_pair = (
            baseline["input1_processing_channel"],
            baseline["input2_processing_channel"],
        )

        stage = "channel1_bypass"
        device.set_preset_enabled(TARGET_CHANNEL, False)
        sleep_fn(0.35)
        params = device.read_params()
        if params is None:
            raise StageError("Channel-1 bypass readback unavailable")
        bypass_state = _readable_state(params)
        if bypass_state["input1_preset_enabled"]:
            raise StageError("physical Channel 1 did not enter bypass")
        _verify_untouched_state(
            bypass_state, preserved_channel2, preserved_gains, processing_pair)

        target_slot_before_normalization = bypass_state["input1_slot_index"]
        target_slot_normalized = \
            target_slot_before_normalization != ALTERNATE_SLOT
        prewrite_state = bypass_state
        if target_slot_normalized:
            stage = "channel1_slot1_normalize"
            device.set_preset_slot(TARGET_CHANNEL, ALTERNATE_SLOT)
            sleep_fn(0.35)
            params = device.read_params()
            if params is None:
                raise StageError("Channel-1 slot-1 readback unavailable")
            prewrite_state = _readable_state(params)
            if prewrite_state["input1_preset_enabled"] or \
                    prewrite_state["input1_slot_index"] != ALTERNATE_SLOT:
                raise StageError(
                    "physical Channel 1 did not remain bypassed on slot 1")
            _verify_untouched_state(
                prewrite_state, preserved_channel2, preserved_gains,
                processing_pair)

        stage = "uc_tagged_slot0_write"
        record_write_attempted = True
        transport = device.save_uc_device_slot(TARGET_SLOT, record)
        if transport.get("slot") != TARGET_SLOT or \
                transport.get("fragments_sent") != plan["memp_fragments"]:
            raise StageError("slot-0 transport report differs")

        stage = "channel1_slot0_select"
        device.set_preset_slot(TARGET_CHANNEL, TARGET_SLOT)
        sleep_fn(0.75)
        stage = "channel1_enable"
        device.set_preset_enabled(TARGET_CHANNEL, True)
        sleep_fn(0.35)

        # Do not rely on an unproved Stat recall to make the requested sound.
        # Apply the same complete strip parameters directly to Channel 1.
        stage = "channel1_direct_profile_apply"
        direct_apply = io24_presets.apply_preset(
            device, record, TARGET_CHANNEL, with_fx=False)
        # Pari/5 is the separate preamp HPF switch shown on the device screen.
        device.set_highpass(TARGET_CHANNEL, False)
        sleep_fn(0.35)

        stage = "post_state"
        params = device.read_params()
        if params is None:
            raise StageError("post-stage readable state unavailable")
        post = _readable_state(params)
        if post["input1_slot_index"] != TARGET_SLOT:
            raise StageError("physical Channel 1 did not select slot 0")
        if not post["input1_preset_enabled"]:
            raise StageError("physical Channel-1 preset did not enable")
        _verify_untouched_state(
            post, preserved_channel2, preserved_gains, processing_pair)

        return {
            **plan,
            "status": "MAIN_ACTIVE_WRITE_SENT",
            "battery_percent": battery_percent,
            "baseline": baseline,
            "prewrite_state": prewrite_state,
            "transport": transport,
            "post_state": post,
            "target_slot_before_normalization":
                target_slot_before_normalization,
            "target_slot_normalized": target_slot_normalized,
            "direct_apply": direct_apply,
            "preamp_hpf_switch": "OFF_WRITE_SENT",
            "left_selected_and_enabled": True,
            "physical_commit": "UNPROVED",
            "audibility": "REQUIRES_USER_LISTENING",
        }
    except (Exception, SystemExit) as error:
        if device is not None:
            try:
                device.set_preset_enabled(TARGET_CHANNEL, False)
                cleanup = "CHANNEL_1_BYPASS_WRITE_SENT"
            except Exception as cleanup_error:
                cleanup = "%s: %s" % (
                    type(cleanup_error).__name__, cleanup_error)
        return {
            **plan,
            "status": "STAGE_FAILED",
            "failed_stage": stage,
            "record_write_attempted": record_write_attempted,
            "failure_cleanup": cleanup,
            "baseline": baseline,
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
        "--battery-path", type=Path,
        default=Path("/sys/class/power_supply/BAT0/capacity"),
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--accept-slot0-overwrite", action="store_true")
    arguments = parser.parse_args(argv)

    record = build_main_record()
    try:
        plan = build_plan(record)
    except (TypeError, ValueError, StageError) as error:
        print(json.dumps({"status": "BLOCKED_TARGET",
                          "target_error": str(error)}, sort_keys=True))
        return 3
    if not arguments.execute:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    if not arguments.accept_slot0_overwrite:
        print(json.dumps({
            "status": "BLOCKED_SLOT0_OVERWRITE_NOT_ACCEPTED",
            "required_flag": "--accept-slot0-overwrite",
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
    return 0 if result["status"] == "MAIN_ACTIVE_WRITE_SENT" else 3


if __name__ == "__main__":
    raise SystemExit(main())
