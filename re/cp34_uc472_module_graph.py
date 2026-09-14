#!/usr/bin/env python3
"""A reliable function map and direct call graph for a UC 4.7.2 x64 module.

Every earlier address-level result in this project was produced by hand or by
a linear sweep. A linear x86 sweep desynchronises on embedded data: it produced
a false "no block-201 site exists" negative in this very module, because the
real site stores the block id as a QWORD and the sweep never decoded it.

This builds the map from `.pdata` instead. On x64 PE every non-leaf function
has a RUNTIME_FUNCTION entry giving exact begin/end, so each function is
disassembled from a known-good start and never from a guessed one. RIP-relative
targets are resolved by capstone rather than by arithmetic.

What it gives:

* `functions()`   -- exact (begin, end) pairs, sorted
* `call_graph()`  -- direct call/jmp edges between function starts
* `reaches()`     -- reverse reachability over those edges
* `vtable_slots()`-- where a function address appears as a data pointer

The direct graph is deliberately honest about its limit: this module dispatches
almost everything through vtables, so an empty reverse-reachability result
means "not reachable by direct calls", never "not reachable".
"""

import argparse
import bisect
import hashlib
import json
import struct
from pathlib import Path

import capstone


class ModuleGraphError(RuntimeError):
    """The input is not a usable x64 PE module."""


class Module:
    def __init__(self, data):
        if data[:2] != b"MZ":
            raise ModuleGraphError("not a PE image")
        self.data = data
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe:pe + 4] != b"PE\0\0":
            raise ModuleGraphError("bad PE signature")
        nsec = struct.unpack_from("<H", data, pe + 6)[0]
        optsz = struct.unpack_from("<H", data, pe + 20)[0]
        magic = struct.unpack_from("<H", data, pe + 24)[0]
        if magic != 0x20B:
            raise ModuleGraphError("not PE32+")
        self.base = struct.unpack_from("<Q", data, pe + 24 + 24)[0]
        self.sections = []
        off = pe + 24 + optsz
        for _ in range(nsec):
            name = data[off:off + 8].rstrip(b"\0").decode("ascii", "replace")
            vsz, va, rsz, ra = struct.unpack_from("<IIII", data, off + 8)
            # Keep the raw size separately. A section's virtual span may run
            # past its raw data, so using max() for file-offset containment
            # makes neighbouring sections overlap in file space and
            # mis-attributes an offset to the wrong section.
            self.sections.append((name, va, max(vsz, rsz), ra, rsz))
            off += 40
        self.sha256 = hashlib.sha256(data).hexdigest()

    def section_of(self, addr):
        rva = addr - self.base
        for name, va, size, _ra, _rsz in self.sections:
            if va <= rva < va + size:
                return name
        return None

    def offset_of(self, addr):
        rva = addr - self.base
        for _name, va, size, ra, _rsz in self.sections:
            if va <= rva < va + size:
                return ra + (rva - va)
        return None

    def _section(self, want):
        for entry in self.sections:
            if entry[0] == want:
                return entry
        raise ModuleGraphError("no %s section" % want)

    def address_of_offset(self, file_offset):
        """Virtual address for a file offset, using RAW extents only."""
        for _name, va, _size, ra, rsz in self.sections:
            if rsz and ra <= file_offset < ra + rsz:
                return self.base + va + (file_offset - ra)
        return None

    def functions(self):
        """Exact function bounds from .pdata RUNTIME_FUNCTION entries."""
        _n, _va, size, ra, _rsz = self._section(".pdata")
        out = set()
        for i in range(size // 12):
            begin, end, _unwind = struct.unpack_from("<III", self.data,
                                                     ra + i * 12)
            if begin or end:
                out.add((self.base + begin, self.base + end))
        if not out:
            raise ModuleGraphError(".pdata holds no functions")
        return sorted(out)

    def call_graph(self, functions=None):
        """Direct call/jmp edges between function starts."""
        functions = functions or self.functions()
        starts = {begin for begin, _end in functions}
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
        md.detail = True
        callers, callees = {}, {}
        for begin, end in functions:
            offset = self.offset_of(begin)
            if offset is None:
                continue
            body = self.data[offset:offset + (end - begin)]
            for ins in md.disasm(body, begin):
                if ins.mnemonic not in ("call", "jmp"):
                    continue
                if len(ins.operands) != 1:
                    continue
                operand = ins.operands[0]
                if operand.type != capstone.x86.X86_OP_IMM:
                    continue
                target = operand.imm
                if target in starts and target != begin:
                    callers.setdefault(target, set()).add(begin)
                    callees.setdefault(begin, set()).add(target)
        return callers, callees

    def vtable_slots(self, address):
        """Every place the module stores `address` as an 8-byte pointer."""
        probe = struct.pack("<Q", address)
        hits, start = [], 0
        while True:
            index = self.data.find(probe, start)
            if index < 0:
                break
            address = self.address_of_offset(index)
            if address is not None:
                hits.append(address)
            start = index + 1
        return hits


def reaches(callers, target):
    """Functions that reach `target` over direct edges, with depth."""
    depth = {target: 0}
    frontier = [target]
    while frontier:
        nxt = []
        for node in frontier:
            for caller in callers.get(node, ()):
                if caller not in depth:
                    depth[caller] = depth[node] + 1
                    nxt.append(caller)
        frontier = nxt
    depth.pop(target, None)
    return depth


def owner_of(functions, address):
    """The function whose exact bounds contain `address`."""
    starts = [begin for begin, _end in functions]
    i = bisect.bisect_right(starts, address) - 1
    if i < 0:
        return None
    begin, end = functions[i]
    return (begin, end) if begin <= address < end else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", type=Path)
    parser.add_argument("--reaches", type=lambda s: int(s, 0), default=None,
                        help="report direct callers of this address's function")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    module = Module(args.module.read_bytes())
    functions = module.functions()
    callers, callees = module.call_graph(functions)
    result = {
        "schema": "cp34-uc472-module-graph-v1",
        "sha256": module.sha256,
        "image_base": hex(module.base),
        "functions": len(functions),
        "direct_edges": sum(len(v) for v in callees.values()),
        "limit": ("direct call/jmp edges only; this module dispatches through "
                  "vtables, so absence of a path is not absence of a caller"),
    }
    if args.reaches is not None:
        owner = owner_of(functions, args.reaches)
        if owner is None:
            raise ModuleGraphError("0x%x is in no function" % args.reaches)
        depth = reaches(callers, owner[0])
        result["query"] = {
            "address": hex(args.reaches),
            "function": "0x%x..0x%x" % owner,
            "direct_callers": [hex(c) for c in sorted(callers.get(owner[0], ()))],
            "reaching_functions": len(depth),
            "pointer_slots": [hex(s) for s in module.vtable_slots(owner[0])],
        }
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
