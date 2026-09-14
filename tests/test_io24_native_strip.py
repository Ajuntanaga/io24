#!/usr/bin/env python3
"""Field-level contracts for the channel-strip components of a slot record.

Firmware 1.28 loads only native version-2 records, so writing a preset the
unit will actually apply means writing these component states. The layout was
decoded from the four records embedded in the firmware; the evidence is in
`runs/20260914T031459-0700-native-slot-builder/DECODE-NOTES.md`.

The strongest check here is that decoding and re-encoding every component of
every embedded record returns the original bytes exactly: the codec carries
what it does not understand instead of rebuilding it.

Nothing here opens USB, audio or a display.
"""

import json
import copy
import math
import os
from pathlib import Path
import struct
import unittest

import io24
import io24_dsp
import io24_native_stat
import io24_native_strip as strip

FIRMWARE = os.path.expanduser("~/.cache/io24/re/io24_fw.bin")
OFFSETS = (0x69230, 0x69670, 0x69AB0, 0x69EB4)
LENGTHS = (0x440, 0x440, 0x404, 0x404)
RUN = (Path(__file__).resolve().parents[1] / ".superpowers" / "sdd" /
       "2026-08-28-cp34-preset-effect-control" / "runs" /
       "20260914T031459-0700-native-slot-builder")


def _records():
    with open(FIRMWARE, "rb") as stream:
        image = stream.read()
    for offset, length in zip(OFFSETS, LENGTHS):
        record = io24_native_stat.decode_native_stat_record(
            image[offset:offset + length])
        group = [c for c in record.chunks if c.key == b"opt "][0].payload
        yield io24_native_stat.decode_chunk_group(group)


@unittest.skipUnless(os.path.exists(FIRMWARE), "firmware image not retained")
class NativeStripTests(unittest.TestCase):
    def setUp(self):
        self.records = list(_records())
        self.piano_ch2 = json.loads(
            (RUN / "backup" / "Piano Accomany.scene").read_text(
                encoding="utf-8-sig"))["line"]["ch2"]

    def test_every_component_round_trips_byte_for_byte(self):
        for index, chunks in enumerate(self.records):
            original = {chunk.key: bytes(chunk.payload) for chunk in chunks}
            for key, component in strip.decode_components(chunks).items():
                with self.subTest(record=index, component=key):
                    self.assertEqual(component.encode(), original[key])

    def test_the_filters_carry_one_set_per_clock(self):
        for index, chunks in enumerate(self.records):
            components = strip.decode_components(chunks)
            with self.subTest(record=index):
                self.assertEqual(
                    tuple(block.rate for block in components[b"filt"].blocks),
                    strip.RATES)
                # three bands, then the remaining band, each at four clocks
                self.assertEqual(
                    tuple(block.rate for block in components[b"eq  "].blocks),
                    strip.RATES + strip.RATES)

    def test_a_filter_edit_replaces_all_four_clocks_and_only_coefficients(self):
        component = strip.decode_components(self.records[0])[b"filt"]
        before = component.encode()
        replacement = {
            rate: (0.5, 0.25, -0.5, 0.125, -0.25)
            for rate in strip.RATES
        }

        component.set_filter_coefficients(replacement)

        self.assertEqual(component.filter_coefficients(), replacement)
        after = component.encode()
        allowed = set()
        for index in range(4):
            start = index * strip.FILT_UNIT + 4
            allowed.update(range(start, start + strip.BIQUAD * 4))
        differing = {index for index, pair in enumerate(zip(before, after))
                     if pair[0] != pair[1]}
        self.assertTrue(differing)
        self.assertTrue(differing <= allowed)
        self.assertEqual(len(before), len(after))

    def test_an_invalid_filter_edit_is_refused_atomically(self):
        component = strip.decode_components(self.records[0])[b"filt"]
        before = component.encode()

        with self.assertRaises(strip.NativeStripError):
            component.set_filter_coefficients({
                rate: (1.0, 0.0, 0.0, 0.0, 0.0)
                for rate in strip.RATES[:-1]
            })
        self.assertEqual(component.encode(), before)

        with self.assertRaises(strip.NativeStripError):
            component.set_filter_coefficients({
                rate: (1.0, 0.0, float("nan"), 0.0, 0.0)
                for rate in strip.RATES
            })
        self.assertEqual(component.encode(), before)

    def test_the_eq_exposes_three_biquads_and_one_third_order_band(self):
        # Firmware slot 2 exercises the two trailing coefficients.  If the
        # seven-float band were still treated as a biquad plus padding, this
        # evidence would be silently discarded.
        component = strip.decode_components(self.records[2])[b"eq  "]

        coefficients = component.eq_coefficients()

        self.assertEqual(tuple(coefficients), strip.RATES)
        for rate, bands in coefficients.items():
            with self.subTest(rate=rate):
                self.assertEqual(tuple(bands), strip.EQ_BAND_ORDER)
                self.assertEqual(len(bands["low-mid"]), 5)
                self.assertEqual(len(bands["hi-mid"]), 5)
                self.assertEqual(len(bands["high"]), 5)
                self.assertEqual(len(bands["wide"]), 7)
        self.assertNotEqual(coefficients[48000.0]["wide"][-2:], (0.0, 0.0))

    def test_an_eq_edit_changes_only_its_22_coefficients_per_rate(self):
        component = strip.decode_components(self.records[0])[b"eq  "]
        before = component.encode()
        replacement = {
            rate: {
                "low-mid": (1.0, 0.0, 0.0, 0.0, 0.0),
                "hi-mid": (0.5, 0.25, -0.5, 0.125, -0.25),
                "high": (0.75, 0.5, -0.25, 0.25, -0.5),
                "wide": (0.5, 0.25, -0.5, 0.125, -0.25, 0.0625, -0.125),
            }
            for rate in strip.RATES
        }

        component.set_eq_coefficients(replacement)

        self.assertEqual(component.eq_coefficients(), replacement)
        after = component.encode()
        allowed = set()
        for index in range(4):
            main = index * strip.EQ_MAIN_UNIT + 4
            allowed.update(range(main, main + 3 * strip.BIQUAD * 4))
            wide = strip.EQ_EXTRA_AT + index * strip.EQ_EXTRA_UNIT + 4
            allowed.update(range(wide, wide + 7 * 4))
        differing = {index for index, pair in enumerate(zip(before, after))
                     if pair[0] != pair[1]}
        self.assertTrue(differing)
        self.assertTrue(differing <= allowed)
        self.assertEqual(len(before), len(after))

    def test_an_invalid_eq_edit_is_refused_atomically(self):
        component = strip.decode_components(self.records[0])[b"eq  "]
        before = component.encode()
        incomplete = {
            rate: {
                "low-mid": (1.0, 0.0, 0.0, 0.0, 0.0),
                "hi-mid": (1.0, 0.0, 0.0, 0.0, 0.0),
                "high": (1.0, 0.0, 0.0, 0.0, 0.0),
                "wide": (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            }
            for rate in strip.RATES[:-1]
        }

        with self.assertRaises(strip.NativeStripError):
            component.set_eq_coefficients(incomplete)

        self.assertEqual(component.encode(), before)

    def test_standard_scene_designs_all_four_native_rate_sections(self):
        saved = self.piano_ch2["eq"]

        designed = strip.design_standard_eq(saved)

        self.assertEqual(tuple(designed), strip.RATES)
        for rate, bands in designed.items():
            with self.subTest(rate=rate):
                self.assertEqual(tuple(bands), strip.EQ_BAND_ORDER)
                self.assertEqual(
                    bands["low-mid"],
                    tuple(io24.biquad_peaking(
                        saved["eqfreq2"], saved["eqgain2"], rate,
                        saved["eqq2"])))
                self.assertEqual(
                    bands["hi-mid"],
                    tuple(io24.biquad_peaking(
                        saved["eqfreq3"], saved["eqgain3"], rate,
                        saved["eqq3"])))
                self.assertEqual(
                    bands["high"], (1.0, 0.0, 0.0, 0.0, 0.0))
                self.assertEqual(
                    bands["wide"],
                    tuple(io24.biquad_lowshelf(
                        saved["eqfreq1"], saved["eqgain1"], rate,
                        saved["eqq1"])) + (0.0, 0.0))

    def test_standard_scene_designs_enabled_outer_peaking_and_high_shelf(self):
        saved = copy.deepcopy(self.piano_ch2["eq"])
        saved["eqbandop1"] = 0
        saved["eqbandon4"] = 1
        saved["eqbandop4"] = 1

        designed = strip.design_standard_eq(saved)

        for rate, bands in designed.items():
            with self.subTest(rate=rate):
                self.assertEqual(
                    bands["wide"],
                    tuple(io24.biquad_peaking(
                        saved["eqfreq1"], saved["eqgain1"], rate,
                        saved["eqq1"])) + (0.0, 0.0))
                self.assertEqual(
                    bands["high"],
                    tuple(io24.biquad_highshelf(
                        saved["eqfreq4"], saved["eqgain4"], rate,
                        saved["eqq4"])))

    def test_standard_scene_validation_is_strict_even_when_eq_is_off(self):
        for field in ("eqallon", "eqbandon1", "eqbandop1"):
            malformed = copy.deepcopy(self.piano_ch2["eq"])
            malformed[field] = "0"
            with self.subTest(field=field), \
                    self.assertRaises(strip.NativeStripError):
                strip.design_standard_eq(malformed)

        malformed = copy.deepcopy(self.piano_ch2["eq"])
        malformed["eqallon"] = 0
        malformed["eqfreq1"] = float("nan")
        with self.assertRaises(strip.NativeStripError):
            strip.design_standard_eq(malformed)

    def test_standard_eq_builds_a_complete_native_stat_without_other_changes(self):
        firmware = Path(FIRMWARE).read_bytes()
        base = firmware[OFFSETS[0]:OFFSETS[0] + LENGTHS[0]]
        saved = self.piano_ch2["eq"]

        result = io24_native_stat.build_native_standard_eq_stat_record(
            base, 0, saved)

        self.assertEqual(io24_native_stat.validate_native_stat_record(result, 0),
                         result)
        before = io24_native_stat.decode_native_stat_record(base)
        after = io24_native_stat.decode_native_stat_record(result)
        before_top = {chunk.key: chunk.payload for chunk in before.chunks}
        after_top = {chunk.key: chunk.payload for chunk in after.chunks}
        before_channel = {chunk.key: chunk.payload for chunk in
                          io24_native_stat.decode_chunk_group(before_top[b"opt "])}
        after_channel = {chunk.key: chunk.payload for chunk in
                         io24_native_stat.decode_chunk_group(after_top[b"opt "])}
        for key in set(before_channel) - {b"eq  "}:
            with self.subTest(key=key):
                self.assertEqual(after_channel[key], before_channel[key])
        rebuilt = strip.ComponentState(b"eq  ", after_channel[b"eq  "])
        self.assertEqual(rebuilt.eq_coefficients(),
                         strip.design_standard_eq(saved))

    def test_the_compressor_parameters_are_the_live_blob_order(self):
        # record 3 is a plain 2:1 at -30 dB: values a misread could not invent
        components = strip.decode_components(self.records[3])
        values = components[b"comp"].comp_parameters()
        self.assertAlmostEqual(values["threshold_db"], -30.0, places=4)
        self.assertAlmostEqual(values["knee"], 3.0, places=4)
        self.assertAlmostEqual(values["attack"], 0.01, places=5)
        self.assertAlmostEqual(values["release"], 0.15, places=5)
        # the stored slope is 0.49525, i.e. 1.98:1 - a 2:1 compressor as
        # the firmware rounds it, not a coincidence of misalignment
        self.assertAlmostEqual(
            1.0 / (1.0 - values["slope"]), 2.0, delta=0.05)
        self.assertAlmostEqual(
            20 * math.log10(values["makeup"]), 3.0, places=2)

    def test_the_limiter_threshold_is_the_hosts_own_formula(self):
        first = strip.decode_components(self.records[0])[b"lim "].limiter()
        self.assertTrue(first["on"])
        self.assertAlmostEqual(first["inverse_threshold"],
                               io24_dsp.limiter_inv_threshold(-1.5), places=6)
        quiet = strip.decode_components(self.records[2])[b"lim "].limiter()
        self.assertAlmostEqual(quiet["inverse_threshold"], 1.0, places=6)

    def test_the_gate_state_is_the_exact_live_blob_payload_at_44100(self):
        component = strip.decode_components(self.records[0])[b"gate"]
        gate = component.gate_parameters()
        self.assertAlmostEqual(20 * math.log10(gate["range"]), -60.0, places=3)
        self.assertAlmostEqual(-20 * math.log10(gate["inverse_threshold"]),
                               -47.5, places=3)
        self.assertAlmostEqual(gate["attack_s"], 0.025, places=5)
        self.assertAlmostEqual(gate["release_s"], 0.7, places=5)
        saved = self.piano_ch2["gate"]
        expected = io24_dsp.gate_blob(
            0, on=bool(saved["on"]), threshold_db=saved["threshold"],
            range_db=saved["range"], attack_s=saved["attack"],
            release_s=saved["release"], keyfilter_hz=saved["keyfilter"],
            expander=bool(saved["expander"]),
            keylisten=bool(saved["keylisten"]), fs=44100.0)
        self.assertEqual(component.gate_blob(0), expected)

    def test_the_compressor_state_and_rate_biquads_match_the_live_builder(self):
        component = strip.decode_components(self.records[0])[b"comp"]
        saved = self.piano_ch2["comp"]
        kwargs = dict(
            on=bool(saved["on"]), input_db=saved["input"],
            output_db=saved["output"], attack_s=saved["attack"],
            release_s=saved["release"], ratio_index=int(saved["ratio"]),
            keyfilter_hz=saved["keyfilter"],
            keylisten=bool(saved["keylisten"]))
        expected = io24_dsp.cpxt_fet(0, fs=44100.0, **kwargs)
        self.assertEqual(component.compressor_blob(0), expected)
        for block in component.blocks:
            with self.subTest(rate=block.rate):
                rate_blob = io24_dsp.cpxt_fet(0, fs=block.rate, **kwargs)
                self.assertEqual(
                    block.biquad(), struct.unpack_from("<5f", rate_blob, 12))

    def test_gate_and_compressor_blob_edits_touch_only_the_selected_state(self):
        gate = strip.decode_components(self.records[0])[b"gate"]
        before_gate = gate.encode()
        gate_blob = io24_dsp.gate_blob(
            1, on=True, threshold_db=-36.0, range_db=-50.0,
            attack_s=0.02, release_s=0.5, keyfilter_hz=500.0,
            expander=False, keylisten=True, fs=44100.0)
        gate.set_gate_blob(gate_blob)
        self.assertEqual(gate.gate_blob(1), gate_blob)
        self.assertEqual(gate.encode()[:strip.GATE_STATE_AT + strip.GATE_STATE_SIZE],
                         before_gate[:strip.GATE_STATE_AT + strip.GATE_STATE_SIZE])

        comp = strip.decode_components(self.records[0])[b"comp"]
        before_comp = comp.encode()
        comp_blob = io24_dsp.cpxt_comp(
            1, on=True, threshold_db=-24.0, ratio=4.0,
            attack_s=0.01, release_s=0.2, gain_db=6.0,
            softknee=True, fs=44100.0)
        comp.set_compressor_blob(comp_blob)
        self.assertEqual(comp.compressor_blob(1), comp_blob)
        self.assertEqual(comp.encode()[:strip.COMP_STATE_AT + strip.COMP_STATE_SIZE],
                         before_comp[:strip.COMP_STATE_AT + strip.COMP_STATE_SIZE])

    def test_an_edit_changes_only_the_bytes_it_names(self):
        components = strip.decode_components(self.records[0])
        component = components[b"comp"]
        before = component.encode()
        component.set_comp_parameters(threshold_db=-24.0)
        after = component.encode()
        differing = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
        field = strip.COMP_PARAMS_AT + 20 + \
            component.COMP_FIELDS.index("threshold_db") * 4
        self.assertTrue(differing)
        self.assertTrue(set(differing) <= set(range(field, field + 4)),
                        "an edit reached outside its own field: %s" % differing)
        self.assertEqual(len(before), len(after))
        self.assertAlmostEqual(
            component.comp_parameters()["threshold_db"], -24.0, places=5)

    def test_a_state_that_is_not_that_shape_is_refused(self):
        chunks = self.records[0]
        filt = [c for c in chunks if c.key == b"filt"][0]
        broken = bytearray(filt.payload)
        struct.pack_into("<f", broken, 25, 12345.0)     # not a sample rate
        with self.assertRaises(strip.NativeStripError):
            strip.ComponentState(b"filt", bytes(broken))


if __name__ == "__main__":
    unittest.main()
