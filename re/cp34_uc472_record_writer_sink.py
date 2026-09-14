#!/usr/bin/env python3
"""Source-bind the UC 4.7.2 save serializer to record-buffer byte zero.

The analyzer accepts only the exact officially reacquired UC 4.7.2
``dspusbdevice.dll``.  It follows one same-slot snapshot/send path through the
archive writer adapter and selected record's append implementation.  Vendor
code is never loaded or executed, and Wine, USB, audio, and firmware hardware
are never accessed.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from capstone.x86_const import X86_INS_JMP, X86_INS_LEA


RE_DIR = Path(__file__).resolve().parent
if str(RE_DIR) not in sys.path:
    sys.path.insert(0, str(RE_DIR))

import cp34_uc5_serializer_comparison as pe_helpers  # noqa: E402


class AnalysisError(ValueError):
    """The input differs from the exact UC 4.7.2 source or byte flow."""


UC472_SIZE = 4_979_672
UC472_SHA256 = (
    "de685e89c88b191b9709145056aa37d58a76f141a53a9c153"
    "3dff917f611fd28"
)
UC472_IMAGE_BASE = 0x180000000

SLOT_SNAPSHOT = 0x1800420C0
SLOT_SEND = 0x1800421C0
RECORD_LOOKUP = 0x180042060
RECORD_SERIALIZER = 0x18002E270
RECORD_ELEMENT_CONSTRUCTOR = 0x18002FDF0
RECORD_VTABLE = 0x18043A658
RECORD_RESET = 0x180063020
RECORD_APPEND = 0x180063060
WRITER_PRIMARY_VTABLE = 0x18043AA08
WRITER_SECONDARY_VTABLE = 0x18043AA50
WRITER_ADAPTER = 0x1800649A0
SENDER_VTABLE = 0x1804393E0
MEMP_FRAGMENTER = 0x180050F10
QUEUE_TARGET = 0x180053420
ARCHIVE_OPEN = 0x1800688B0
COPY_THUNK = 0x1800D14D8


EXACT_INSTRUCTIONS = {
    # The caller is the active-slot settled-state synchronizer. It requires a
    # pending timestamp, more than 500 ms elapsed, the same selected slot, no
    # intervening event flag, and dirty bit 1 before snapshot/send.
    0x180041BAC: "488b47c0",
    0x180041BB0: "4885c0",
    0x180041BB3: "0f8884000000",
    0x180041BB9: "488b542470",
    0x180041BBE: "482bd0",
    0x180041BC1: "4881faf4010000",
    0x180041BC8: "7e73",
    0x180041BCA: "453bfe",
    0x180041BCD: "756e",
    0x180041BCF: "84c9",
    0x180041BD1: "756a",
    0x180041BD3: "f6476002",
    0x180041BD7: "48c747c0ffffffff",
    0x180041BDF: "0f84fa010000",

    # One caller snapshots and sends the same r14d slot in sequence.
    0x180041C19: "418bd6",
    0x180041C21: "84c0",
    0x180041C29: "488d8fa8feffff",
    0x180041C30: "418bd6",

    # Snapshot lookup result (rax) becomes the serializer output (rcx), while
    # the controller remains its source (rdx).  It returns success directly.
    0x180042103: "8bd7",
    0x180042105: "488bcb",
    0x18004210D: "488bc8",
    0x180042110: "488bd3",
    0x180042118: "b001",

    # The Stat sender selects component+0x2d8 + slot*0x38 and supplies that
    # record as r9 to sender virtual slot +0x10 at component+0x308.
    0x1800421CA: "4863da",
    0x1800421D0: "8bd3",
    0x180042201: "488b8108030000",
    0x180042208: "4c8b5810",
    0x180042218: "4c6bcb38",
    0x18004221C: "4c0389d8020000",
    0x18004222C: "4c8d442440",
    0x180042231: "c744244074617453",
    0x180042239: "488d542448",
    0x18004223E: "895c2444",
    0x180042242: "4881c108030000",
    0x180042249: "48c74424486c707041",
    0x180042252: "41ffd3",

    # The component owns four 0x38-byte records at +0x340 via +0x2d8, and a
    # sender object at +0x308.
    0x1800305E4: "488d9ed0020000",
    0x1800305EF: "488d4b70",
    0x1800305F3: "48894b08",
    0x1800305F7: "c7431004000000",
    0x18003062B: "488d4338",
    0x180030633: "488d15a68d4000",
    0x18003063A: "488910",
    0x18003066D: "4c8d0d7cf7ffff",
    0x180030674: "ba38000000",
    0x180030679: "41b804000000",

    # Each record starts empty with its final vtables and known members.
    0x18002FE0A: "488d0547a84000",
    0x18002FE11: "488901",
    0x18002FE14: "488d056da84000",
    0x18002FE1B: "48894108",
    0x18002FE21: "48894110",
    0x18002FE25: "48894118",
    0x18002FE29: "c6412001",
    0x18002FE2D: "48c7412800200000",
    0x18002FE35: "894130",

    # Serializer captures the output as r14, resets cursor and length, installs
    # the writer vtables, binds r14 at writer+0x18, and opens a null-name map.
    0x18002E28C: "488bda",
    0x18002E28F: "4c8bf1",
    0x18002E2A3: "4533ff",
    0x18002E43F: "498b06",
    0x18002E442: "4533c0",
    0x18002E445: "33d2",
    0x18002E447: "498bce",
    0x18002E44A: "ff5008",
    0x18002E44D: "45897e30",
    0x18002E458: "45897e2c",
    0x18002E45C: "488d05a5c54000",
    0x18002E463: "488945d0",
    0x18002E46E: "488d05dbc54000",
    0x18002E475: "488945d8",
    0x18002E479: "4c8975e8",
    0x18002E48E: "4533c0",
    0x18002E491: "33d2",
    0x18002E493: "488d4dd0",

    # A null name selects the zero-length branch.  The first writer operation
    # is exactly one byte, 0x7b ('{').
    0x1800688BC: "4885d2",
    0x1800688BF: "488d055ae90700",
    0x1800688CC: "480f45c2",
    0x1800688D0: "48c7c3ffffffff",
    0x1800688D7: "48ffc3",
    0x1800688DA: "803c1800",
    0x1800688E4: "85db",
    0x180068A06: "488b4508",
    0x180068A0A: "488d542440",
    0x180068A0F: "41b801000000",
    0x180068A15: "c64424407b",
    0x180068A1A: "488d4d08",
    0x180068A1E: "ff5008",

    # The secondary writer receiver reaches writer+0x18, then tailcalls the
    # record's append slot.
    0x1800649A0: "488b4910",
    0x1800649A4: "488b01",
    0x1800649A7: "48ff6018",

    # With r8d=0, record reset stores edx=0 to cursor +0x2c.
    0x180063020: "4585c0",
    0x180063023: "740f",
    0x180063034: "89512c",

    # Append writes source bytes directly at data+cursor, then advances cursor
    # and length.  There is no prefix or headroom adjustment.
    0x180063074: "488bd9",
    0x180063077: "4963f8",
    0x18006307A: "8b492c",
    0x1800630CC: "8b4b2c",
    0x1800630D3: "4863c9",
    0x1800630D6: "4c8bc7",
    0x1800630D9: "48034b10",
    0x1800630DD: "488bd5",
    0x1800630E5: "017b2c",
    0x1800630E8: "8b4b2c",
    0x1800630EB: "3b4b30",
    0x1800630F0: "894b30",

    # Fragmenter captures r9, then reads the selected record's length/data.
    0x180050F29: "498bd8",
    0x180050F2C: "c7442420506d654d",
    0x180050F34: "4c8bea",
    0x180050F37: "c7442424ec070000",
    0x180050F56: "4d8bf9",
    0x180050F5E: "8b03",
    0x180050F60: "4533c0",
    0x180050F69: "8b4304",
    0x180050F6C: "418bf0",
    0x180050F73: "418b4730",
    0x180050FEB: "498b5710",
    0x180051001: "488d4c243d",
    0x180051006: "440fb7c0",
    0x18005105D: "4d8bc5",
    0x180051060: "488d542420",
}


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _read_u64(image_base, sections, address):
    raw = pe_helpers._section_bytes(image_base, sections, address, 8)
    return struct.unpack("<Q", raw)[0]


def _rip_target(image_base, sections, address):
    return pe_helpers._rip_memory_target(
        image_base, sections, address, X86_INS_LEA)


def analyze(data):
    """Return the exact UC 4.7.2 writer-to-record reconciliation report."""
    digest = hashlib.sha256(data).hexdigest()
    _require(len(data) == UC472_SIZE,
             "UC 4.7.2 size differs: %d" % len(data))
    _require(digest == UC472_SHA256,
             "UC 4.7.2 SHA-256 differs: %s" % digest)

    try:
        image_base, sections = pe_helpers._parse_pe(data)
        _require(image_base == UC472_IMAGE_BASE,
                 "UC 4.7.2 image base differs: %#x" % image_base)

        for address, expected_hex in EXACT_INSTRUCTIONS.items():
            pe_helpers._require_bytes(
                image_base, sections, address, expected_hex)

        direct_edges = {
            0x180041C1C: SLOT_SNAPSHOT,
            0x180041C33: SLOT_SEND,
            0x180042108: RECORD_LOOKUP,
            0x180042113: RECORD_SERIALIZER,
            0x18003067F: 0x1800D0930,
            0x18002E497: ARCHIVE_OPEN,
            0x1800630E0: COPY_THUNK,
            0x18005100A: COPY_THUNK,
            0x180051065: QUEUE_TARGET,
        }
        for address, target in direct_edges.items():
            pe_helpers._require_direct_target(
                image_base, sections, address, target)

        _require(_rip_target(image_base, sections, 0x180030633)
                 == SENDER_VTABLE,
                 "sender vtable reference differs")
        _require(_rip_target(image_base, sections, 0x18003066D)
                 == RECORD_ELEMENT_CONSTRUCTOR,
                 "record element constructor reference differs")
        _require(_rip_target(image_base, sections, 0x18002FE0A)
                 == RECORD_VTABLE,
                 "record vtable reference differs")
        _require(_rip_target(image_base, sections, 0x18002FE14)
                 == 0x18043A688,
                 "record secondary vtable reference differs")
        _require(_rip_target(image_base, sections, 0x18002E45C)
                 == WRITER_PRIMARY_VTABLE,
                 "writer primary vtable reference differs")
        _require(_rip_target(image_base, sections, 0x18002E46E)
                 == WRITER_SECONDARY_VTABLE,
                 "writer secondary vtable reference differs")

        _require(_read_u64(image_base, sections, SENDER_VTABLE + 0x10)
                 == MEMP_FRAGMENTER,
                 "sender vtable slot +0x10 differs")
        _require(_read_u64(image_base, sections, RECORD_VTABLE + 0x08)
                 == RECORD_RESET,
                 "record reset vtable slot differs")
        _require(_read_u64(image_base, sections, RECORD_VTABLE + 0x18)
                 == RECORD_APPEND,
                 "record append vtable slot differs")
        _require(_read_u64(
            image_base, sections, WRITER_SECONDARY_VTABLE + 0x08)
            == WRITER_ADAPTER,
            "writer secondary slot +0x8 differs")

        pe_helpers._require_jle_target(
            image_base, sections, 0x1800688E6, 0x180068A06)
        empty_name = _rip_target(image_base, sections, 0x1800688BF)
        _require(
            pe_helpers._section_bytes(
                image_base, sections, empty_name, 1) == b"\0",
            "archive fallback name is not empty",
        )

        copy_iat = pe_helpers._rip_memory_target(
            image_base, sections, COPY_THUNK, X86_INS_JMP)
        imports = pe_helpers._import_names_by_iat(
            data, image_base, sections)
        _require(imports.get(copy_iat) == "memcpy",
                 "record copy thunk does not resolve to memcpy")
    except (pe_helpers.AnalysisError,
            pe_helpers.PeAnalysisError) as error:
        raise AnalysisError(str(error)) from error

    return {
        "boundary": (
            "UC472_SERIALIZER_RESOLVED_DEVICE_COMMIT_RUNTIME_"
            "COMPONENT_SELECTION_AND_AUDIBILITY_REMAIN_UNOBSERVED"
        ),
        "first_write": {
            "adapter": "0x1800649a0",
            "adapter_record_flow": (
                "writer+8 receiver +0x10 -> writer+0x18 -> r14 record"
            ),
            "archive_call": "0x180068a1e -> writer vtable+0x8",
            "cursor_after_success": 1,
            "cursor_before": 0,
            "destination": "record.data(+0x10)+record.cursor(+0x2c)",
            "length_after_success": 1,
            "length_before": 0,
            "logical_byte_hex": "7b",
            "logical_size": 1,
            "native_u32_two_prefix_inserted": False,
            "physical_prefix_hex": "7b",
            "record_append": "0x180063060",
            "record_copy": "0x1800630e0 -> memcpy",
        },
        "post_serializer_send": {
            "caller_pair": (
                "0x180041c1c snapshot then 0x180041c33 send, same r14d slot"
            ),
            "fragmenter": "0x180050f10",
            "fragmenter_record_members": "data +0x10, length +0x30",
            "post_serializer_mutation": False,
            "snapshot_return": (
                "0x180042113 serializer call -> 0x180042118 success return"
            ),
        },
        "settled_state_trigger": {
            "caller_range": "0x180041bac..0x180041c38",
            "pending_timestamp_member": "owner-0x40",
            "elapsed_compare": "now - pending_timestamp > 500",
            "elapsed_threshold_ms": 500,
            "same_selected_slot": "r15d == r14d",
            "intervening_event_required_clear": True,
            "dirty_flag": "owner+0x60 bit 1 (mask 0x2)",
            "pending_timestamp_cleared_before_send": True,
            "role": "ACTIVE_SLOT_SETTLED_STATE_SYNCHRONIZER",
        },
        "reconciliation": {
            "firmware_recall": "stored_record[0:4] reaches 0x531e0 unchanged",
            "firmware_required_native_u32": "0x00000002",
            "uc472_physical_first_byte": "0x7b",
            "uc472_prefix_eligible_for_native_u32_two": False,
        },
        "record_collection": {
            "count": 4,
            "element_constructor": "0x18002fdf0",
            "element_stride": "0x38",
            "owner_member": "controller+0x2d8 -> controller+0x340",
            "record_append_target": "0x180063060",
            "record_reset_target": "0x180063020",
            "record_vtable": "0x18043a658",
            "vector_constructor_call": "0x18003067f -> 0x1800d0930",
        },
        "serializer_writer": {
            "adapter_output_member": "writer+0x18 = r14 record",
            "adapter_primary_vtable": "0x18043aa08",
            "adapter_secondary_vtable": "0x18043aa50",
            "cursor_reset": (
                "0x18002e44a -> record vtable+0x8 -> 0x180063020"
            ),
            "function": "0x18002e270",
            "length_reset": "0x18002e44d: record+0x30 = 0",
            "output_record": "r14",
        },
        "source": {
            "image_base": hex(image_base),
            "sha256": digest,
            "size": len(data),
        },
        "status": (
            "UC472_SAVE_SERIALIZER_SOURCE_BOUND_RECORD_BYTE_ZERO_"
            "0X7B_NO_NATIVE_U32_TWO_PREFIX"
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
