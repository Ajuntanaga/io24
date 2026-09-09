#!/usr/bin/env python3
"""Stage UC's factory Slap Echo in Channel-2 slot 3 as an audible discriminator.

The Reverb stage proved that the tagged slot record's ordinary channel-strip
state is applied, but did not produce an identifiable reverb tail.  This
hardware-free-by-default wrapper reuses the already sealed Channel-2
assignment/save/recall sequence and substitutes only UC's byte-pinned factory
Slap Echo record.  Its 150 ms repeat is deliberately easier to distinguish
from EQ, filtering, compression, and preset bypass.

Live execution still requires both ``--execute`` and
``--accept-unreadable-overwrite``.  It writes only global slot 3, never slot 0.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "re" / "cp34_channel2_reverb_slot_stage.py"
EXPECTED_BASE_SHA256 = (
    "da62bac72827eed65df9c087dabb462b8cbee8deb649167e6d1c367eb6cbcab0"
)
EXPECTED_FACTORY_FILE_SHA256 = (
    "89b0572dd760b77831d012e2db0568b4f4eeb158985a4ca86126be28e934c73d"
)
FACTORY_INDEX = 4
EXPECTED_RECORD_BYTES = 850
EXPECTED_RECORD_SHA256 = (
    "a6c3294b62cfb3a46122a82c93514ea2aeb836280fb5d1e458707a78634f87eb"
)
EXPECTED_FRAME_SHA256 = (
    "6377ac677c5884d57b1bba30e2e8f3d109585fa8c5281deca242c7c6b1e8b2ae"
)
EXPECTED_VOICEFX = {
    "__classid": "{98A527BA-2D6E-4B35-BB26-251EC081A067}",
    "on": 1,
    "time": 0.15,
    "feedback": 0.25,
    "mix": 0.5,
}


def _load_base_module():
    digest = hashlib.sha256(BASE_PATH.read_bytes()).hexdigest()
    if digest != EXPECTED_BASE_SHA256:
        raise RuntimeError("sealed Channel-2 stage implementation differs")
    spec = importlib.util.spec_from_file_location(
        "cp34_channel2_reverb_slot_stage_for_slap", BASE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load_base_module()
_BASE_BUILD_PLAN = BASE.build_plan


def load_factory_slap_echo(path):
    """Load only record 4 from the hash-pinned UC factory collection."""
    from io24_preset_record import complete_device_slot_record, encode_preset_record

    path = Path(path)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_FACTORY_FILE_SHA256:
        raise BASE.StageError("factory preset collection SHA-256 differs")
    try:
        records = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BASE.StageError("factory preset collection is not valid JSON") from error
    if not isinstance(records, list) or len(records) <= FACTORY_INDEX:
        raise BASE.StageError("factory Slap Echo record 4 is unavailable")
    record = complete_device_slot_record(records[FACTORY_INDEX])
    encoded = encode_preset_record(record)
    if record.get("preset_name") != "Slap Echo" or \
            len(encoded) != EXPECTED_RECORD_BYTES or \
            hashlib.sha256(encoded).hexdigest() != EXPECTED_RECORD_SHA256:
        raise BASE.StageError("factory record 4 is not the pinned Slap Echo")
    if record.get("voicefx") != EXPECTED_VOICEFX:
        raise BASE.StageError("factory Slap Echo Voice FX fields differ")
    return record


@contextlib.contextmanager
def _slap_hash_binding(*, plan_builder=None):
    """Bind the sealed generic sequence to the pinned Slap record in-process."""
    old_record = BASE.EXPECTED_RECORD_SHA256
    old_frame = BASE.EXPECTED_FRAME_SHA256
    old_mix = BASE.TARGET_VOICEFX_MIX
    old_builder = BASE.build_plan
    BASE.EXPECTED_RECORD_SHA256 = EXPECTED_RECORD_SHA256
    BASE.EXPECTED_FRAME_SHA256 = EXPECTED_FRAME_SHA256
    BASE.TARGET_VOICEFX_MIX = EXPECTED_VOICEFX["mix"]
    if plan_builder is not None:
        BASE.build_plan = plan_builder
    try:
        yield
    finally:
        BASE.EXPECTED_RECORD_SHA256 = old_record
        BASE.EXPECTED_FRAME_SHA256 = old_frame
        BASE.TARGET_VOICEFX_MIX = old_mix
        BASE.build_plan = old_builder


def build_plan(record):
    """Return the exact no-I/O Slap Echo discriminator plan."""
    with _slap_hash_binding():
        plan = _BASE_BUILD_PLAN(record)
    plan["record"]["target_profile"] = "FACTORY_SLAP_ECHO_50_PERCENT_WET"
    plan.update({
        "schema": "cp34-channel2-slap-echo-discriminator-v1",
        "status": "OFFLINE_READY",
        "purpose": (
            "distinguish audible block-201 Voice FX from ordinary channel-strip "
            "processing already heard on Channel-2 block 2"
        ),
        "expected_signature": {
            "kind": "REPEAT_150MS",
            "delay_seconds": 0.15,
            "feedback": 0.25,
            "wet_dry_mix": 0.5,
        },
        "commands_if_executed": [
            "read and validate the exposed baseline",
            "require and reassert Assign Voice FX to Ch2",
            "verify that same-value assignment changes no exposed state",
            "bypass physical preset-control Channel 2",
            "if active, move physical Channel 2 from slot 3 to slot 2",
            "write one complete pinned UC Slap Echo record to MemP/Stat(3)",
            "set the unit to two visible preset blocks",
            "select slot 3 and enable physical preset-control Channel 2",
            "read and verify exposed slot, enable, link, and assignment state",
        ],
        "standalone_audibility": "REQUIRES_USER_150MS_REPEAT_LISTENING",
    })
    return plan


def run_stage(device_factory, battery_percent, record,
              overwrite_acknowledgement, sleep_fn=BASE.time.sleep):
    """Run the sealed Channel-2 sequence with only the pinned Slap body changed."""
    with _slap_hash_binding(plan_builder=build_plan):
        result = BASE.run_stage(
            device_factory,
            battery_percent,
            record,
            overwrite_acknowledgement,
            sleep_fn=sleep_fn,
        )
    if result.get("status") == "STAGED_FOR_STANDALONE_LISTENING":
        result["status"] = "STAGED_FOR_SLAP_ECHO_LISTENING"
        result["audibility"] = "UNPROVED_PENDING_150MS_REPEAT_LISTENING"
    return result


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
        record = load_factory_slap_echo(arguments.factory_presets)
        plan = build_plan(record)
    except (OSError, TypeError, ValueError, RuntimeError) as error:
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
            "required_acknowledgement": BASE.OVERWRITE_ACKNOWLEDGEMENT,
        }, indent=2, sort_keys=True))
        return 3
    try:
        battery_percent = BASE._read_battery(arguments.battery_path)
    except BASE.StageError as error:
        print(json.dumps({"status": "BLOCKED_BATTERY_UNAVAILABLE",
                          "battery_error": str(error)}, sort_keys=True))
        return 3

    result = run_stage(
        BASE.io24.Io24,
        battery_percent,
        record,
        BASE.OVERWRITE_ACKNOWLEDGEMENT,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == \
        "STAGED_FOR_SLAP_ECHO_LISTENING" else 3


if __name__ == "__main__":
    raise SystemExit(main())
