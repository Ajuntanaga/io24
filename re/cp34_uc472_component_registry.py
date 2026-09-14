#!/usr/bin/env python3
"""Decode UC 4.7.2's DSP component registry and its creators.

CP34 isolated the Voice FX object -- 0xE8 bytes, two vtables, block-201 emit
at slot 1 of the secondary -- but could not find who builds it. Neither of its
constructors is called anywhere in the module, is stored as a pointer, or is
the target of any `call rel32`. The reason is that the creator is neither
called nor stored: it is *loaded* with a RIP-relative `lea` inside a CRT static
initializer, which appends it to a name-keyed registry at DLL load.

This decodes that initializer. Each registration writes a 32-byte record --
name pointer, creator, destroyer -- into a table capped at 100 entries, so the
whole component set falls out of one function.

The technique matters as much as the result: an address that appears nowhere as
a pointer and nowhere as a call target may still be *referenced*, and a search
that only looks for pointers and calls will wrongly conclude the code is dead.

Offline only; no vendor code is executed.
"""

import argparse
import json
from pathlib import Path
import sys

import capstone

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util as _ilu  # noqa: E402
_SPEC = _ilu.spec_from_file_location(
    "cp34_uc472_module_graph", ROOT / "re" / "cp34_uc472_module_graph.py")
_MG = _ilu.module_from_spec(_SPEC); _SPEC.loader.exec_module(_MG)
Module = _MG.Module

REGISTRY_BUILDER = 0x180001990
REGISTRY_BUILDER_END = 0x180001B6F
CRT_INITIALIZER_SLOT = 0x1800E4898


class RegistryError(RuntimeError):
    """The registry could not be decoded from this module."""


def _rip_target(instruction):
    for operand in instruction.operands:
        if operand.type == capstone.x86.X86_OP_MEM and \
                operand.mem.base == capstone.x86.X86_REG_RIP:
            return instruction.address + instruction.size + operand.mem.disp
    return None


def decode_registry(module, begin=REGISTRY_BUILDER, end=REGISTRY_BUILDER_END):
    """Return the ordered component registrations the initializer performs.

    The initializer repeats one shape per component: load a name pointer, then
    a creator, then a destroyer, then store the 32-byte record. Reading the
    `lea` sequence in order therefore recovers the table without simulating it.
    """
    offset = module.offset_of(begin)
    if offset is None:
        raise RegistryError("registry builder is outside the image")
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True

    pending, components = [], []
    for ins in md.disasm(module.data[offset:offset + (end - begin)], begin):
        if ins.mnemonic != "lea":
            continue
        target = _rip_target(ins)
        if target is None:
            continue
        section = module.section_of(target)
        if section == ".rdata":
            text = module.cstring(target)
            if text and text.endswith("Component"):
                pending = [("name", target, text)]
        elif section == ".text" and pending:
            pending.append(("fn", target, None))
            if len(pending) == 3:
                components.append({
                    "component": pending[0][2],
                    "name_address": hex(pending[0][1]),
                    "creator": hex(pending[1][1]),
                    "destroyer": hex(pending[2][1]),
                })
                pending = []
    if not components:
        raise RegistryError("no component registrations decoded")
    return components


def analyze(module):
    components = decode_registry(module)
    slots = module.vtable_slots(REGISTRY_BUILDER)
    return {
        "schema": "cp34-uc472-component-registry-v1",
        "sha256": module.sha256,
        "registry_builder": hex(REGISTRY_BUILDER),
        "registered_at_load": CRT_INITIALIZER_SLOT in slots,
        "crt_initializer_slots": [hex(s) for s in slots],
        "component_count": len(components),
        "components": components,
        "note": ("creators are referenced only by a RIP-relative lea inside a "
                 "CRT static initializer, so they appear in no pointer table "
                 "and are the target of no call"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    module = Module(args.module.read_bytes())
    result = analyze(module)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
