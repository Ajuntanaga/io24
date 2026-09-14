#!/usr/bin/env python3
"""Recover the UC 4.7.2 Standard low-shelf route and transcribe its maths.

Vendor code is parsed and disassembled as data and is never loaded or run.
The analyzer has no USB, audio, Wine, firmware, network, or device surface.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys


RE_DIR = Path(__file__).resolve().parent
if str(RE_DIR) not in sys.path:
    sys.path.insert(0, str(RE_DIR))

import uc472_standard_peaking as peaking  # noqa: E402


base = peaking.base
AnalysisError = base.AnalysisError
LOW_SHELF_START = 0x18001028A
LOW_SHELF_SIZE = 0xEC
LOW_SHELF_SHA256 = (
    "1f872416ba1c15204afbcfcaac43bb2516cf37d0a1027063e0cd779f7a046d63"
)


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _f32(value):
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _validate_route(dsp, image_base, sections):
    peaking._validate_route(dsp, image_base, sections)
    outer = base._read_u32s(image_base, sections, 0x180010508, 13)
    outer_map = base._section_bytes(image_base, sections, 0x18001053C, 32)
    inner = base._read_u32s(image_base, sections, 0x18001055C, 11)
    inner_map = base._section_bytes(image_base, sections, 0x180010588, 30)
    _require(outer[outer_map[8]] == 0xFF44,
             "selector 8 does not enter the full trigonometric class")
    _require(inner[inner_map[8 - 2]] == 0x1028A,
             "selector 8 does not enter the full low-shelf branch")

    raw = base._section_bytes(
        image_base, sections, LOW_SHELF_START, LOW_SHELF_SIZE)
    digest = hashlib.sha256(raw).hexdigest()
    _require(digest == LOW_SHELF_SHA256,
             "low-shelf bounded-region SHA-256 differs: %s" % digest)
    return {
        "end_exclusive": hex(LOW_SHELF_START + LOW_SHELF_SIZE),
        "name": "full_lowshelf_and_shared_tail",
        "sha256": digest,
        "size": LOW_SHELF_SIZE,
        "start": hex(LOW_SHELF_START),
    }


def _uc_full_lowshelf(frequency_hz, gain_db, q, sample_rate_hz):
    """Instruction-order transcription of 0x1028a and shared 0x1033b tail."""
    frequency_hz = _f32(frequency_hz)
    gain_db = _f32(gain_db)
    q = _f32(q)
    sample_rate_hz = float(sample_rate_hz)

    w = (frequency_hz + frequency_hz) * (math.pi / sample_rate_hz)
    sine = math.sin(w)
    cosine = math.cos(w)
    amplitude = math.pow(10.0, gain_db * 0.025)
    amplitude_minus_one = amplitude - 1.0
    sqrt_amplitude = math.sqrt(amplitude)
    inverse_q = 1.0 / q
    beta_base = sqrt_amplitude * inverse_q
    amplitude_plus_one = amplitude + 1.0
    minus_cosine = amplitude_minus_one * cosine
    plus_cosine = amplitude_plus_one * cosine
    denominator_base = amplitude_plus_one + minus_cosine
    numerator_base = amplitude_plus_one - minus_cosine
    beta = beta_base * sine
    normalization = 1.0 / (denominator_base + beta)

    twice_amplitude_minus_one = (
        amplitude_minus_one + amplitude_minus_one)
    twice_plus_cosine = plus_cosine + plus_cosine
    neg_a1 = (twice_plus_cosine + twice_amplitude_minus_one) * normalization
    amplitude_normalized = amplitude * normalization
    b1_base = ((amplitude_minus_one - plus_cosine)
               + (amplitude_minus_one - plus_cosine))
    b1 = b1_base * amplitude_normalized
    neg_a2 = -((denominator_base - beta) * normalization)
    b2 = (numerator_base - beta) * amplitude_normalized
    b0 = (numerator_base + beta) * amplitude_normalized
    return [_f32(value) for value in (b0, neg_a1, b1, neg_a2, b2)]


def _factory_vector(factory):
    try:
        presets = json.loads(factory.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AnalysisError("factory extraction is not valid UTF-8 JSON") from error
    matches = []
    for preset in presets:
        eq = preset.get("eq", {})
        if (preset.get("preset_name") == "Broadcast"
                and preset.get("_offset") == 154720979
                and eq.get("__classid", "").upper()
                == "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}"
                and eq.get("eqbandon1") == 1
                and eq.get("eqbandop1") == 1
                and eq.get("eqfreq1") == 59.999992
                and eq.get("eqgain1") == -1.75
                and eq.get("eqq1") == 1.0):
            matches.append(preset)
    _require(len(matches) == 1, "Broadcast factory preset is not unique")
    preset = matches[0]
    eq = preset.get("eq", {})
    _require(eq.get("__classid", "").upper()
             == "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}",
             "Broadcast does not use Standard EQ")
    _require(eq.get("eqbandon1") == 1 and eq.get("eqbandop1") == 1,
             "Broadcast first-band low shelf is not enabled")
    values = {
        "frequency_hz": eq.get("eqfreq1"),
        "gain_db": eq.get("eqgain1"),
        "q": eq.get("eqq1"),
    }
    _require(values == {
        "frequency_hz": 59.999992,
        "gain_db": -1.75,
        "q": 1.0,
    }, "Broadcast low-shelf tuple differs")
    coefficients = _uc_full_lowshelf(
        values["frequency_hz"], values["gain_db"], values["q"], 48000.0)
    packed = struct.pack("<5f", *coefficients)
    _require(packed.hex()
             == "f8e57f3f3cf0fe3f70f0febfede47dbf8dfe7d3f",
             "low-shelf golden bytes differ: %s" % packed.hex())
    return {
        "band": 1,
        "coefficient_bytes_le": packed.hex(),
        "coefficients": coefficients,
        "inputs": values,
        "preset": preset["preset_name"],
        "record_offset": preset["_offset"],
        "sample_rate_hz": 48000.0,
    }


def analyze(dsp, factory):
    dsp_identity = base._identity(
        "DSP", dsp, base.DSP_SIZE, base.DSP_SHA256)
    factory_identity = base._identity(
        "factory", factory, base.FACTORY_SIZE, base.FACTORY_SHA256)
    image_base, sections = base._parse_pe(dsp)
    _require(image_base == base.IMAGE_BASE,
             "DSP image base differs: %#x" % image_base)
    region = _validate_route(dsp, image_base, sections)
    dsp_identity["image_base"] = hex(image_base)
    return {
        "algorithm": {
            "input_precision":
                "three binary32 values widened exactly to binary64",
            "internal_precision":
                "scalar binary64; no intermediate binary32 narrowing",
            "output_rounding":
                "five independent cvtpd2ps binary64-to-binary32 conversions",
            "wire_order": ["b0", "-a1", "b1", "-a2", "b2"],
        },
        "analyzed_region": region,
        "boundary": (
            "STATIC_EXACT_DLL_AND_RETAINED_FACTORY_ONLY_NO_RUNTIME_DEVICE_"
            "AUDIBILITY_STORAGE_OR_STANDALONE_PERSISTENCE_CLAIM"
        ),
        "golden_vector": _factory_vector(factory),
        "selector": {
            "automatic_shape_setter": "0x180015be0",
            "designer_selector": 8,
            "enabled_first_band_table_index": 1,
            "full_branch": "0x18001028a",
            "selector_map": [3, 8, 9, 6],
            "standard_band_caller": "0x1800160c0",
            "standard_designer_setter": "0x1800167e0",
        },
        "source": {"dsp": dsp_identity, "factory": factory_identity},
        "status": "UC472_STANDARD_LOWSHELF_SOURCE_BOUND",
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
