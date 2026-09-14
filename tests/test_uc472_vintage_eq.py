#!/usr/bin/env python3
"""Contracts for running UC 4.7.2's own Vintage EQ designers.

PROTOCOL.md 12N recorded the Vintage model's switch frequencies as "table not
recovered", and the Host applied 1073 values as a labelled guess. The table is
now read from the binary, and the designers with it:
`runs/20260914T031459-0700-native-slot-builder/VINTAGE-EQ-TABLE.md`.

`re/uc472_vintage_eq.py` does not re-implement the designers - it executes the
vendor's instructions, so the arithmetic is theirs. Two things are checked
here. First, that the four designers write one shared buffer in four adjacent
pieces totalling 22 floats, which is exactly what a stored `eq  ` unit holds
per sample rate; that is the evidence the record stores designer output rather
than a conversion of it. Second, that the low band is a real Neve-style shelf
whose corner tracks the recovered switch positions, which is what makes the
table a reading rather than a guess.

Nothing here opens USB, audio or a display.
"""

import cmath
import importlib.util
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "re" / "uc472_vintage_eq.py"
DLL = ROOT / (".superpowers/sdd/"
              "2026-08-28-cp34-preset-effect-control/runs/"
              "20260906T001130-0700-uc472-official-reacquisition/extracted/"
              "hwaccess/dspusbdevice.dll")
FIRMWARE = Path.home() / ".cache" / "io24" / "re" / "io24_fw.bin"
VINTAGE = {
    "__classid": "{E1C5E024-C5CD-473C-B08A-6EC177812E01}",
    "eqallon": 1,
    "lowgain": 2.0,
    "lowfreq": 3,
    "lowmidgain": -1.5,
    "lowmidfreq": 2,
    "himidgain": 1.5,
    "himidfreq": 0,
    "higain": -1.0,
}

# The device's convention is interleaved - b0, -a1, b1, -a2, b2 - which
# `re/uc472_standard_highshelf.py` already pinned with golden bytes. A
# seven-float band is the same thing carried to third order.
AUDIO = (20.0, 50.0, 100.0, 1000.0, 5000.0, 15000.0)


def _module():
    spec = importlib.util.spec_from_file_location("uc472_vintage_eq", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _response(coefficients, frequency, rate):
    padded = list(coefficients) + [0.0, 0.0]
    b0, na1, b1, na2, b2, na3, b3 = padded[:7]
    z = cmath.exp(-2j * math.pi * frequency / rate)
    numerator = b0 + b1 * z + b2 * z ** 2 + b3 * z ** 3
    denominator = 1 - na1 * z - na2 * z ** 2 - na3 * z ** 3
    return 20 * math.log10(abs(numerator / denominator))


@unittest.skipUnless(DLL.is_file(), "retained UC 4.7.2 DLL is not present")
class VintageDesignerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _module()
        cls.image = cls.module.Image(str(DLL))

    def low(self, index, gain, rate=48000.0):
        return self.module.design_band(self.image, index, gain, rate)

    # -- the switch table -------------------------------------------------
    def test_the_switch_table_is_four_three_and_three(self):
        self.assertEqual(self.module.LOW_FREQUENCIES, (35.0, 60.0, 110.0, 220.0))
        self.assertEqual(self.module.LOW_MID_FREQUENCIES, (360.0, 700.0, 1600.0))
        self.assertEqual(self.module.HI_MID_FREQUENCIES, (3200.0, 4800.0, 7200.0))

    # -- what the designers write ----------------------------------------
    def test_the_four_designers_tile_one_buffer_without_overlapping(self):
        regions = []
        for band, (_, _, _, at, count) in self.module.BAND_DESIGNERS.items():
            result = self.module.design(self.image, band, 1, 6.0, 48000.0)
            with self.subTest(band=band):
                self.assertIsNotNone(result["written"], "%s wrote nothing" % band)
                first, last = result["written"]
                self.assertEqual(first, at)
                self.assertEqual(last, at + count * 4 - 1)
                self.assertEqual(len(result["coefficients"]), count)
            regions.append((at, count))
        regions.sort()
        cursor = 0
        for at, count in regions:
            self.assertEqual(at, cursor, "a gap or overlap at 0x%x" % at)
            cursor = at + count * 4
        self.assertEqual(cursor // 4, self.module.BAND_COEFFICIENT_TOTAL)

    def test_the_total_is_what_a_stored_eq_unit_holds_per_rate(self):
        import io24_native_strip as strip
        stored = strip.EQ_MAIN_BANDS * strip.BIQUAD + 7
        self.assertEqual(stored, self.module.BAND_COEFFICIENT_TOTAL)

    def test_only_the_low_band_needs_the_seven_float_slot(self):
        widths = {band: entry[4]
                  for band, entry in self.module.BAND_DESIGNERS.items()}
        self.assertEqual(widths.pop("low"), 7)
        self.assertEqual(set(widths.values()), {5})

    def test_a_vintage_record_is_designed_in_native_band_order_at_every_rate(self):
        designed = self.module.design_eq(self.image, VINTAGE)

        self.assertEqual(tuple(designed), (44100.0, 48000.0, 88200.0, 96000.0))
        for rate, bands in designed.items():
            with self.subTest(rate=rate):
                self.assertEqual(
                    tuple(bands), ("low-mid", "hi-mid", "high", "wide"))
                self.assertEqual(
                    bands["low-mid"],
                    tuple(self.module.design(
                        self.image, "low-mid", 2, -1.5, rate)["coefficients"]))
                self.assertEqual(
                    bands["hi-mid"],
                    tuple(self.module.design(
                        self.image, "hi-mid", 0, 1.5, rate)["coefficients"]))
                self.assertEqual(
                    bands["high"],
                    tuple(self.module.design(
                        self.image, "high", 0, -1.0, rate)["coefficients"]))
                self.assertEqual(
                    bands["wide"],
                    tuple(self.module.design(
                        self.image, "low", 3, 2.0, rate)["coefficients"]))

    @unittest.skipUnless(FIRMWARE.is_file(), "firmware image not retained")
    def test_a_vintage_record_replaces_only_native_eq_coefficient_bytes(self):
        import io24_native_stat as native

        firmware = FIRMWARE.read_bytes()
        record = native.decode_native_stat_record(firmware[0x69230:0x69670])
        group = native.decode_chunk_group(next(
            chunk.payload for chunk in record.chunks if chunk.key == b"opt "))
        original = next(chunk.payload for chunk in group if chunk.key == b"eq  ")

        rebuilt = self.module.build_eq_component(self.image, original, VINTAGE)

        component = __import__("io24_native_strip").ComponentState(b"eq  ", rebuilt)
        self.assertEqual(component.eq_coefficients(),
                         self.module.design_eq(self.image, VINTAGE))
        allowed = set()
        strip = __import__("io24_native_strip")
        for index in range(4):
            main = index * strip.EQ_MAIN_UNIT + 4
            allowed.update(range(main, main + 3 * strip.BIQUAD * 4))
            wide = strip.EQ_EXTRA_AT + index * strip.EQ_EXTRA_UNIT + 4
            allowed.update(range(wide, wide + 7 * 4))
        differing = {index for index, pair in enumerate(zip(original, rebuilt))
                     if pair[0] != pair[1]}
        self.assertTrue(differing)
        self.assertTrue(differing <= allowed)

    @unittest.skipUnless(FIRMWARE.is_file(), "firmware image not retained")
    def test_a_vintage_record_builds_one_complete_valid_native_slot_body(self):
        import io24_native_stat as native

        base = FIRMWARE.read_bytes()[0x69230:0x69670]
        result = self.module.build_native_stat_record(
            self.image, base, 0, VINTAGE)

        self.assertEqual(native.validate_native_stat_record(result, 0), result)
        before = native.decode_native_stat_record(base)
        after = native.decode_native_stat_record(result)
        before_top = {chunk.key: chunk.payload for chunk in before.chunks}
        after_top = {chunk.key: chunk.payload for chunk in after.chunks}
        self.assertEqual(after_top[b"\x00\x00\x00\xc9"],
                         before_top[b"\x00\x00\x00\xc9"])
        before_channel = {chunk.key: chunk.payload for chunk in
                          native.decode_chunk_group(before_top[b"opt "])}
        after_channel = {chunk.key: chunk.payload for chunk in
                         native.decode_chunk_group(after_top[b"opt "])}
        self.assertEqual(
            after_channel[b"eq  "],
            self.module.build_eq_component(
                self.image, before_channel[b"eq  "], VINTAGE))
        for key in set(before_channel) - {b"eq  "}:
            with self.subTest(key=key):
                self.assertEqual(after_channel[key], before_channel[key])

    # -- what the low band sounds like ------------------------------------
    def test_no_gain_designs_an_identity_across_the_audio_band(self):
        coefficients = self.low(0, 0.0)["coefficients"]
        for frequency in AUDIO:
            with self.subTest(frequency=frequency):
                self.assertLess(
                    abs(_response(coefficients, frequency, 48000.0)), 0.1)

    def test_it_is_a_low_shelf_that_returns_to_unity(self):
        for index in range(len(self.module.LOW_FREQUENCIES)):
            for gain in (6.0, -6.0):
                coefficients = self.low(index, gain)["coefficients"]
                with self.subTest(index=index, gain=gain):
                    shelf = _response(coefficients, 10.0, 48000.0)
                    self.assertGreater(abs(shelf), 4.0)
                    self.assertLess(abs(shelf), abs(gain))
                    self.assertEqual(shelf > 0, gain > 0)
                    for frequency in (5000.0, 15000.0):
                        self.assertLess(
                            abs(_response(coefficients, frequency, 48000.0)), 0.05)

    def test_the_corner_tracks_the_recovered_switch_positions(self):
        corners = []
        for index in range(len(self.module.LOW_FREQUENCIES)):
            coefficients = self.low(index, 6.0)["coefficients"]
            half = _response(coefficients, 10.0, 48000.0) / 2.0
            corner = None
            for step in range(4000):
                frequency = 10.0 * (2000.0 ** (step / 3999.0))
                if _response(coefficients, frequency, 48000.0) <= half:
                    corner = frequency
                    break
            self.assertIsNotNone(corner, "no half-gain point for index %d" % index)
            corners.append(corner)
        self.assertEqual(corners, sorted(corners))
        for corner, switch in zip(corners, self.module.LOW_FREQUENCIES):
            with self.subTest(switch=switch):
                self.assertGreater(corner / switch, 0.6)
                self.assertLess(corner / switch, 1.1)

    def test_every_sample_rate_the_records_carry_is_designed(self):
        for rate in (44100.0, 48000.0, 88200.0, 96000.0):
            with self.subTest(rate=rate):
                result = self.low(1, 6.0, rate)
                self.assertEqual(result["rate_hz"], rate)
                shelf = _response(result["coefficients"], 10.0, rate)
                self.assertGreater(shelf, 4.0)
                self.assertLess(
                    abs(_response(result["coefficients"], rate / 4, rate)), 0.05)

    # -- the guard rails --------------------------------------------------
    def test_a_binary_that_is_not_the_pinned_one_is_refused(self):
        with self.assertRaises(self.module.AnalysisError):
            self.module.Image(str(ROOT / "io24.py"))

    def test_an_unknown_band_is_refused(self):
        with self.assertRaises(self.module.AnalysisError):
            self.module.design(self.image, "presence", 0, 0.0, 48000.0)


if __name__ == "__main__":
    unittest.main()
