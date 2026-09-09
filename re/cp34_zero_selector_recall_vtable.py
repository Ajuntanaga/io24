#!/usr/bin/env python3
"""Bind the CP34 zero-selector ``Stat`` callbacks to the final device vtable.

The derived device constructor first invokes a base constructor, then replaces
the temporary base tables with its final tables.  A separately registered
teardown callback later restores base tables.  This analyzer pins that order so
the transient base-table ``+0x38`` no-op cannot be mistaken for the live
receiver used by the stored-record recall route.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct

from capstone import CS_ARCH_ARM, CS_MODE_THUMB, CS_OP_IMM, Cs


class AnalysisError(ValueError):
    """The input differs from the pinned firmware or expected zero route."""


FIRMWARE_SIZE = 1_104_448
FIRMWARE_SHA256 = (
    "65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a"
)
FIRMWARE_BASE = 0x60020000

DEVICE_GLOBAL_ADDRESS = 0x20216660
BASE_VTABLE_RAW = 0x6D3A8
BASE_VTABLE_ADDRESS = FIRMWARE_BASE + BASE_VTABLE_RAW
FINAL_VTABLE_HEADER_RAW = 0x10CB38
FINAL_VTABLE_HEADER_ADDRESS = FIRMWARE_BASE + FINAL_VTABLE_HEADER_RAW
FINAL_VTABLE_RAW = FINAL_VTABLE_HEADER_RAW + 8
FINAL_VTABLE_ADDRESS = FIRMWARE_BASE + FINAL_VTABLE_RAW
FINAL_SLOT_0X38_RAW = FINAL_VTABLE_RAW + 0x38


CODE_SLICES = {
    "recall_wrapper": (
        0x2F8AC, 0x58,
        "5eff2a6ade387c5e4c4a2a46fd2fe640bf42e2a6d71082f681381bbc47a17f17",
    ),
    "lazy_singleton_initializer": (
        0x3D4F0, 0x60,
        "61cddc025684c040d1d8f7cc71ea4a5280394dafd3d1636b0e3bfd8454cf3c05",
    ),
    "base_constructor": (
        0x5D990, 0x50,
        "13a85f078d439c7adea4147ac780f56f91ebdd80df24cf632247fdd9a49839c5",
    ),
    "final_derived_constructor": (
        0x5E014, 0x80,
        "e23a27aa8b2abe9e4d1dfc7becd9ff22fe71a6c7c14a26f21ddc3de59f1c4854",
    ),
    "registered_teardown": (
        0x41580, 0x26,
        "f6a79055ce3dcae1734fcda65bd2cd2a25ceee324fab5765e35f7f20e762591f",
    ),
    "device_selector": (
        0x3CE98, 0x8E,
        "68f55a9b89e937f06f4850fff156fe85fcf5179c4be8fc7cf3b254d9a7cf207f",
    ),
    "packet_router": (
        0x419A0, 0x1BE,
        "fc602b1bd35f77aaaba89940dec23898eaf727cc9b5400b773f450d438843208",
    ),
    "dispatcher_stat_calls": (
        0x42200, 0x84,
        "4688961222d27e87422d96fed169f0618d8bb3b896b25d034531c37c7f84fb8f",
    ),
    "structured_state_entry": (
        0x531E0, 0x3A,
        "09fba74a6b31254079358ae59b7a2e515291d177943a1c6f296830cdb01fd29c",
    ),
    "base_vtable": (
        BASE_VTABLE_RAW, 0x3C,
        "ed90c24ea82187e8331a10bd2fca61744ce55797f318ffa75817810d84c0892a",
    ),
    "final_vtable": (
        FINAL_VTABLE_RAW, 0x3C,
        "c9fb1bb593b31e353f0061ae719610671e35f4ab4d1f3f6aa6cbe8567c4b02de",
    ),
}


U32_ANCHORS = {
    # Stored-record callback packet and lazy singleton construction.
    0x2F90C: 0x53657450,  # SetP
    0x3D544: DEVICE_GLOBAL_ADDRESS,
    0x3D54C: FIRMWARE_BASE + 0x41581,

    # Both base-construction and teardown paths load the transient table.
    0x5DD10: BASE_VTABLE_ADDRESS,
    0x418B8: BASE_VTABLE_ADDRESS,
    0x418BC: DEVICE_GLOBAL_ADDRESS,

    # The derived constructor loads the table header, then forms header + 8.
    0x5E08C: FINAL_VTABLE_HEADER_ADDRESS,

    # Transient base-table and final derived-table slots.
    0x6D3A8: FIRMWARE_BASE + 0x420BD,
    0x6D3E0: FIRMWARE_BASE + 0x3CCB5,
    0x10CB40: FIRMWARE_BASE + 0x420BD,
    0x10CB78: FIRMWARE_BASE + 0x531E1,
}


EXACT_INSTRUCTIONS = {
    # Recall driver supplies two zero words; callback copies them after SetP.
    0x2F11E: "cde90033",
    0x2F118: "6946",
    0x2F8CE: "0f4f",
    0x2F8D6: "43f8047b",
    0x2F8DA: "d1f800c0",
    0x2F8DE: "4f68",
    0x2F8E2: "c6f804c0",
    0x2F8E6: "5f60",

    # Lazy initialization constructs the global, then registers teardown.
    0x3D528: "0648",
    0x3D52A: "20f073fd",
    0x3D534: "0548",
    0x3D536: "22f065fb",

    # The base constructor temporarily installs the base primary/secondary
    # tables before the derived constructor resumes.
    0x5D990: "df4a",
    0x5D9A0: "0446",
    0x5D9B6: "c4e9002c",

    # The derived constructor loads header 0x6012cb38, adds eight, and writes
    # final primary/secondary tables over the base tables.
    0x5E014: "f8b5",
    0x5E016: "0446",
    0x5E018: "fff7bafc",
    0x5E01C: "1b4b",
    0x5E02A: "03f10805",
    0x5E036: "2560",
    0x5E038: "03f15005",
    0x5E03C: "5c33",
    0x5E042: "6560",
    0x5E048: "a360",

    # Registered teardown restores base tables; it is not the live state left
    # by construction.
    0x41580: "cd4b",
    0x4158A: "03f14800",
    0x41594: "03f15405",
    0x4159A: "6060",
    0x415A0: "2360",
    0x415A2: "a560",

    # Zero selector returns the selected device unchanged.
    0x3CE98: "0b68",
    0x3CE9A: "0246",
    0x3CEBE: "abb1",
    0x3CEEC: "0346",
    0x3CED6: "1846",
    0x3CED8: "7047",
    0x3CF20: "a0f10800",

    # Router submits {0,0}, retains the returned object, and enters slot zero.
    0x419B6: "d2f80090",
    0x419BA: "d9f80470",
    0x419C0: "61d0",
    0x41A86: "ca46",
    0x41A88: "8368",
    0x41A8A: "0830",
    0x41A8C: "5af8044b",
    0x41A90: "1b68",
    0x41A92: "5146",
    0x41A94: "9847",
    0x41A9A: "0546",
    0x41B44: "0368",
    0x41B46: "1b68",
    0x41B48: "9847",
    0x41B6C: "a0f10400",

    # Dispatcher captures the selected receiver, copies Stat bytes, then loads
    # both +0x38 callbacks from that final receiver's primary vtable.
    0x420C4: "0c46",
    0x420C8: "0546",
    0x420EA: "00f08980",
    0x42200: "d1f81960",
    0x42210: "1d31",
    0x4221E: "cbf087fb",
    0x4225A: "2868",
    0x4225C: "0123",
    0x4225E: "03aa",
    0x42260: "3146",
    0x42262: "846b",
    0x42264: "2846",
    0x42266: "a047",
    0x42274: "2968",
    0x42276: "3346",
    0x42278: "03aa",
    0x4227A: "8c6b",
    0x4227C: "2846",
    0x4227E: "0121",
    0x42280: "a047",
}


DIRECT_TARGETS = {
    0x3CF24: FIRMWARE_BASE + 0x3CE98,
    0x3D52A: FIRMWARE_BASE + 0x5E014,
    0x3D536: FIRMWARE_BASE + 0x5FC04,
    0x41B70: FIRMWARE_BASE + 0x419A0,
    0x420EA: FIRMWARE_BASE + 0x42200,
    0x5E018: FIRMWARE_BASE + 0x5D990,
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
    """Return the source-bound final receiver/vtable report."""
    digest = hashlib.sha256(data).hexdigest()
    _require(len(data) == FIRMWARE_SIZE,
             "firmware size differs: %d" % len(data))
    _require(digest == FIRMWARE_SHA256,
             "firmware SHA-256 differs: %s" % digest)

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

    header_occurrences = data.count(struct.pack(
        "<I", FINAL_VTABLE_HEADER_ADDRESS))
    _require(header_occurrences == 1,
             "final vtable header literal occurrence count differs: %d" %
             header_occurrences)
    final_pointer_occurrences = data.count(struct.pack(
        "<I", FINAL_VTABLE_ADDRESS))
    _require(final_pointer_occurrences == 0,
             "final vtable pointer unexpectedly appears literally")

    return {
        "boundary": (
            "0X531E0_RUNTIME_COMPLETION_SELECTED_COMPONENT_AND_"
            "PHYSICAL_OUTCOMES_REMAIN_UNRESOLVED"
        ),
        "base_constructor": {
            "call": "0x5e018 -> 0x5d990",
            "installed_primary_vtable": "0x6008d3a8",
            "lifetime": "transient during construction and teardown",
            "slot_0x38": "0x6d3e0 -> 0x3ccb4",
        },
        "construction_order": {
            "derived_constructor_call": "0x3d52a -> 0x5e014",
            "global": "0x20216660",
            "lazy_initializer": "0x3d4f0",
            "registered_teardown_callback": "0x41580",
            "teardown_registration_call": "0x3d536 -> 0x5fc04",
        },
        "final_derived_constructor": {
            "constructor": "0x5e014",
            "header_literal": "0x5e08c -> 0x6012cb38",
            "header_literal_exact_occurrences": header_occurrences,
            "primary_vtable_formation": (
                "0x5e02a: 0x6012cb38 + 8 -> 0x6012cb40"
            ),
            "primary_vtable_store": "0x5e036 -> [global+0]",
            "slot_0x0": "0x10cb40 -> 0x420bc",
            "slot_0x38": "0x10cb78 -> 0x531e0",
        },
        "retraction": {
            "retracted_intermediate_claim": (
                "0x42266 and 0x42280 -> base vtable +0x38 -> 0x3ccb4"
            ),
            "root_cause": (
                "base-constructor and registered-teardown vtable writes "
                "were mistaken for the final derived construction state"
            ),
        },
        "dispatcher": {
            "accumulation_copy": "Stat+0x1d -> primary+0x18+fragment_offset",
            "entry": "0x420bc",
            "first_callback": "0x42266 -> 0x531e0",
            "first_callback_arguments": "r1=0, r3=1",
            "receiver_capture": "0x420c8: r5 = selected primary",
            "second_callback": "0x42280 -> 0x531e0",
            "second_callback_arguments": "r1=1, r3=0",
            "structured_state_reached_on_zero_route": True,
        },
        "route_effect": {
            "incoming_or_stored_payload_prefix_interpreted": True,
            "structured_prefix_gate_applicable": True,
            "zero_route_after_accumulation": "two structured-state callbacks",
        },
        "source": {
            "image_base": "0x60020000",
            "sha256": FIRMWARE_SHA256,
            "size": FIRMWARE_SIZE,
        },
        "status": (
            "ZERO_SELECTOR_STAT_ROUTE_SOURCE_BOUND_FINAL_DERIVED_"
            "SLOT_0X38_0X531E0"
        ),
        "zero_selector": {
            "callback_query": "{0, 0}",
            "packet_layout": "SetP | 0 | 0 | nested Stat message",
            "packet_router": "0x419a0",
            "result": "final derived device global unchanged",
            "selector": "0x3cf20/0x3ce98",
            "zero_branch": "0x3cebe -> 0x3ceec",
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
