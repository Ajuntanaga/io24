#!/usr/bin/env python3
"""Pin the firmware lifecycle of block 201's selected-model delegate.

This analyzer is offline-only.  It proves that the block constructor's model-0
selection reaches the work virtual, lazily constructs a delegate in embedded
storage, and writes its pointer to the block.  It also pins the reset-relocated
audio-root call into block 201, the block's virtual handoff to model 0, and the
complete model-5 Delay message/process/lane path.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from capstone import CS_ARCH_ARM, CS_MODE_THUMB, Cs


class AnalysisError(ValueError):
    """The supplied firmware differs from the pinned source."""


FIRMWARE_BASE = 0x60020000
FIRMWARE_SIZE = 1_104_448
FIRMWARE_SHA256 = (
    "65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a")
ITCM_FILE_TO_RUNTIME_DELTA = 0xD18

CODE_SLICES = {
    "block201_constructor": (
        0x591BC, 0x94,
        "d65cd9f8c37ab71204970a70eb842e96e12cd5648d81dc337389ae1a15ae8b60"),
    "model_selector": (
        0x55388, 0x48,
        "8f1ecb6e2ed75578c94d1d1fe641c3fd2ca39186a404bf7ce35546dcfdcaa96a"),
    "block201_primary_handler": (
        0x553D4, 0x88,
        "99fab8507b4eb5192b14224b6ba62f0ac495f481c9660ad5637dd3f326c01c58"),
    "parameter_handler": (
        0x50AF8, 0x2C,
        "c2ca241ae540c492e57b6aca68c64f28e417b5a2ebde78eefe9eb5aa1e84c48e"),
    "lazy_delegate_installer": (
        0x5F130, 0xBA,
        "37e1c3d9e4fe583055873bc1065783a344a667ee43e39fc6868c7650472d395a"),
    "work_virtual": (
        0x5F1F4, 0x58,
        "fe312f957ef1181e5fca7fb1653e7f144ab3b09c3610e83d150ea6e92f1c5ad2"),
    "three_member_workspace_call": (
        0x3F110, 0x2E,
        "cb7cca1b4c15fe3c25b0c99310dc10428df99c1ae80af02afc7d37c62842ac02"),
    "workspace_sizer_core": (
        0x3E608, 0xA2,
        "65ea67d780ed531f092742c96f01dc35b25d0ca28b3221adf178b1ab6c43274f"),
    "block201_itcm_process": (
        0x1A580, 0x278,
        "e53f8dc0d86058f2ed17576b374ad610f344fb6606e94d7c002c45a9d4db8f35"),
    "audio_root_itcm_call": (
        0x20546, 0x10,
        "66eb5517fdf9f3e5570009007d161ab070ad4499fc6d002eda97e5bd2e46ffb2"),
    "block201_primary_vtable": (
        0x10C6BC, 0x3C,
        "c5dd80f8b6eeeb7be825e8d94a9a832a95ccaf90a677a47bd2e21c751eb6b107"),
    "model0_primary_vtable": (
        0x10C890, 0x40,
        "631d77d1dd8d7d97941fa5ff72963eca1a17b8db8423269c55f7a35a1fec556f"),
    "sample_rate_eligibility_gate": (
        0x3DC20, 0x20,
        "fc21ea1d995f6473547276b6585dfef41cd7118e59cfddfcb5b809d4afe8c692"),
    "audio_root_call_gate": (
        0x1F39E, 0x38,
        "74d256729067c65bd32daedcf03e14545d85a19545fdc3adadac6978f1acb8b5"),
    "stereo_link_capture": (
        0x3F8F0, 0x24,
        "b69602a02398ea96118eb1fe25f1d346e0306e0979418054d03e1a6b0ad25153"),
    "block_transition_configuration": (
        0x4D6A8, 0x58,
        "3fb5b313e87cecba8446c0444fe1ee835a279c629dfc26c586ae795cfc1b48ae"),
    "block_setu_construction": (
        0x3DBEC, 0x34,
        "16d2a710c9e22339f219fc2aad33dd2ea73b19c18b168240e0f5973e00bfb0a9"),
    "model5_constructor_dispatch": (
        0x5F1D2, 0x18,
        "8b5622aea93be40b350c9df9ff7ab3f6d2bb883d87bfa3201454ab79f873a40e"),
    "model5_constructor": (
        0x56F34, 0x44,
        "b40e9f3c4888679c0698e854e5dce0fd8c0481ccb1311e3b45295999c85a1fd6"),
    "model5_tagged_handler": (
        0x57240, 0x34,
        "8e395ac9011518921d91d31090acf164ed94069883dce8ba1cf9c7ac633ea260"),
    "model5_process": (
        0x4EBD4, 0x12A,
        "d57ce9f225d075e145eceb6fdbe96faff76cdd230aba7605724b2cdeb5601f23"),
    "generic_delegate_handler": (
        0x5079C, 0x24,
        "71c782713c33c8bdfc935564c47ea381cd0739cfe4b001eb8a8103c437031d53"),
    "audio_root_buffer_descriptor": (
        0x1F39E, 0x36,
        "8269b30b2f0c961089fcaa42193098c17acba94ee57206d7d3dfb770e12a65b3"),
    "model5_primary_vtable": (
        0x10C7E8, 0x34,
        "1a5200b12ce4061daf15970618e443b3f990d731964bc5011968c83981c8fd16"),
}

INSTRUCTIONS = {
    "constructor_embedded_manager": (0x591BE, "add.w", "r1, r0, #0x50"),
    "constructor_manager_field": (0x591D4, "str", "r1, [r4, #0x10]"),
    "constructor_null_delegate": (0x59200, "str", "r5, [r4, #0x14]"),
    "constructor_model_zero": (0x59240, "mov", "r1, r5"),
    "selector_reads_delegate": (0x553A4, "ldr", "r2, [r4, #0x14]"),
    "selector_stores_requested_model": (0x553A6, "str", "r5, [r4, #0x18]"),
    "selector_requests_bypass": (0x553A8, "strb.w", "r3, [r4, #0x44]"),
    "selector_null_to_work": (0x553AC, "cbz", "r2, #0x600753b8"),
    "selector_reads_latched_bypass": (
        0x553AE, "ldrb.w", "r0, [r4, #0x39]"),
    "selector_waits_for_bypass": (0x553B2, "cbz", "r0, #0x600753c8"),
    "selector_reads_transition_countdown": (0x553B4, "ldr", "r3, [r4, #0x40]"),
    "selector_waits_for_countdown": (0x553B6, "cbnz", "r3, #0x600753c2"),
    "selector_work_slot": (0x553BC, "ldr", "r3, [r3, #0x34]"),
    "selector_calls_work": (0x553BE, "blx", "r3"),
    "primary_reads_tag": (0x553D6, "ldr", "r2, [r1]"),
    "primary_compares_vofx": (0x553F2, "cmp", "r2, r5"),
    "primary_nonselector_branch": (0x553F4, "bne", "#0x6007541c"),
    "primary_nonselector_to_generic": (0x5541E, "b.w", "#0x6007079c"),
    "primary_ringmod_model_id": (0x55432, "movs", "r1, #3"),
    "primary_ringmod_to_selector": (0x55436, "b.w", "#0x60075388"),
    "installer_reads_delegate": (0x5F134, "ldr", "r0, [r0, #0x14]"),
    "installer_reads_manager": (0x5F136, "ldr", "r5, [r4, #0x10]"),
    "installer_embedded_model": (0x5F158, "add.w", "r6, r5, #0x10"),
    "installer_stores_delegate": (0x5F170, "str", "r6, [r4, #0x14]"),
    "installer_requests_processing": (0x5F184, "strb.w", "r3, [r4, #0x44]"),
    "handler_reads_delegate": (0x50AFC, "ldr", "r0, [r0, #0x14]"),
    "handler_delegate_slot": (0x50B02, "ldr", "r3, [r3, #0x10]"),
    "handler_calls_delegate": (0x50B04, "blx", "r3"),
    "handler_then_checks_rebuild": (0x50B06, "ldrb.w", "r3, [r4, #0x44]"),
    "work_returns": (0x5F248, "pop", "{r4, r5, pc}"),
    "literal_pool_alignment": (0x5F24A, "nop", ""),
    "work_loads_first_literal": (0x5F214, "ldr", "r5, [pc, #0x34]"),
    "work_loads_second_literal": (0x5F218, "ldr", "r2, [pc, #0x34]"),
    "workspace_array_block201": (0x3F110, "add.w", "r3, r5, #0x11e0"),
    "workspace_array_count": (0x3F11C, "movs", "r2, #3"),
    "workspace_member_load": (0x3E620, "ldr", "r0, [r4, #4]!"),
    "workspace_member_size_slot": (0x3E626, "ldr", "r3, [r3, #0x18]"),
    "workspace_member_size_call": (0x3E628, "blx", "r3"),
    "workspace_takes_maximum": (0x3E62E, "mov", "r5, r0"),
    "workspace_destination_offset": (0x3E634, "movw", "r4, #0x11d0"),
    "sample_rate_gate_field": (0x3DC26, "movw", "r2, #0x5e71"),
    # Capstone decodes these isolated from the preceding IT block as MOVS;
    # the pinned surrounding slice retains the LS/HI predicates.
    "sample_rate_gate_true": (0x3DC38, "movs", "r1, #1"),
    "sample_rate_gate_false": (0x3DC3A, "movs", "r1, #0"),
    "sample_rate_gate_store": (0x3DC3C, "strb", "r1, [r5, r2]"),
    "audio_root_reads_flags": (0x3F8FA, "ldr.w", "lr, [r0, lr]"),
    "audio_root_masks_stereo_link": (0x3F902, "and", "lr, lr, #0x1000"),
    "audio_root_stores_stereo_link": (0x3F90E, "str.w", "lr, [sp, #0x28]"),
    "model5_dispatch_compare": (0x5F1D6, "cmp", "r1, #1"),
    "model5_constructor_vtable_store": (0x56F5E, "str", "r2, [r0]"),
    "generic_loads_delegate": (0x507AE, "ldr", "r0, [r5, #0x14]"),
    "generic_loads_tagged_handler": (0x507B6, "ldr", "r3, [r3]"),
    "generic_calls_tagged_handler": (0x507BC, "bx", "r3"),
    "model5_handler_reads_on": (0x5725C, "ldr", "r5, [r3, #0xc]!"),
    "model5_handler_stores_on": (0x57266, "str", "r5, [r0, #0x10]"),
    "model5_handler_stores_mix": (0x57268, "str", "r4, [r0, #0x14]"),
    "model5_handler_stores_feedback": (0x5726A, "str", "r1, [r0, #0x18]"),
    "model5_handler_stores_time": (0x5726C, "str", "r3, [r0, #0x1c]"),
    "model5_process_reads_descriptor_flag": (0x4EBD8, "ldr", "r3, [r1, #0x18]"),
    "model5_process_reads_on": (0x4EBE6, "ldr", "r5, [r0, #0x10]"),
    "model5_process_reads_mix": (0x4EC02, "vldr", "s11, [r0, #0x14]"),
    "model5_process_reads_feedback": (0x4EC62, "vldr", "s13, [r0, #0x18]"),
    "model5_process_feedback_accumulate": (0x4EC6C, "vfma.f32", "s15, s13, s14"),
    "model5_process_wet_gain": (0x4EC92, "vmul.f32", "s15, s11, s14"),
    "model5_process_dry_gain": (0x4ECA8, "vfma.f32", "s15, s14, s12"),
}

ITCM_INSTRUCTIONS = {
    "audio_root_loads_device": (0x20546, "ldr", "r3, [sp, #0xc]"),
    "audio_root_buffer_descriptor": (0x20548, "add", "r1, sp, #0x40"),
    "audio_root_block201_object": (0x2054A, "add.w", "r0, r3, #0x11e0"),
    "block_reads_target_bypass": (0x1A582, "ldrb.w", "ip, [r0, #0x44]"),
    "block_reads_latched_bypass": (0x1A588, "ldrb.w", "r3, [r0, #0x39]"),
    "block_reads_delegate": (0x1A59E, "ldr", "r0, [r6, #0x14]"),
    "block_loads_model_process_slot": (0x1A5B4, "ldr", "r3, [r3, #0xc]"),
    "block_calls_model_process": (0x1A5B6, "blx", "r3"),
    "audio_root_eligibility_field": (0x1F3A8, "movw", "r1, #0x5e71"),
    "audio_root_reads_eligibility": (0x1F3B6, "ldrb", "r1, [r4, r1]"),
    "audio_root_skips_if_ineligible": (0x1F3CC, "cbz", "r1, #0x1e6be"),
    "audio_root_reads_stereo_link": (0x1F3CE, "ldr", "r3, [sp, #0x28]"),
    "audio_root_calls_if_unlinked": (0x1F3D2, "beq.w", "#0x1f82e"),
    "descriptor_input_table": (0x1F3BA, "str", "r3, [sp, #0x40]"),
    "descriptor_output_table": (0x1F3BC, "str", "r3, [sp, #0x44]"),
    "descriptor_input_output_counts": (0x1F3C4, "strd", "r4, r0, [sp, #0x48]"),
    "descriptor_frame_workspace": (0x1F3C0, "strd", "r2, r5, [sp, #0x50]"),
    "descriptor_flags_clear": (0x1F3C8, "strd", "r3, r3, [sp, #0x58]"),
}

DIRECT_CALLS = {
    "constructor_calls_selector": (0x59248, 0x55388),
    "work_calls_lazy_installer": (0x5F1FA, 0x5F130),
    "model_zero_constructor": (0x5F18C, 0x5E270),
    "three_member_array_calls_workspace_sizer": (0x3F13A, 0x3E608),
    "installer_calls_model5_constructor": (0x5F1DC, 0x56F34),
}


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _u32(data, offset):
    _require(0 <= offset <= len(data) - 4,
             "u32 at %#x exceeds firmware" % offset)
    return struct.unpack_from("<I", data, offset)[0]


def _instruction(data, offset):
    decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    instructions = list(decoder.disasm(
        data[offset:offset + 4], FIRMWARE_BASE + offset, count=1))
    _require(len(instructions) == 1,
             "instruction at %#x does not decode" % offset)
    return instructions[0]


def _itcm_instruction(data, raw_offset):
    decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    runtime_address = raw_offset - ITCM_FILE_TO_RUNTIME_DELTA
    instructions = list(decoder.disasm(
        data[raw_offset:raw_offset + 4], runtime_address, count=1))
    _require(len(instructions) == 1,
             "ITCM instruction at %#x does not decode" % raw_offset)
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
            "offset": hex(offset), "size": size, "sha256": actual,
        }

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

    calls = {}
    for name, (offset, target_offset) in DIRECT_CALLS.items():
        instruction = _instruction(data, offset)
        expected = "#%#x" % (FIRMWARE_BASE + target_offset)
        _require(instruction.mnemonic == "bl" and
                 instruction.op_str == expected,
                 "%s differs: %s %s" %
                 (name, instruction.mnemonic, instruction.op_str))
        calls[name] = {
            "offset": hex(offset), "target_offset": hex(target_offset),
        }

    itcm_instructions = {}
    for name, (offset, mnemonic, operands) in ITCM_INSTRUCTIONS.items():
        instruction = _itcm_instruction(data, offset)
        _require((instruction.mnemonic, instruction.op_str) ==
                 (mnemonic, operands),
                 "%s differs: %s %s" %
                 (name, instruction.mnemonic, instruction.op_str))
        itcm_instructions[name] = {
            "raw_offset": hex(offset),
            "runtime_address": hex(offset - ITCM_FILE_TO_RUNTIME_DELTA),
            "mnemonic": instruction.mnemonic,
            "operands": instruction.op_str,
        }

    audio_root_call = _itcm_instruction(data, 0x2054E)
    _require((audio_root_call.mnemonic, audio_root_call.op_str) ==
             ("bl", "#0x19868"),
             "audio-root block-201 call differs: %s %s" %
             (audio_root_call.mnemonic, audio_root_call.op_str))

    block_process_pointer = _u32(data, 0x10C6C8)
    _require(block_process_pointer == 0x19869,
             "block-201 vtable +0x0c differs: %#x" % block_process_pointer)
    _require(block_process_pointer - 1 + ITCM_FILE_TO_RUNTIME_DELTA == 0x1A580,
             "block-201 process no longer maps to raw 0x1a580")

    model0_process_pointer = _u32(data, 0x10C89C)
    _require(model0_process_pointer == 0x1D491,
             "model-0 vtable +0x0c differs: %#x" % model0_process_pointer)
    _require(model0_process_pointer - 1 + ITCM_FILE_TO_RUNTIME_DELTA == 0x1E1A8,
             "model-0 process no longer maps to raw 0x1e1a8")

    model5_vtable = _u32(data, 0x571A8)
    _require(model5_vtable == FIRMWARE_BASE + 0x10C7E8,
             "model-5 constructor vtable differs: %#x" % model5_vtable)
    model5_handler_pointer = _u32(data, 0x10C7E8)
    _require(model5_handler_pointer == FIRMWARE_BASE + 0x57240 + 1,
             "model-5 tagged handler differs: %#x" % model5_handler_pointer)
    model5_process_pointer = _u32(data, 0x10C7F4)
    _require(model5_process_pointer == FIRMWARE_BASE + 0x4EBD4 + 1,
             "model-5 process differs: %#x" % model5_process_pointer)
    model5_tag = _u32(data, 0x57274)
    _require(model5_tag == 0x76656368,
             "model-5 tag differs: %#x" % model5_tag)

    work_pointer = _u32(data, 0x10C6F0)
    _require(work_pointer == FIRMWARE_BASE + 0x5F1F4 + 1,
             "block-201 vtable +0x34 differs: %#x" % work_pointer)

    first_literal = _u32(data, 0x5F24C)
    second_literal = _u32(data, 0x5F250)
    _require(first_literal == 0x49466163,
             "first work literal differs: %#x" % first_literal)
    _require(second_literal == 0x4D525370,
             "second work literal differs: %#x" % second_literal)

    vofx_tag = _u32(data, 0x55458)
    _require(vofx_tag == 0x5646784F,
             "VoFx primary-handler literal differs: %#x" % vofx_tag)

    sample_rate_limit_bits = _u32(data, 0x3DD7C)
    _require(sample_rate_limit_bits == 0x47BB8000,
             "sample-rate limit differs: %#x" % sample_rate_limit_bits)

    transition_ms = struct.unpack_from("<f", data, 0x4D708)[0]
    transition_ms_divisor = struct.unpack_from("<f", data, 0x4D70C)[0]
    _require(transition_ms == 40.0,
             "model transition duration differs: %r" % transition_ms)
    _require(transition_ms_divisor == 1000.0,
             "model transition divisor differs: %r" % transition_ms_divisor)
    sample_rate = 96000.0
    quantum = 512
    transition_blocks = int(
        math.floor(sample_rate * transition_ms /
                   quantum / transition_ms_divisor + 0.5))
    transition_duration_ms = transition_blocks * quantum / sample_rate * 1000.0

    return {
        "schema": "cp34-block201-delegate-lifecycle-v4",
        "firmware": {
            "size": len(data), "sha256": digest,
            "load_base": hex(FIRMWARE_BASE),
        },
        "code_slices": slices,
        "instructions": instructions,
        "itcm_instructions": itcm_instructions,
        "calls": calls,
        "delegate_lifecycle": {
            "constructor_path_installs_delegate": True,
            "initial_model": 0,
            "manager_field": "block+0x10",
            "manager_object_offset": "block+0x50",
            "delegate_object_offset": "block+0x60",
            "delegate_pointer_field": "block+0x14",
            "selector_requests_bypass": "block+0x44=1",
            "installer_requests_processing": "block+0x44=0",
            "plus_0x44_semantics":
                "target bypass state; 0 processes, 1 bypasses",
            "path": [
                "0x591bc constructor",
                "0x59248 -> 0x55388 select model 0",
                "null block+0x14 -> primary vtable+0x34",
                "0x5f1f4 -> 0x5f130 lazy installer",
                "0x5f18c -> 0x5e270 model-0 constructor",
                "0x5f170 stores block+0x60 at block+0x14",
                "0x5f184 clears block+0x44",
            ],
        },
        "parameter_handler": {
            "offset": "0x50af8",
            "delegate_forward_field": "block+0x14",
            "delegate_virtual_slot": "vtable+0x10",
            "forward_precedes_rebuild_check": True,
            "primary_setp_message_path": False,
            "sequencing_relevance": (
                "does not make ordinary model-state messages revisit the "
                "selector rebuild check"),
        },
        "message_routing": {
            "primary_handler": "0x553d4",
            "selector_tag": "VoFx",
            "selector_tag_u32": hex(vofx_tag),
            "selector_path": "0x553d4 -> 0x55388",
            "model_state_path": (
                "0x553d4 -> 0x5079c -> delegate vtable+0x00"),
            "model_state_revisits_rebuild_check": False,
            "selector_rebuild_conditions": [
                "block+0x14 delegate exists",
                "block+0x39 latched bypass is 1",
                "block+0x40 transition countdown is 0",
            ],
            "required_deferred_rebuild_trigger": (
                "replay VoFx selector after bypass transition"),
        },
        "literal_pool_after_work": {
            "work_return_offset": "0x5f248",
            "alignment_nop_offset": "0x5f24a",
            "first_literal_offset": "0x5f24c",
            "first_literal_u32": hex(first_literal),
            "second_literal_offset": "0x5f250",
            "second_literal_u32": hex(second_literal),
            "first_literal_is_code": False,
        },
        "three_member_workspace_sizer": {
            "call_offset": "0x3f13a",
            "function_offset": "0x3e608",
            "input_member_count": 3,
            "member_virtual_slot": "vtable+0x18",
            "operation": "maximum member workspace requirement",
            "destination_field": "device+0x11d0",
            "retains_member_pointers": False,
            "proves_signal_chain_installation": False,
        },
        "audio_execution": {
            "block201_process_virtual_slot": "vtable+0x0c",
            "block201_process_vtable_pointer": hex(block_process_pointer),
            "block201_process_raw_offset": "0x1a580",
            "selected_model_process_virtual_slot": "vtable+0x0c",
            "model0_process_vtable_pointer": hex(model0_process_pointer),
            "model0_process_raw_offset": "0x1e1a8",
            "block_process_reaches_model0_process": True,
            "bypass_state": {
                "target": "block+0x44",
                "latched": "block+0x39",
                "transition_countdown": "block+0x40",
                "processing_value": 0,
                "bypass_value": 1,
            },
        },
        "audio_root_binding": {
            "call_source_raw_offset": "0x20546",
            "direct_call_raw_offset": "0x2054e",
            "direct_call_runtime_target": "0x19868",
            "block201_object": "device+0x11e0",
            "buffer_descriptor": "stack+0x40",
            "scheduler_and_buffer_handoff_source_bound": True,
            "call_gate": {
                "sample_rate_eligibility_field": "device+0x5e71",
                "sample_rate_source_field": "device+0x5dc0",
                "sample_rate_limit_bits": hex(sample_rate_limit_bits),
                "sample_rate_rule_hz": "sample_rate <= 96000",
                "stereo_link_field": "device+0x5e58 bit 12",
                "call_condition":
                    "sample-rate eligible and stereo link clear",
            },
        },
        "model_replacement_transition": {
            "sample_rate_source": "Setu+0x08 -> block+0x24",
            "quantum_source": "Setu+0x0c -> block+0x28",
            "countdown_field": "block+0x3c",
            "nominal_duration_ms": transition_ms,
            "blocks_formula":
                "round(sample_rate * 40 / quantum / 1000)",
            "blocks_at_96khz_512": transition_blocks,
            "duration_at_96khz_512_ms": transition_duration_ms,
            "rebuild_trigger_order":
                "replayed selector invokes rebuild after bypass",
        },
        "model5_execution": {
            "model_id": 5,
            "tag": "vech",
            "constructor_raw_offset": "0x56f34",
            "primary_vtable": hex(model5_vtable),
            "tagged_handler_pointer": hex(model5_handler_pointer),
            "tagged_handler_raw_offset": "0x57240",
            "process_pointer": hex(model5_process_pointer),
            "process_raw_offset": "0x4ebd4",
            "parameter_fields": {
                "on": "model+0x10",
                "mix": "model+0x14",
                "feedback": "model+0x18",
                "time_seconds": "model+0x1c",
            },
            "message_path": [
                "block primary handler 0x553d4",
                "non-VoFx tag -> generic delegate handler 0x5079c",
                "block+0x14 -> model vtable+0x00",
                "model-5 handler 0x57240 accepts vech",
                "copies on/mix/feedback/time into model+0x10..+0x1c",
            ],
            "buffer_descriptor": {
                "input_pointer_table": "device+0x5068",
                "output_pointer_table": "device+0x5068",
                "input_count": 1,
                "output_count": 2,
                "frame_count": "audio callback descriptor +0x08",
                "workspace": "device+0x11d0",
                "flags_at_plus_0x18_and_0x1c": [0, 0],
                "in_place_pointer_table": True,
            },
            "process_equation": {
                "feedback_loop": "delay_write = input + feedback * delayed",
                "output": "mix * delayed + (1 - mix) * input",
                "feedback_wire_value_for_api_1_0": 0.5,
                "stationary_white_noise_gain_db_at_full_wet":
                    10.0 * math.log10(1.0 / (1.0 - 0.5 ** 2)),
            },
            "model5_state_and_lane_path_source_bound": True,
        },
        "conclusion": {
            "delegate_null_explains_live_inertness": False,
            "signal_path_execution_proven": True,
            "selector_state_replay_sequence_falsified": True,
            "required_host_sequence": (
                "selector -> wait for bypass -> selector replay -> model state"),
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
