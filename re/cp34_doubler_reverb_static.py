#!/usr/bin/env python3
"""Prove how Doubler/Transformer reverb is represented in CP34 presets.

This analyzer reads only a pinned io24 firmware image and two extracted
Universal Control metadata files.  It does not import the io24 transport,
open Wine, or access USB/audio hardware.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

from capstone import CS_ARCH_ARM, CS_MODE_THUMB, Cs
from capstone.arm_const import ARM_OP_IMM


class AnalysisError(ValueError):
    """A source artifact differs from the sealed CP34 evidence."""


FIRMWARE_SHA256 = "65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a"
FIRMWARE_SIZE = 1_104_448
FIRMWARE_BASE = 0x60020000
FACTORY_JSON_SHA256 = "89b0572dd760b77831d012e2db0568b4f4eeb158985a4ca86126be28e934c73d"
FX_PARAMS_XML_SHA256 = "3f5f99bd6efdfd54b65adf15c82d8b9da36116b25b11e3c88a4ad441b9decd89"

DOUBLER_CLASS_ID = "{66A10093-D461-4CAC-A80C-91F6A1BB37E5}"
EXPECTED_REVERB_VOICEFX = {
    "__classid": DOUBLER_CLASS_ID,
    "on": 1,
    "lows": 0.06,
    "width": 0.405,
    "mix": 0.295,
}
FORBIDDEN_PRESET_KEYS = frozenset({
    "reverb", "vrvb", "FXA", "size", "predelay", "hp_freq",
})


FIRMWARE_VTABLE_ANCHORS = {
    "block202_primary_handler": (0x10CA3C, 0x56E70),
    "block202_core_config": (0x10CA6C, 0x5ADD4),
    "doubler_primary_handler": (0x10C890, 0x5BB6C),
    "doubler_runtime_config": (0x10C8C0, 0x5BFE0),
    "doubler_structured_state": (0x10C8C4, 0x5E0EC),
}


FIRMWARE_CODE_SLICES = {
    "device_block_construction": (
        0x5D9A8, 0x80,
        "c37631d303f2fd12358eb87de78f83f18792e16d082666af179fdbd651fc49af"),
    "voicefx_model_factory": (
        0x5F254, 0x64,
        "b289c54c6fae74e630918c36d4b39b967c8151d99864762702d2397033f2de40"),
    "block202_constructor": (
        0x5B258, 0x5E,
        "f867d055fe9f6d50fcc43b54520186cc845a2db4e9ebc6ab8e312ec895d335fc"),
    "doubler_private_core_constructor": (
        0x5E356, 0x2A,
        "f9c142cf0f4a779203febe98de77f77e3810ef5b1c4f74f80b9c95a9b76b1688"),
    "block202_core_configuration": (
        0x5ADD4, 0x28,
        "cdba3a95c542b0b50b06511534d62dfc338032862e3968be2232c1abeb677433"),
    "doubler_private_core_configuration": (
        0x5ADFC, 0x1C,
        "b9ce1ee4ae8d4efb020d6b31b6637d2134ed0888748c270714d66c6103c2cb6d"),
    "doubler_runtime_configuration_call": (
        0x5C062, 0x16,
        "105f71f96e3bd35f16feef6a86ae1c22857c2ae834eddebdf50cb09ce2978198"),
    "shared_reverb_core_constructor": (
        0x5AF14, 0x40,
        "baa75a3fce0d0bd57f91d50084bde1065a81d7f82a8b52c08f558caf4b334280"),
    "voicefx_two_input_two_output_setup": (
        0x3DBEC, 0x38,
        "0e3c8ed34ee6817c9a24bc9b58c4acd3c9547d3e90fd8eac519e97d10b118f1d"),
    "physical_input_lane_mapping": (
        0x3F8A2, 0x48,
        "e124e3cfa251b611c2bb60d9bcbca946c089dd0bbe64959b011cd1287a690145"),
    "processing_channel_pair_permutation": (
        0x2E6BC, 0x88,
        "15c17390229a54d5d799eece710d1035ceede35a7e805dcc38feec4b239933cf"),
    "processing_assignment_active_slot_swap": (
        0x2E77A, 0x42,
        "4fed3b4674f89b8a94498cf064f9e38fc8f5336da454bff5aeb399b9c4ae1093"),
    "doubler_private_core_two_lane_bind": (
        0x5AE60, 0x64,
        "405b44ab50d0ca7233fe3d7eab462016d04099e0a69dea33210e8d55cf346992"),
    "private_core_indexed_lane_helper": (
        0x56CC8, 0x60,
        "1d3ce22cabfe75cbad9b7c03f6edf2dc70985abe4fddb53b5e1234a181b29687"),
    "doubler_public_message_handler": (
        0x5BB6C, 0x1D0,
        "4ce38c9fbc85f27a17593d8fd7c3f36609b04984710b2c6b346377d4cb8a962a"),
}


FIRMWARE_CALL_ANCHORS = {
    "device_constructs_block201": (0x5DA12, 0x591BC),
    "device_constructs_block202": (0x5DA1E, 0x5B258),
    "model_zero_constructs_doubler": (0x5F260, 0x5E270),
    "block202_constructs_shared_core": (0x5B274, 0x5AF14),
    "doubler_constructs_private_core": (0x5E37C, 0x5AF14),
    "block202_configures_shared_core": (0x5ADE6, 0x5A6A8),
    "doubler_configures_private_core": (0x5AE0E, 0x5A6A8),
    "doubler_runtime_calls_private_config": (0x5C06C, 0x5ADFC),
    "device_sets_up_voicefx_two_lanes": (0x3DC1C, 0x553D4),
    "doubler_binds_indexed_private_core_lane": (0x5AEAC, 0x56CC8),
}


FIRMWARE_INSTRUCTION_ANCHORS = {
    "voicefx_setup_lane_count": (0x3DBF4, "movs", "r2, #2"),
    "voicefx_setup_two_equal_counts": (
        0x3DC10, "strd", "r2, r2, [sp, #0x1c]"),
    "voicefx_setup_singleton_object": (
        0x3DC16, "add.w", "r0, r5, #0x11e0"),
    "first_physical_input_map": (0x3F8A4, "movw", "r0, #0x5d74"),
    "second_physical_input_map": (0x3F8AA, "movw", "r3, #0x5d78"),
    "per_channel_processing_stride": (0x3F8AE, "movw", "r1, #0xcec"),
    "first_lane_object_select": (0x3F8BC, "mla", "r0, r1, r0, r6"),
    "second_lane_object_select": (0x3F8C8, "mla", "r3, r1, r3, r6"),
    "processing_assignment_first_slot_target": (
        0x2E7A0, "mov", "r3, r8"),
    "processing_assignment_first_slot_wire_id": (
        0x2E7A4, "movs", "r1, #0x10"),
    "processing_assignment_second_slot_target": (
        0x2E7B0, "mov", "r3, sb"),
    "processing_assignment_second_slot_wire_id": (
        0x2E7B8, "movs", "r1, #0x10"),
    "private_core_uses_loop_lane_index": (0x5AE90, "mov", "r3, r4"),
    "private_core_advances_to_lane_one": (0x5AEB2, "movs", "r4, #1"),
    "private_core_repeats_lane_bind": (0x5AEB4, "b", "#0x6007ae76"),
}


FIRMWARE_LITERAL_ANCHORS = {
    "doubler_handler_VFxO": (0x5BD30, 0x5646784F),
    "doubler_handler_Setu": (0x5BD34, 0x53657475),
    "doubler_handler_godv": (0x5BD38, 0x676F6476),
}


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _u32(data, offset):
    _require(0 <= offset <= len(data) - 4,
             "u32 at %#x exceeds the input" % offset)
    return struct.unpack_from("<I", data, offset)[0]


def _nested_keys(value):
    """Return every mapping key below a decoded JSON value."""
    found = set()
    if isinstance(value, dict):
        found.update(value)
        for child in value.values():
            found.update(_nested_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_nested_keys(child))
    return found


def _thumb_call_target(data, offset):
    """Decode one pinned Thumb BL and return its absolute target."""
    decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    decoder.detail = True
    instructions = list(decoder.disasm(
        data[offset:offset + 4], FIRMWARE_BASE + offset))
    _require(len(instructions) == 1,
             "call at %#x does not decode as one instruction" % offset)
    instruction = instructions[0]
    _require(instruction.mnemonic == "bl" and len(instruction.operands) == 1,
             "instruction at %#x is not BL" % offset)
    operand = instruction.operands[0]
    _require(operand.type == ARM_OP_IMM,
             "BL at %#x has no immediate target" % offset)
    return operand.imm


def _thumb_instruction(data, offset):
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

    vtables = {}
    for name, (word_offset, target_offset) in FIRMWARE_VTABLE_ANCHORS.items():
        pointer = _u32(data, word_offset)
        expected = FIRMWARE_BASE + target_offset + 1
        _require(pointer == expected,
                 "%s vtable word differs: %#x" % (name, pointer))
        vtables[name] = {
            "vtable_word_offset": hex(word_offset),
            "thumb_pointer": hex(pointer),
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

    calls = {}
    for name, (call_offset, target_offset) in FIRMWARE_CALL_ANCHORS.items():
        target = _thumb_call_target(data, call_offset)
        expected = FIRMWARE_BASE + target_offset
        _require(target == expected,
                 "%s target differs: %#x" % (name, target))
        calls[name] = {
            "call_file_offset": hex(call_offset),
            "target_file_offset": hex(target_offset),
            "target_address": hex(target),
        }

    instructions = {}
    for name, (offset, expected_mnemonic, expected_operands) in \
            FIRMWARE_INSTRUCTION_ANCHORS.items():
        instruction = _thumb_instruction(data, offset)
        _require(instruction.mnemonic == expected_mnemonic and
                 instruction.op_str == expected_operands,
                 "%s instruction differs: %s %s" %
                 (name, instruction.mnemonic, instruction.op_str))
        instructions[name] = {
            "file_offset": hex(offset),
            "mnemonic": instruction.mnemonic,
            "operands": instruction.op_str,
        }

    literals = {}
    for name, (offset, expected) in FIRMWARE_LITERAL_ANCHORS.items():
        actual = _u32(data, offset)
        _require(actual == expected,
                 "%s literal differs: %#x" % (name, actual))
        literals[name] = {"file_offset": hex(offset), "value": hex(actual)}

    block202_ctor = calls["block202_constructs_shared_core"]["target_address"]
    doubler_ctor = calls["doubler_constructs_private_core"]["target_address"]
    _require(block202_ctor == doubler_ctor,
             "block 202 and Doubler use different core constructors")
    block202_config = calls["block202_configures_shared_core"]["target_address"]
    doubler_config = calls["doubler_configures_private_core"]["target_address"]
    _require(block202_config == doubler_config,
             "block 202 and Doubler use different core configurators")

    return {
        "sha256": digest,
        "size": len(data),
        "load_base": hex(FIRMWARE_BASE),
        "vtable_anchors": vtables,
        "code_slices": code_slices,
        "call_anchors": calls,
        "instruction_anchors": instructions,
        "literal_anchors": literals,
        "object_layout": {
            "block201_voicefx": "device+0x11e0",
            "selected_model_object": "device+0x11f0",
            "doubler_private_reverb_core": "device+0x1574",
            "block202_shared_reverb": "device+0x3a70",
            "block202_shared_reverb_core": "device+0x3a80",
            "instances_are_distinct": True,
        },
        "implementation_identity": {
            "constructor_file_offset": "0x5af14",
            "configurator_file_offset": "0x5a6a8",
            "same_core_implementation": True,
            "same_state_instance": False,
        },
        "processing_topology": {
            "physical_input_mapping_offsets": ["device+0x5d74", "device+0x5d78"],
            "per_channel_object_stride": "0xcec",
            "block201_instances": 1,
            "block201_setup_inputs": 2,
            "block201_setup_outputs": 2,
            "private_core_bound_lane_indexes": [0, 1],
            "two_private_core_lanes_bound": True,
            "processing_assignment_swaps_active_slot_indexes": True,
            "active_slot_wire_id_replayed": 16,
            "simultaneous_hardware_input_processing": "UNPROVED_RUNTIME_GATE",
            "independent_private_reverb_parameter_sets": False,
        },
        "doubler_parameter_surface": {
            "record_fields": ["on", "lows", "width", "mix"],
            "native_state_tag": "godv",
            "shared_between_lanes": True,
            "block202_fields_accepted": False,
        },
    }


def analyze_factory_json(data):
    digest = _sha256(data)
    _require(digest == FACTORY_JSON_SHA256,
             "factory JSON SHA-256 differs: %s" % digest)
    try:
        records = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AnalysisError("factory JSON is invalid: %s" % error) from error
    _require(isinstance(records, list) and len(records) == 41,
             "factory JSON must contain 41 records")

    matches = [(index, record) for index, record in enumerate(records)
               if record.get("preset_name") == "Reverb"]
    _require(len(matches) == 1, "factory JSON must contain one Reverb record")
    index, record = matches[0]
    _require(index == 30, "Reverb record index differs: %d" % index)
    _require(record.get("voicefx") == EXPECTED_REVERB_VOICEFX,
             "Reverb record Voice FX fields differ")

    all_keys = _nested_keys(records)
    present_forbidden = sorted(FORBIDDEN_PRESET_KEYS.intersection(all_keys))
    _require(not present_forbidden,
             "shared-reverb fields occur in preset JSON: %s" %
             ", ".join(present_forbidden))

    return {
        "sha256": digest,
        "record_count": len(records),
        "reverb_named_record": {
            "index": index,
            "extracted_file_offset": record.get("_offset"),
            "preset_name": record["preset_name"],
            "voicefx": record["voicefx"],
        },
        "forbidden_shared_reverb_keys": sorted(FORBIDDEN_PRESET_KEYS),
        "forbidden_keys_present": present_forbidden,
    }


def analyze_fx_params_xml(data):
    digest = _sha256(data)
    _require(digest == FX_PARAMS_XML_SHA256,
             "FX parameter XML SHA-256 differs: %s" % digest)
    # The extracted resource is a pinned concatenation of two ComponentModel
    # documents followed by a Windows manifest, not one XML document.  Parse
    # each complete ComponentModel segment and keep hashing the whole resource.
    start_tag = b"<uc:ComponentModel"
    end_tag = b"</uc:ComponentModel>"
    roots = []
    cursor = 0
    while True:
        start = data.find(start_tag, cursor)
        if start < 0:
            break
        end = data.find(end_tag, start)
        _require(end >= 0, "unterminated ComponentModel resource")
        end += len(end_tag)
        try:
            roots.append(ET.fromstring(data[start:end]))
        except ET.ParseError as error:
            raise AnalysisError(
                "FX ComponentModel XML is invalid: %s" % error) from error
        cursor = end
    _require(len(roots) == 2,
             "expected two concatenated ComponentModel resources")

    namespace = {"uc": "http://www.presonus.com/xml/uc"}
    lists = {}
    for root in roots:
        for param_list in root.findall(".//uc:ParamList", namespace):
            lists[param_list.attrib["id"]] = [
                item.attrib["id"]
                for item in param_list.findall("uc:Param", namespace)
            ]
    _require(lists.get("VoiceOfGod") == ["on", "lows", "width", "mix"],
             "VoiceOfGod parameter list differs")
    _require(lists.get("VocalReverb") ==
             ["on", "size", "mix", "hp_freq", "predelay"],
             "VocalReverb parameter list differs")

    templates = {}
    for root in roots:
        templates.update({
            item.attrib["id"]: item.attrib
            for item in root.findall(".//uc:Template", namespace)
        })
    doubler = templates.get(DOUBLER_CLASS_ID)
    _require(doubler is not None, "Doubler class template is absent")
    _require(doubler.get("paramlist") == "VoiceOfGod" and
             doubler.get("classname") == "VoiceOfGodComponent",
             "Doubler class template differs")

    return {
        "sha256": digest,
        "component_model_documents": len(roots),
        "doubler_template": dict(sorted(doubler.items())),
        "doubler_storable_fields": lists["VoiceOfGod"],
        "shared_reverb_fields": lists["VocalReverb"],
        "component_models_are_distinct": True,
    }


def analyze(firmware, factory_json, fx_params_xml):
    return {
        "schema": "cp34-doubler-private-reverb-v2",
        "firmware": analyze_firmware(firmware),
        "uc_factory_preset_json": analyze_factory_json(factory_json),
        "uc_fx_parameter_model": analyze_fx_params_xml(fx_params_xml),
        "static_conclusions": {
            "architecture": (
                "Doubler/Transformer owns a private reverb-core instance; it "
                "uses the same constructor and configurator implementation as "
                "block 202 but not block 202's state object or send/return path"),
            "two_lane_contract": (
                "the device maps both physical input selectors into two "
                "processing objects, configures singleton block 201 with two "
                "inputs and two outputs, and binds private-core indexes 0 and "
                "1; this proves two structural lanes but not that stock "
                "runtime routing enables both hardware inputs simultaneously"),
            "shared_settings_limit": (
                "block 201 and model 0 are singletons: on/lows/width/mix is one "
                "shared setting set for both lanes, not two independently "
                "parameterised per-channel Doubler instances"),
            "preset_contract": (
                "the tagged library template identifies Doubler and its "
                "on/lows/width/mix surface; it is not itself the firmware-"
                "native Stat record and contains no vrvb, FXA, size, predelay, "
                "or hp_freq field"),
            "sample_rate": (
                "sample rate is runtime configuration, not a preset-record "
                "field; native model configuration rebuilds the private core "
                "for the device's current rate, including 96 kHz"),
            "save_implication": (
                "translate the template fields into native model-0 component "
                "201 state in its owning slot family only; do not duplicate "
                "component 201 into channel-strip-only slots or add block-202 "
                "reverb/send state; physical-input routing is independent"),
            "boundary": (
                "static structure does not prove physical nonvolatile commit, "
                "front-panel recall, audible output, or power-cycle survival"),
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware")
    parser.add_argument("factory_json")
    parser.add_argument("fx_params_xml")
    arguments = parser.parse_args(argv)
    try:
        report = analyze(
            Path(arguments.firmware).read_bytes(),
            Path(arguments.factory_json).read_bytes(),
            Path(arguments.fx_params_xml).read_bytes(),
        )
    except (OSError, AnalysisError, ValueError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
