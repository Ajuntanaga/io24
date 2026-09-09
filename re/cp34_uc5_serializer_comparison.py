#!/usr/bin/env python3
"""Source-bind the installed UC5 save-record serializer's leading byte.

This analyzer is deliberately version-local and static.  It reads one exact
``dspusbdevice.dll`` image, verifies its identity, and checks the instruction
and vtable edges from slot snapshot through ``MemP/Stat`` fragmentation.  It
does not load vendor code, access Wine, or touch USB/audio hardware.

The result does not describe the missing UC 4.7.2 image and does not resolve
the firmware recall-to-live-``Stat`` transformation boundary.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from capstone import CS_ARCH_X86, CS_MODE_64, Cs
from capstone.x86_const import (
    X86_INS_CALL,
    X86_INS_JLE,
    X86_INS_JMP,
    X86_INS_LEA,
    X86_OP_IMM,
    X86_OP_MEM,
    X86_REG_RIP,
)


RE_DIR = Path(__file__).resolve().parent
if str(RE_DIR) not in sys.path:
    sys.path.insert(0, str(RE_DIR))

from cp34_host_queue_inventory import (  # noqa: E402
    AnalysisError as PeAnalysisError,
    _parse_pe,
)


class AnalysisError(ValueError):
    """The input differs from the exact UC5 source or its expected semantics."""


UC5_SIZE = 4_984_704
UC5_SHA256 = "567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b"
UC5_IMAGE_BASE = 0x180000000

SLOT_SNAPSHOT = 0x180042840
SLOT_SEND = 0x180042940
RECORD_LOOKUP = 0x1800427E0
RECORD_SERIALIZER = 0x18002E9E0
SENDER_VTABLE = 0x18043A5B0
MEMP_FRAGMENTER = 0x180052270
QUEUE_TARGET = 0x1800546B0
ARCHIVE_OPEN = 0x180069C40
COPY_THUNK = 0x1800D2448


EXACT_INSTRUCTIONS = {
    # One caller snapshots and sends the same r14d slot in sequence.
    0x180042399: "418bd6",              # mov edx,r14d
    0x1800423B0: "418bd6",              # mov edx,r14d

    # Snapshot lookup result (rax) becomes serializer output (rcx); the
    # controller remains the serializer source argument (rdx).
    0x180042883: "8bd7",                # mov edx,edi
    0x180042885: "488bcb",              # mov rcx,rbx
    0x18004288D: "488bc8",              # mov rcx,rax
    0x180042890: "488bd3",              # mov rdx,rbx

    # The dynamic Stat sender selects component+0x2d8 + slot*0x38 and passes
    # that record in r9 to sender virtual slot +0x10 at component+0x308.
    0x18004294A: "4863da",              # movsxd rbx,edx
    0x180042950: "8bd3",                # mov edx,ebx
    0x180042981: "488b8108030000",      # mov rax,[rcx+0x308]
    0x180042988: "4c8b5810",            # mov r11,[rax+0x10]
    0x180042998: "4c6bcb38",            # imul r9,rbx,0x38
    0x18004299C: "4c0389d8020000",      # add r9,[rcx+0x2d8]
    0x1800429AC: "4c8d442440",          # lea r8,[rsp+0x40]
    0x1800429B1: "c744244074617453",    # Stat
    0x1800429B9: "488d542448",          # lea rdx,[rsp+0x48]
    0x1800429BE: "895c2444",            # slot index
    0x1800429C2: "4881c108030000",      # add rcx,0x308
    0x1800429C9: "48c74424486c707041",  # Appl followed by index zero
    0x1800429D2: "41ffd3",              # call r11

    # The component constructor places this sender vtable at +0x2d0+0x38.
    0x180030D64: "488d9ed0020000",      # lea rbx,[rsi+0x2d0]
    0x180030DAB: "488d4338",            # lea rax,[rbx+0x38]
    0x180030DBA: "488910",              # mov [rax],rdx

    # Sender captures r9 as the record, then reads its length/data members.
    0x180052284: "498bd8",              # mov rbx,r8
    0x180052287: "c7442420506d654d",    # MemP
    0x18005228F: "4c8be2",              # mov r12,rdx
    0x180052292: "c7442424ec070000",    # length 0x7ec
    0x1800522B1: "4d8bf1",              # mov r14,r9
    0x1800522B9: "8b03",                # copy Stat tag
    0x1800522BB: "4533c0",              # zero first-fragment state
    0x1800522C4: "8b4304",              # copy Stat index
    0x1800522C7: "418bf8",              # fragment number starts at zero
    0x1800522CE: "418b4630",            # mov eax,[r14+0x30]
    0x180052314: "418bf0",              # record offset starts at zero
    0x18005233B: "498b5610",            # mov rdx,[r14+0x10]
    0x180052351: "488d4c243d",          # record destination
    0x180052356: "440fb7c0",            # copy size
    0x180052386: "4d8bc4",              # r8 = Appl descriptor
    0x180052389: "488d542420",          # rdx = MemP envelope

    # Serializer captures its record output and clears it before binding the
    # archive writer and making the first data-producing call.
    0x18002E9FC: "488bda",              # mov rbx,rdx
    0x18002E9FF: "4c8bf1",              # mov r14,rcx
    0x18002EA13: "4533ff",              # r15d = zero
    0x18002EBAF: "498b06",              # mov rax,[r14]
    0x18002EBB2: "4533c0",              # xor r8d,r8d
    0x18002EBB5: "33d2",                # xor edx,edx
    0x18002EBB7: "498bce",              # mov rcx,r14
    0x18002EBBA: "ff5008",              # call [rax+0x8]
    0x18002EBBD: "45897e30",            # mov [r14+0x30],r15d (zero)
    0x18002EBE9: "4c8975e8",            # writer output = r14
    0x18002EBFE: "4533c0",              # xor r8d,r8d
    0x18002EC01: "33d2",                # xor edx,edx
    0x18002EC03: "488d4dd0",            # lea rcx,writer

    # Null name chooses the empty-name branch.  Its first writer operation
    # emits one byte, 0x7b ('{').
    0x180069C4C: "4885d2",              # test rdx,rdx
    0x180069C56: "488bf2",              # mov rsi,rdx
    0x180069C5C: "480f45c2",            # cmovne rax,rdx
    0x180069C60: "48c7c3ffffffff",      # rbx = -1
    0x180069C67: "48ffc3",              # increment before first byte test
    0x180069C6A: "803c1800",            # scan name byte
    0x180069C74: "85db",                # test zero length
    0x180069D96: "488b4508",            # load writer vtable
    0x180069D9A: "488d542440",          # byte address
    0x180069D9F: "41b801000000",        # one byte
    0x180069DA5: "c64424407b",          # '{'
    0x180069DAA: "488d4d08",            # writer receiver
    0x180069DAE: "ff5008",              # call writer slot +0x8
}


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _section_bytes(image_base, sections, address, size):
    rva = address - image_base
    for section in sections.values():
        start = section["virtual_address"]
        available = min(section["virtual_size"], section["raw_size"])
        relative = rva - start
        if 0 <= relative and relative + size <= available:
            return section["data"][relative:relative + size]
    raise AnalysisError("virtual address %#x is not file-backed" % address)


def _decode_one(image_base, sections, address):
    code = _section_bytes(image_base, sections, address, 15)
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    instructions = list(decoder.disasm(code, address, count=1))
    _require(instructions and instructions[0].address == address,
             "cannot decode instruction at %#x" % address)
    return instructions[0]


def _require_bytes(image_base, sections, address, expected_hex):
    expected = bytes.fromhex(expected_hex)
    actual = _section_bytes(image_base, sections, address, len(expected))
    _require(actual == expected,
             "instruction bytes differ at %#x: %s" % (address, actual.hex()))


def _require_direct_target(image_base, sections, address, target):
    instruction = _decode_one(image_base, sections, address)
    _require(
        instruction.id == X86_INS_CALL
        and len(instruction.operands) == 1
        and instruction.operands[0].type == X86_OP_IMM
        and instruction.operands[0].imm == target,
        "direct call at %#x does not target %#x" % (address, target),
    )


def _rip_memory_target(image_base, sections, address, instruction_id):
    instruction = _decode_one(image_base, sections, address)
    _require(instruction.id == instruction_id,
             "unexpected instruction at %#x" % address)
    memory_operands = [
        operand for operand in instruction.operands
        if operand.type == X86_OP_MEM and operand.mem.base == X86_REG_RIP
    ]
    _require(len(memory_operands) == 1,
             "expected one RIP-relative operand at %#x" % address)
    return instruction.address + instruction.size + memory_operands[0].mem.disp


def _require_jle_target(image_base, sections, address, target):
    instruction = _decode_one(image_base, sections, address)
    _require(
        instruction.id == X86_INS_JLE
        and len(instruction.operands) == 1
        and instruction.operands[0].type == X86_OP_IMM
        and instruction.operands[0].imm == target,
        "conditional branch at %#x does not target %#x" % (address, target),
    )


def _rva_file_offset(data, sections, rva):
    for section in sections.values():
        start = section["virtual_address"]
        relative = rva - start
        if 0 <= relative < section["raw_size"]:
            return section["raw_pointer"] + relative
    raise AnalysisError("RVA %#x is not file-backed" % rva)


def _read_u64_rva(data, sections, rva):
    offset = _rva_file_offset(data, sections, rva)
    _require(offset + 8 <= len(data), "u64 at RVA %#x exceeds input" % rva)
    return struct.unpack_from("<Q", data, offset)[0]


def _read_cstring_rva(data, sections, rva):
    offset = _rva_file_offset(data, sections, rva)
    end = data.find(b"\0", offset, min(len(data), offset + 4096))
    _require(end >= 0, "unterminated import string at RVA %#x" % rva)
    try:
        return data[offset:end].decode("ascii")
    except UnicodeDecodeError as error:
        raise AnalysisError("non-ASCII import string at RVA %#x" % rva) from error


def _import_names_by_iat(data, image_base, sections):
    """Return IAT virtual address -> imported name for a bounded PE32+ image."""
    pe_offset, = struct.unpack_from("<I", data, 0x3C)
    optional = pe_offset + 24
    _require(optional + 128 <= len(data), "truncated PE32+ optional header")
    directory_count, = struct.unpack_from("<I", data, optional + 108)
    _require(directory_count >= 2, "PE image has no import directory entry")
    import_rva, import_size = struct.unpack_from("<II", data, optional + 120)
    _require(import_rva and import_size >= 20, "PE image has no import directory")

    imports = {}
    descriptor_limit = min(import_size // 20 + 1, 4096)
    for descriptor_index in range(descriptor_limit):
        descriptor_rva = import_rva + descriptor_index * 20
        descriptor_offset = _rva_file_offset(data, sections, descriptor_rva)
        _require(descriptor_offset + 20 <= len(data),
                 "truncated import descriptor")
        original_thunk, timestamp, forwarder, name_rva, first_thunk = \
            struct.unpack_from("<IIIII", data, descriptor_offset)
        if not (original_thunk or timestamp or forwarder or name_rva or first_thunk):
            break
        _require(first_thunk != 0, "import descriptor has no IAT")
        lookup_rva = original_thunk or first_thunk
        for thunk_index in range(65536):
            lookup = _read_u64_rva(
                data, sections, lookup_rva + thunk_index * 8)
            if lookup == 0:
                break
            if lookup & (1 << 63):
                continue
            name = _read_cstring_rva(data, sections, lookup + 2)
            imports[image_base + first_thunk + thunk_index * 8] = name
        else:
            raise AnalysisError("unterminated import lookup table")
    else:
        raise AnalysisError("unterminated import descriptor table")
    return imports


def analyze(data):
    digest = _sha256(data)
    _require(len(data) == UC5_SIZE,
             "UC5 size differs: %d" % len(data))
    _require(digest == UC5_SHA256,
             "UC5 SHA-256 differs: %s" % digest)

    try:
        image_base, sections = _parse_pe(data)
    except PeAnalysisError as error:
        raise AnalysisError(str(error)) from error
    _require(image_base == UC5_IMAGE_BASE,
             "UC5 image base differs: %#x" % image_base)

    for address, expected_hex in EXACT_INSTRUCTIONS.items():
        _require_bytes(image_base, sections, address, expected_hex)

    direct_edges = {
        0x18004239C: SLOT_SNAPSHOT,
        0x1800423B3: SLOT_SEND,
        0x180042888: RECORD_LOOKUP,
        0x180042893: RECORD_SERIALIZER,
        0x180042952: 0x180042760,
        0x18005235A: COPY_THUNK,
        0x18005238E: QUEUE_TARGET,
        0x18002EC07: ARCHIVE_OPEN,
    }
    for address, target in direct_edges.items():
        _require_direct_target(image_base, sections, address, target)

    vtable_reference = _rip_memory_target(
        image_base, sections, 0x180030DB3, X86_INS_LEA)
    _require(vtable_reference == SENDER_VTABLE,
             "sender vtable reference differs: %#x" % vtable_reference)

    sender_target, = struct.unpack(
        "<Q", _section_bytes(image_base, sections, SENDER_VTABLE + 0x10, 8))
    _require(sender_target == MEMP_FRAGMENTER,
             "sender vtable slot +0x10 differs: %#x" % sender_target)

    _require_jle_target(
        image_base, sections, 0x180069C76, 0x180069D96)
    empty_name = _rip_memory_target(
        image_base, sections, 0x180069C4F, X86_INS_LEA)
    _require(_section_bytes(image_base, sections, empty_name, 1) == b"\0",
             "archive fallback name is not empty")

    copy_iat = _rip_memory_target(
        image_base, sections, COPY_THUNK, X86_INS_JMP)
    import_names = _import_names_by_iat(data, image_base, sections)
    _require(import_names.get(copy_iat) == "memcpy",
             "record copy thunk does not resolve to memcpy")

    return {
        "archive_open": {
            "empty_name_branch": "0x180069c76 -> 0x180069d96",
            "first_emitted_ascii": "{",
            "first_emitted_byte": "0x7b",
            "first_output_call": "0x180069dae -> vtable+0x8",
            "first_output_size": 1,
            "function": hex(ARCHIVE_OPEN),
            "native_u32_two_prefix": False,
        },
        "boundary": (
            "UC5_ONLY_UC472_AND_FIRMWARE_RECALL_TO_LIVE_STAT_BRIDGE_UNRESOLVED"
        ),
        "fragmenter": {
            "function": hex(MEMP_FRAGMENTER),
            "memp_length": "0x7ec",
            "memp_tag": "MemP",
            "queue_call": "0x18005238e -> 0x1800546b0",
            "record_copy_call": "0x18005235a -> memcpy",
            "record_data_member": "+0x10",
            "record_length_member": "+0x30",
        },
        "serializer": {
            "archive_open_call": "0x18002ec07 -> 0x180069c40",
            "archive_open_name_argument": "null/empty",
            "function": hex(RECORD_SERIALIZER),
            "output_record_flow": "rcx -> r14 -> writer.output",
            "record_length_clear": "0x18002ebbd: [r14+0x30] = 0",
            "record_reset_call": "0x18002ebba -> record.vtable+0x8",
        },
        "slot_snapshot_then_send": {
            "call_pair": {
                "send_call": "0x1800423b3 -> 0x180042940",
                "slot_register": "r14d",
                "snapshot_call": "0x18004239c -> 0x180042840",
            },
            "record_lookup_call": "0x180042888 -> 0x1800427e0",
            "serializer_call": "0x180042893 -> 0x18002e9e0",
        },
        "source": {
            "image_base": hex(image_base),
            "sha256": digest,
            "size": len(data),
        },
        "stat_sender": {
            "application_index": 0,
            "application_tag": "Appl",
            "function": hex(SLOT_SEND),
            "record_argument": "r9",
            "record_member": "controller+0x2d8",
            "record_stride": "0x38",
            "sender_member": "controller+0x308",
            "sender_target": hex(sender_target),
            "sender_virtual_slot": "0x10",
            "sender_vtable": hex(SENDER_VTABLE),
            "stat_index": "slot",
            "stat_tag": "Stat",
        },
        "status": (
            "UC5_SAVE_SERIALIZER_SOURCE_BOUND_TAGGED_MAP_OPENER_"
            "NOT_NATIVE_U32_TWO"
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pe_image", help="exact installed UC5 dspusbdevice.dll")
    arguments = parser.parse_args(argv)
    try:
        data = Path(arguments.pe_image).read_bytes()
        report = analyze(data)
    except (OSError, AnalysisError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
