#!/usr/bin/env python3
"""Bind Passive/Vintage Linux-Host packets to UC 4.7.2 call sites.

This is a bounded, deterministic source analyzer. It reads the pinned PE image
as data, decodes only the listed instructions, and verifies each coefficient
designer call plus the packet tag, byte width, and live index assembled
immediately afterward. It never loads the DLL and never touches a device.
"""

import argparse
import json
from pathlib import Path
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_IMM, X86_OP_REG

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from io24_uc472_vintage_eq import Image, DSP_SHA256, DSP_SIZE  # noqa: E402


DEFAULT_DLL = ROOT / (
    ".superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/"
    "20260906T001130-0700-uc472-official-reacquisition/extracted/"
    "hwaccess/dspusbdevice.dll")

LFDF = 0x4C666466
BQDF = 0x42716466

# model, semantic section, designer call/target (or None for identity), packet
# tag address/value, size address/value, index address/value, zeroing address.
ROUTES = (
    ("passive", "identity-2", None, None,
     0x18001A04E, BQDF, 0x18001A056, 0x24, 0x18001A05E, 2, None),
    ("passive", "identity-3", None, None,
     0x18001A09C, BQDF, 0x18001A0A4, 0x24, 0x18001A0AC, 3, None),
    ("passive", "high", 0x18001A1E3, 0x18001A610,
     0x18001A203, LFDF, 0x18001A20B, 0x2C, 0x18001A213, 0, 0x18001A030),
    ("passive", "low", 0x18001A43F, 0x18001ADB0,
     0x18001A452, BQDF, 0x18001A45A, 0x24, 0x18001A462, 1, None),
    ("vintage", "low", 0x18001C276, 0x18001D470,
     0x18001C290, LFDF, 0x18001C298, 0x2C, 0x18001C2A0, 0, 0x18001C222),
    ("vintage", "high", 0x18001C438, 0x18001CF30,
     0x18001C44B, BQDF, 0x18001C453, 0x24, 0x18001C45B, 1, None),
    ("vintage", "hi-mid", 0x18001C5D5, 0x18001CC20,
     0x18001C5E8, BQDF, 0x18001C5F0, 0x24, 0x18001C5F8, 2, None),
    ("vintage", "low-mid", 0x18001C777, 0x18001C910,
     0x18001C78A, BQDF, 0x18001C792, 0x24, 0x18001C79A, 3, None),
)


class RouteError(ValueError):
    pass


def _instruction(image, decoder, address):
    instruction = next(decoder.disasm(image.read(address, 16), address), None)
    if instruction is None or instruction.address != address:
        raise RouteError("cannot decode instruction at %#x" % address)
    return instruction


def _immediate(image, decoder, address, expected):
    instruction = _instruction(image, decoder, address)
    if instruction.mnemonic != "mov" or not instruction.operands or \
            instruction.operands[-1].type != X86_OP_IMM or \
            instruction.operands[-1].imm != expected:
        raise RouteError("%#x does not load immediate %#x: %s %s" %
                         (address, expected, instruction.mnemonic,
                          instruction.op_str))
    return "%s %s" % (instruction.mnemonic, instruction.op_str)


def analyze(path=DEFAULT_DLL):
    image = Image(path)
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    report = {"status": "UC472_ALTERNATE_EQ_LIVE_ROUTE_SOURCE_BOUND",
              "source": {"sha256": DSP_SHA256, "size": DSP_SIZE},
              "models": {"passive": [], "vintage": []}}
    for (model, section, call_at, designer, tag_at, tag, size_at, size,
         index_at, index, zero_at) in ROUTES:
        if call_at is not None:
            instruction = _instruction(image, decoder, call_at)
            if instruction.mnemonic != "call" or \
                    instruction.operands[0].type != X86_OP_IMM or \
                    instruction.operands[0].imm != designer:
                raise RouteError("%#x does not call %#x" % (call_at, designer))
        _immediate(image, decoder, tag_at, tag)
        _immediate(image, decoder, size_at, size)
        if index:
            _immediate(image, decoder, index_at, index)
        else:
            zero = _instruction(image, decoder, zero_at)
            target = _instruction(image, decoder, index_at)
            if zero.mnemonic != "xor" or zero.op_str != "esi, esi" or \
                    target.mnemonic != "mov" or \
                    target.operands[-1].type != X86_OP_REG or \
                    target.reg_name(target.operands[-1].reg) != "esi":
                raise RouteError("index 0 is not sourced from zeroed esi")
        report["models"][model].append({
            "section": section,
            "designer_call": None if call_at is None else hex(call_at),
            "designer": None if designer is None else hex(designer),
            "packet": {
                "tag": "Lfdf" if tag == LFDF else "Bqdf",
                "size": size,
                "index": index,
            },
        })
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dll", type=Path, default=DEFAULT_DLL)
    args = parser.parse_args(argv)
    print(json.dumps(analyze(args.dll), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
