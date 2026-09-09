#!/usr/bin/env python3
"""Source-bind CP34 stored-``Stat`` zero-selector recall in firmware 1.28.

This analyzer accepts only the exact recovered application image.  It checks
the stored-record reader, recall wrapper, singleton/device binding, packet
router, live ``Stat`` dispatcher, and the final derived receiver's two
``+0x38`` callbacks.  It does not load firmware, emit an image, or access
USB/audio hardware.

The result is deliberately conditional on the bytes already present in the
stored record.  The route adds no prefix, copies the payload into the primary
accumulation buffer, starts its reader at cursor zero, and reaches structured-
state method ``0x531e0`` through the final derived vtable.  It exposes no
physical device contents.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from capstone import CS_ARCH_ARM, CS_MODE_THUMB, CS_OP_IMM, Cs


RE_DIR = Path(__file__).resolve().parent
if str(RE_DIR) not in sys.path:
    sys.path.insert(0, str(RE_DIR))

import cp34_zero_selector_recall_vtable as zero_receiver  # noqa: E402


class AnalysisError(ValueError):
    """The input differs from the exact pinned firmware or expected route."""


FIRMWARE_SIZE = 1_104_448
FIRMWARE_SHA256 = (
    "65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a"
)
FIRMWARE_BASE = 0x60020000


CODE_SLICES = {
    "fallback_copy": (
        0x30708, 0x68,
        "889bec6d66fe99fff56291cb08d515a1b0cfe75187f926f6ece60e4b14bc55ef",
    ),
    "storage_reader": (
        0x30A90, 0xE0,
        "48f0c20a4d13ac12c732e9abf39c8a307f2ab6345f90b5a350f43d2184bdea3e",
    ),
    "stat_reader": (
        0x30BE0, 0x50,
        "e08472744991dc9000ca96c9febf8aa29eff30a895c88ab2ddca36f0857a9cbf",
    ),
    "recall_driver": (
        0x2F0D0, 0x68,
        "be0b1bed05a1cb36c0ca5fa35c9706eb6d0d187c52a63382186f86a52aa16405",
    ),
    "recall_wrapper": (
        0x2F8AC, 0x58,
        "5eff2a6ade387c5e4c4a2a46fd2fe640bf42e2a6d71082f681381bbc47a17f17",
    ),
    "manager_bridge": (
        0x3163C, 0x38,
        "4cc5dd6fae37fc54a1cf40d9726f807b774957aff61cbf36d58ca9e89bb5ecff",
    ),
    "application_router": (
        0x20754, 0x30,
        "d5e27f35bc37b1f1949c6fadc1f800a8c35ccb9308daa5b116531985d71592aa",
    ),
    "singleton_lookup": (
        0x34CB8, 0x0C,
        "3f96d7faa885ddc791e911b60343107d9a19e6ffaacb42b65378231f2cabb3e5",
    ),
    "singleton_projection": (
        0x3CC08, 0x04,
        "eea00f3392bbbf5ec7ea83e049192860f6e231d5978f598abaafbf0076ca004d",
    ),
    "singleton_forwarder": (
        0x3CC40, 0x2E,
        "ec43a5b416faa096ceee09c541a94c2187976a57c29585345b5364dfc3f2ae53",
    ),
    "singleton_binding": (
        0x3D4F0, 0x60,
        "61cddc025684c040d1d8f7cc71ea4a5280394dafd3d1636b0e3bfd8454cf3c05",
    ),
    "registered_device_teardown": (
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
    "device_router_adjustor": (
        0x41B6C, 0x06,
        "4599ee8d3a00ecd891b673f9a915b6a0e3c94e4add30be305d026d2569c40151",
    ),
    "dispatcher_tag": (
        0x420BC, 0x32,
        "bb6d8f1dcb856f0618b4115b782addae7887ac1fedc85bbeb10e407df7e7f829",
    ),
    "dispatcher_stat": (
        0x42200, 0x68,
        "320973459ba52eef1dbdd66ea30cf58d7d8a90b7b51ea0c8dd6b6d32435f1782",
    ),
    "final_derived_constructor": (
        0x5E014, 0x80,
        "e23a27aa8b2abe9e4d1dfc7becd9ff22fe71a6c7c14a26f21ddc3de59f1c4854",
    ),
    "structured_state_entry": (
        0x531E0, 0x3A,
        "09fba74a6b31254079358ae59b7a2e515291d177943a1c6f296830cdb01fd29c",
    ),
}


U32_ANCHORS = {
    # Tags embedded next to the exact reader/wrapper/router paths.
    0x2F90C: 0x53657450,   # SetP
    0x30C30: 0x53746174,   # Stat
    0x41B60: 0x53657450,   # SetP

    # Singleton projection and secondary forwarder tables.
    0x6D40C: 0x6005CC09,
    0x6D434: 0x6005CC41,

    # Final derived primary, routing-adjustor, and selector vtable slots.
    0x10CB40: 0x600620BD,
    0x10CB78: 0x600731E1,
    0x10CB88: 0x60061B6D,
    0x10CB94: 0x6005CF21,

    # Lazy singleton construction, teardown registration, and final table
    # header loaded by the derived constructor.
    0x3D540: 0x2021C4F8,
    0x3D544: 0x20216660,
    0x3D548: 0x20220C88,
    0x3D54C: 0x60061581,
    0x5E08C: 0x6012CB38,
    0x418B8: 0x6008D3A8,
    0x418BC: 0x20216660,

    # Non-owning stream and structured-state wrapper vtables.
    0x534C4: 0x60086B54,
    0x669F4: 0x6004CBB5,
    0x66B54: 0x6004CD21,
}


EXACT_INSTRUCTIONS = {
    # Stored Stat validation and storage/fallback selection.
    0x30BE6: "8a68",              # message tag at +8
    0x30BE8: "8d75",              # initial status byte = 2
    0x30BF0: "c968",              # slot at +0xc
    0x30BF2: "0329",              # slot <= 3
    0x30BFC: "fff7bafd",          # storage-key helper
    0x30C06: "fff743ff",          # storage reader
    0x30C0C: "d4f81930",          # stored length at message+0x19
    0x30C12: "f1d1",              # stored path returns when length != 0
    0x30C22: "d2f89030",          # fallback descriptor length
    0x30C26: "d2f8a020",          # fallback descriptor data pointer
    0x30C2A: "fff76dfd",          # fallback copy

    # Storage reads a four-byte length, then payload directly into +0x1d.
    0x30AAA: "01f11902",          # length destination message+0x19
    0x30AB8: "fbf7f6fa",          # four-byte storage read
    0x30B10: "08f11d02",          # payload destination message+0x1d
    0x30B16: "fbf7c7fa",          # payload storage read
    0x30B20: "a8f81730",          # fragment length at +0x17

    # Factory fallback copies source+offset directly to message+0x1d.
    0x30730: "d119",              # source = descriptor bytes + offset
    0x30736: "04f11d00",          # destination = message+0x1d
    0x3073E: "ddf0f7f8",          # memcpy
    0x30750: "a675",              # completion byte at +0x16

    # Recall driver passes the complete message with two zero metadata words.
    0x2F112: "2068",
    0x2F116: "3246",
    0x2F118: "6946",
    0x2F11E: "cde90033",
    0x2F122: "b847",

    # Wrapper layout: SetP, two metadata words, then the full nested message.
    0x2F8B2: "5568",
    0x2F8CE: "0f4f",
    0x2F8D6: "43f8047b",
    0x2F8DA: "d1f800c0",
    0x2F8DE: "4f68",
    0x2F8E0: "1146",
    0x2F8E2: "c6f804c0",
    0x2F8E6: "5f60",
    0x2F8E8: "5268",
    0x2F8EA: "def021f8",

    # Manager bridge and application router retain packet pointer and length.
    0x31650: "6168",
    0x31652: "0268",
    0x3165E: "2968",
    0x31660: "aa68",
    0x20764: "14f0a8fa",
    0x20772: "2a46",
    0x20778: "3946",

    # Singleton binding resolves its +0x13c cell to device subobject +4.  The
    # lazy initializer constructs the final derived object before registering
    # the separate teardown callback.
    0x3D4FE: "104b",
    0x3D504: "0f4a",
    0x3D512: "5a51",
    0x3D514: "0432",
    0x3D518: "5a50",
    0x3D528: "0648",
    0x3D52A: "20f073fd",
    0x3D534: "0548",
    0x3D536: "22f065fb",
    0x41580: "cd4b",
    0x4158A: "03f14800",
    0x41594: "03f15405",
    0x4159A: "6060",
    0x415A0: "2360",
    0x415A2: "a560",
    0x5E018: "fff7bafc",
    0x5E01C: "1b4b",
    0x5E02A: "03f10805",
    0x5E036: "2560",
    0x5E042: "6560",
    0x5E048: "a360",
    0x3CC08: "0430",
    0x3CC12: "d0f83c01",
    0x3CC42: "d0f83801",
    0x3CC4A: "0568",
    0x3CC4E: "0091",
    0x3CC52: "cde90122",
    0x3CC5A: "6a46",
    0x3CC5C: "2b68",
    0x3CC62: "9847",

    # Device routing adjustor and zero-selector path.
    0x41B6C: "a0f10400",
    0x41B70: "16e7",
    0x419A4: "d2f80880",
    0x419B6: "d2f80090",
    0x419BA: "d9f80470",
    0x419C0: "61d0",
    0x41A86: "ca46",
    0x41A8C: "5af8044b",
    0x41A9E: "09f10c01",
    0x41AAA: "2d4b",
    0x41AAC: "9c42",
    0x41AAE: "49d0",
    0x41B44: "0368",
    0x41B46: "1b68",
    0x41B48: "9847",
    0x3CF20: "a0f10800",
    0x3CF24: "b8e7",
    0x3CE98: "0b68",
    0x3CEBE: "abb1",
    0x3CEEC: "0346",
    0x3CEEE: "f2e7",

    # Nested Stat payload is copied to the live accumulation buffer unchanged.
    0x420BE: "0b68",
    0x420C8: "0546",
    0x420E4: "8a68",
    0x420EA: "00f08980",
    0x42200: "d1f81960",
    0x42208: "d1f81200",
    0x42210: "1d31",
    0x4221A: "3844",
    0x4221E: "cbf087fb",
    0x42238: "eaf75cfd",
    0x4223C: "0023",
    0x42240: "0022",
    0x42242: "0096",
    0x42244: "eaf78cfc",
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

    # Structured-state entry retains the supplied stream, initializes the
    # local native-u32 destination to zero, reads it, and requires value two.
    0x531EE: "1446",
    0x53200: "1a94",
    0x53204: "1295",
    0x53206: "d9f703fe",
    0x53212: "bbf1020f",
}


DIRECT_TARGETS = {
    0x30B16: FIRMWARE_BASE + 0x2C0A8,
    0x30C06: FIRMWARE_BASE + 0x30A90,
    0x30C2A: FIRMWARE_BASE + 0x30708,
    0x2F8EA: 0x6012D930,
    0x20764: FIRMWARE_BASE + 0x34CB8,
    0x3D52A: FIRMWARE_BASE + 0x5E014,
    0x3D536: FIRMWARE_BASE + 0x5FC04,
    0x41B70: FIRMWARE_BASE + 0x419A0,
    0x3CF24: FIRMWARE_BASE + 0x3CE98,
    0x420EA: FIRMWARE_BASE + 0x42200,
    0x4221E: 0x6012D930,
    0x42238: FIRMWARE_BASE + 0x2CCF4,
    0x42244: FIRMWARE_BASE + 0x2CB60,
    0x5E018: FIRMWARE_BASE + 0x5D990,
    0x53206: FIRMWARE_BASE + 0x2CE10,
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
    """Return the exact stored-record recall framing report."""
    digest = hashlib.sha256(data).hexdigest()
    _require(len(data) == FIRMWARE_SIZE,
             "firmware size differs: %d" % len(data))
    _require(digest == FIRMWARE_SHA256,
             "firmware SHA-256 differs: %s" % digest)

    try:
        zero_report = zero_receiver.analyze(data)
    except zero_receiver.AnalysisError as error:
        raise AnalysisError(str(error)) from error
    _require(
        zero_report["status"]
        == (
            "ZERO_SELECTOR_STAT_ROUTE_SOURCE_BOUND_FINAL_DERIVED_"
            "SLOT_0X38_0X531E0"
        ),
        "zero-selector receiver status differs",
    )

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

    return {
        "boundary": (
            "PHYSICAL_STORED_BYTES_AND_UC472_SERIALIZER_REMAIN_UNOBSERVED"
        ),
        "final_receiver_construction": {
            "base_constructor": "0x5e018 -> 0x5d990",
            "base_vtable_lifetime": (
                "0x6008d3a8 transient during construction and teardown"
            ),
            "derived_constructor": "0x3d52a -> 0x5e014",
            "final_primary_vtable": "0x5e02a/0x5e036 -> 0x6012cb40",
            "final_slot_0x38": "0x10cb78 -> 0x531e0",
            "global": "0x20216660",
            "registered_teardown": "0x41580 after construction",
        },
        "known_host_prefix_effect": {
            "copied_into_accumulation_if_recalled": True,
            "first_native_word_if_present": "0x700b697b",
            "interpreted_on_zero_selector_route": True,
            "linux_tagged_map_prefix_hex": "7b690b70",
            "physical_device_presence": "UNOBSERVED",
            "required_native_word": "0x00000002",
        },
        "live_stat_handoff": {
            "accumulation_destination": "device+0x18+fragment_offset",
            "constructed_stack_reader_cursor": 0,
            "dispatcher": "0x420bc",
            "first_callback": "0x42266 -> 0x531e0",
            "first_callback_arguments": "r1=0, r3=1",
            "nested_payload_source": "Stat+0x1d",
            "prefix_inserted": False,
            "second_callback": "0x42280 -> 0x531e0",
            "second_callback_arguments": "r1=1, r3=0",
            "stat_branch": "0x42200",
            "structured_state_reached": True,
        },
        "packet_router": {
            "device_lookup": (
                "device+8 final vtable slot -> 0x3cf20/0x3ce98"
            ),
            "device_lookup_query": "packet+4 = {0, 0}",
            "device_lookup_result": "final derived device global",
            "dispatcher_vtable": "0x6012cb40 slot 0 -> 0x420bc",
            "function": "0x419a0",
            "nested_stat_argument": "r1 = packet+0xc",
            "setp_branch": "0x41aaa -> 0x41b44",
        },
        "recall_wrapper": {
            "callback": "0x2f8ac",
            "copy_call": "0x2f8ea -> memcpy",
            "driver": "0x2f0d0",
            "nested_stat_offset": 12,
            "packet_layout": "SetP | 0 | 0 | nested Stat message",
        },
        "route_reconciliation": {
            "exact_route": (
                "0x3cc40 -> 0x41b6c/0x419a0 -> "
                "0x3cf20/0x3ce98 -> 0x420bc -> 0x531e0"
            ),
            "intermediate_noop_claim_retracted": True,
            "old_shorthand": "0x3cc40 -> 0x420bc",
            "ultimate_dispatcher_unchanged": True,
        },
        "singleton_forwarding": {
            "application_router": "0x20790/0x20754 -> 0x34cb8",
            "device_router_adjustor": "0x41b6c -> 0x419a0",
            "device_router_cell": (
                "0x20216664 -> final secondary vtable -> 0x41b6c"
            ),
            "manager_bridge": "0x31674/0x3163c",
            "projection": "vtable 0x6d40c -> 0x3cc08",
            "secondary_forwarder": "vtable 0x6d434 -> 0x3cc40",
            "singleton_field": "primary+0x13c -> cell 0x20216664",
        },
        "source": {
            "image_base": "0x60020000",
            "sha256": FIRMWARE_SHA256,
            "size": FIRMWARE_SIZE,
        },
        "status": (
            "STORED_STAT_RECALL_SOURCE_BOUND_BYTE_PRESERVING_NO_PREFIX_"
            "INSERTION"
        ),
        "stored_record_reader": {
            "entry": "0x30be0",
            "fallback_copy": "0x30c2a -> 0x30708",
            "fallback_payload_flow": (
                "descriptor bytes -> message+0x1d unchanged"
            ),
            "slot_range": "0..3",
            "stat_tag": "Stat",
            "storage_payload_flow": (
                "stored bytes -> message+0x1d unchanged"
            ),
            "storage_payload_read": "0x30b16 -> 0x2c0a8",
            "storage_record_length_member": "message+0x19",
            "storage_reader": "0x30a90",
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
