#!/usr/bin/env python3
"""Recover the UC 4.7.2 Standard peaking-EQ route and transcribe its maths.

The retained vendor DLL is parsed and disassembled as data; it is never loaded
or executed.  This analyzer is file-only and performs no USB, audio, Wine,
firmware, network, or device operation.
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

import uc472_standard_highshelf as base  # noqa: E402


AnalysisError = base.AnalysisError

REGIONS = (
    ("standard_band_defaults", 0x180015A40, 0x114,
     "38e52fd7fec678007b301b5979326112fc1204afb470fdf55bc44ca0a14ce3d3"),
    ("automatic_outer_shapes", 0x180015BE0, 0x71,
     "b03df2157ec16f86838ef83afd2c59c9b87483b3696b3dc70cac5c4b150c205a"),
    ("full_peaking", 0x18000FE4C, 0xF8,
     "63fbd4f59ce49d2af8f454199d9a1acbcbbf5d53c340c3187a8b5d944ea459f9"),
    ("output_conversion", 0x180014396, 0x59,
     "818d0df14dacb8b415737b2e1a29c510b8989712421aad8c65a30bcf5223b46d"),
)

TAN_THUNK = 0x1800D3568
TAN_IAT = 0x1800E44D8


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _f32(value):
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _f32_bits(value):
    return "0x%08x" % struct.unpack("<I", struct.pack("<f", value))[0]


def _bounded_regions(image_base, sections):
    result = []
    for name, start, size, expected in REGIONS:
        raw = base._section_bytes(image_base, sections, start, size)
        digest = hashlib.sha256(raw).hexdigest()
        _require(digest == expected,
                 "%s bounded-region SHA-256 differs: %s" % (name, digest))
        result.append({
            "end_exclusive": hex(start + size),
            "name": name,
            "sha256": digest,
            "size": size,
            "start": hex(start),
        })
    return result


def _validate_route(dsp, image_base, sections):
    # All eight Standard bands are initialized as selector 6.  The automatic
    # shape setter retains table index 3 (selector 6) for middle bands and
    # substitutes only index 1/2 for an enabled first/last band.
    base._require_bytes(image_base, sections, 0x180015A40,
                        "41c70106000000")
    base._require_bytes(image_base, sections, 0x180015BF1,
                        "41b803000000")
    base._require_bytes(image_base, sections, 0x180015C0D,
                        "85d2")
    base._require_bytes(image_base, sections, 0x180015C11,
                        "41b801000000")
    base._require_bytes(image_base, sections, 0x180015C19,
                        "418d41ff")
    base._require_bytes(image_base, sections, 0x180015C1D,
                        "41b902000000")
    base._require_bytes(image_base, sections, 0x180015C34,
                        "428b0480")
    mapping = base._read_u32s(
        image_base, sections, base.SELECTOR_TABLE, 4)
    _require(mapping == (3, 8, 9, 6), "Standard selector map differs")

    # Full designer dispatch sends selector 6 directly to the bounded peaking
    # branch.  The ordinary Standard caller uses the double designer and the
    # common five-field binary32 output conversion.
    outer = base._read_u32s(image_base, sections, 0x180010508, 13)
    outer_map = base._section_bytes(
        image_base, sections, 0x18001053C, 32)
    _require(outer == base.FULL_OUTER_TARGET_RVAS,
             "full-recompute outer targets differ")
    _require(outer_map == base.FULL_OUTER_MAP,
             "full-recompute outer selector map differs")
    _require(outer[outer_map[6]] == 0xFE4C,
             "selector 6 does not enter the full peaking branch")
    base._require_direct_target(
        image_base, sections, 0x1800160DB, 0x1800167E0)
    base._require_direct_target(
        image_base, sections, 0x1800168EF, 0x18000F8B0)

    imported = base.pe_helpers._import_names_by_iat(
        dsp, image_base, sections)
    _require(imported.get(base.POW_IAT) == "pow",
             "double pow IAT binding differs")
    _require(imported.get(TAN_IAT) == "tan",
             "double tan IAT binding differs")
    base._require_bytes(image_base, sections, TAN_THUNK, "ff256a0f0100")
    base._require_direct_target(
        image_base, sections, 0x18000FE5C, base.POW_THUNK)
    base._require_direct_target(
        image_base, sections, 0x18000FE77, TAN_THUNK)


def _uc_full_peaking(frequency_hz, gain_db, q, sample_rate_hz):
    """Instruction-order transcription of selector 6 at 0x18000fe4c."""
    frequency_hz = _f32(frequency_hz)
    gain_db = _f32(gain_db)
    q = _f32(q)
    sample_rate_hz = float(sample_rate_hz)

    gain_power = math.pow(10.0, gain_db * 0.05)
    k = math.tan(frequency_hz * (math.pi / sample_rate_hz))
    k2 = k * k
    alpha_numerator = math.sqrt(gain_power) * k
    alpha_numerator = alpha_numerator / q
    alpha_denominator = alpha_numerator / gain_power
    denominator = (alpha_denominator + k2) + 1.0

    neg_a2 = ((alpha_denominator - 1.0) - k2) / denominator
    neg_a1 = ((1.0 - k2) + (1.0 - k2)) / denominator
    b0 = ((k2 + alpha_numerator) + 1.0) / denominator
    b1 = (((k2 - 1.0) + k2) - 1.0) / denominator
    b2 = ((k2 - alpha_numerator) + 1.0) / denominator
    return [_f32(value) for value in (b0, neg_a1, b1, neg_a2, b2)]


def _factory_vector(factory):
    try:
        presets = json.loads(factory.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AnalysisError("factory extraction is not valid UTF-8 JSON") from error
    matches = [preset for preset in presets
               if preset.get("preset_name") == "Bright Vocal"]
    _require(len(matches) == 1, "Bright Vocal factory preset is not unique")
    preset = matches[0]
    eq = preset.get("eq", {})
    _require(eq.get("__classid", "").upper()
             == "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}",
             "Bright Vocal does not use Standard EQ")
    values = {
        "frequency_hz": eq.get("eqfreq2"),
        "gain_db": eq.get("eqgain2"),
        "q": eq.get("eqq2"),
    }
    _require(values == {
        "frequency_hz": 353.317841,
        "gain_db": -2.164948,
        "q": 0.6,
    }, "Bright Vocal middle-band tuple differs")
    coefficients = _uc_full_peaking(
        values["frequency_hz"], values["gain_db"], values["q"], 48000.0)
    packed = struct.pack("<5f", *coefficients)
    _require(packed.hex()
             == "6ca37d3f6908f53f6908f5bf1d976abfb2f36c3f",
             "peaking golden bytes differ: %s" % packed.hex())
    return {
        "band": 2,
        "coefficient_bytes_le": packed.hex(),
        "coefficient_f32_bits": [_f32_bits(value) for value in coefficients],
        "coefficients": coefficients,
        "input_f32_bits": {
            name: _f32_bits(value) for name, value in values.items()
        },
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
    _validate_route(dsp, image_base, sections)
    dsp_identity["image_base"] = hex(image_base)
    return {
        "algorithm": {
            "input_precision":
                "three binary32 values widened exactly to binary64",
            "internal_precision":
                "scalar binary64; no intermediate binary32 narrowing",
            "operations_in_source_order": [
                "f=round_f32(frequency_hz); g=round_f32(gain_db); q=round_f32(q)",
                "P=pow(10.0,g*0.05); k=tan(f*(pi/sample_rate_hz)); k2=k*k",
                "alpha_n=sqrt(P)*k/q; alpha_d=alpha_n/P",
                "denominator=(alpha_d+k2)+1.0",
                "b0=((k2+alpha_n)+1.0)/denominator",
                "neg_a1=((1.0-k2)+(1.0-k2))/denominator",
                "b1=(((k2-1.0)+k2)-1.0)/denominator",
                "neg_a2=((alpha_d-1.0)-k2)/denominator",
                "b2=((k2-alpha_n)+1.0)/denominator",
            ],
            "output_rounding":
                "five independent cvtpd2ps binary64-to-binary32 conversions",
            "wire_order": ["b0", "-a1", "b1", "-a2", "b2"],
        },
        "analyzed_regions": _bounded_regions(image_base, sections),
        "boundary": (
            "STATIC_EXACT_DLL_AND_RETAINED_FACTORY_ONLY_NO_RUNTIME_DEVICE_"
            "AUDIBILITY_STORAGE_OR_STANDALONE_PERSISTENCE_CLAIM"
        ),
        "golden_vector": _factory_vector(factory),
        "selector": {
            "automatic_shape_setter": "0x180015be0",
            "designer_selector": 6,
            "full_branch": "0x18000fe4c",
            "middle_band_default_table_index": 3,
            "selector_map": [3, 8, 9, 6],
            "standard_band_caller": "0x1800160c0",
            "standard_designer_setter": "0x1800167e0",
        },
        "source": {"dsp": dsp_identity, "factory": factory_identity},
        "status": "UC472_STANDARD_PEAKING_SOURCE_BOUND",
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
