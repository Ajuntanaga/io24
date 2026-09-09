#!/usr/bin/env python3
"""Source-bind CP34 ``MemP/Stat`` ingress and storage framing.

The analyzer accepts only the exact firmware 1.28 application. It follows an
incoming ``Stat`` fragment through the preset record writer, the CRC/length
storage wrapper, and the paired reader. It reconciles that byte-preserving path
with the source-bound zero-selector recall route into structured-state method
``0x531e0`` through the final derived device vtable. It never emits or loads
firmware and never accesses USB or audio hardware.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from capstone import CS_ARCH_ARM, CS_MODE_THUMB, CS_OP_IMM, Cs


RE_DIR = Path(__file__).resolve().parent
if str(RE_DIR) not in sys.path:
    sys.path.insert(0, str(RE_DIR))

import cp34_firmware_recall_framing as predecessor  # noqa: E402


class AnalysisError(ValueError):
    """The input differs from the pinned firmware or expected byte path."""


FIRMWARE_SIZE = predecessor.FIRMWARE_SIZE
FIRMWARE_SHA256 = predecessor.FIRMWARE_SHA256
FIRMWARE_BASE = predecessor.FIRMWARE_BASE


CODE_SLICES = {
    "root_component_construction": (
        0x3C890, 0x54,
        "4e32838d6f96acaa5cdf21940ffcc31f404260841c0a90aeb4222b7daf500f77",
    ),
    "root_child_binding": (
        0x2FD18, 0x14,
        "ae20e284b90f90b6fbe355398956735550fabb9fc11529b5d6b6565dff6fdaf8",
    ),
    "root_memp_handler": (
        0x2F210, 0x64,
        "21ce6c37eec3b7bc075667a5c42b4e252ffbc08f493717d885029be2e7447c23",
    ),
    "component_constructor": (
        0x306BC, 0x48,
        "70132ab35e6d8c9c917669dee138edc170e0f37c2d0798241cac200d9a27d10e",
    ),
    "component_bind_route": (
        0x300AC, 0x10,
        "51178b6de0b723bd3e3c0c1d44e590fd325b5074ed590dcdf336db46f63a095e",
    ),
    "component_storage_bind": (
        0x306B4, 0x08,
        "d9acda92b239cc2b3c993cf57b79820fa6dd6b8577d4cb2414a025ac185312ce",
    ),
    "fragment_handler": (
        0x3099C, 0x70,
        "88af1e0c52748b560c297ca84b30c88c07c12ca19db3a4706d0ddb32b0120429",
    ),
    "record_writer": (
        0x3092C, 0x70,
        "7898bcd992c0df3971fa8cf55cf2eb5a4947c6980da5c2d8eab0f09dca6b8826",
    ),
    "storage_wrapper_write": (
        0x2BFE4, 0xC0,
        "f697af59a7d35d1070c7738b0806160e6d007f3b359ed7b7c5e6c1bcd0571656",
    ),
    "storage_wrapper_read": (
        0x2C0A8, 0x108,
        "8aef3313b31e243d842f871f64b192d714c1433968667341be82274c606b58e1",
    ),
    "backend_constructor": (
        0x31A34, 0x70,
        "2b9f9587c812b6e1efcd19c4ad2a65ab2ad28a74363af935db3cb2e6cf8ee2f8",
    ),
    "backend_startup_bind": (
        0x31AB0, 0x38,
        "1130e7c1d6411fab1f9c59a10208a178d6b532a7713009eac11d0a2f95e07bdf",
    ),
    "backend_write_read": (
        0x316B0, 0x64,
        "4daac328e7877ab540e1177abf8258ab8a8a703f7650cbcef1b4694a06ef2e31",
    ),
    "checksum_adapter": (
        0x3196C, 0x28,
        "04540323dc7eda8e084fcff2b637ec4bc456f63de18a94e7f3ab06bea9345371",
    ),
    "crc32_update": (
        0x3665C, 0x24,
        "65fdd190ca302d30f9bdcbc22d40a5150e7cb82ed95bfc281dd16db2791b6742",
    ),
}


U32_ANCHORS = {
    # Root and preset component dynamic ingress slots.
    0x6D288: 0x6004F211,
    0x30704: 0x600874F8,
    0x67510: 0x6005099D,
    0x30A10: 0x53746174,  # Stat

    # Generic CRC/length wrapper and its exact slots.
    0x2C1BC: 0x60086994,
    0x66994: 0x6004BFE5,
    0x66998: 0x6004C0A9,
    0x669A0: 0x6004BF41,

    # Storage backend subobject and write/read/checksum slots.
    0x31AA8: 0x6008760C,
    0x676EC: 0x600516DD,
    0x676F0: 0x6005170D,
    0x676F8: 0x6005198D,
    0x31988: 0x600883E0,
}


EXACT_INSTRUCTIONS = {
    # Root construction retains root+0x1240 as root+0x70 and constructs the
    # component with vtable 0x600874f8.
    0x3C894: "00f59256",
    0x3C89E: "3146",
    0x3C8CA: "3046",
    0x2FD22: "2667",
    0x306BC: "114b",
    0x306C4: "40f8083b",

    # MemP root dispatch loads the retained component and preserves r1 until
    # the non-default component vtable +0x18 call.
    0x2F216: "006f",
    0x2F21C: "0368",
    0x2F21E: "0d46",
    0x2F220: "9b69",
    0x2F26E: "9847",

    # Stat validation and the direct handoff to record writer 0x3092c.
    0x309A2: "8b68",
    0x309AA: "194a",
    0x309B0: "c968",
    0x309B2: "0329",
    0x309B4: "12dc",
    0x309C6: "d4f81910",
    0x30A02: "2146",
    0x30A04: "3046",

    # Record writer: optional separate four-byte total-length record, then
    # the unchanged fragment pointer and u16 fragment length.
    0x30930: "d1f81230",
    0x30934: "8846",
    0x30936: "1646",
    0x30938: "00f10807",
    0x3093C: "3bb9",
    0x3093E: "01f11902",
    0x30942: "0423",
    0x30944: "3146",
    0x30946: "3846",
    0x30950: "0436",
    0x30956: "d8f81250",
    0x3095A: "0644",
    0x3097C: "3146",
    0x3097E: "3846",
    0x30980: "b8f81730",
    0x30984: "08f11d02",

    # Write wrapper preserves source/size, calculates CRC32, and emits
    # crc32@+0, payload_length@+4, payload@+8 via backend slot zero.
    0x2BFEC: "9b46",
    0x2BFF6: "0d46",
    0x2BFF8: "9246",
    0x2C002: "cdf808b0",
    0x2C034: "6068",
    0x2C036: "5146",
    0x2C038: "029a",
    0x2C03A: "0368",
    0x2C03C: "db68",
    0x2C040: "6168",
    0x2C042: "0390",
    0x2C044: "0423",
    0x2C048: "0846",
    0x2C04A: "03aa",
    0x2C04C: "2946",
    0x2C04E: "3668",
    0x2C054: "6068",
    0x2C056: "0423",
    0x2C058: "02aa",
    0x2C05C: "e918",
    0x2C05E: "3668",
    0x2C064: "6068",
    0x2C066: "5246",
    0x2C068: "05f10801",
    0x2C06C: "029b",
    0x2C06E: "0468",
    0x2C070: "2468",

    # Read wrapper consumes crc32 and length internally, reads exactly the
    # stored payload from +8 to the caller destination, and verifies CRC32.
    0x2C0B0: "9846",
    0x2C0BA: "0d46",
    0x2C0BC: "1646",
    0x2C0DC: "6068",
    0x2C0E4: "02aa",
    0x2C0EA: "2946",
    0x2C0F0: "dcf804b0",
    0x2C0FC: "0423",
    0x2C102: "03aa",
    0x2C108: "e918",
    0x2C10A: "dcf804a0",
    0x2C114: "039a",
    0x2C116: "d8f80030",
    0x2C11A: "9342",
    0x2C152: "6068",
    0x2C154: "05f10801",
    0x2C158: "039b",
    0x2C15A: "3246",
    0x2C15C: "0568",
    0x2C15E: "6d68",
    0x2C164: "6068",
    0x2C166: "3146",
    0x2C168: "039a",
    0x2C16A: "0368",
    0x2C16C: "db68",
    0x2C170: "029b",
    0x2C172: "8342",
    0x2C176: "039b",
    0x2C17A: "c8f80030",

    # Backend interface construction and binding into component+8 wrapper.
    0x31A34: "1b4a",
    0x31A36: "1c4b",
    0x31A66: "03f1e001",
    0x31A88: "c4e90a01",
    0x31ACC: "04f12c01",
    0x31AD0: "e06f",
    0x2D660: "006b",
    0x300AC: "006f",
    0x300B0: "0368",
    0x300B2: "db68",
    0x300BA: "1847",
    0x306B4: "0830",
    0x2C1B4: "014a",
    0x2C1B6: "c0e90021",
    0x2C1C0: "4160",

    # Backend write/read forwarding preserves all three explicit arguments;
    # write supplies only its separate flag-one stack argument.
    0x316B0: "006a",
    0x316BA: "0393",
    0x316BE: "cde90421",
    0x316C2: "a047",
    0x316C8: "0095",
    0x316CA: "6468",
    0x316CC: "dde90421",
    0x316D0: "a047",
    0x316E4: "006a",
    0x316EE: "0193",
    0x316F0: "cde90221",
    0x316F4: "a047",
    0x316F8: "0399",
    0x316FA: "a468",
    0x316FC: "dde90132",
    0x31700: "a047",

    # CRC32 initializes to all ones, visits exactly r2 source bytes, and
    # returns the inverted accumulator.
    0x31970: "4ff0ff33",
    0x31974: "044c",
    0x31976: "6846",
    0x31978: "cde90043",
    0x31980: "0198",
    0x31982: "c043",
    0x3665C: "30b4",
    0x3665E: "4468",
    0x36660: "5ab1",
    0x36662: "0a44",
    0x36664: "0568",
    0x36666: "11f8013b",
    0x3666A: "6340",
    0x3666C: "9142",
    0x3666E: "dbb2",
    0x36670: "55f82330",
    0x36674: "83ea1424",
    0x36678: "f5d1",
    0x3667A: "4460",
}


DIRECT_TARGETS = {
    0x3C8C4: FIRMWARE_BASE + 0x30260,
    0x30264: FIRMWARE_BASE + 0x2FCA8,
    0x3C8DC: FIRMWARE_BASE + 0x306BC,
    0x306B6: FIRMWARE_BASE + 0x2C1C0,
    0x30A06: FIRMWARE_BASE + 0x3092C,
    0x30948: FIRMWARE_BASE + 0x2BFE4,
    0x30952: FIRMWARE_BASE + 0x2BF40,
    0x30962: FIRMWARE_BASE + 0x2BF50,
    0x30970: FIRMWARE_BASE + 0x2BF40,
    0x30988: FIRMWARE_BASE + 0x2BFE4,
    0x30AB8: FIRMWARE_BASE + 0x2C0A8,
    0x30B16: FIRMWARE_BASE + 0x2C0A8,
    0x31AD2: FIRMWARE_BASE + 0x2D660,
    0x2D664: FIRMWARE_BASE + 0x300AC,
    0x316E0: FIRMWARE_BASE + 0x316B0,
    0x31710: FIRMWARE_BASE + 0x316E4,
    0x3197C: FIRMWARE_BASE + 0x3665C,
    0x31990: FIRMWARE_BASE + 0x3196C,
}


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _span(data, offset, size):
    end = offset + size
    _require(0 <= offset <= end <= len(data),
             "span at %#x exceeds firmware" % offset)
    return data[offset:end]


def _u32(data, offset):
    return struct.unpack("<I", _span(data, offset, 4))[0]


def _instruction(data, offset):
    decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    decoder.detail = True
    decoded = list(decoder.disasm(
        _span(data, offset, 4), FIRMWARE_BASE + offset, count=1))
    _require(decoded and decoded[0].address == FIRMWARE_BASE + offset,
             "cannot decode Thumb instruction at %#x" % offset)
    return decoded[0]


def _require_direct_target(data, offset, expected):
    instruction = _instruction(data, offset)
    targets = [
        operand.imm for operand in instruction.operands
        if operand.type == CS_OP_IMM
    ]
    _require(
        len(targets) == 1 and targets[0] == expected,
        "branch at %#x targets %s, expected %#x" % (
            offset,
            ", ".join("%#x" % target for target in targets) or "nothing",
            expected,
        ),
    )


def analyze(data):
    """Return the exact ingress/storage/recall logical-byte report."""
    digest = hashlib.sha256(data).hexdigest()
    _require(len(data) == FIRMWARE_SIZE,
             "firmware size differs: %d" % len(data))
    _require(digest == FIRMWARE_SHA256,
             "firmware SHA-256 differs: %s" % digest)

    try:
        recall_report = predecessor.analyze(data)
    except predecessor.AnalysisError as error:
        raise AnalysisError(str(error)) from error
    _require(
        recall_report["status"]
        == (
            "STORED_STAT_RECALL_SOURCE_BOUND_BYTE_PRESERVING_NO_PREFIX_"
            "INSERTION"
        ),
        "predecessor recall status differs",
    )

    for name, (offset, size, expected) in CODE_SLICES.items():
        actual = hashlib.sha256(_span(data, offset, size)).hexdigest()
        _require(actual == expected,
                 "%s slice differs: %s" % (name, actual))

    for offset, expected in U32_ANCHORS.items():
        actual = _u32(data, offset)
        _require(actual == expected,
                 "u32 anchor at %#x differs: %#x" % (offset, actual))

    for offset, expected_hex in EXACT_INSTRUCTIONS.items():
        expected = bytes.fromhex(expected_hex)
        actual = _span(data, offset, len(expected))
        _require(actual == expected,
                 "instruction bytes differ at %#x: %s" % (
                     offset, actual.hex()))

    for offset, target in DIRECT_TARGETS.items():
        _require_direct_target(data, offset, target)

    return {
        "backend_forwarding": {
            "backend_vtable": "0x600876ec",
            "checksum": "slot +0xc -> 0x3198c/0x3196c -> CRC32 0x3665c",
            "read": (
                "slot +0x4 -> 0x3170c/0x316e4, same "
                "address/destination/length"
            ),
            "write": (
                "slot +0x0 -> 0x316dc/0x316b0, same "
                "address/source/length, flag 1"
            ),
        },
        "boundary": (
            "PHYSICAL_BACKEND_COMMIT_AND_UC472_SERIALIZER_REMAIN_UNOBSERVED"
        ),
        "ingress_dispatch": {
            "component_binding": "root+0x70 = root+0x1240",
            "component_vtable": "0x600874f8 slot +0x18 -> 0x3099c",
            "handler": "0x2f210",
            "message_argument_preserved": True,
            "root_vtable_slot": "0x6d288 -> 0x2f210",
            "slot_range": "0..3",
            "stat_tag": "Stat",
            "writer_call": "0x30a06 -> 0x3092c",
        },
        "paired_record_reader": {
            "entry": "0x30a90",
            "first_fragment_storage_advance": (
                "4 logical length bytes + 8 wrapper bytes"
            ),
            "logical_round_trip": (
                "incoming message+0x1d -> recalled message+0x1d"
            ),
            "payload_destination": "message+0x1d",
            "payload_read": "0x30b16 -> 0x2c0a8",
            "prefix_inserted": False,
            "record_length_destination": "message+0x19",
            "record_length_read": "0x30ab8 -> 0x2c0a8",
        },
        "reconciliation": {
            "logical_byte_zero_at_paired_reader_output": (
                "incoming_payload[0]"
            ),
            "parser_visible_first_word": (
                "little_endian_u32(incoming_payload[0:4])"
            ),
            "structured_state_0x531e0_reached_on_zero_route": True,
            "structured_state_0x531e0_source_bound_caller": (
                "0x42266/0x42280 via final derived vtable 0x6012cb40"
            ),
            "wrapper_header_exposed_to_paired_reader_caller": False,
            "zero_selector_recall_after_accumulation": (
                "two structured-state callbacks through slot +0x38"
            ),
        },
        "record_writer": {
            "entry": "0x3092c",
            "first_fragment_condition": "fragment_offset == 0",
            "first_fragment_length_write": (
                "0x30948 -> 0x2bfe4, message+0x19, 4 bytes"
            ),
            "fragment_length": "u16(message+0x17)",
            "fragment_offset": "u32(message+0x12)",
            "native_u32_two_inserted": False,
            "payload_source": "message+0x1d",
            "payload_source_preserved": True,
            "payload_write": "0x30988 -> 0x2bfe4",
            "total_record_length": "u32(message+0x19)",
        },
        "source": {
            "image_base": "0x60020000",
            "sha256": FIRMWARE_SHA256,
            "size": FIRMWARE_SIZE,
        },
        "status": (
            "FIRMWARE_STAT_INGRESS_RECALL_SOURCE_BOUND_LOGICAL_BYTE_ZERO_"
            "UNCHANGED_NO_PREFIX_INSERTION"
        ),
        "storage_wrapper": {
            "backend_address_layout": (
                "crc32@+0 | payload_length@+4 | payload@+8"
            ),
            "checksum_validation": (
                "CRC32(original payload) stored and checked on read"
            ),
            "header_size": 8,
            "read": "0x2c0a8",
            "read_destination_preserved": True,
            "read_payload_source": "storage_address+8",
            "wrapper_header_exposed_to_caller": False,
            "wrapper_vtable": "0x60086994",
            "write": "0x2bfe4",
            "write_payload_destination": "storage_address+8",
            "write_payload_source_preserved": True,
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args(argv)

    try:
        report = analyze(arguments.firmware.read_bytes())
    except (OSError, AnalysisError) as error:
        print("error: %s" % error)
        return 1

    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(encoded, end="")
    else:
        arguments.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
