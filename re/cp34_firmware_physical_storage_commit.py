#!/usr/bin/env python3
"""Source-bind CP34 ``Stat`` writes through physical storage completion.

The analyzer accepts only the exact io24 firmware 1.28 application. It extends
the sealed ``MemP/Stat`` ingress analysis through the concrete device storage
object, its compare-before-program implementation, the program transaction,
and the post-program ready poll. It never emits or loads firmware and never
accesses USB or audio hardware.
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

import cp34_firmware_ingress_storage_framing as predecessor  # noqa: E402


class AnalysisError(ValueError):
    """The input differs from the pinned firmware or expected byte path."""


FIRMWARE_SIZE = predecessor.FIRMWARE_SIZE
FIRMWARE_SHA256 = predecessor.FIRMWARE_SHA256
FIRMWARE_BASE = predecessor.FIRMWARE_BASE


CODE_SLICES = {
    "device_backend_registration": (
        0x20D3C, 0x14,
        "f114f844ec3f6ac41275b1d5961ce31236a6c514f29c99829922fd733b2488f7",
    ),
    "singleton_receiver_binding": (
        0x3D4BC, 0x30,
        "b00effa1e267f621a17072579c12983ee61c846d5b69cd647c8f4e535c12378d",
    ),
    "singleton_subobject_projection": (
        0x31AAC, 0x10,
        "c73fca11323f83d4d7e261441a2af12f0d5b6c34e65f279224393a1c8d065e4c",
    ),
    "backend_receiver_write_adapter": (
        0x316B0, 0x34,
        "e89cdd94b3de642671c4d1a42fbad6bb1a1dbd6d672b50c2941b91731e3d25b8",
    ),
    "device_constructor": (
        0x4B748, 0x50,
        "e8cdda4e156bbd51202f62a02a65c42b93ced242dcded1cfc20727363820615e",
    ),
    "storage_stack_constructor": (
        0x4C840, 0x24,
        "9eee6914644847f24d003559a87073038af04832293be2b37cc065b8c3fc4b09",
    ),
    "storage_manager_constructor": (
        0x4C120, 0xB4,
        "9eb637fe025b16a70e9a0d9239094c17ce9954ef623f2b6e2e2a25f4861fa11d",
    ),
    "physical_interface_constructor": (
        0x4AB24, 0x20,
        "fbef73e5541f170525ac2d058024cc770bf908ef3692f394bd9904eaae91c486",
    ),
    "root_storage_query": (
        0x20808, 0x22,
        "f8bbde45e29909d0f4e8a1abf34095195186696b7c60183a1ef0f0259d5efc67",
    ),
    "root_storage_projection": (
        0x4B410, 0x0A,
        "b4b4e5afb6e63016ecb271ae15f66ecd9ad1f367d8f6708ce31552d8ca925952",
    ),
    "manager_physical_projection": (
        0x4BF04, 0x08,
        "123e5970309c19cac75c68e337c952f9aa6beed34faf748a5f7456d6d3eded18",
    ),
    "physical_write": (
        0x4AA90, 0x60,
        "faeed7bb6120989c4530a03821d8b7c0b06fe620177ea4afdd8a7e5c64a25a60",
    ),
    "physical_read": (
        0x4AAF4, 0x2C,
        "7a68cb6a45aa613429ea4a3a3eeec12ed9b06ce69a9ece51b9836454299b406d",
    ),
    "compare_program": (
        0x32CD8, 0x9C,
        "52d926458c90e6ff0a538a4579bad1d932c6d1d668da9f70b6885273cac1b6c9",
    ),
    "program_transaction": (
        0x32C0C, 0x68,
        "7b10140424c2e269f7c39418028431cc5dfed72c739f24d5e6602223973c23b5",
    ),
    "transaction_wait": (
        0x326DC, 0xF0,
        "a553845a737c4c97f09c26099bb76036e289dc2b91afc407bf125cc3abfa995c",
    ),
    "ready_poll": (
        0x32A70, 0x80,
        "e2057a1143bde4525c32b8d501cfa76a18890255dfa663f9af166c35010fc8c9",
    ),
}


U32_ANCHORS = {
    # Static singleton whose +0x38 field receives device+8.
    0x3D4E8: 0x20220C08,

    # Device construction and storage-manager construction tables.
    0x4B798: 0x6012BD48,
    0x4C864: 0x6012BCFC,
    0x4C1D4: 0x6012BF5C,
    0x4AB40: 0x6012BC78,
    0x4AB44: 0x6012BC68,

    # Query path: device+8 -> manager+8 -> physical interface.
    0x10BE20: 0x60040809,
    0x10BDD4: 0x6006B411,
    0x10BFC4: 0x6006BF05,

    # Concrete physical interface and its exact logical-region descriptor.
    0x10BC84: 0x6006AA91,
    0x10BC88: 0x6006AAF5,
    0x10BC68: 0x00008000,
    0x10BC6C: 0x00000040,
    0x10BC70: 0x00000001,
    0x10BC74: 0x0000000A,
}


EXACT_INSTRUCTIONS = {
    # The device initialization caller passes device+8 into the singleton
    # registration path. 0x31aac projects singleton+0x18 and the store at
    # +0x20 therefore binds device+8 at singleton+0x38.
    0x20D3E: "0446",
    0x20D42: "0830",
    0x20D44: "1cf0bafb",
    0x3D4BE: "0a4c",
    0x3D4C0: "0546",
    0x3D4C2: "2046",
    0x3D4C4: "f4f7f2fa",
    0x3D4CC: "1d62",
    0x3D4DE: "f4f7e7fa",
    0x31AAC: "1830",

    # The Stat write adapter's adjustor recovers singleton+0x18, and 0x316b0
    # reloads +0x20 (the bound device+8) before calling vtable +0x10. That
    # exact slot is the 0x20808 query anchored below; its result is passed to
    # the physical interface's +0x4 write slot with backend flag one.
    0x316B0: "006a",
    0x316B4: "0468",
    0x316BC: "2469",
    0x316C2: "a047",
    0x316CA: "6468",
    0x316DC: "a0f11400",
    0x316E0: "fff7e6bf",

    # Device+0xe9c owns a manager at +0x26c == device+0x1108.
    0x4B752: "04f69c60",
    0x4B786: "01f05bf8",
    0x4C84A: "04f51b70",
    0x4C85C: "fff760fc",

    # Manager vtables and concrete interface at manager+0x27c.
    0x4C132: "02f15401",
    0x4C13A: "02f10806",
    0x4C140: "c4e90213",
    0x4C146: "2660",
    0x4C1C2: "04f51f70",
    0x4C1CA: "fef7abfc",
    0x4AB28: "03f10802",
    0x4AB32: "0260",
    0x4AB36: "6360",

    # Dynamic query first projects device+0x1110, then +0x274 to the
    # concrete manager+0x27c physical interface.
    0x20808: "50f8083c",
    0x2080C: "0838",
    0x2080E: "d3f88430",
    0x20818: "044a",
    0x2081A: "5b69",
    0x20820: "bde81040",
    0x4B412: "41f21010",
    0x4B416: "1844",
    0x4BF04: "00f51d70",

    # The backend's flag one takes compare-before-program; flag zero would
    # take the direct path. Both preserve address/source/length.
    0x4AA9A: "d7e90007",
    0x4AAA8: "bcf1000f",
    0x4AACE: "e8f703f9",
    0x4AAD6: "2825",
    0x4AAE4: "e8f7c6b8",
    0x4AAFC: "d6e90046",
    0x4AB10: "e8f748f8",

    # Changed data is read, compared, programmed synchronously, and followed
    # by a ready poll before the call returns success.
    0x32D40: "fff704ff",
    0x32D50: "daf0b2fd",
    0x32D62: "fff753ff",
    0x32C48: "fff75aff",
    0x32C5E: "fff73dfd",
    0x32C62: "18b9",
    0x32C68: "fff702ff",
    0x326E4: "4ff0ff31",
    0x326E8: "8068",
    0x32746: "dbf0a3f8",
    0x32758: "9847",
    0x32764: "9847",
    0x32772: "2046",
    0x32AD2: "fff703fe",
    0x32ADE: "0028",
}


DIRECT_TARGETS = {
    0x20D44: FIRMWARE_BASE + 0x3D4BC,
    0x3D4C4: FIRMWARE_BASE + 0x31AAC,
    0x3D4CE: FIRMWARE_BASE + 0x31AAC,
    0x3D4DE: FIRMWARE_BASE + 0x31AB0,
    0x316E0: FIRMWARE_BASE + 0x316B0,
    0x4B786: FIRMWARE_BASE + 0x4C840,
    0x4C85C: FIRMWARE_BASE + 0x4C120,
    0x4C1CA: FIRMWARE_BASE + 0x4AB24,
    0x4AB38: FIRMWARE_BASE + 0x32A5C,
    0x4AACE: FIRMWARE_BASE + 0x32CD8,
    0x4AAE4: FIRMWARE_BASE + 0x32C74,
    0x4AB10: FIRMWARE_BASE + 0x32BA4,
    0x32D40: FIRMWARE_BASE + 0x32B4C,
    0x32D50: 0x6012D8B8,
    0x32D62: FIRMWARE_BASE + 0x32C0C,
    0x32C48: FIRMWARE_BASE + 0x32B00,
    0x32C5E: FIRMWARE_BASE + 0x326DC,
    0x32C68: FIRMWARE_BASE + 0x32A70,
    0x32746: 0x6012D890,
    0x32AD2: FIRMWARE_BASE + 0x326DC,
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
    """Return the exact physical-backend completion report."""
    digest = hashlib.sha256(data).hexdigest()
    _require(len(data) == FIRMWARE_SIZE,
             "firmware size differs: %d" % len(data))
    _require(digest == FIRMWARE_SHA256,
             "firmware SHA-256 differs: %s" % digest)

    try:
        ingress_report = predecessor.analyze(data)
    except predecessor.AnalysisError as error:
        raise AnalysisError(str(error)) from error
    _require(
        ingress_report["status"]
        == (
            "FIRMWARE_STAT_INGRESS_RECALL_SOURCE_BOUND_LOGICAL_BYTE_ZERO_"
            "UNCHANGED_NO_PREFIX_INSERTION"
        ),
        "predecessor ingress status differs",
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

    descriptor = [_u32(data, 0x10BC68 + offset)
                  for offset in range(0, 16, 4)]
    _require(descriptor[0] - descriptor[1] == 0x7FC0,
             "physical logical-region capacity differs")

    return {
        "backend_resolution": {
            "adapter_receiver_join": (
                "0x20d3c passes device+8 to 0x3d4bc; 0x3d4bc "
                "stores it at singleton+0x38; 0x316dc/0x316b0 "
                "reloads that field before device vtable +0x10"
            ),
            "device_constructor": "0x4b748",
            "device_storage_subobject": "device+0xe9c",
            "manager_constructor": "0x4c120 at device+0x1108",
            "physical_interface": "manager+0x27c = device+0x1384",
            "physical_interface_constructor": "0x4ab24",
            "physical_vtable": "0x6012bc80",
            "query_chain": (
                "0x20808 -> device vtable +0x84/0x4b410 -> "
                "manager vtable +0x14/0x4bf04"
            ),
            "read_slot": "+0x8 -> 0x4aaf4",
            "write_slot": "+0x4 -> 0x4aa90",
        },
        "completion_semantics": {
            "backend_flag_one": "compare before program",
            "changed_bytes": "0x52cd8 -> 0x52c0c",
            "compare": "0x52d50 -> memcmp 0x6012d8b8",
            "program_transaction": "0x52c5e -> 0x526dc",
            "ready_poll_after_program": "0x52c68 -> 0x52a70",
            "separate_commit_after_success": False,
            "unchanged_bytes": "successful no-op after comparison",
            "write_return": (
                "success only after compare and, when changed, "
                "program transaction plus ready poll"
            ),
        },
        "logical_region": {
            "capacity": 0x7FC0,
            "descriptor": "0x6012bc68",
            "descriptor_words": descriptor,
        },
        "remaining_live_boundary": (
            "SET_P_TRANSPORT_HAS_NO_READABLE_STORAGE_RESULT; stored bytes "
            "and successful physical return remain unobserved"
        ),
        "source": {
            "image_base": "0x60020000",
            "sha256": FIRMWARE_SHA256,
            "size": FIRMWARE_SIZE,
        },
        "status": (
            "FIRMWARE_STAT_PHYSICAL_BACKEND_SOURCE_BOUND_SYNCHRONOUS_"
            "COMPARE_PROGRAM_NO_SEPARATE_COMMIT"
        ),
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
