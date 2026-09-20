#!/usr/bin/env python3
"""Prepare the final stock-firmware Channel-2 VoiceFX discriminator.

The default invocation is hardware-free. Live execution remains separately
gated by ``--execute`` and ``--accept-unreadable-overwrite``. It retains every
safety and state check from the completed Channel-2 Reverb stage, but adds the
UC 4.7.2 state transition that stage omitted: resolve the known snapshot class,
select/instantiate model 0, and apply its state before sending the same pinned
complete record to Channel-2 slot 3.

This does not implement Hot Key as a new device command. Hot Key is the host's
complete-channel snapshot override; model-before-state is its relevant
block-201 apply behavior. No custom firmware is built, staged, or written.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RE_DIR = Path(__file__).resolve().parent
for directory in (ROOT, RE_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import cp34_channel2_reverb_slot_stage as base  # noqa: E402
import io24  # noqa: E402
import io24_fx  # noqa: E402


TARGET_CHANNEL = base.TARGET_CHANNEL
TARGET_SLOT = base.TARGET_SLOT
EXPECTED_SERIAL = base.EXPECTED_SERIAL
EXPECTED_FIRMWARE_VERSION = base.EXPECTED_FIRMWARE_VERSION
OVERWRITE_ACKNOWLEDGEMENT = base.OVERWRITE_ACKNOWLEDGEMENT
EXPECTED_VOICEFX_MESSAGE_SHA256 = (
    "6f93bc2cd158c84cd019f1f0d5813a4ed07f89d5bc447c7b91d5d0c399e662d6",
    "e1f3d0cb6bb53f04771c4a2781eeceafd5fdbfa4bbfce2d459d73ecc345cd0ae",
    "d006ae3b704fb6caf98abd9a5636b3d6a95ff6b2a0b32d51e7550969545876a6",
    "2d51f9aa23ec137c25dd7b0d8647cb61ead1c996a24b390cabdb6aecc4610d8b",
    "18689ace19bdf78d95fd9999bd424be13cbc50ba30c264bf9fa19c6943a0fd4e",
    "92c475598b12dd7b3418da6846016e0f23d93c0255436c1185d9938fb1ad8dc7",
)

load_factory_reverb = base.load_factory_reverb


def _voicefx_plan(record):
    model, kwargs = io24_fx.voicefx_preset_call(record["voicefx"])
    if model != "transformer" or kwargs != {
            "on": True, "lows": 0.06, "width": 0.405, "mix": 1.0}:
        raise base.StageError("pinned Reverb VoiceFX apply state differs")
    messages = io24_fx.set_fx_transformer(**kwargs)
    hashes = tuple(hashlib.sha256(message).hexdigest()
                   for message in messages)
    if hashes != EXPECTED_VOICEFX_MESSAGE_SHA256:
        raise base.StageError("pinned VoiceFX wire messages differ")
    return {
        "model": model,
        "enabled": kwargs["on"],
        "selection_order": "MODEL_BEFORE_STATE",
        "wire_messages": len(messages),
        "wire_message_sha256": list(hashes),
        "processing_gate": "UNPROVED",
        "audibility": "UNPROVED",
    }


def build_plan(record):
    """Return the exact hardware-free successor to the completed stage."""
    plan = base.build_plan(record)
    voicefx = _voicefx_plan(record)
    commands = list(plan["commands_if_executed"])
    write_index = commands.index(
        "write one complete UC tagged MemP/Stat(3) record")
    commands.insert(
        write_index,
        "select/instantiate VoiceFX model 0, then apply its known state",
    )
    plan.update({
        "schema": "cp34-channel2-voicefx-materialization-stage-v1",
        "commands_if_executed": commands,
        "direct_voicefx_parameter_write": True,
        "voicefx_apply": voicefx,
        "hotkey_interpretation": (
            "full-channel host snapshot transition, not a separate device slot"
        ),
        "custom_firmware": (
            "DEFERRED_UNTIL_AFTER_INITIAL_GITHUB_PUBLICATION"
        ),
    })
    return plan


class _MaterializingDevice:
    """Insert model-before-state immediately before the existing slot write."""

    def __init__(self, device):
        self._device = device
        self.dev = device.dev
        self.direct_attempted = False
        self.direct_completed = False
        self.direct_result = None
        self.direct_error = None
        self.record_write_attempted = False

    def __getattr__(self, name):
        return getattr(self._device, name)

    def save_uc_device_slot(self, slot, record):
        self.direct_attempted = True
        try:
            report = self._device.apply_voicefx_snapshot(record["voicefx"])
            expected = {
                "model": "transformer",
                "enabled": True,
                "parameter_writes": 6,
                "selection_order": "MODEL_BEFORE_STATE",
                "activation": "UNPROVED",
                "audibility": "UNPROVED",
            }
            if report != expected:
                raise base.StageError("VoiceFX apply report differs")
            self.direct_result = report
            self.direct_completed = True
        except Exception as error:
            self.direct_error = error
            raise

        self.record_write_attempted = True
        return self._device.save_uc_device_slot(slot, record)


def run_stage(device_factory, battery_percent, record,
              overwrite_acknowledgement, sleep_fn=time.sleep,
              expected_serial=EXPECTED_SERIAL,
              expected_firmware=EXPECTED_FIRMWARE_VERSION):
    """Run the inherited safe sequence with the exact missing state apply."""
    try:
        plan = build_plan(record)
        base_plan = base.build_plan(record)
    except (TypeError, ValueError, base.StageError) as error:
        return {"status": "BLOCKED_TARGET", "target_error": str(error)}

    wrappers = []

    def wrapped_factory(**kwargs):
        wrapper = _MaterializingDevice(device_factory(**kwargs))
        wrappers.append(wrapper)
        return wrapper

    result = base.run_stage(
        wrapped_factory,
        battery_percent,
        record,
        overwrite_acknowledgement,
        sleep_fn=sleep_fn,
        expected_serial=expected_serial,
        expected_firmware=expected_firmware,
    )

    # Replace the predecessor plan fields with this stage's controlling plan,
    # while retaining every dynamic state, error, and transport observation.
    output = dict(plan)
    for key, value in result.items():
        if key not in base_plan or key == "status":
            output[key] = value

    if wrappers:
        wrapper = wrappers[0]
        output["record_write_attempted"] = wrapper.record_write_attempted
        if wrapper.direct_result is not None:
            output["direct_voicefx_apply"] = wrapper.direct_result
        if wrapper.direct_error is not None and output.get("status") == "STAGE_FAILED":
            output["failed_stage"] = "voicefx_model_and_state_apply"
            output["direct_voicefx_error"] = "%s: %s" % (
                type(wrapper.direct_error).__name__, wrapper.direct_error)
    return output


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
    except (OSError, TypeError, ValueError, base.StageError) as error:
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
        battery_percent = base._read_battery(arguments.battery_path)
    except base.StageError as error:
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
