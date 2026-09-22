#!/usr/bin/env python3
"""Pin the io24 Delay model's sample-rate configuration path.

This analyzer is intentionally offline-only.  It identifies what firmware
1.28 actually does when a ``Setu`` record reaches Voice FX model 5, calculates
the model's two rate-scaled buffer requests, and records the limit of that
evidence.  It does not access USB, modify firmware, or diagnose an unobserved
processor from a generic DSP-family anecdote.
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
FIRMWARE_SIZE = 0x12A694
FIRMWARE_SHA256 = (
    "790f668608448b7c9f244c360ad72e3c51f71b4e8a3d828eab0e08cd03b35de1")

CODE_SLICES = {
    "setu_builder": (
        0x3DBEC, 0x34,
        "16d2a710c9e22339f219fc2aad33dd2ea73b19c18b168240e0f5973e00bfb0a9"),
    "float_buffer_resize_allocator": (
        0x3CF90, 0x12C,
        "7f54ebf56aeee1be06dd11cc8c2a83f38512151d8e35c8e8b3b2567409611d6d"),
    "generic_delegate_handler": (
        0x5079C, 0x24,
        "71c782713c33c8bdfc935564c47ea381cd0739cfe4b001eb8a8103c437031d53"),
    "block201_model_selector": (
        0x55388, 0x48,
        "8f1ecb6e2ed75578c94d1d1fe641c3fd2ca39186a404bf7ce35546dcfdcaa96a"),
    "block201_primary_handler": (
        0x553D4, 0x88,
        "99fab8507b4eb5192b14224b6ba62f0ac495f481c9660ad5637dd3f326c01c58"),
    "block201_lazy_delegate_installer": (
        0x5F130, 0xBA,
        "37e1c3d9e4fe583055873bc1065783a344a667ee43e39fc6868c7650472d395a"),
    "block201_work_virtual": (
        0x5F1F4, 0x58,
        "fe312f957ef1181e5fca7fb1653e7f144ab3b09c3610e83d150ea6e92f1c5ad2"),
    "block201_transition_configuration": (
        0x4D6A8, 0x58,
        "3fb5b313e87cecba8446c0444fe1ee835a279c629dfc26c586ae795cfc1b48ae"),
    "delay_constructor": (
        0x56F34, 0x278,
        "7ae02ab75d131484d1c3ff8465c4382a9608d63c4398bb951b4a05732911ecc5"),
    "delay_capacity_update": (
        0x571D4, 0x66,
        "3134ff0bed17ec440cbd4037bf8b511e7b735713c19f657175ebaeb4def10605"),
    "delay_tagged_handler": (
        0x57240, 0x34,
        "8e395ac9011518921d91d31090acf164ed94069883dce8ba1cf9c7ac633ea260"),
    "delay_runtime_config": (
        0x572D4, 0xC6,
        "37be0f521d8ec7b4d10f6b7822cf3f087fdc912934e686e91ab2fedd6ee78a15"),
    "delay_process": (
        0x4EBD4, 0x12A,
        "d57ce9f225d075e145eceb6fdbe96faff76cdd230aba7605724b2cdeb5601f23"),
    "sample_rate_eligibility_gate": (
        0x3DC20, 0x20,
        "fc21ea1d995f6473547276b6585dfef41cd7118e59cfddfcb5b809d4afe8c692"),
    "delay_workspace_size": (
        0x4D674, 0x04,
        "a7ddd513d149ea16fdd4db3f82267f83087aeaddd06b5dde5468adb704205fc4"),
    "default_allocator_adapter": (
        0x3CE68, 0x16,
        "e6bcf5e208101b25c637e62a12df534f7113b1a47c26e34211ac568847a1bfb7"),
    "sbrk_and_literals": (
        0x36130, 0x30,
        "ca0dd631f2fde077f2fc86f6d31039d0347887f5dc995a249ff2c1317f59af63"),
    "reset_ram_tables": (
        0x300, 0x34,
        "ea048f2587f6b58ff1c894e23ee40976d1dac19b2fc83c4519b82f32d0834453"),
    "default_allocator_object": (
        0x129C94, 0x18,
        "9902a1f14a69ad9e69810bfa86fb9993948c6ec874f7e59b3677e8e6bd690d89"),
    "default_allocator_vtable": (
        0x6D354, 0x18,
        "b67d485c95ae93e586c88f979cae2b9c49d438da41be3331bb8d45de922918b7"),
}

INSTRUCTIONS = {
    "generic_dispatches_setu_to_owner_config": (
        0x507AA, "bl", "#0x60070780"),
    "generic_loads_selected_delegate": (
        0x507AE, "ldr", "r0, [r5, #0x14]"),
    "generic_calls_selected_delegate_handler": (
        0x507BC, "bx", "r3"),
    "primary_compares_vofx": (
        0x553F2, "cmp", "r2, r5"),
    "selector_reads_active_delegate": (
        0x553A4, "ldr", "r2, [r4, #0x14]"),
    "selector_stores_requested_model": (
        0x553A6, "str", "r5, [r4, #0x18]"),
    "selector_requests_bypass": (
        0x553A8, "strb.w", "r3, [r4, #0x44]"),
    "selector_reads_latched_bypass": (
        0x553AE, "ldrb.w", "r0, [r4, #0x39]"),
    "selector_reads_transition_countdown": (
        0x553B4, "ldr", "r3, [r4, #0x40]"),
    "selector_loads_work_virtual": (
        0x553BC, "ldr", "r3, [r3, #0x34]"),
    "selector_calls_work_virtual": (
        0x553BE, "blx", "r3"),
    "work_calls_lazy_installer": (
        0x5F1FA, "bl", "#0x6007f130"),
    "installer_stores_new_delegate": (
        0x5F170, "str", "r6, [r4, #0x14]"),
    "installer_requests_processing": (
        0x5F184, "strb.w", "r3, [r4, #0x44]"),
    "work_returns_after_installer": (
        0x5F248, "pop", "{r4, r5, pc}"),
    "config_forward_loads_vtable": (
        0x50780, "ldr", "r3, [r0]"),
    "config_forward_loads_slot_0x30": (
        0x50782, "ldr", "r3, [r3, #0x30]"),
    "config_forward_tail_calls_slot": (
        0x50784, "bx", "r3"),
    "delay_setu_tail_forwards_to_config": (
        0x57256, "b.w", "#0x60070780"),
    "delay_config_reads_sample_rate": (
        0x572D6, "ldr", "r3, [r1, #8]"),
    "delay_config_reads_quantum": (
        0x572DA, "ldr", "r6, [r1, #0xc]"),
    "delay_config_stores_sample_rate": (
        0x572DC, "str.w", "r3, [r0, #0xc0]"),
    "delay_config_stores_first_capacity": (
        0x57326, "str", "r1, [r4, #0x40]"),
    "delay_config_stores_second_capacity": (
        0x5734C, "str.w", "r1, [r4, #0x8c]"),
    "delay_state_recomputes_capacity": (
        0x57270, "b.w", "#0x600771d4"),
    "buffer_resize_multiplies_requested_elements": (
        0x3CF96, "mul", "r5, r1, r3"),
    "buffer_resize_adds_allocator_overhead": (
        0x3CFF2, "add.w", "r2, r5, #0x20"),
    "buffer_resize_converts_floats_to_bytes": (
        0x3CFF8, "lsls", "r2, r2, #2"),
    "buffer_resize_calls_allocator": (
        0x3D00C, "blx", "r3"),
    "buffer_resize_checks_allocator_result": (
        0x3D010, "cbz", "r0, #0x6005d032"),
    "buffer_resize_null_sets_length_zero": (
        0x3D032, "str", "r0, [r4, #0x14]"),
    "delay_process_loads_buffer_object": (
        0x4EC46, "ldr.w", "r2, [lr, #0x20]"),
    "delay_process_loads_logical_length": (
        0x4EC50, "ldr", "r3, [r2, #0x14]"),
    "delay_process_first_divides_by_length": (
        0x4EC74, "sdiv", "fp, r1, r3"),
    "delay_process_second_divides_by_length": (
        0x4EC84, "sdiv", "r1, sl, r3"),
    "delay_reports_zero_shared_workspace": (
        0x4D674, "movs", "r0, #0"),
    "default_resource_realloc_moves_pointer": (
        0x3CE70, "mov", "r0, r1"),
    "default_resource_realloc_moves_size": (
        0x3CE72, "mov", "r1, r2"),
    "default_resource_realloc_calls_runtime": (
        0x3CE74, "b.w", "#0x600801f8"),
}

SETU_TAG = 0x53657475
DELAY_MODEL = 5
DELAY_VTABLE_RAW_OFFSET = 0x10C7E8
DELAY_CONFIG_VTABLE_SLOT_RAW_OFFSET = DELAY_VTABLE_RAW_OFFSET + 0x30
DELAY_CONFIG_RAW_OFFSET = 0x572D4
DELAY_MAX_SECONDS_LITERAL_RAW_OFFSET = 0x5739C
DELAY_SECONDARY_SECONDS = 0.25
DELAY_ALLOCATOR_OVERHEAD_FLOATS = 32
BLOCK201_TRANSITION_MS = 40.0
HOST_SELECTOR_SETTLE_MS = 60.0
DELAY_WORKSPACE_VTABLE_SLOT_RAW_OFFSET = DELAY_VTABLE_RAW_OFFSET + 0x18
DELAY_WORKSPACE_SIZE_RAW_OFFSET = 0x4D674
DEFAULT_RESOURCE_GLOBAL = 0x20216658
DEFAULT_RESOURCE_OBJECT = 0x202B0E54
DEFAULT_RESOURCE_OBJECT_RAW_OFFSET = 0x129C94
DEFAULT_RESOURCE_VTABLE = 0x6008D354
DEFAULT_RESOURCE_VTABLE_RAW_OFFSET = 0x6D354
DEFAULT_RESOURCE_REALLOC_RAW_OFFSET = 0x3CE70
SBRK_RAW_OFFSET = 0x36130
SBRK_CURRENT_POINTER = 0x20215D18
SBRK_HEAP_START = 0x202B1860
SBRK_HEAP_LIMIT = 0x202B1860


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _u32(data, offset):
    _require(0 <= offset <= len(data) - 4,
             "u32 at %#x exceeds firmware" % offset)
    return struct.unpack_from("<I", data, offset)[0]


def _f32(data, offset):
    _require(0 <= offset <= len(data) - 4,
             "f32 at %#x exceeds firmware" % offset)
    return struct.unpack_from("<f", data, offset)[0]


def _instruction(data, offset):
    decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    instructions = list(decoder.disasm(
        data[offset:offset + 4], FIRMWARE_BASE + offset, count=1))
    _require(len(instructions) == 1,
             "instruction at %#x does not decode" % offset)
    return instructions[0]


def _f32_mul(left, right):
    """Match the single-precision multiply used before VCVT in firmware."""
    return struct.unpack("<f", struct.pack("<f", float(left) * float(right)))[0]


def buffer_plan(rate_hz, quantum):
    _require(rate_hz > 0, "sample rate must be positive")
    _require(quantum >= 0, "quantum must be non-negative")
    max_seconds = 0.3499999940395355
    first_capacity = math.trunc(_f32_mul(rate_hz, max_seconds)) + 2
    second_capacity = math.trunc(
        _f32_mul(rate_hz, DELAY_SECONDARY_SECONDS)) + 2
    first_request_samples = first_capacity + quantum
    second_request_samples = second_capacity + quantum
    first_allocator_bytes = (
        first_request_samples + DELAY_ALLOCATOR_OVERHEAD_FLOATS) * 4
    second_allocator_bytes = (
        second_request_samples + DELAY_ALLOCATOR_OVERHEAD_FLOATS) * 4
    return {
        "sample_rate_hz": rate_hz,
        "quantum_frames": quantum,
        "first_capacity_samples": first_capacity,
        "second_capacity_samples": second_capacity,
        "first_request_samples": first_request_samples,
        "second_request_samples": second_request_samples,
        "first_allocator_bytes": first_allocator_bytes,
        "second_allocator_bytes": second_allocator_bytes,
        "total_allocator_bytes": (
            first_allocator_bytes + second_allocator_bytes),
    }


def analyze_firmware(data, quantum=512):
    digest = _sha256(data)
    _require(len(data) == FIRMWARE_SIZE,
             "firmware size differs: %d" % len(data))
    _require(digest == FIRMWARE_SHA256,
             "firmware SHA-256 differs: %s" % digest)
    initial_stack_pointer = _u32(data, 0x00)
    reset_vector = _u32(data, 0x04)
    _require(initial_stack_pointer == 0x20000600,
             "Cortex-M initial stack pointer differs: %#x" %
             initial_stack_pointer)
    _require(reset_vector == 0x60020335,
             "Thumb reset vector differs: %#x" % reset_vector)

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

    _require(_u32(data, 0x50798) == SETU_TAG,
             "generic config-forward Setu literal differs")
    _require(_u32(data, 0x507C0) == SETU_TAG,
             "generic delegate Setu literal differs")
    _require(_u32(data, 0x57278) == SETU_TAG,
             "Delay Setu literal differs")
    _require(_u32(data, 0x55458) == 0x5646784F,
             "block-201 VoFx literal differs")
    _require(_u32(data, 0x6D370) == FIRMWARE_BASE + 0x3CF90 + 1,
             "Delay float-buffer resize vtable entry differs")
    config_pointer = _u32(data, DELAY_CONFIG_VTABLE_SLOT_RAW_OFFSET)
    _require(config_pointer == FIRMWARE_BASE + DELAY_CONFIG_RAW_OFFSET + 1,
             "Delay vtable +0x30 differs: %#x" % config_pointer)
    workspace_pointer = _u32(data, DELAY_WORKSPACE_VTABLE_SLOT_RAW_OFFSET)
    _require(workspace_pointer ==
             FIRMWARE_BASE + DELAY_WORKSPACE_SIZE_RAW_OFFSET + 1,
             "Delay vtable +0x18 differs: %#x" % workspace_pointer)

    # The complete vendor package, unlike the old 0x10da40-byte truncation,
    # includes the initialized-RAM source that owns the default allocator
    # object. Pin both reset copies and their mapped object/vtable before using
    # them as evidence about the Delay allocation route.
    _require((_u32(data, 0x304), _u32(data, 0x308), _u32(data, 0x30C)) ==
             (0x6012D940, 0x20003A00, 0x1C300),
             "primary initialized-RAM copy differs")
    _require((_u32(data, 0x310), _u32(data, 0x314), _u32(data, 0x318)) ==
             (0x60149C40, 0x202B0E00, 0xA4D),
             "secondary initialized-RAM copy differs")
    _require((_u32(data, 0x31C), _u32(data, 0x320),
              _u32(data, 0x324), _u32(data, 0x328),
              _u32(data, 0x32C), _u32(data, 0x330)) ==
             (0x20003000, 0x99C, 0x20200080, 0xB0D7C,
              0x202BF800, 0x740),
             "zero-initialized RAM ranges differ")
    _require(_u32(data, DEFAULT_RESOURCE_OBJECT_RAW_OFFSET) ==
             DEFAULT_RESOURCE_VTABLE,
             "default resource object vtable differs")
    _require(_u32(data, DEFAULT_RESOURCE_VTABLE_RAW_OFFSET + 0x0C) ==
             FIRMWARE_BASE + DEFAULT_RESOURCE_REALLOC_RAW_OFFSET + 1,
             "default resource realloc vtable entry differs")
    _require(_u32(data, 0x3D0C0) == DEFAULT_RESOURCE_GLOBAL,
             "default resource global literal differs")
    _require(_u32(data, 0x3D0CC) == DEFAULT_RESOURCE_OBJECT,
             "default resource object literal differs")
    _require((_u32(data, 0x36154), _u32(data, 0x36158),
              _u32(data, 0x3615C)) ==
             (SBRK_CURRENT_POINTER, SBRK_HEAP_LIMIT, SBRK_HEAP_START),
             "sbrk heap literals differ")

    max_seconds = _f32(data, DELAY_MAX_SECONDS_LITERAL_RAW_OFFSET)
    _require(max_seconds == 0.3499999940395355,
             "Delay maximum literal differs: %r" % max_seconds)
    sample_rate_limit = _f32(data, 0x3DD7C)
    _require(sample_rate_limit == 96000.0,
             "Voice FX sample-rate limit differs: %r" % sample_rate_limit)
    transition_ms = _f32(data, 0x4D708)
    _require(transition_ms == BLOCK201_TRANSITION_MS,
             "block-201 transition duration differs: %r" % transition_ms)
    _require(_f32(data, 0x4D70C) == 1000.0,
             "block-201 transition divisor differs")
    _require(_u32(data, 0x10C6F0) == FIRMWARE_BASE + 0x5F1F4 + 1,
             "block-201 work virtual differs")

    at_48k = buffer_plan(48000, quantum)
    at_96k = buffer_plan(96000, quantum)

    architecture_markers = {
        marker: marker in data
        for marker in (b"SigmaDSP", b"ADAU", b"SHARC", b"Blackfin")
    }

    return {
        "schema": "cp34-delay-rate-config-v3",
        "firmware": {
            "size": len(data),
            "sha256": digest,
            "load_base": hex(FIRMWARE_BASE),
            "architecture_evidence": {
                "format": "complete UC 4.7.2 ARM Cortex-M vendor package",
                "initial_stack_pointer": hex(initial_stack_pointer),
                "reset_vector": hex(reset_vector),
                "reset_vector_thumb_bit": reset_vector & 1,
                "vfp_in_delay_config": True,
            },
        },
        "code_slices": slices,
        "instructions": instructions,
        "setu_path": {
            "tag": "Setu",
            "block_config_virtual_slot": "vtable+0x30",
            "selected_model_handler_virtual_slot": "vtable+0x00",
            "delay_config_virtual_slot": "vtable+0x30",
            "delay_config_raw_offset": hex(DELAY_CONFIG_RAW_OFFSET),
            "runs_on_each_setu": True,
        },
        "delay_buffers": {
            "sample_rate_field": "model+0xc0",
            "quantum_source": "Setu+0x0c",
            "first_capacity_field": "model+0x40",
            "first_max_seconds": max_seconds,
            "second_capacity_field": "model+0x8c",
            "second_max_seconds": DELAY_SECONDARY_SECONDS,
            "allocator_overhead_floats_per_buffer":
                DELAY_ALLOCATOR_OVERHEAD_FLOATS,
            "resize_raw_offset": "0x3cf90",
            "allocator_request_formula":
                "(requested_samples + 32) * sizeof(float)",
            "at_48khz": at_48k,
            "at_96khz": at_96k,
            "additional_allocator_bytes_48_to_96": (
                at_96k["total_allocator_bytes"] -
                at_48k["total_allocator_bytes"]),
            "state_change_rechecks_capacity": True,
        },
        "allocation_failure_path": {
            "allocator_null_branch_raw_offset": "0x3d010",
            "null_result_sets_logical_length_zero": True,
            "logical_length_field": "buffer+0x14",
            "process_length_load_raw_offset": "0x4ec50",
            "process_uses_length_as_divisor": True,
            "first_divide_raw_offset": "0x4ec74",
            "length_zero_guard_between_load_and_first_divide": False,
            "failure_is_viable_fault_path": True,
            "actual_96khz_allocation_failure_established": False,
            "bounded_interpretation": (
                "If resize allocation returns null, the buffer length becomes "
                "zero and Delay processing reaches SDIV with that value. This "
                "can trap when divide-by-zero trapping is enabled; otherwise "
                "the resulting index arithmetic is not safely bounded. The "
                "trace does not prove that the 96 kHz request returns null."),
        },
        "allocator_context": {
            "delay_workspace_virtual_slot": "vtable+0x18",
            "delay_workspace_size_raw_offset":
                hex(DELAY_WORKSPACE_SIZE_RAW_OFFSET),
            "delay_reported_shared_workspace_bytes": 0,
            "default_resource_global": hex(DEFAULT_RESOURCE_GLOBAL),
            "default_resource_object": hex(DEFAULT_RESOURCE_OBJECT),
            "default_resource_object_raw_offset":
                hex(DEFAULT_RESOURCE_OBJECT_RAW_OFFSET),
            "default_resource_vtable": hex(DEFAULT_RESOURCE_VTABLE),
            "default_resource_realloc_raw_offset":
                hex(DEFAULT_RESOURCE_REALLOC_RAW_OFFSET),
            "sbrk_raw_offset": hex(SBRK_RAW_OFFSET),
            "sbrk_current_pointer": hex(SBRK_CURRENT_POINTER),
            "sbrk_heap_start": hex(SBRK_HEAP_START),
            "sbrk_heap_limit": hex(SBRK_HEAP_LIMIT),
            "sbrk_static_extendable_bytes":
                SBRK_HEAP_LIMIT - SBRK_HEAP_START,
            "initialized_ram_copies": [
                {"source": "0x6012d940", "destination": "0x20003a00",
                 "length": 0x1C300},
                {"source": "0x60149c40", "destination": "0x202b0e00",
                 "length": 0xA4D},
            ],
            "bounded_interpretation": (
                "Delay reports no shared workspace and reaches the runtime "
                "reallocator through the initialized default resource. The "
                "static sbrk start and limit are equal, but 48 kHz Delay is "
                "empirically functional; therefore the live allocator arena "
                "and the actual 96 kHz allocation outcome remain unresolved."),
        },
        "sample_rate_gate": {
            "maximum_hz": sample_rate_limit,
            "rule": "Voice FX audio root is eligible at sample_rate <= 96000",
        },
        "host_quiesce_transition": {
            "selector_tag": "VoFx",
            "safe_replacement_model": 0,
            "active_delegate_field": "block+0x14",
            "requested_model_field": "block+0x18",
            "target_bypass_field": "block+0x44",
            "latched_bypass_field": "block+0x39",
            "transition_countdown_field": "block+0x40",
            "nominal_transition_ms": transition_ms,
            "host_selector_settle_ms": HOST_SELECTOR_SETTLE_MS,
            "post_ack_audio_settle_formula":
                "2 * old_rate_quantum_frames / old_rate_hz",
            "post_ack_audio_settle_ms_at_48khz_512":
                2.0 * 512 / 48000.0 * 1000.0,
            "first_selector_action":
                "store requested model and request bypass",
            "replay_preconditions": [
                "latched bypass is 1",
                "transition countdown is 0",
            ],
            "replayed_selector_action": (
                "call work virtual synchronously; installer stores the new "
                "delegate at block+0x14 before returning"),
            "safe_host_order": [
                "send VoFx model 0 at the old rate",
                "wait 60 ms for the nominal 40 ms bypass transition",
                "replay VoFx model 0 and receive its transport reply",
                "send complete model-0 Off state",
                "wait two complete audio quanta at the old rate",
                "only then request 96 kHz",
            ],
            "usb_reply_is_audio_frame_fence_proven": False,
            "bounded_interpretation": (
                "The second selector's firmware path stores the model-0 "
                "delegate before its handler returns. The USB reply is not "
                "claimed as an audio-frame fence, so the Host also waits "
                "two complete old-rate audio quanta before changing the "
                "rate."),
        },
        "architecture_string_markers": {
            key.decode("ascii"): value
            for key, value in architecture_markers.items()
        },
        "conclusion": {
            "forty_eight_first_skips_96k_reconfiguration": False,
            "rate_scaled_buffer_growth_source_bound": True,
            "unchecked_allocation_failure_path_source_bound": True,
            "sigma_dsp_mips_overrun_established": False,
            "allocation_failure_established": False,
            "exact_reset_cause": "UNRESOLVED",
            "safe_host_policy": (
                "never select hardware model 5 at 96 kHz; replace it with "
                "model 0 through the selector-replay, 60 ms selector barrier "
                "and two-quantum audio barrier before an upward rate "
                "transition, then run "
                "the same Delay controls in the bounded Linux Host insert"),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware", type=Path)
    parser.add_argument("--quantum", type=int, default=512)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze_firmware(args.firmware.read_bytes(), quantum=args.quantum)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
