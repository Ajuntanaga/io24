#!/usr/bin/env python3
"""Pin the firmware math behind CP34's zero-output Ring-Mod test."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

from capstone import CS_ARCH_ARM, CS_MODE_THUMB, Cs


FIRMWARE_BASE = 0x60020000
FIRMWARE_SIZE = 1_104_448
FIRMWARE_SHA256 = (
    "65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a")

CODE_SLICES = {
    "model3_installer_dispatch": (
        0x5F1C6, 0x0C,
        "f9066fbccb2886171b54c64d3c3bf9229322fd18de1a7dbd3969f2a015fd6620"),
    "model3_constructor_head": (
        0x58920, 0x40,
        "778d452849f9677811d97ab0d5df880eaddd37cc3447163a5ac0759ebd92fee0"),
    "model3_tagged_handler": (
        0x58DB0, 0x44,
        "87642970570d366fde1c154966ae1b27e8111d7ebb5f2a64dffd68096f6ebfef"),
    "model3_parameter_apply": (
        0x58B80, 0x52,
        "d5760681f3ac513e804e047ab933f6bb2ebf06313ba4573b287bae164d9fc25d"),
    "model3_process_gain_head": (
        0x4FF6C, 0x36,
        "6272e52697837b241ccbe3fac888ed49c01776ea26f8d68eea9f3e63185320d9"),
    "model3_process_output": (
        0x5035E, 0x12,
        "f55277d3c05aeb3a38be08c954fa0cafa0ce5ce9711821b707fbeaf68b8debba"),
    "model3_primary_vtable": (
        0x10C9A4, 0x30,
        "37b685cce6f93b88d853320f01ee6e506415ae0eec38eecfcc86e3a8a16ffd02"),
    "off_wet_gain_literal": (
        0x5034C, 0x04,
        "df3f619804a92fdb4057192dc43dd748ea778adc52bc498ce80524c014b81119"),
}

INSTRUCTIONS = {
    "installer_selects_model3": (0x5F1C6, "cmp", "r1, #3"),
    "constructor_stores_vtables": (0x58952, "strd", "r2, r0, [r4]"),
    "handler_reads_on": (0x58DD0, "ldr", "r5, [r1, #0xc]!"),
    "handler_stores_on": (0x58DDA, "str", "r5, [r0, #0x14]"),
    "handler_stores_volume": (0x58DDC, "str", "r6, [r0, #0x20]"),
    "handler_stores_mix": (0x58DEC, "str", "r3, [r0, #0x2c]"),
    "apply_sets_active_byte": (0x58BC4, "strb", "r3, [r4, #0x10]"),
    "process_reads_active": (0x4FF70, "ldrb", "r3, [r0, #0x10]"),
    "process_reads_mix": (0x4FF8A, "vldr", "s14, [r0, #0x2c]"),
    "process_reads_volume": (0x4FF8E, "vldr", "s15, [r0, #0x20]"),
    "process_one_minus_mix": (0x4FF92, "vsub.f32", "s16, s16, s14"),
    "process_twice_volume": (0x4FF96, "vadd.f32", "s17, s15, s15"),
    "process_dry_gain": (0x4FF9A, "vmul.f32", "s16, s16, s15"),
    "process_wet_gain": (0x4FF9E, "vmul.f32", "s17, s17, s14"),
    "output_applies_wet_gain": (0x50366, "vmul.f32", "s15, s17, s15"),
    "output_adds_dry_gain": (0x5036A, "vfma.f32", "s15, s14, s16"),
}


class AnalysisError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def _instruction(data, offset):
    decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    instructions = list(decoder.disasm(
        data[offset:offset + 4], FIRMWARE_BASE + offset, count=1))
    _require(len(instructions) == 1,
             "instruction at %#x does not decode" % offset)
    return instructions[0]


def analyze_firmware(data):
    digest = _sha256(data)
    _require(len(data) == FIRMWARE_SIZE,
             "firmware size differs: %d" % len(data))
    _require(digest == FIRMWARE_SHA256,
             "firmware SHA-256 differs: %s" % digest)

    slices = {}
    for name, (offset, size, expected) in CODE_SLICES.items():
        actual = _sha256(data[offset:offset + size])
        _require(actual == expected,
                 "%s slice differs: %s" % (name, actual))
        slices[name] = {
            "offset": hex(offset), "size": size, "sha256": actual}

    instructions = {}
    for name, (offset, mnemonic, operands) in INSTRUCTIONS.items():
        instruction = _instruction(data, offset)
        _require((instruction.mnemonic, instruction.op_str) ==
                 (mnemonic, operands),
                 "%s differs: %s %s" %
                 (name, instruction.mnemonic, instruction.op_str))
        instructions[name] = {
            "offset": hex(offset),
            "mnemonic": instruction.mnemonic,
            "operands": instruction.op_str,
        }

    constructor_call = _instruction(data, 0x5F1CC)
    _require((constructor_call.mnemonic, constructor_call.op_str) ==
             ("bl", "#0x60078920"),
             "model-3 constructor call differs")

    primary_vtable = _u32(data, 0x58B50)
    tagged_handler = _u32(data, 0x10C9A4)
    process = _u32(data, 0x10C9B0)
    tag = _u32(data, 0x58DF8)
    off_wet_gain = struct.unpack_from("<f", data, 0x5034C)[0]
    _require(primary_vtable == 0x6012C9A4,
             "model-3 constructor vtable differs")
    _require(tagged_handler == 0x60078DB1,
             "model-3 tagged handler differs")
    _require(process == 0x6006FF6D,
             "model-3 process differs")
    _require(tag == 0x626F7462, "model-3 tag differs")
    _require(off_wet_gain == 0.0, "model-3 off wet gain differs")

    volume = 0.0
    mix = 1.0
    return {
        "schema": "cp34-ringmod-zero-output-discriminator-v1",
        "firmware": {
            "size": len(data), "sha256": digest,
            "load_base": hex(FIRMWARE_BASE),
        },
        "code_slices": slices,
        "instructions": instructions,
        "model3_execution": {
            "model_id": 3,
            "tag": "botb",
            "constructor_raw_offset": "0x58920",
            "primary_vtable": hex(primary_vtable),
            "tagged_handler_pointer": hex(tagged_handler),
            "tagged_handler_raw_offset": "0x58db0",
            "process_pointer": hex(process),
            "process_raw_offset": "0x4ff6c",
            "parameter_fields": {
                "on": "model+0x14",
                "volume": "model+0x20",
                "mix": "model+0x2c",
                "active_byte": "model+0x10",
            },
            "process_equation": {
                "dry_gain": "volume * (1 - mix)",
                "wet_gain": "2 * volume * mix",
                "output": "wet_signal * wet_gain + input * dry_gain",
            },
        },
        "zero_output_discriminator": {
            "parameters": {"volume": volume, "mix": mix},
            "active_output_gains": {
                "dry": volume * (1.0 - mix),
                "wet": 2.0 * volume * mix,
            },
            "off_output_gains": {"dry": 1.0, "wet": off_wet_gain},
            "resolved_scalar_discriminator": True,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze_firmware(args.firmware.read_bytes())
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
