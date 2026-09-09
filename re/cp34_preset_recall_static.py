#!/usr/bin/env python3
"""Verify the CP34 native Stat-recall path in pinned firmware and UC 4.7.2.

This analyzer only reads two local binary images.  It never loads vendor code,
opens Wine, imports the io24 transport, or accesses USB/audio hardware.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from capstone import CS_AC_READ, CS_AC_WRITE, CS_ARCH_X86, CS_MODE_64, Cs
from capstone.x86_const import X86_OP_MEM


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from io24_preset_record import (  # noqa: E402
    decode_preset_record_prefix,
    encode_preset_record,
)
from cp34_host_queue_inventory import AnalysisError as PeAnalysisError  # noqa: E402
from cp34_host_queue_inventory import _parse_pe  # noqa: E402


class AnalysisError(ValueError):
    """A source image does not match the sealed CP34 structural evidence."""


FIRMWARE_SHA256 = "65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a"
FIRMWARE_SIZE = 1_104_448
FIRMWARE_BASE = 0x60020000
UC472_SHA256 = "de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28"
UC472_SIZE = 4_979_672


FIRMWARE_VTABLE_ANCHORS = {
    "root_fragment_apply": (0x6D254, 0x2F8AC),
    "root_stat_recall": (0x6D260, 0x2F0D0),
    "root_slot_change": (0x6D274, 0x2F334),
    "root_memp_ingress": (0x6D288, 0x2F210),
    "preset_stat_reader": (0x6751C, 0x30BE0),
    "manager_callback_bridge": (0x676D4, 0x31674),
    "application_router": (0x10BE8C, 0x20790),
    "router_singleton_projection": (0x6D40C, 0x3CC08),
    "router_singleton_record_forward": (0x6D434, 0x3CC40),
    "live_record_dispatcher": (0x10CB40, 0x420BC),
    "live_structured_state_apply": (0x10CB78, 0x531E0),
    "voicefx_primary_gate_handler": (0x10C6CC, 0x50AF8),
    "voicefx_primary_state_apply": (0x10C6E4, 0x5545C),
    "voicefx_primary_work_slot": (0x10C6F0, 0x5F1F4),
    "voicefx_state_apply_adjustor": (0x10C704, 0x555B8),
}


FIRMWARE_CODE_SLICES = {
    "slot_change_dispatch": (0x2F3E4, 0x38,
        "f8890a0ecedcfb99226d9967bcbd2a17ba3d9efbb6cbcfc77dd1e2d3fe91d4a6"),
    "stat_recall": (0x2F0D0, 0x6C,
        "54498abfd4282dd20683120259929407f6618f90217ab98045270b39dd386352"),
    "stat_record_reader": (0x30BE0, 0x54,
        "32091a8693dae4a94c30e242f83e83cb68618605eb43dfd0ecb6c561afd644ee"),
    "fragment_callback": (0x2F8AC, 0x58,
        "5eff2a6ade387c5e4c4a2a46fd2fe640bf42e2a6d71082f681381bbc47a17f17"),
    "callback_bridge": (0x3163C, 0x38,
        "4cc5dd6fae37fc54a1cf40d9726f807b774957aff61cbf36d58ca9e89bb5ecff"),
    "application_router": (0x20754, 0x3C,
        "2b03f9ae7407c774bcd93c252b6833b3db299f7bf65de180376d280901508913"),
    "preset_table_binder": (0x3C9EE, 0x50,
        "cae1994270c45081441276d225f7f10ac77403e223970094186ef5ee549b9bcd"),
    "factory_bank_binder": (0x3066C, 0x48,
        "b53ff9d91a43f6f095adb39f11dd95ab0faf9752eb6a0afecf86c9452d60e782"),
    "router_singleton_lookup": (0x34CB8, 0x0C,
        "3f96d7faa885ddc791e911b60343107d9a19e6ffaacb42b65378231f2cabb3e5"),
    "singleton_interface_projection": (0x3CC08, 0x04,
        "eea00f3392bbbf5ec7ea83e049192860f6e231d5978f598abaafbf0076ca004d"),
    "singleton_record_forward": (0x3CC40, 0x2E,
        "ec43a5b416faa096ceee09c541a94c2187976a57c29585345b5364dfc3f2ae53"),
    "live_dispatch_tag": (0x420BC, 0x32,
        "bb6d8f1dcb856f0618b4115b782addae7887ac1fedc85bbeb10e407df7e7f829"),
    "live_stat_record_branch": (0x42200, 0x82,
        "2528259839a4a64ca6fa9f628dd3018feb4f7966f5d8c4db390616ed24cf5ea0"),
    "state_component_dispatch": (0x53222, 0x16C,
        "1a61bd7651e7ac8d60a096288c72e4e322e4488704dcd8fc73ff61fd47d6fe43"),
    "device_component_table_binder": (0x5E014, 0x54,
        "94fe5ba1d6c74e69f0c77960cf7f7e33dea86e19dbae17992d03a918f4ef4e87"),
    "voicefx_block_constructor": (0x591BC, 0x92,
        "757744a5de70949bc0f39469d4b26ac34b045776ad5d4ceab2eebc7ca8e5c418"),
    "voicefx_model_select": (0x55388, 0x48,
        "8f1ecb6e2ed75578c94d1d1fe641c3fd2ca39186a404bf7ce35546dcfdcaa96a"),
    "voicefx_state_gate_arm": (0x554A6, 0x20,
        "e5fc9c4031722a40b150e96e592bf08d21fe8aa4955de93e3359d0f3a8df50cf"),
}


FIRMWARE_INSTRUCTION_ANCHORS = {
    "live_stat_tag": (0x423D4, bytes.fromhex("74617453")),
    "voicefx_model_gate_a_assignment": (
        0x553A2, bytes.fromhex("01236269a56184f84430")),
    "voicefx_state_gate_bc_assignment": (
        0x554B0,
        bytes.fromhex("002540f20113b1693046356433874ff0000afff761ff")),
}


FACTORY_RECORDS = (
    (0, 0x6A2B8, 822, "Broadcast", 0),
    (0, 0x6A5F0, 814, "Vocal", 0),
    (0, 0x6A920, 854, "Acoustic Guitar", 0),
    (0, 0x6AC78, 697, "Electric Guitar", 0),
    (0, 0x6AF34, 659, "Vintage Channel", 0),
    (0, 0x6B1C8, 850, "Slap Echo", 1),
    (0, 0x6B51C, 645, "Detuned Vocal", 1),
    (0, 0x6B7A4, 846, "Robot", 1),
    (1, 0x6BAF4, 822, "Broadcast", 0),
    (1, 0x6BE2C, 814, "Vocal", 0),
    (1, 0x6C15C, 854, "Acoustic Guitar", 0),
    (1, 0x6C4B4, 697, "Electric Guitar", 0),
    (1, 0x6C770, 712, "Bass Guitar", None),
    (1, 0x6CA38, 731, "Stereo Acoustic", None),
    (1, 0x6CD14, 720, "Stereo Piano", None),
    (1, 0x6CFE4, 537, "Stereo DJ", None),
)


EXPECTED_E6_ACCESSES = (
    (0x1800290E7, "write"),
    (0x18003BB38, "read"),
    (0x18003C037, "write"),
    (0x18003C20D, "write"),
    (0x18003C4E8, "write"),
    (0x180044E89, "read"),
)


UC_PARSER_ANCHORS = {
    "voicefx_name_reference": (
        0x18003C1A4, bytes.fromhex("4c8d3dbd973f00")),
    "nested_on_name": (
        0x18003C297,
        bytes.fromhex("488b424880386f750c8078016e750680780200740a")),
    "integer_or_real_equals_one": (
        0x18003C2B6,
        bytes.fromhex(
            "0fb742086683e07f6683f8017506488b4210eb11"
            "6683f8027508f2480f2c4210eb03488bc3"
            "4883f8010f8526ffffffe923ffffff")),
    "voicefx_on_store": (
        0x18003C20D, bytes.fromhex("418885e6000000")),
    "serializer_read": (
        0x18003BB38, bytes.fromhex("4280bc31e6000000007440")),
}


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _u32_table(data, offset, count):
    end = offset + count * 4
    _require(0 <= offset <= end <= len(data),
             "u32 table at %#x exceeds the input" % offset)
    return list(struct.unpack_from("<%dI" % count, data, offset))


def _section_bytes(image_base, sections, virtual_address, size):
    rva = virtual_address - image_base
    for section in sections.values():
        start = section["virtual_address"]
        available = min(section["virtual_size"], section["raw_size"])
        relative = rva - start
        if 0 <= relative and relative + size <= available:
            return section["data"][relative:relative + size]
    raise AnalysisError("virtual address %#x is not file-backed" % virtual_address)


def scan_byte_field_accesses(code, address, displacement):
    """Return instruction-boundary accesses to one x86-64 field displacement."""
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    decoder.skipdata = True
    found = []
    for instruction in decoder.disasm(code, address):
        if instruction.id == 0:
            continue
        for operand in instruction.operands:
            if operand.type != X86_OP_MEM or operand.mem.disp != displacement:
                continue
            access = []
            if operand.access & CS_AC_READ:
                access.append("read")
            if operand.access & CS_AC_WRITE:
                access.append("write")
            found.append({
                "address": instruction.address,
                "access": "+".join(access) or "unknown",
                "instruction": "%s %s" % (
                    instruction.mnemonic, instruction.op_str),
            })
    return found


def analyze_firmware(data):
    digest = _sha256(data)
    _require(len(data) == FIRMWARE_SIZE,
             "firmware size differs: %d" % len(data))
    _require(digest == FIRMWARE_SHA256,
             "firmware SHA-256 differs: %s" % digest)

    anchors = {}
    for name, (word_offset, target_offset) in FIRMWARE_VTABLE_ANCHORS.items():
        word, = _u32_table(data, word_offset, 1)
        expected = FIRMWARE_BASE + target_offset + 1
        _require(word == expected,
                 "%s vtable word differs: %#x" % (name, word))
        anchors[name] = {
            "vtable_word_offset": hex(word_offset),
            "thumb_pointer": hex(word),
            "target_file_offset": hex(target_offset),
        }

    code_slices = {}
    for name, (offset, size, expected) in FIRMWARE_CODE_SLICES.items():
        actual = _sha256(data[offset:offset + size])
        _require(actual == expected,
                 "%s code slice differs: %s" % (name, actual))
        code_slices[name] = {
            "offset": hex(offset), "size": size, "sha256": actual,
        }

    instruction_anchors = {}
    for name, (offset, expected) in FIRMWARE_INSTRUCTION_ANCHORS.items():
        actual = data[offset:offset + len(expected)]
        _require(actual == expected,
                 "%s instruction bytes differ at %#x" % (name, offset))
        instruction_anchors[name] = {
            "offset": hex(offset), "bytes": actual.hex(),
        }

    records = []
    bank_lengths = [[], []]
    for bank, offset, expected_size, title, expected_on in FACTORY_RECORDS:
        record, consumed = decode_preset_record_prefix(data[offset:])
        _require(consumed == expected_size,
                 "%s record size differs: %d" % (title, consumed))
        _require(encode_preset_record(record) == data[offset:offset + consumed],
                 "%s record does not round-trip" % title)
        _require(record.get("preset_name") == title,
                 "factory title differs at %#x" % offset)
        voicefx = record.get("voicefx")
        actual_on = voicefx.get("on") if voicefx is not None else None
        _require(actual_on == expected_on,
                 "%s voicefx.on differs: %r" % (title, actual_on))
        bank_lengths[bank].append(consumed)
        records.append({
            "bank": bank,
            "offset": hex(offset),
            "size": consumed,
            "preset_name": title,
            "voicefx_on": actual_on,
            "voicefx_classid": (
                voicefx.get("__classid") if voicefx is not None else None),
        })

    table_0 = _u32_table(data, 0x691F0, 8)
    table_1 = _u32_table(data, 0x69210, 8)
    _require(table_0 == bank_lengths[0], "factory bank 0 size table differs")
    _require(table_1 == bank_lengths[1], "factory bank 1 size table differs")
    stat_lengths = _u32_table(data, 0x691E0, 4)
    _require(stat_lengths == [0x440, 0x440, 0x404, 0x404],
             "four-Stat descriptor table differs")

    return {
        "sha256": digest,
        "size": len(data),
        "load_base": hex(FIRMWARE_BASE),
        "vtable_anchors": anchors,
        "code_slices": code_slices,
        "instruction_anchors": instruction_anchors,
        "voicefx_processing_gate": {
            "component_id": 201,
            "component_base_offset": "0x11e0",
            "state_interface_offset": "0x11e4",
            "primary_vtable_file_offset": "0x10c6bc",
            "state_interface_vtable_file_offset": "0x10c700",
            "state_apply": {
                "adjustor": "0x555b8",
                "target": "0x5545c",
            },
            "assignments": [
                {"site": "0x554ba", "field": "+0x40", "value": 0},
                {"site": "0x554bc", "field": "+0x39", "value": 1,
                 "source": "high byte of little-endian halfword 0x0101 at +0x38"},
                {"site": "0x553a8", "field": "+0x44", "value": 1,
                 "source": "valid model selection called by 0x554c2"},
            ],
            "gated_handler": "0x50af8",
            "required_conditions": ["+0x44 != 0", "+0x39 != 0", "+0x40 == 0"],
        },
        "factory_records": records,
        "factory_bank_size_tables": [table_0, table_1],
        "stat_descriptor_lengths": stat_lengths,
    }


def analyze_uc472(data):
    digest = _sha256(data)
    _require(len(data) == UC472_SIZE,
             "UC 4.7.2 module size differs: %d" % len(data))
    _require(digest == UC472_SHA256,
             "UC 4.7.2 module SHA-256 differs: %s" % digest)
    try:
        image_base, sections = _parse_pe(data)
    except PeAnalysisError as error:
        raise AnalysisError(str(error)) from error

    text = sections[".text"]
    text_size = min(text["virtual_size"], text["raw_size"])
    text_address = image_base + text["virtual_address"]
    accesses = scan_byte_field_accesses(
        text["data"][:text_size], text_address, 0xE6)
    actual = tuple((item["address"], item["access"]) for item in accesses)
    _require(actual == EXPECTED_E6_ACCESSES,
             "UC +0xe6 access census differs: %r" % (actual,))

    parser_anchors = {}
    for name, (address, expected) in UC_PARSER_ANCHORS.items():
        actual_bytes = _section_bytes(image_base, sections, address, len(expected))
        _require(actual_bytes == expected,
                 "%s bytes differ at %#x" % (name, address))
        parser_anchors[name] = {
            "address": hex(address),
            "bytes": actual_bytes.hex(),
        }
    _require(_section_bytes(image_base, sections, 0x180435968, 8)
             == b"voicefx\0", "voicefx field literal differs")
    _require(_section_bytes(image_base, sections, 0x1804359A0, 9)
             == b"VoiceFxOn", "VoiceFxOn serializer literal differs")

    return {
        "sha256": digest,
        "size": len(data),
        "image_base": hex(image_base),
        "voicefx_on_field_offset": "0xe6",
        "field_accesses": [{
            **item, "address": hex(item["address"]),
        } for item in accesses],
        "parser_anchors": parser_anchors,
        "field_literals": {
            "record_parent": "voicefx",
            "record_child": "on",
            "serializer_label": "VoiceFxOn",
        },
    }


def analyze(firmware, uc_module):
    return {
        "schema": "cp34-preset-recall-static-v2",
        "firmware": analyze_firmware(firmware),
        "uc_4_7_2_module": analyze_uc472(uc_module),
        "static_conclusions": {
            "stat_recall": (
                "selected Stat 0..3 is read by the firmware preset component "
                "and forwarded through the native application callback/router"),
            "voicefx_on": (
                "Voice FX activation intent is stored as voicefx.on in the "
                "same tagged preset record; three embedded active presets set it to 1"),
            "voicefx_processing_gate": (
                "the native Voice FX component state loader sets +0x39=1, "
                "+0x40=0, and +0x44=1 before applying the selected model state; "
                "these are all three conditions checked by gate handler 0x50af8"),
            "separate_enable_packet": (
                "the recovered native preset-application path contains its own "
                "processing-gate assignment; no additional standalone enable "
                "packet is missing from that path"),
            "boundary": (
                "static structure does not prove physical nonvolatile commit, "
                "power-cycle survival, audible DSP output, or that voicefx.on "
                "itself is copied directly into field +0x44"),
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware")
    parser.add_argument("uc_module")
    arguments = parser.parse_args(argv)
    try:
        firmware = Path(arguments.firmware).read_bytes()
        uc_module = Path(arguments.uc_module).read_bytes()
        report = analyze(firmware, uc_module)
    except (OSError, AnalysisError, ValueError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
