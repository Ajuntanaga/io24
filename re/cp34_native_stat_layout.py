#!/usr/bin/env python3
"""Bind firmware 1.28 native ``Stat`` defaults apart from library archives.

The analyzer reads the exact UC 4.7.2 DSP module as data, locates its embedded
io24 recovery package, verifies the startup RAM-copy pointer table, and decodes
the four native slot records.  It never emits firmware or accesses hardware.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import io24_firmware  # noqa: E402
from io24_native_stat import (  # noqa: E402
    build_native_model0_stat_record,
    decode_native_stat_record,
    native_stat_summary,
)
from io24_preset_record import decode_preset_record_prefix  # noqa: E402


class AnalysisError(ValueError):
    """The input differs from the exact pinned source or native layout."""


UC472_SIZE = 4_979_672
UC472_SHA256 = (
    "de685e89c88b191b9709145056aa37d58a76f141a53a9c153"
    "3dff917f611fd28"
)
PACKAGE_SHA256 = io24_firmware.UC472_IO24_PACKAGE_SHA256
FIRMWARE_BASE = 0x60020000
APPLICATION_SIZE = 1_104_448
APPLICATION_SHA256 = (
    "65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a"
    "7679e387952eb1a"
)

COPY_TABLE_ENTRY_RAW = 0x310
RAM_INITIALIZER_SOURCE = 0x60149C40
RAM_POINTER_TABLE = 0x202B0E00
RAM_INITIALIZER_SIZE = 0xA4D
RAM_INITIALIZER_RAW = RAM_INITIALIZER_SOURCE - FIRMWARE_BASE

STAT_LENGTHS_RAW = 0x691E0
STAT_POINTERS_RAW = RAM_INITIALIZER_RAW + 4
STAT_OFFSETS = (0x69230, 0x69670, 0x69AB0, 0x69EB4)
STAT_LENGTHS = (0x440, 0x440, 0x404, 0x404)
FACTORY_POINTERS_RAW = STAT_POINTERS_RAW + 4 * 4
FIRST_FACTORY_OFFSET = 0x6A2B8
FACTORY_COUNT = 16
MODEL0_SERIALIZER_RAW = 0x53680
MODEL0_STATE_BYTES = 20
MODEL0_REVERB_PARAMETERS = {
    "enabled": True,
    "lows": 0.06,
    "width": 0.405,
    "mix": 0.295,
}


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _u32s(data, offset, count):
    end = offset + 4 * count
    _require(0 <= offset <= end <= len(data),
             "u32 range at %#x exceeds source" % offset)
    return struct.unpack_from("<%dI" % count, data, offset)


def analyze(dll):
    """Return the exact native-slot/library separation report."""
    digest = hashlib.sha256(dll).hexdigest()
    _require(len(dll) == UC472_SIZE,
             "UC 4.7.2 DLL size differs: %d" % len(dll))
    _require(digest == UC472_SHA256,
             "UC 4.7.2 DLL SHA-256 differs: %s" % digest)

    start, end, version = io24_firmware.locate_firmware(dll)
    _require(start is not None, "embedded io24 package was not located")
    package = dll[start:end]
    package_info = io24_firmware.inspect_io24_recovery_package(package)
    _require(package_info["sha256"] == PACKAGE_SHA256,
             "embedded package SHA-256 differs")
    application = package[:APPLICATION_SIZE]
    application_digest = hashlib.sha256(application).hexdigest()
    _require(application_digest == APPLICATION_SHA256,
             "firmware application SHA-256 differs: %s" % application_digest)

    copy_entry = _u32s(application, COPY_TABLE_ENTRY_RAW, 3)
    _require(copy_entry == (
        RAM_INITIALIZER_SOURCE, RAM_POINTER_TABLE, RAM_INITIALIZER_SIZE),
        "startup RAM initializer copy entry differs: %r" % (copy_entry,))

    stat_pointers = _u32s(package, STAT_POINTERS_RAW, 4)
    expected_stat_pointers = tuple(FIRMWARE_BASE + offset
                                   for offset in STAT_OFFSETS)
    _require(stat_pointers == expected_stat_pointers,
             "native Stat pointer table differs: %r" % (stat_pointers,))
    stat_lengths = _u32s(application, STAT_LENGTHS_RAW, 4)
    _require(stat_lengths == STAT_LENGTHS,
             "native Stat length table differs: %r" % (stat_lengths,))

    expected_offsets = []
    cursor = STAT_OFFSETS[0]
    for length in stat_lengths:
        expected_offsets.append(cursor)
        cursor += length
    _require(tuple(expected_offsets) == STAT_OFFSETS,
             "native Stat records are not contiguous")
    _require(cursor == FIRST_FACTORY_OFFSET,
             "native Stat extent does not end at first factory record")

    factory_pointers = _u32s(package, FACTORY_POINTERS_RAW, FACTORY_COUNT)
    _require(factory_pointers[0] == FIRMWARE_BASE + FIRST_FACTORY_OFFSET,
             "first factory pointer does not follow native Stat records")
    first_factory, consumed = decode_preset_record_prefix(
        application[FIRST_FACTORY_OFFSET:])
    _require(application[FIRST_FACTORY_OFFSET] == ord("{"),
             "first factory library record is not a tagged archive")
    _require(first_factory.get("preset_name") == "Broadcast",
             "first factory library title differs")

    slots = []
    for index, (offset, length) in enumerate(zip(STAT_OFFSETS, stat_lengths)):
        record = application[offset:offset + length]
        summary = native_stat_summary(record, slot_index=index)
        summary.update({
            "index": index,
            "raw_offset": hex(offset),
            "sha256": hashlib.sha256(record).hexdigest(),
        })
        slots.append(summary)

    # The two Voice-FX-owning defaults carry the exact same model-5 state. Its four
    # words match the already mapped Delay live-state layout after that
    # message's 12-byte tag/size/index header.  This binds the native leaf's
    # leading u32 as a byte count, rather than another semantic parameter.
    expected_delay_state = struct.pack("<Ifff", 0, 0.5, 0.1, 0.19)
    for slot in slots[:2]:
        _require(slot["voicefx"]["selected_model"] == 5,
                 "Voice FX fallback does not select model 5")
        _require(slot["voicefx"]["state_bytes"] == len(expected_delay_state),
                 "native model-5 state byte count differs")
        _require(slot["voicefx"]["state_hex"] == expected_delay_state.hex(),
                 "native model-5 state differs from mapped Delay state")

    # Model 0's symmetric structured serializer declares and copies exactly
    # 0x14 bytes from model+0x340.  These exact instructions are sufficient to
    # pin the model-0 native leaf size without attributing any physical result.
    serializer_anchors = {
        0x53696: bytes.fromhex("1421"),       # movs r1, #0x14
        0x536A6: bytes.fromhex("08f55071"),   # add.w r1, r8, #0x340
        0x536AA: bytes.fromhex("1422"),       # movs r2, #0x14
    }
    for offset, expected in serializer_anchors.items():
        _require(application[offset:offset + len(expected)] == expected,
                 "model-0 serializer anchor differs at %#x" % offset)

    return {
        "status": (
            "FIRMWARE128_STAT_DEFAULTS_NATIVE_V2_SEPARATE_FROM_TAGGED_LIBRARY"
        ),
        "source": {
            "uc472_dll_sha256": digest,
            "package_offset": hex(start),
            "package_sha256": package_info["sha256"],
            "application_sha256": application_digest,
            "firmware_version": version,
        },
        "startup_binding": {
            "copy_table_entry_raw_offset": hex(COPY_TABLE_ENTRY_RAW),
            "initializer_source": hex(RAM_INITIALIZER_SOURCE),
            "pointer_table_destination": hex(RAM_POINTER_TABLE),
            "initializer_bytes": RAM_INITIALIZER_SIZE,
            "stat_pointer_table_destination": hex(RAM_POINTER_TABLE + 4),
            "factory_pointer_table_destination": hex(RAM_POINTER_TABLE + 0x14),
        },
        "native_stat": {
            "length_table_raw_offset": hex(STAT_LENGTHS_RAW),
            "lengths": list(stat_lengths),
            "records": slots,
            "end_raw_offset": hex(cursor),
        },
        "voicefx_native_bridge": {
            "voicefx_storage_slot_indexes": [0, 1],
            "channel_strip_only_slot_indexes": [2, 3],
            "storage_owner_does_not_fix_runtime_input": True,
            "component_id": 201,
            "parent_version": 6,
            "default_selected_model": 5,
            "model5_state_bytes": len(expected_delay_state),
            "model5_state_hex": expected_delay_state.hex(),
            "model5_matches_mapped_delay_state": True,
            "model0_serializer_raw_offset": hex(MODEL0_SERIALIZER_RAW),
            "model0_state_bytes": MODEL0_STATE_BYTES,
            "model0_state_source": "model+0x340",
        },
        "factory_library": {
            "count": FACTORY_COUNT,
            "first_raw_offset": hex(FIRST_FACTORY_OFFSET),
            "first_prefix_hex": application[
                FIRST_FACTORY_OFFSET:FIRST_FACTORY_OFFSET + 4].hex(),
            "first_record_bytes": consumed,
            "first_preset_name": first_factory["preset_name"],
        },
        "correction": {
            "json_archive_directly_native_stat_eligible": False,
            "old_shared_tagged_record_model": "RETRACTED",
            "remaining_boundary": (
                "OTHER_NATIVE_COMPONENT_LEAVES_AND_PHYSICAL_OUTCOMES_UNPROVED"
            ),
        },
    }


def build_model0_candidates(dll):
    """Build exact reversible slot-0/1 candidates without device access.

    The four returned binary artifacts contain two byte-identical firmware
    defaults and their model-0 derivatives.  This function deliberately uses
    the pinned firmware defaults because a device's current stored slot body is
    not readable through the known protocol.
    """
    report = analyze(dll)
    start, end, _version = io24_firmware.locate_firmware(dll)
    _require(start is not None, "embedded io24 package was not located")
    application = dll[start:end][:APPLICATION_SIZE]
    artifacts = {}
    candidates = []
    for slot_index in (0, 1):
        offset = STAT_OFFSETS[slot_index]
        length = STAT_LENGTHS[slot_index]
        base = application[offset:offset + length]
        candidate = build_native_model0_stat_record(
            base,
            slot_index,
            **MODEL0_REVERB_PARAMETERS,
        )
        base_chunks = {
            chunk.key: chunk.payload
            for chunk in decode_native_stat_record(base).chunks
        }
        candidate_chunks = {
            chunk.key: chunk.payload
            for chunk in decode_native_stat_record(candidate).chunks
        }
        _require(candidate_chunks[b"opt "] == base_chunks[b"opt "],
                 "candidate changed the native Fat Channel state")
        default_name = "slot%d-firmware-default.stat" % slot_index
        candidate_name = "slot%d-model0-private-reverb.stat" % slot_index
        artifacts[default_name] = base
        artifacts[candidate_name] = candidate
        candidates.append({
            "slot_index": slot_index,
            "storage_role": "VOICEFX_COMPONENT_201_OWNER",
            "default_file": default_name,
            "default_bytes": len(base),
            "default_sha256": hashlib.sha256(base).hexdigest(),
            "candidate_file": candidate_name,
            "candidate_bytes": len(candidate),
            "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
            "fat_channel_preserved_byte_for_byte": True,
            "changed_top_level_component": 201,
        })
    report["model0_private_reverb_candidates"] = {
        "parameters": dict(MODEL0_REVERB_PARAMETERS),
        "records": candidates,
        "current_device_slot_contents_readable": False,
        "restoration_basis": "EXACT_FIRMWARE_DEFAULT_NOT_CURRENT_DEVICE_CONTENT",
        "device_io_performed": False,
        "physical_outcome": "UNOBSERVED",
    }
    return report, artifacts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uc472_dspusbdevice", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--candidate-directory", type=Path,
        help="write exact slot-0/1 firmware defaults and model-0 derivatives",
    )
    arguments = parser.parse_args(argv)
    try:
        source = arguments.uc472_dspusbdevice.read_bytes()
        if arguments.candidate_directory is None:
            report = analyze(source)
            artifacts = {}
        else:
            report, artifacts = build_model0_candidates(source)
            arguments.candidate_directory.mkdir(parents=True, exist_ok=True)
            destinations = {
                name: arguments.candidate_directory / name
                for name in artifacts
            }
            existing = [str(path) for path in destinations.values()
                        if path.exists()]
            if existing:
                raise AnalysisError(
                    "refusing to overwrite candidate artifacts: %s" %
                    ", ".join(existing))
            for name, data in artifacts.items():
                destinations[name].write_bytes(data)
    except (OSError, ValueError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 2
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(encoded, end="")
    else:
        arguments.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
