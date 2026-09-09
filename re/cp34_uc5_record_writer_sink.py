#!/usr/bin/env python3
"""Source-bind the installed UC5 archive writer to record-buffer byte zero.

The analyzer accepts only the exact installed UC5 ``dspusbdevice.dll``.  It
extends the sealed serializer comparison through the writer adapter and the
selected record's append implementation.  It never loads vendor code or
accesses Wine, USB, audio, or firmware hardware.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from capstone.x86_const import X86_INS_LEA


RE_DIR = Path(__file__).resolve().parent
if str(RE_DIR) not in sys.path:
    sys.path.insert(0, str(RE_DIR))

import cp34_uc5_serializer_comparison as predecessor  # noqa: E402


class AnalysisError(ValueError):
    """The input differs from the exact UC5 source or expected byte flow."""


UC5_SIZE = predecessor.UC5_SIZE
UC5_SHA256 = predecessor.UC5_SHA256
UC5_IMAGE_BASE = predecessor.UC5_IMAGE_BASE

RECORD_ELEMENT_CONSTRUCTOR = 0x180030570
RECORD_VTABLE = 0x18043B828
RECORD_RESET = 0x1800643B0
RECORD_APPEND = 0x1800643F0
WRITER_PRIMARY_VTABLE = 0x18043BBD8
WRITER_SECONDARY_VTABLE = 0x18043BC20
WRITER_ADAPTER = 0x180065D30


CODE_SLICES = {
    "record_collection": (
        0x180030D64, 0xA0,
        "7c93748aba222464ef85e5a78dc57df28e99bd8c408b22200b01af053f05f99e",
    ),
    "record_element_constructor": (
        0x180030570, 0x49,
        "bfd9c57ca84cc209ed100cbd15221512c5e2ccbfc8d1a9d26fa927e676107564",
    ),
    "serializer_writer_setup": (
        0x18002EBAF, 0x5D,
        "0983086b95f25a5e0a8599519be265bf9613ddcc63db95994afd1a26054a46c3",
    ),
    "writer_adapter": (
        0x180065D30, 0x0B,
        "0432777057e0f381106b9ba3ab440099700cfab5fe533c33491ea8b9c7ca72a1",
    ),
    "record_cursor_reset": (
        0x1800643B0, 0x3B,
        "2ef1ae79de86468415174032e6346c637c6e9faa6a1c4a8cc23cc7d7f7e29444",
    ),
    "record_append": (
        0x1800643F0, 0xB1,
        "ca7047a20db87343d461176a1f2de2dc25675dd5377f02202ae5cb72d4246158",
    ),
    "archive_first_write": (
        0x180069D96, 0x1B,
        "8245621a14a5bf89e01a69290b113f22b0538bbec0baddecee29ad89b60bac62",
    ),
    "snapshot_tail": (
        0x180042883, 0x22,
        "c77182331054a3b7393eab4b8b5f03d65ba3bd695282f352cd4c98a6738ef0b5",
    ),
    "caller_snapshot_send_pair": (
        0x180042392, 0x2B,
        "0ad3f82c634ba377f897259894153b10f6d2137d1a12f4b2477acc4aa8135bae",
    ),
}


EXACT_INSTRUCTIONS = {
    # Four 0x38-byte records are constructed at the pointer stored in +0x2d8.
    0x180030D64: "488d9ed0020000",      # owner at controller+0x2d0
    0x180030D6F: "488d4b70",            # array at controller+0x340
    0x180030D73: "48894b08",            # [controller+0x2d8] = array
    0x180030DED: "4c8d0d7cf7ffff",      # element constructor
    0x180030DF4: "ba38000000",          # stride 0x38
    0x180030DF9: "41b804000000",        # count four

    # Final element vtable and initially empty record members.
    0x18003058A: "488d0597b24000",
    0x180030591: "488901",
    0x18003059F: "33c0",
    0x1800305A1: "48894110",            # data +0x10 = null
    0x1800305A5: "48894118",            # allocation size +0x18 = 0
    0x1800305AD: "48c7412800200000",    # growth unit +0x28 = 0x2000
    0x1800305B5: "894130",              # length +0x30 = 0

    # Serializer resets the record, then binds it at writer +0x18.
    0x18002E9FF: "4c8bf1",              # r14 = output record
    0x18002EBB2: "4533c0",              # r8d = 0
    0x18002EBB5: "33d2",                # edx = 0
    0x18002EBB7: "498bce",              # rcx = r14
    0x18002EBBA: "ff5008",              # record vtable +0x8 reset
    0x18002EBBD: "45897e30",            # record length = 0
    0x18002EBCC: "488d0505d04000",      # writer primary vtable
    0x18002EBD3: "488945d0",
    0x18002EBDE: "488d053bd04000",      # writer secondary vtable
    0x18002EBE5: "488945d8",
    0x18002EBE9: "4c8975e8",            # writer +0x18 = r14

    # Empty-name archive emits one byte, 0x7b, through secondary slot +0x8.
    0x180069D96: "488b4508",
    0x180069D9A: "488d542440",
    0x180069D9F: "41b801000000",
    0x180069DA5: "c64424407b",
    0x180069DAA: "488d4d08",
    0x180069DAE: "ff5008",

    # Adapter loads writer+0x18 through secondary receiver +0x10 and tailcalls
    # record vtable slot +0x18.
    0x180065D30: "488b4910",
    0x180065D34: "488b01",
    0x180065D37: "48ff6018",

    # With r8d=0, record reset stores edx=0 to cursor +0x2c.
    0x1800643B0: "4585c0",
    0x1800643B3: "740f",
    0x1800643C4: "89512c",

    # Append computes data+cursor, copies exactly r8 bytes, then advances the
    # cursor and length.  There is no prefix or headroom adjustment.
    0x180064404: "488bd9",
    0x180064407: "4963f8",              # requested size
    0x18006440A: "8b492c",              # cursor
    0x18006445C: "8b4b2c",              # cursor after optional growth
    0x180064463: "4863c9",
    0x180064466: "4c8bc7",              # copy size
    0x180064469: "48034b10",            # destination data+cursor
    0x18006446D: "488bd5",              # source
    0x180064475: "017b2c",              # cursor += size
    0x180064478: "8b4b2c",
    0x18006447B: "3b4b30",              # compare current length
    0x180064480: "894b30",              # length = cursor

    # Snapshot returns immediately after serialization; caller sends same slot.
    0x18004288D: "488bc8",
    0x180042890: "488bd3",
    0x180042898: "b001",
    0x180042399: "418bd6",
    0x1800423A1: "84c0",
    0x1800423A9: "488d8fa8feffff",
    0x1800423B0: "418bd6",
}


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _read_u64(image_base, sections, address):
    raw = predecessor._section_bytes(image_base, sections, address, 8)
    return struct.unpack("<Q", raw)[0]


def _rip_target(image_base, sections, address):
    return predecessor._rip_memory_target(
        image_base, sections, address, X86_INS_LEA)


def analyze(data):
    """Return the exact UC5 logical-writer to physical-record report."""
    digest = hashlib.sha256(data).hexdigest()
    _require(len(data) == UC5_SIZE, "UC5 size differs: %d" % len(data))
    _require(digest == UC5_SHA256, "UC5 SHA-256 differs: %s" % digest)

    # Retain every source-bound predecessor assertion, including same-slot
    # snapshot/send, record member selection, fragmenter copy, and queue call.
    try:
        predecessor_report = predecessor.analyze(data)
        image_base, sections = predecessor._parse_pe(data)
    except (predecessor.AnalysisError,
            predecessor.PeAnalysisError) as error:
        raise AnalysisError(str(error)) from error
    _require(image_base == UC5_IMAGE_BASE,
             "UC5 image base differs: %#x" % image_base)

    for name, (address, size, expected) in CODE_SLICES.items():
        raw = predecessor._section_bytes(image_base, sections, address, size)
        actual = hashlib.sha256(raw).hexdigest()
        _require(actual == expected, "%s slice differs: %s" % (name, actual))

    for address, expected_hex in EXACT_INSTRUCTIONS.items():
        try:
            predecessor._require_bytes(
                image_base, sections, address, expected_hex)
        except predecessor.AnalysisError as error:
            raise AnalysisError(str(error)) from error

    direct_edges = {
        0x180030DFF: 0x1800D18A0,
        0x18002EC07: 0x180069C40,
        0x180064470: predecessor.COPY_THUNK,
        0x180042893: predecessor.RECORD_SERIALIZER,
        0x18004239C: predecessor.SLOT_SNAPSHOT,
        0x1800423B3: predecessor.SLOT_SEND,
    }
    for address, target in direct_edges.items():
        try:
            predecessor._require_direct_target(
                image_base, sections, address, target)
        except predecessor.AnalysisError as error:
            raise AnalysisError(str(error)) from error

    _require(_rip_target(image_base, sections, 0x180030DED)
             == RECORD_ELEMENT_CONSTRUCTOR,
             "record element constructor reference differs")
    _require(_rip_target(image_base, sections, 0x18003058A) == RECORD_VTABLE,
             "record vtable reference differs")
    _require(_rip_target(image_base, sections, 0x18002EBCC)
             == WRITER_PRIMARY_VTABLE,
             "writer primary vtable reference differs")
    _require(_rip_target(image_base, sections, 0x18002EBDE)
             == WRITER_SECONDARY_VTABLE,
             "writer secondary vtable reference differs")

    _require(_read_u64(image_base, sections, RECORD_VTABLE + 0x08)
             == RECORD_RESET,
             "record vtable reset slot differs")
    _require(_read_u64(image_base, sections, RECORD_VTABLE + 0x18)
             == RECORD_APPEND,
             "record vtable append slot differs")
    _require(_read_u64(image_base, sections, WRITER_SECONDARY_VTABLE + 0x08)
             == WRITER_ADAPTER,
             "writer secondary slot +0x8 differs")

    # The predecessor already resolves COPY_THUNK's PE import as memcpy.  Pin
    # that conclusion here so a future predecessor schema change fails closed.
    _require(
        predecessor_report["fragmenter"]["record_copy_call"]
        == "0x18005235a -> memcpy",
        "predecessor memcpy binding differs",
    )

    return {
        "boundary": (
            "UC5_ONLY_UC472_AND_FIRMWARE_INGRESS_STORAGE_"
            "TRANSFORM_UNRESOLVED"
        ),
        "first_write": {
            "adapter": "0x180065d30",
            "adapter_record_flow": (
                "writer+8 receiver +0x10 -> writer+0x18 -> r14 record"
            ),
            "archive_call": "0x180069dae -> writer vtable+0x8",
            "cursor_after_success": 1,
            "cursor_before": 0,
            "destination": "record.data(+0x10)+record.cursor(+0x2c)",
            "length_after_success": 1,
            "length_before": 0,
            "logical_byte_hex": "7b",
            "logical_size": 1,
            "native_u32_two_prefix_inserted": False,
            "physical_prefix_hex": "7b",
            "record_append": "0x1800643f0",
            "record_copy": "0x180064470 -> memcpy",
        },
        "post_serializer_send": {
            "caller_pair": (
                "0x18004239c snapshot then 0x1800423b3 send, same r14d slot"
            ),
            "fragmenter": "0x180052270",
            "fragmenter_record_members": "data +0x10, length +0x30",
            "post_serializer_mutation": False,
            "snapshot_return": (
                "0x180042893 serializer call -> 0x180042898 success return"
            ),
        },
        "reconciliation": {
            "firmware_recall": "stored_record[0:4] reaches 0x531e0 unchanged",
            "firmware_required_native_u32": "0x00000002",
            "uc5_physical_first_byte": "0x7b",
            "uc5_prefix_eligible_for_native_u32_two": False,
        },
        "record_collection": {
            "count": 4,
            "element_constructor": "0x180030570",
            "element_stride": "0x38",
            "owner_member": "controller+0x2d8 -> controller+0x340",
            "record_append_target": "0x1800643f0",
            "record_reset_target": "0x1800643b0",
            "record_vtable": "0x18043b828",
            "vector_constructor_call": "0x180030dff -> 0x1800d18a0",
        },
        "serializer_writer": {
            "adapter_output_member": "writer+0x18 = r14 record",
            "adapter_primary_vtable": "0x18043bbd8",
            "adapter_secondary_vtable": "0x18043bc20",
            "cursor_reset": (
                "0x18002ebba -> record vtable+0x8 -> 0x1800643b0"
            ),
            "function": "0x18002e9e0",
            "length_reset": "0x18002ebbd: record+0x30 = 0",
            "output_record": "r14",
        },
        "source": {
            "image_base": hex(image_base),
            "sha256": digest,
            "size": len(data),
        },
        "status": (
            "UC5_RECORD_WRITER_SOURCE_BOUND_PHYSICAL_BYTE_ZERO_"
            "0X7B_NO_PREFIX_INSERTION"
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pe_image", type=Path)
    arguments = parser.parse_args(argv)
    try:
        report = analyze(arguments.pe_image.read_bytes())
    except (OSError, AnalysisError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
