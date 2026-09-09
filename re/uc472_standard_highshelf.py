#!/usr/bin/env python3
"""Recover the exact UC 4.7.2 Standard high-shelf coefficient route.

The analyzer is deliberately version-local, bounded, and static.  It accepts
only the retained ``dspusbdevice.dll`` and retained factory extraction, checks
the ``eqtype4`` descriptor and Standard component call path, and disassembles
only the listed selector/recompute/output regions.  Vendor code is never
loaded or executed.  No USB, audio, Wine, firmware, network, or user-cache
surface is touched.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

from capstone import CS_ARCH_X86, CS_MODE_64, Cs


RE_DIR = Path(__file__).resolve().parent
if str(RE_DIR) not in sys.path:
    sys.path.insert(0, str(RE_DIR))

from cp34_host_queue_inventory import (  # noqa: E402
    AnalysisError as PeAnalysisError,
    _parse_pe,
)
import cp34_uc5_serializer_comparison as pe_helpers  # noqa: E402


class AnalysisError(ValueError):
    """An input or bounded instruction region differs from retained UC 4.7.2."""


DSP_SIZE = 4_979_672
DSP_SHA256 = "de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28"
FACTORY_SIZE = 47_158
FACTORY_SHA256 = "89b0572dd760b77831d012e2db0568b4f4eeb158985a4ca86126be28e934c73d"
IMAGE_BASE = 0x180000000

DESCRIPTOR_TABLE = 0x1800ED690
DESCRIPTOR_COUNT = 25
EQTYPE4_DESCRIPTOR = 0x1800EDE48
BRIEF_EQTYPE4_DESCRIPTOR = 0x1800EF2E8
SELECTOR_TABLE = 0x1800E81E0
STANDARD_VTABLE = 0x180434320
SELECTOR_MAPPER_SLOT = STANDARD_VTABLE + 0xC0

POW_THUNK = 0x1800D3556
POW_IAT = 0x1800E4508
PAIRED_TRIG = 0x1800D15C0


# Each region is an exact contiguous instruction interval.  Table data is
# checked separately and is never offered to the disassembler.
REGIONS = (
    ("standard_constructor", 0x180048AA3, 0x13B,
     "245158983c028d4f90962e284973f248ac54c087b348be117976249be750747e"),
    ("selector_mapper", 0x180015C60, 0x19,
     "1e4593e76cb322f38007d5b78ae91529740577224fa0b03cdf3cacf1c5e8f0c9"),
    ("parameter_partition", 0x180015CD0, 0xB4,
     "8a231cf9ca9246ade53e005503145d1df9065ae242662f5004e56d983f7eb1fe"),
    ("eqtype_case", 0x180015D84, 0x1B,
     "b8a662fc33306c7248409eed21d11d04808ece0df870658dfc1b85b1bad3e729"),
    ("standard_band_caller", 0x1800160C0, 0x20,
     "4258046cacff760f9151d9ecc9e4944c55f4487b8e1998e6f7e557a5582d9073"),
    ("standard_output_call", 0x1800160E0, 0x6C,
     "37767d4a8a1ba552eae9fece106df2cec6d2649d9aa50b6c00c1d92201cb2987"),
    ("setter_inputs_and_full_call", 0x180016872, 0x87,
     "eebac494d2eef63b6815420fd40092556da7798ecd2564743dde0d193b291327"),
    ("sample_rate_scale", 0x18000F7D6, 0x24,
     "8c85c449da2dd3ef3376936de68469512ca14f21113a5088f123eab54ef65f94"),
    ("full_dispatch", 0x18000F922, 0x34,
     "cfdb82f7118534e56b6d824a171c32265d97578be37e491209fda7ffa0085e3c"),
    ("full_trig_dispatch", 0x18000FF44, 0x93,
     "0ca394fe5e55deaebd696fc01e75d448d6d7f0573194bf0aea23ce030e869127"),
    ("full_highshelf_shared_tail", 0x18001033B, 0x3B,
     "319c4ee56e35e71e40b1a74213a1a404420c86655b0078907f3420b0ac03612e"),
    ("full_highshelf", 0x18001039D, 0xD3,
     "14de852983923b54e3a35c1b8e93d2b21e41ebf987a1fdfe3bf1c7477bc416a1"),
    ("full_store", 0x180010470, 0x97,
     "1870663796e536f110cb233cb778e90f3f98e4e30cad961b40c22e05658069a7"),
    ("incremental_trig_dispatch", 0x180017036, 0xB5,
     "96ffac0933107fc1d3abb53019f8d540addf5c4bf2a00d3cd372d00e1bbabb0c"),
    ("incremental_highshelf", 0x1800175CD, 0x14A,
     "8f2f6a50b5c313e07dc0926f47d782cee1d09655ad749d7c521e58800d97ebe2"),
    ("incremental_store", 0x180017717, 0x7C,
     "8190ae3013d9ac666b60c60423123efc1277ce80a73d65e452b1cb53f580ab50"),
    ("output_conversion", 0x180014396, 0x59,
     "818d0df14dacb8b415737b2e1a29c510b8989712421aad8c65a30bcf5223b46d"),
    ("paired_trig_entry", 0x1800D15C0, 0x49,
     "e3314a74d1d3fdaa7cdf453d3b600873d5890c7ae4edb66bbea1f94ee316b3ec"),
)


FULL_OUTER_TARGET_RVAS = (
    0xF956, 0xF9B2, 0xFAEB, 0xFB8C, 0xFC36, 0xFD10, 0xFE4C,
    0xFF44, 0xFC2E, 0xFD08, 0xFA11, 0xFA85, 0x1049C,
)
FULL_OUTER_MAP = bytes.fromhex(
    "000102030405060707070707070c0c08090707070707070707070a0b07070707")
FULL_INNER_TARGET_RVAS = (
    0x10192, 0x101F7, 0xFFD7, 0x1028A, 0x1039D, 0x1002D,
    0x10087, 0x10136, 0x10263, 0x10376, 0x10454,
)
FULL_INNER_MAP = bytes.fromhex(
    "00010a0a0a0203040506070a0a0a0a0809000102000100010a0a08090809")

INCREMENTAL_OUTER_TARGET_RVAS = (
    0x16951, 0x169BD, 0x16B19, 0x16BDC, 0x16CAF, 0x16DCD,
    0x16F2C, 0x17036, 0x16CA7, 0x16DC5, 0x16A24, 0x16AA5, 0x17745,
)
INCREMENTAL_INNER_TARGET_RVAS = (
    0x1733C, 0x173C1, 0x170EB, 0x17473, 0x175CD, 0x17163,
    0x171DC, 0x172C7, 0x1744B, 0x175A5, 0x176FD,
)

PARAMETER_CASE_TARGET_RVAS = (
    0x15D84, 0x15DAE, 0x15DC3, 0x15DD8, 0x15DED, 0x15E0C,
)


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _identity(label, data, size, expected_sha256):
    _require(len(data) == size, "%s size differs: %d" % (label, len(data)))
    digest = hashlib.sha256(data).hexdigest()
    _require(digest == expected_sha256,
             "%s SHA-256 differs: %s" % (label, digest))
    return {"sha256": digest, "size": len(data)}


def _section_bytes(image_base, sections, address, size):
    try:
        return pe_helpers._section_bytes(image_base, sections, address, size)
    except pe_helpers.AnalysisError as error:
        raise AnalysisError(str(error)) from error


def _require_bytes(image_base, sections, address, expected_hex):
    try:
        pe_helpers._require_bytes(image_base, sections, address, expected_hex)
    except pe_helpers.AnalysisError as error:
        raise AnalysisError(str(error)) from error


def _require_direct_target(image_base, sections, address, target):
    try:
        pe_helpers._require_direct_target(
            image_base, sections, address, target)
    except pe_helpers.AnalysisError as error:
        raise AnalysisError(str(error)) from error


def _read_u64(image_base, sections, address):
    return struct.unpack("<Q", _section_bytes(
        image_base, sections, address, 8))[0]


def _read_u32s(image_base, sections, address, count):
    return struct.unpack(
        "<" + "I" * count,
        _section_bytes(image_base, sections, address, count * 4),
    )


def _f32(value):
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _f32_bits(value):
    return "0x%08x" % struct.unpack("<I", struct.pack("<f", value))[0]


def _bounded_regions(image_base, sections):
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    result = []
    for name, start, size, expected_sha256 in REGIONS:
        code = _section_bytes(image_base, sections, start, size)
        digest = hashlib.sha256(code).hexdigest()
        _require(digest == expected_sha256,
                 "%s bounded-region SHA-256 differs: %s" % (name, digest))
        instructions = list(decoder.disasm(code, start))
        consumed = sum(instruction.size for instruction in instructions)
        _require(consumed == size,
                 "%s does not end on an instruction boundary" % name)
        result.append({
            "end_exclusive": hex(start + size),
            "instruction_count": len(instructions),
            "name": name,
            "sha256": digest,
            "size": size,
            "start": hex(start),
        })
    return result


def _descriptor(image_base, sections):
    raw = _section_bytes(image_base, sections, EQTYPE4_DESCRIPTOR, 0x68)
    kind, parameter_id = struct.unpack_from("<II", raw)
    name = raw[8:0x20].split(b"\0", 1)[0].decode("ascii")
    maximum, default, ui_step = struct.unpack_from("<fff", raw, 0x2C)
    _require((kind, parameter_id, name) == (2, 19, "eqtype4"),
             "eqtype4 descriptor identity differs")
    _require((maximum, default, ui_step) == (3.0, 0.0, 2.0),
             "eqtype4 descriptor numeric fields differ")
    _require(
        _section_bytes(image_base, sections, BRIEF_EQTYPE4_DESCRIPTOR, 8)
        != struct.pack("<II", 2, 19),
        "brief eqtype4 VA unexpectedly matches this exact DLL",
    )
    return {
        "actual_va": hex(EQTYPE4_DESCRIPTOR),
        "brief_va": hex(BRIEF_EQTYPE4_DESCRIPTOR),
        "brief_va_matches": False,
        "kind": kind,
        "name": name,
        "parameter_id": parameter_id,
        "minimum": 0.0,
        "maximum": maximum,
        "default": default,
        "ui_step": ui_step,
    }


def _validate_routes(dsp, image_base, sections):
    # Standard model construction and its 25-record descriptor registration.
    _require_direct_target(image_base, sections, 0x180048B17, 0x180015970)
    _require_bytes(image_base, sections, 0x180048B32, "488d05e7b73e00")
    _require_bytes(image_base, sections, 0x180048BA2, "83791c19")
    _require_bytes(image_base, sections, 0x180048BB3, "488d3dd64a0a00")
    _require_bytes(image_base, sections, 0x180048BBA, "bd19000000")
    _require_bytes(image_base, sections, 0x180048BCF, "4883c768")
    _require(_read_u64(image_base, sections, SELECTOR_MAPPER_SLOT)
             == 0x180015C60,
             "Standard vtable +0xc0 does not select the enum mapper")

    # Parameter 19 partitions as band (19-1)//6 == 3 and case
    # (19-1)%6 == 0.  Case zero rounds the enum and calls vtable +0xc0.
    _require(_read_u32s(image_base, sections, 0x180015E3C, 6)
             == PARAMETER_CASE_TARGET_RVAS,
             "Standard parameter-case table differs")
    _require_bytes(image_base, sections, 0x180015D84, "f30f5815b8a94600")
    _require_bytes(image_base, sections, 0x180015D92, "f30f2cd2")
    _require_bytes(image_base, sections, 0x180015D96, "ff90c0000000")

    mapping = _read_u32s(image_base, sections, SELECTOR_TABLE, 4)
    _require(mapping == (3, 8, 9, 6), "Standard EQ selector map differs")

    # Standard band values are movss inputs.  The designer wrapper widens
    # frequency, Q, and gain to doubles and takes the full-recompute path when
    # the mapped type changes.
    _require_direct_target(image_base, sections, 0x1800160DB, 0x1800167E0)
    _require_direct_target(image_base, sections, 0x1800168EF, 0x18000F8B0)
    _require_direct_target(image_base, sections, 0x18001610F, 0x180013270)
    _require_bytes(image_base, sections, 0x18001687B, "660f5ac7")
    _require_bytes(image_base, sections, 0x180016887, "0f57ff")
    _require_bytes(image_base, sections, 0x18001688A, "f30f5afa")
    _require_bytes(image_base, sections, 0x180016899, "66410f5ac1")
    _require_bytes(image_base, sections, 0x1800168B6, "f3440f5acb")
    _require_bytes(image_base, sections, 0x1800168D4, "660f5ac6")
    _require_bytes(image_base, sections, 0x1800168E0, "0f5af1")

    # Sample-rate update stores pi/fs; both recompute modes then form
    # w=(f+f)*(pi/fs).  The paired routine's small-input lane construction
    # directly fixes low lane=sin and high lane=cos.
    _require_bytes(image_base, sections, 0x18000F7D6, "f20f100532104700")
    _require_bytes(image_base, sections, 0x18000F7E1, "f20f115158")
    _require_bytes(image_base, sections, 0x18000F7E6, "f20f5ec2")
    _require_bytes(image_base, sections, 0x18000F7F2, "f20f1181b8000000")
    _require_direct_target(image_base, sections, 0x18000FF5E, PAIRED_TRIG)
    _require_direct_target(image_base, sections, 0x18001706E, PAIRED_TRIG)
    _require_bytes(image_base, sections, 0x1800D1604, "660f14c1")

    # Full dispatch: selector 9 -> outer class 7 -> inner class 4 -> 0x1039d.
    full_outer = _read_u32s(image_base, sections, 0x180010508, 13)
    full_outer_map = _section_bytes(image_base, sections, 0x18001053C, 32)
    full_inner = _read_u32s(image_base, sections, 0x18001055C, 11)
    full_inner_map = _section_bytes(image_base, sections, 0x180010588, 30)
    _require(full_outer == FULL_OUTER_TARGET_RVAS,
             "full-recompute outer targets differ")
    _require(full_outer_map == FULL_OUTER_MAP,
             "full-recompute outer selector map differs")
    _require(full_inner == FULL_INNER_TARGET_RVAS,
             "full-recompute inner targets differ")
    _require(full_inner_map == FULL_INNER_MAP,
             "full-recompute inner selector map differs")
    _require(full_outer[full_outer_map[9]] == 0xFF44,
             "selector 9 does not enter the full trig class")
    _require(full_inner[full_inner_map[9 - 2]] == 0x1039D,
             "selector 9 does not enter the full high-shelf branch")

    # Standard incremental clone: selector 9 follows the matching class-7
    # trig route and branch at 0x175cd.
    incremental_outer = _read_u32s(
        image_base, sections, 0x180017800, 13)
    incremental_outer_map = _section_bytes(
        image_base, sections, 0x180017834, 32)
    incremental_inner = _read_u32s(
        image_base, sections, 0x180017854, 11)
    incremental_inner_map = _section_bytes(
        image_base, sections, 0x180017880, 30)
    _require(incremental_outer == INCREMENTAL_OUTER_TARGET_RVAS,
             "incremental outer targets differ")
    _require(incremental_outer_map == FULL_OUTER_MAP,
             "incremental outer selector map differs")
    _require(incremental_inner == INCREMENTAL_INNER_TARGET_RVAS,
             "incremental inner targets differ")
    _require(incremental_inner_map == FULL_INNER_MAP,
             "incremental inner selector map differs")
    _require(incremental_outer[incremental_outer_map[9]] == 0x17036,
             "selector 9 does not enter the incremental trig class")
    _require(incremental_inner[incremental_inner_map[9 - 2]] == 0x175CD,
             "selector 9 does not enter the incremental high-shelf branch")

    # Pow is the double CRT import; constants and sign mask are exact doubles.
    try:
        imported_by_iat = pe_helpers._import_names_by_iat(
            dsp, image_base, sections)
    except pe_helpers.AnalysisError as error:
        raise AnalysisError(str(error)) from error
    _require(imported_by_iat.get(POW_IAT) == "pow",
             "double pow IAT binding differs")
    _require_bytes(image_base, sections, POW_THUNK, "ff25ac0f0100")
    _require_direct_target(image_base, sections, 0x1800103AD, POW_THUNK)
    _require_direct_target(image_base, sections, 0x1800175EF, POW_THUNK)

    # Five object doubles are narrowed independently and copied in ascending
    # field order to five adjacent output floats.
    for address in (0x1800143A3, 0x1800143A7, 0x1800143B8,
                    0x1800143D6, 0x1800143DA):
        instruction = pe_helpers._decode_one(image_base, sections, address)
        _require(instruction.mnemonic == "cvtpd2ps",
                 "output conversion at %#x is not cvtpd2ps" % address)


def _constant(image_base, sections, address, expected, name):
    raw = _section_bytes(image_base, sections, address, 8)
    value, = struct.unpack("<d", raw)
    _require(raw == struct.pack("<d", expected),
             "%s double constant differs at %#x" % (name, address))
    return {
        "f64_bits": "0x%016x" % struct.unpack("<Q", raw)[0],
        "name": name,
        "value": value,
        "va": hex(address),
    }


def _uc_full_highshelf(frequency_hz, gain_db, q, sample_rate_hz):
    """Instruction-order transcription of 0xff44 + 0x1039d/0x1033b."""
    frequency_hz = _f32(frequency_hz)
    gain_db = _f32(gain_db)
    q = _f32(q)
    sample_rate_hz = float(sample_rate_hz)

    pi_over_fs = math.pi / sample_rate_hz
    w = (frequency_hz + frequency_hz) * pi_over_fs
    sine = math.sin(w)
    cosine = math.cos(w)

    gain_exponent = gain_db * 0.025
    amplitude = math.pow(10.0, gain_exponent)
    amplitude_minus_one = amplitude - 1.0
    sqrt_amplitude = math.sqrt(amplitude)
    inverse_q = 1.0 / q
    beta_base = sqrt_amplitude * inverse_q
    amplitude_plus_one = amplitude + 1.0
    minus_cosine = amplitude_minus_one * cosine
    denominator_base = amplitude_plus_one - minus_cosine
    plus_cosine = amplitude_plus_one * cosine
    numerator_base = amplitude_plus_one + minus_cosine
    beta = beta_base * sine
    a0 = denominator_base + beta
    normalization = 1.0 / a0

    neg_a1_base = amplitude_minus_one - plus_cosine
    b1_base = amplitude_minus_one + plus_cosine
    b1_base = b1_base * -2.0
    neg_a1_base = neg_a1_base * -2.0
    neg_a1 = neg_a1_base * normalization
    amplitude_normalized = amplitude * normalization
    neg_a2_base = denominator_base - beta
    b0_base = numerator_base + beta
    b2_base = numerator_base - beta
    b1 = b1_base * amplitude_normalized
    neg_a2 = -(neg_a2_base * normalization)
    b2 = b2_base * amplitude_normalized
    b0 = b0_base * amplitude_normalized
    return [_f32(value) for value in (b0, neg_a1, b1, neg_a2, b2)]


def _uc_incremental_highshelf(frequency_hz, gain_db, q, sample_rate_hz):
    """Instruction-order transcription of the Standard clone at 0x175cd."""
    frequency_hz = _f32(frequency_hz)
    gain_db = _f32(gain_db)
    q = _f32(q)
    sample_rate_hz = float(sample_rate_hz)

    pi_over_fs = math.pi / sample_rate_hz
    w = (frequency_hz + frequency_hz) * pi_over_fs
    sine = math.sin(w)
    cosine = math.cos(w)
    amplitude = math.pow(10.0, gain_db * 0.025)
    beta_base = math.sqrt(amplitude) * (1.0 / q)
    amplitude_minus_one = amplitude - 1.0
    beta = beta_base * sine
    amplitude_plus_one = amplitude + 1.0
    minus_cosine = cosine * amplitude_minus_one
    plus_cosine = cosine * amplitude_plus_one
    denominator_base = amplitude_plus_one - minus_cosine
    numerator_base = minus_cosine + amplitude_plus_one
    a0 = denominator_base + beta
    neg_a2_base = denominator_base - beta
    b2_base = numerator_base - beta
    b0_base = numerator_base + beta
    normalization = 1.0 / a0
    neg_a1_base = (amplitude_minus_one - plus_cosine) * -2.0
    amplitude_normalized = amplitude * normalization
    b1_base = (plus_cosine + amplitude_minus_one) * -2.0
    neg_a2 = -(neg_a2_base * normalization)
    neg_a1 = neg_a1_base * normalization
    b2 = b2_base * amplitude_normalized
    b1 = b1_base * amplitude_normalized
    b0 = b0_base * amplitude_normalized
    return [_f32(value) for value in (b0, neg_a1, b1, neg_a2, b2)]


def _factory_vector(factory):
    try:
        presets = json.loads(factory.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AnalysisError("factory extraction is not valid UTF-8 JSON") from error
    matches = []
    for preset in presets:
        eq = preset.get("eq", {})
        if (preset.get("preset_name") == "Bright Vocal"
                and eq.get("__classid", "").upper()
                == "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}"
                and eq.get("eqbandop4") == 1
                and eq.get("eqbandon4") == 1):
            matches.append((preset, eq))
    _require(len(matches) == 1,
             "retained Bright Vocal Standard high shelf is not unique")
    preset, eq = matches[0]
    values = {
        "frequency_hz": eq.get("eqfreq4"),
        "gain_db": eq.get("eqgain4"),
        "q": eq.get("eqq4"),
    }
    _require(values == {
        "frequency_hz": 3926.376953,
        "gain_db": 6.030929,
        "q": 0.6,
    }, "retained Bright Vocal high-shelf tuple differs")

    coefficients = _uc_full_highshelf(
        values["frequency_hz"], values["gain_db"], values["q"], 48000.0)
    incremental = _uc_incremental_highshelf(
        values["frequency_hz"], values["gain_db"], values["q"], 48000.0)
    packed = struct.pack("<5f", *coefficients)
    incremental_packed = struct.pack("<5f", *incremental)
    _require(packed == incremental_packed,
             "full/incremental factory coefficient bytes differ")
    _require(packed.hex()
             == "ac5ce03f98b18e3ff79b16c08c69b6be1c88573f",
             "retained factory golden bytes differ: %s" % packed.hex())
    return {
        "coefficient_bytes_le": packed.hex(),
        "coefficient_f32_bits": [_f32_bits(value) for value in coefficients],
        "coefficients": coefficients,
        "full_and_incremental_bytes_match": True,
        "input_f32_bits": {
            name: _f32_bits(value) for name, value in values.items()
        },
        "inputs": values,
        "preset": preset["preset_name"],
        "record_offset": preset["_offset"],
        "sample_rate_hz": 48000.0,
        "standard_eq_class_id": eq["__classid"],
    }


def analyze(dsp, factory):
    dsp_identity = _identity("DSP", dsp, DSP_SIZE, DSP_SHA256)
    factory_identity = _identity(
        "factory", factory, FACTORY_SIZE, FACTORY_SHA256)
    try:
        image_base, sections = _parse_pe(dsp)
    except PeAnalysisError as error:
        raise AnalysisError("DSP: %s" % error) from error
    _require(image_base == IMAGE_BASE,
             "DSP image base differs: %#x" % image_base)

    descriptor = _descriptor(image_base, sections)
    _validate_routes(dsp, image_base, sections)
    regions = _bounded_regions(image_base, sections)
    constants = [
        _constant(image_base, sections, 0x1804807A8, 0.025, "gain_exponent"),
        _constant(image_base, sections, 0x1804807F0, 0.5, "one_half"),
        _constant(image_base, sections, 0x1804807F8, 1.0, "one"),
        _constant(image_base, sections, 0x180480810, math.pi, "pi"),
        _constant(image_base, sections, 0x180480828, 10.0, "pow_base"),
        _constant(image_base, sections, 0x180480A68, -2.0, "minus_two"),
        _constant(image_base, sections, 0x180480D60, -0.0, "sign_mask_lane0"),
    ]
    dsp_identity["image_base"] = hex(image_base)

    return {
        "algorithm": {
            "input_precision":
                "three binary32 values widened exactly to binary64",
            "internal_precision":
                "scalar binary64; no intermediate binary32 narrowing",
            "operations_in_source_order": [
                "f=round_f32(frequency_hz); g=round_f32(gain_db); q=round_f32(q)",
                "pi_over_fs=pi/sample_rate_hz; w=(f+f)*pi_over_fs",
                "sine=sin(w); cosine=cos(w)",
                "A=pow(10.0,g*0.025); Am1=A-1.0",
                "beta_base=sqrt(A)*(1.0/q); Ap1=A+1.0",
                "Am1c=Am1*cosine; denominator_base=Ap1-Am1c",
                "Ap1c=Ap1*cosine; numerator_base=Ap1+Am1c",
                "beta=beta_base*sine; normalization=1.0/(denominator_base+beta)",
                "neg_a1=((Am1-Ap1c)*-2.0)*normalization",
                "A_normalized=A*normalization",
                "b1=((Am1+Ap1c)*-2.0)*A_normalized",
                "neg_a2=-((denominator_base-beta)*normalization)",
                "b2=(numerator_base-beta)*A_normalized",
                "b0=(numerator_base+beta)*A_normalized",
            ],
            "output_rounding":
                "five independent cvtpd2ps binary64-to-binary32 conversions",
            "wire_order": ["b0", "-a1", "b1", "-a2", "b2"],
        },
        "analyzed_regions": regions,
        "boundary": (
            "STATIC_EXACT_DLL_AND_RETAINED_FACTORY_ONLY_NO_RUNTIME_DEVICE_"
            "AUDIBILITY_STORAGE_OR_STANDALONE_PERSISTENCE_CLAIM"
        ),
        "constants": constants,
        "descriptor": descriptor,
        "golden_vector": _factory_vector(factory),
        "recompute": {
            "double_pow": "api-ms-win-crt-math-l1-1-0.dll!pow",
            "designer_setter": "0x1800167e0",
            "full_recompute": "0x18000f8b0",
            "full_selector_9_branch": "0x18001039d",
            "incremental_selector_9_branch": "0x1800175cd",
            "output_conversion": "0x180014396",
            "paired_double_trig": "0x1800d15c0 low-lane sine high-lane cosine",
            "sample_rate_scale": "0x18000f7d0 stores pi/sample_rate",
            "standard_band_caller": "0x1800160c0",
        },
        "reconciliation": {
            "brief_descriptor_va_is_stale_for_exact_dll": True,
            "brief_float_designer": "0x180010d30",
            "brief_float_designer_used_by_standard_route": False,
            "brief_low_shelf_comparison": "0x1800125de",
            "standard_route_uses_double_designer": True,
        },
        "selector": {
            "component_constructor": "0x180048aa3",
            "descriptor_registration": "0x180048bb3",
            "eqtype_case": "0x180015d84",
            "high_shelf_designer_selector": 9,
            "high_shelf_ui_enum": 2,
            "mapper": "0x180015c60",
            "mapper_vtable_slot": hex(SELECTOR_MAPPER_SLOT),
            "mapping_table": hex(SELECTOR_TABLE),
            "parameter_setter": "0x180015c80",
            "ui_enum_to_designer": [3, 8, 9, 6],
        },
        "source": {
            "dsp": dsp_identity,
            "factory": factory_identity,
        },
        "status": "UC472_STANDARD_HIGHSHELF_SOURCE_BOUND",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dsp", type=Path)
    parser.add_argument("factory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = analyze(args.dsp.read_bytes(), args.factory.read_bytes())
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
