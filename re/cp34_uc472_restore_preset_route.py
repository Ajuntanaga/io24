#!/usr/bin/env python3
"""Source-bind what UC 4.7.2 actually does when it recalls a preset.

The live probes closed the ``MemP/Stat``-plus-selector route as a negative:
exact-length records were accepted by the transport and changed no DSP state.
That left open why UC appears to recall presets at all.  This analyzer answers
it from the exact ``dspusbdevice.dll`` instead of from the wire.

The vendor's high-level request receiver understands three incoming messages.
``RestorePreset`` branches on ``presetTarget``, and its ``channel`` branch never
builds a device record.  It resolves a channel out of the host-side device model
and hands the preset document to an applier, whose entire direct-call subtree
reaches none of the module's record builders.  The one thing the module can put
a parameter into is a single ``SetP``/``GetP`` frame builder, which sits in the
same protocol-encoder vtable as the ``MemP`` fragmenter.

So UC's channel preset recall is a host-side model apply that replays ordinary
parameters.  It is not a device-side record recall, which is why driving
``MemP/Stat`` produced no audible change.

Vendor code is never loaded or executed.  Wine, USB, audio, firmware hardware,
and the network are never accessed.
"""

import argparse
import bisect
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86_const import (
    X86_INS_CALL,
    X86_INS_LEA,
    X86_INS_MOV,
    X86_INS_RET,
    X86_OP_IMM,
    X86_OP_MEM,
    X86_OP_REG,
    X86_REG_R14,
    X86_REG_RCX,
    X86_REG_RDX,
    X86_REG_RIP,
)

RE_DIR = Path(__file__).resolve().parent
if str(RE_DIR) not in sys.path:
    sys.path.insert(0, str(RE_DIR))

import cp34_uc5_serializer_comparison as pe_helpers  # noqa: E402


class AnalysisError(ValueError):
    """An input differs from the exact source or expected static route."""


DSP_SIZE = 4_979_672
DSP_SHA256 = "de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28"
DSP_IMAGE_BASE = 0x180000000

REQUEST_RECEIVER = 0x18003AEF0
STRING_COMPARE = 0x1800D3562

CHANNEL_INDEX_PARSER = 0x18003C580
CHANNEL_GUARD = 0x18003C8A0
CHANNEL_APPLIER = 0x18002E690
COMPONENT_FILTER_BUILDER = 0x18002E810
COMPONENT_NAME_APPEND = 0x18002DDF0

SCENE_RESTORE = 0x18003BE50
RECORD_SERIALIZER = 0x18002E270
LIBRARY_SENDER = 0x180037250

ENCODER_VTABLE = 0x1804393E0
MEMP_FRAGMENTER = 0x180050F10
PARAMETER_FRAME_BUILDER = 0x1800541D0
ENCODER_MEMP_SLOT = 0x10
ENCODER_PARAMETER_SLOT = 0xD8

# The device model's channel array, as the ``channel`` branch addresses it.
CHANNEL_ARRAY_POINTER = 0x158
CHANNEL_COUNT = 0x160
CHANNEL_ARRAY_HEADER = 0xE8
CHANNEL_STRIDE = 9 * 32

GETP_IMMEDIATE = 0x47657450
SETP_IMMEDIATE = 0x53657450
# The one `mov eax, 'SetP'` in the module, inside 0x18005423b.
SETP_IMMEDIATE_SITE = 0x18005423C

# Wire tags appear in code as the reversed FourCC immediate.
RECORD_TAGS = {
    "MemP": b"PmeM",
    "Stat": b"tatS",
    "PrsM": b"MsrP",
}

EXACT_BYTES = {
    # RestorePreset, and the presetTarget key it branches on.
    0x18003AF68: "488d15f1ab3f00",
    0x18003AF97: "488d15e2ab3f00",

    # presetTarget == "channel": bound against the model's channel count,
    # indexed at a 0x120 stride past a 0xE8 header, guarded, then applied.
    0x18003B112: "488d15f7aa3f00",
    0x18003B13C: "e83f140000",
    0x18003B152: "413b8560010000",
    0x18003B161: "488d1cc0",
    0x18003B165: "48c1e305",
    0x18003B169: "498b8d58010000",
    0x18003B170: "4881c1e8000000",
    0x18003B17A: "e821170000",
    0x18003B198: "4533c0",
    0x18003B19E: "e8ed34ffff",

    # presetTarget == "scene" is the only other branch.
    0x18003B20E: "4c8d0df3a93f00",

    # The applier brackets the work in the channel's own begin/end virtual and
    # delegates the component selection to the filter builder.
    0x18002E702: "ff5008",
    0x18002E738: "e8d3000000",
    0x18002E748: "ff5008",

    # The one place a parameter becomes a frame: version 2 prepends GetP/SetP.
    0x1800541EE: "83796802",
    0x180054236: "ba50746547",
    0x18005423B: "b850746553",
    0x180054240: "0f44d0",
    0x180054255: "4183f902",
    0x18005425B: "8911",
}

COMPONENT_FILTER_NAMES = ("voicefx", "comp", "opt", "voicefxopt")

RECEIVER_MESSAGES = ("GetPresetFileDescriptions", "RestorePreset", "StorePreset")
RESTORE_PRESET_TARGETS = ("channel", "scene")


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


class _Image:
    """The exact dspusbdevice.dll, addressed by virtual address."""

    def __init__(self, data):
        _require(len(data) == DSP_SIZE, "dsp size differs: %d" % len(data))
        digest = hashlib.sha256(data).hexdigest()
        _require(digest == DSP_SHA256, "dsp SHA-256 differs: %s" % digest)
        self.data = data
        self.sha256 = digest
        try:
            self.base, self.sections = pe_helpers._parse_pe(data)
        except pe_helpers.AnalysisError as error:
            raise AnalysisError("dsp: %s" % error) from error
        _require(
            self.base == DSP_IMAGE_BASE,
            "dsp image base differs: %#x" % self.base,
        )
        self.text = self.sections[".text"]
        self.text_base = self.base + self.text["virtual_address"]
        self.text_bytes = self.text["data"][:self.text["virtual_size"]]
        self._cs = Cs(CS_ARCH_X86, CS_MODE_64)
        self._cs.detail = True

    def at(self, address, size):
        try:
            return pe_helpers._section_bytes(self.base, self.sections, address, size)
        except pe_helpers.AnalysisError as error:
            raise AnalysisError(str(error)) from error

    def u64(self, address):
        return struct.unpack("<Q", self.at(address, 8))[0]

    def cstring(self, address, limit=128):
        try:
            raw = self.at(address, limit)
        except AnalysisError:
            return None
        end = raw.find(b"\0")
        if end < 0:
            return None
        try:
            return raw[:end].decode("ascii")
        except UnicodeDecodeError:
            return None

    def body(self, address, limit=4000):
        """Instructions from ``address`` up to and including its first ret."""
        out = []
        for instruction in self._cs.disasm(self.at(address, 0x6000), address):
            out.append(instruction)
            if instruction.id == X86_INS_RET or len(out) >= limit:
                break
        _require(out, "no instruction decodes at %#x" % address)
        return out


def _require_bytes(image, address, expected_hex):
    expected = bytes.fromhex(expected_hex)
    actual = image.at(address, len(expected))
    _require(
        actual == expected,
        "instruction bytes differ at %#x: %s" % (address, actual.hex()),
    )


def _rip_literal(image, instruction):
    """The ASCII string a rip-relative lea points at, or None."""
    if instruction.id != X86_INS_LEA:
        return None
    operand = instruction.operands[1]
    if operand.type != X86_OP_MEM or operand.mem.base != X86_REG_RIP:
        return None
    target = instruction.address + instruction.size + operand.mem.disp
    return image.cstring(target, 64)


def _receiver_vocabulary(image):
    """Split the receiver's string compares into messages and parameter keys.

    A message name is compared against the request object itself (``rcx, r14``);
    a parameter key is compared against a member at ``+0x48``.
    """
    messages = []
    keys = []
    window = []
    for instruction in image.body(REQUEST_RECEIVER):
        if (instruction.id == X86_INS_CALL
                and instruction.operands[0].type == X86_OP_IMM
                and instruction.operands[0].imm == STRING_COMPARE):
            literal = None
            for previous in reversed(window[-6:]):
                if (previous.id == X86_INS_LEA
                        and previous.operands[0].type == X86_OP_REG
                        and previous.operands[0].reg == X86_REG_RDX):
                    literal = _rip_literal(image, previous)
                    break
            _require(
                literal is not None,
                "no string literal precedes the compare at %#x" % instruction.address,
            )
            subject = None
            for previous in reversed(window[-4:]):
                if (previous.id == X86_INS_MOV
                        and previous.operands[0].type == X86_OP_REG
                        and previous.operands[0].reg == X86_REG_RCX):
                    subject = previous.operands[1]
                    break
            _require(
                subject is not None,
                "no compare subject precedes %#x" % instruction.address,
            )
            if subject.type == X86_OP_REG and subject.reg == X86_REG_R14:
                messages.append(literal)
            else:
                _require(
                    subject.type == X86_OP_MEM and subject.mem.disp == 0x48,
                    "unexpected compare subject at %#x" % instruction.address,
                )
                keys.append(literal)
        window.append(instruction)
    return messages, keys


def _call_graph(image):
    """Direct call/jmp edges over .text, with call targets as function starts."""
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = False
    blob = image.text_bytes
    base = image.text_base
    edges = []
    offset = 0
    while offset < len(blob):
        decoded = False
        for instruction in decoder.disasm(blob[offset:], base + offset):
            decoded = True
            offset = instruction.address - base + instruction.size
            if instruction.mnemonic not in ("call", "jmp"):
                continue
            if not instruction.op_str.startswith("0x"):
                if instruction.mnemonic == "call":
                    edges.append((instruction.address, None, instruction.op_str))
                continue
            try:
                target = int(instruction.op_str, 16)
            except ValueError:
                continue
            edges.append((instruction.address, target, instruction.mnemonic))
        if not decoded:
            offset += 1

    starts = sorted({target for _, target, _ in edges if target is not None})
    _require(starts, "no direct call targets decoded in .text")

    def owner(address):
        index = bisect.bisect_right(starts, address) - 1
        return starts[index] if index >= 0 else None

    forward = {}
    indirect = {}
    for address, target, kind in edges:
        function = owner(address)
        if function is None:
            continue
        if target is None:
            indirect.setdefault(function, []).append((address, kind))
        else:
            forward.setdefault(function, set()).add(target)
    return forward, indirect, owner


def _record_builders(image, owner):
    """The functions that materialise a MemP/Stat/PrsM tag immediate."""
    builders = {}
    for tag, reversed_tag in RECORD_TAGS.items():
        for match in re.finditer(re.escape(reversed_tag), image.text_bytes):
            site = image.text_base + match.start()
            function = owner(site)
            _require(
                function is not None,
                "no enclosing function for the %s immediate at %#x" % (tag, site),
            )
            builders.setdefault(function, set()).add(tag)
    _require(builders, "no record-building function was located")
    return builders


def _reachable(forward, root):
    seen = {root}
    stack = [root]
    while stack:
        function = stack.pop()
        for callee in forward.get(function, ()):
            if callee not in seen:
                seen.add(callee)
                stack.append(callee)
    return seen


def analyze(dsp):
    image = _Image(dsp)

    for address, expected in EXACT_BYTES.items():
        _require_bytes(image, address, expected)

    messages, keys = _receiver_vocabulary(image)
    _require(
        tuple(sorted(set(messages))) == RECEIVER_MESSAGES,
        "receiver message vocabulary differs: %s" % sorted(set(messages)),
    )

    # RestorePreset branches on exactly two presetTarget values and no others.
    restore_targets = []
    for instruction in image.body(REQUEST_RECEIVER):
        if not 0x18003B100 <= instruction.address <= 0x18003B240:
            continue
        literal = _rip_literal(image, instruction)
        if literal in RESTORE_PRESET_TARGETS:
            restore_targets.append(literal)
    _require(
        tuple(sorted(set(restore_targets))) == RESTORE_PRESET_TARGETS,
        "RestorePreset presetTarget branches differ: %s" % sorted(set(restore_targets)),
    )

    # The component filter the applier builds, in source order.
    filter_names = []
    appends = 0
    for instruction in image.body(COMPONENT_FILTER_BUILDER):
        if (instruction.id == X86_INS_CALL
                and instruction.operands[0].type == X86_OP_IMM
                and instruction.operands[0].imm == COMPONENT_NAME_APPEND):
            appends += 1
        literal = _rip_literal(image, instruction)
        if literal in COMPONENT_FILTER_NAMES and literal not in filter_names:
            filter_names.append(literal)
    _require(appends, "the applier never appends a component-filter name")
    _require(
        tuple(sorted(filter_names)) == tuple(sorted(COMPONENT_FILTER_NAMES)),
        "applier component filter differs: %s" % filter_names,
    )

    # The protocol encoder carries both the record fragmenter and the single
    # parameter-frame builder, so "record" and "parameter" are two slots of one
    # class rather than two transports.
    _require(
        image.u64(ENCODER_VTABLE + ENCODER_MEMP_SLOT) == MEMP_FRAGMENTER,
        "encoder vtable +0x%x is not the MemP fragmenter" % ENCODER_MEMP_SLOT,
    )
    _require(
        image.u64(ENCODER_VTABLE + ENCODER_PARAMETER_SLOT) == PARAMETER_FRAME_BUILDER,
        "encoder vtable +0x%x is not the parameter frame builder"
        % ENCODER_PARAMETER_SLOT,
    )
    setp_sites = [
        image.text_base + match.start()
        for match in re.finditer(re.escape(struct.pack("<I", SETP_IMMEDIATE)),
                                 image.text_bytes)
    ]
    _require(
        setp_sites == [SETP_IMMEDIATE_SITE],
        "the module has %d SetP sites: %s" % (
            len(setp_sites), [hex(site) for site in setp_sites]),
    )

    forward, indirect, owner = _call_graph(image)
    builders = _record_builders(image, owner)

    applier_subtree = _reachable(forward, CHANNEL_APPLIER)
    reached = sorted(set(applier_subtree) & set(builders))
    _require(
        not reached,
        "the channel applier reaches record builders: %s"
        % [hex(function) for function in reached],
    )
    indirect_sites = sum(len(indirect.get(f, ())) for f in applier_subtree)

    store_subtree = _reachable(forward, LIBRARY_SENDER)
    store_reached = sorted(set(store_subtree) & set(builders))
    _require(
        store_reached,
        "the StorePreset library sender reaches no record builder",
    )

    return {
        "boundary": (
            "STATIC_DIRECT_CALL_EVIDENCE_ONLY_THE_APPLIER_SUBTREE_RETAINS_"
            "INDIRECT_CALL_SITES_AND_NO_LIVE_OR_DEVICE_OBSERVATION_WAS_MADE"
        ),
        "channel_apply": {
            "applier": hex(CHANNEL_APPLIER),
            "brackets_work_in_channel_virtual": "+0x8",
            "channel_array_header": hex(CHANNEL_ARRAY_HEADER),
            "channel_array_pointer": hex(CHANNEL_ARRAY_POINTER),
            "channel_count_field": hex(CHANNEL_COUNT),
            "channel_stride": hex(CHANNEL_STRIDE),
            "component_filter": list(COMPONENT_FILTER_NAMES),
            "component_filter_appends": appends,
            "component_filter_builder": hex(COMPONENT_FILTER_BUILDER),
            "guard": hex(CHANNEL_GUARD),
            "index_parser": hex(CHANNEL_INDEX_PARSER),
        },
        "parameter_frame_builder": {
            "encoder_vtable": hex(ENCODER_VTABLE),
            "function": hex(PARAMETER_FRAME_BUILDER),
            "getp_immediate": hex(GETP_IMMEDIATE),
            "memp_fragmenter": hex(MEMP_FRAGMENTER),
            "memp_slot": hex(ENCODER_MEMP_SLOT),
            "parameter_slot": hex(ENCODER_PARAMETER_SLOT),
            "protocol_version_gate": "[this+0x68] == 2",
            "setp_immediate": hex(SETP_IMMEDIATE),
            "setp_sites": [hex(site) for site in setp_sites],
        },
        "reachability": {
            "applier_direct_call_functions": len(applier_subtree),
            "applier_indirect_call_sites": indirect_sites,
            "applier_reaches_record_builder": False,
            "method": "direct call/jmp edges over .text, call targets as function starts",
            "record_builders": {
                hex(function): sorted(tags) for function, tags in sorted(builders.items())
            },
            "store_reaches_record_builder": [hex(f) for f in store_reached],
        },
        "receiver": {
            "function": hex(REQUEST_RECEIVER),
            "messages": sorted(set(messages)),
            "parameter_keys": sorted(set(keys)),
            "string_compare": hex(STRING_COMPARE),
        },
        "restore_preset": {
            "channel_branch_builds_a_device_record": False,
            "preset_targets": sorted(set(restore_targets)),
            "scene_branch": hex(SCENE_RESTORE),
        },
        "source": {
            "image_base": hex(DSP_IMAGE_BASE),
            "sha256": image.sha256,
            "size": len(dsp),
        },
        "status": (
            "UC472_CHANNEL_PRESET_RECALL_IS_A_HOST_SIDE_MODEL_APPLY_"
            "NOT_A_DEVICE_RECORD_RECALL"
        ),
        "store_preset": {
            "library_sender": hex(LIBRARY_SENDER),
            "serializer": hex(RECORD_SERIALIZER),
            "writes_a_device_record": True,
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dsp", type=Path)
    arguments = parser.parse_args(argv)
    try:
        report = analyze(arguments.dsp.read_bytes())
    except (OSError, AnalysisError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
