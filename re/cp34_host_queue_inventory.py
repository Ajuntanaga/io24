#!/usr/bin/env python3
"""Inventory direct callers of a queue function in a PE32+ host module.

The tool is deliberately static: it reads a PE file, disassembles only its
``.text`` section, and reports calls to one exact virtual address.  It never
loads or executes vendor code.  CP34 uses it to make the host-module operation
inventory reproducible on Linux.
"""

import argparse
import hashlib
import json
import struct
import sys

from capstone import CS_ARCH_X86, CS_MODE_64, Cs
from capstone.x86_const import (
    X86_INS_CALL,
    X86_OP_IMM,
    X86_OP_MEM,
    X86_REG_RIP,
)


class AnalysisError(ValueError):
    """The input is not a bounded PE32+ image this analyzer understands."""


def _unpack(fmt, data, offset, label):
    size = struct.calcsize(fmt)
    if offset < 0 or offset + size > len(data):
        raise AnalysisError("truncated %s" % label)
    return struct.unpack_from(fmt, data, offset)


def _parse_pe(data):
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise AnalysisError("not a PE image: missing MZ header")
    pe_offset, = _unpack("<I", data, 0x3C, "DOS header")
    if pe_offset + 24 > len(data) or data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise AnalysisError("not a PE image: missing PE signature")

    coff = pe_offset + 4
    _, section_count, _, _, _, optional_size, _ = _unpack(
        "<HHIIIHH", data, coff, "COFF header")
    optional = coff + 20
    magic, = _unpack("<H", data, optional, "optional header")
    if magic != 0x20B:
        raise AnalysisError("expected a PE32+ image")
    image_base, = _unpack("<Q", data, optional + 24, "PE32+ image base")

    section_table = optional + optional_size
    sections = {}
    for index in range(section_count):
        entry = section_table + index * 40
        values = _unpack("<8sIIIIIIHHI", data, entry, "section table")
        name = values[0].split(b"\0", 1)[0].decode("ascii", "replace")
        virtual_size, virtual_address, raw_size, raw_pointer = values[1:5]
        if raw_pointer + raw_size > len(data):
            raise AnalysisError("section %s exceeds the input" % name)
        sections[name] = {
            "virtual_size": virtual_size,
            "virtual_address": virtual_address,
            "raw_size": raw_size,
            "raw_pointer": raw_pointer,
            "data": data[raw_pointer:raw_pointer + raw_size],
        }

    if ".text" not in sections:
        raise AnalysisError("PE image has no .text section")
    return image_base, sections


def _runtime_functions(section):
    if section is None:
        return []
    limit = min(section["virtual_size"], section["raw_size"])
    functions = []
    for offset in range(0, limit - limit % 12, 12):
        begin, end, unwind = struct.unpack_from("<III", section["data"], offset)
        if begin == end == unwind == 0:
            continue
        if begin < end:
            functions.append((begin, end))
    return functions


def _ascii_immediates(instructions, start, stop):
    found = []
    for instruction in instructions:
        if instruction.address < start or instruction.address >= stop:
            continue
        if instruction.id == 0:  # Capstone's synthetic skip-data record
            continue
        for operand in instruction.operands:
            if operand.type != X86_OP_IMM:
                continue
            raw = (operand.imm & 0xFFFFFFFF).to_bytes(4, "big")
            if not all(0x20 <= byte <= 0x7E for byte in raw):
                continue
            value = raw.decode("ascii")
            if value not in found:
                found.append(value)
    return found


def _call_matches(instruction, target, call_kind):
    if instruction.id != X86_INS_CALL or not instruction.operands:
        return False
    operand = instruction.operands[0]
    if call_kind == "direct":
        return operand.type == X86_OP_IMM and operand.imm == target
    if operand.type != X86_OP_MEM or operand.mem.base != X86_REG_RIP:
        return False
    return instruction.address + instruction.size + operand.mem.disp == target


def analyze(data, target, context_before, call_kind="direct"):
    image_base, sections = _parse_pe(data)
    text = sections[".text"]
    text_size = min(text["virtual_size"], text["raw_size"])
    text_address = image_base + text["virtual_address"]

    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    decoder.skipdata = True
    instructions = list(decoder.disasm(text["data"][:text_size], text_address))
    runtime_functions = _runtime_functions(sections.get(".pdata"))

    call_sites = []
    for instruction in instructions:
        if not _call_matches(instruction, target, call_kind):
            continue

        rva = instruction.address - image_base
        containing = [item for item in runtime_functions
                      if item[0] <= rva < item[1]]
        function = min(containing, key=lambda item: item[1] - item[0]) \
            if containing else None
        function_start = image_base + function[0] if function else None
        function_end = image_base + function[1] if function else None
        context_start = max(text_address, instruction.address - context_before)
        call_sites.append({
            "address": hex(instruction.address),
            "function_start": hex(function_start) if function_start else None,
            "function_end": hex(function_end) if function_end else None,
            "nearby_ascii_immediates": _ascii_immediates(
                instructions, context_start, instruction.address),
        })

    return {
        "image_base": hex(image_base),
        "queue_target": hex(target),
        "call_kind": call_kind,
        "call_sites": call_sites,
    }


def _integer(value):
    try:
        return int(value, 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected an integer") from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pe_image")
    parser.add_argument("--target", required=True, type=_integer,
                        help="exact queue-function virtual address")
    parser.add_argument("--call-kind", choices=("direct", "rip-indirect"),
                        default="direct",
                        help="direct function call or RIP-relative IAT call")
    parser.add_argument("--context-before", type=_integer, default=0x180,
                        help="bytes before each call scanned for ASCII immediates")
    arguments = parser.parse_args(argv)
    if arguments.context_before < 0:
        parser.error("--context-before must not be negative")

    try:
        with open(arguments.pe_image, "rb") as handle:
            data = handle.read()
        report = analyze(data, arguments.target, arguments.context_before,
                         arguments.call_kind)
    except (OSError, AnalysisError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 2

    report["sha256"] = hashlib.sha256(data).hexdigest()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
