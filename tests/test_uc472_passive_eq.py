#!/usr/bin/env python3
"""Contracts for UC 4.7.2's Passive Program EQ designers.

The retained factory preset ``Big Vocal`` supplies a real Passive semantic
state.  These tests require the implementation to run the pinned vendor
designer routines, populate the native 22-float EQ layout at all four device
rates, and preserve every non-EQ byte in a native slot record.

Nothing here opens USB, audio, Wine, or a display.
"""

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "re" / "uc472_passive_eq.py"
DLL = ROOT / (".superpowers/sdd/"
              "2026-08-28-cp34-preset-effect-control/runs/"
              "20260906T001130-0700-uc472-official-reacquisition/extracted/"
              "hwaccess/dspusbdevice.dll")
FIRMWARE = Path.home() / ".cache" / "io24" / "re" / "io24_fw.bin"
PRESETS = ROOT / "re" / "uc_factory_presets.json"


def _module():
    spec = importlib.util.spec_from_file_location("uc472_passive_eq", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _big_vocal():
    presets = json.loads(PRESETS.read_text())
    return next(preset["eq"] for preset in presets
                if preset["preset_name"] == "Big Vocal")


class PassiveSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _module()
        cls.passive = _big_vocal()

    def test_factory_fixture_is_the_recovered_passive_state(self):
        self.assertEqual(self.passive["__classid"], self.module.PASSIVE_CLASS_ID)
        self.assertEqual(
            set(self.passive),
            {"__classid", "eqallon", "bboost", "batten", "bfreq",
             "mboost", "bbwidth", "mfreq", "hatten", "hsfreq"})

    def test_default_dll_path_names_the_retained_project_fixture(self):
        self.assertEqual(
            Path(self.module.DEFAULT_DLL),
            Path(".superpowers/sdd/2026-08-28-cp34-preset-effect-control/"
                 "runs/20260906T001130-0700-uc472-official-reacquisition/"
                 "extracted/hwaccess/dspusbdevice.dll"))

    def test_eq_off_still_validates_semantics_then_returns_identity(self):
        disabled = dict(self.passive, eqallon=0)
        designed = self.module.design_eq(None, disabled)
        for bands in designed.values():
            self.assertEqual(bands["low-mid"], (1.0, 0.0, 0.0, 0.0, 0.0))
            self.assertEqual(bands["hi-mid"], (1.0, 0.0, 0.0, 0.0, 0.0))
            self.assertEqual(bands["high"], (1.0, 0.0, 0.0, 0.0, 0.0))
            self.assertEqual(
                bands["wide"], (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        with self.assertRaises(self.module.AnalysisError):
            self.module.design_eq(None, dict(disabled, bbwidth=float("nan")))

    def test_switches_and_enable_are_strict_integer_values(self):
        for field, value in (("eqallon", "0"), ("bfreq", 1.5),
                             ("mfreq", 7), ("hsfreq", -1),
                             ("bfreq", True), ("mfreq", False),
                             ("hsfreq", True)):
            with self.subTest(field=field, value=value):
                with self.assertRaises(self.module.AnalysisError):
                    self.module.design_eq(
                        None, dict(self.passive, **{field: value}))


@unittest.skipUnless(DLL.is_file(), "retained UC 4.7.2 DLL is not present")
class PassiveDesignerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _module()
        cls.image = cls.module.Image(str(DLL))
        cls.passive = _big_vocal()

    def test_low_and_high_designers_write_their_observed_widths(self):
        low = self.module.design_low(
            self.image, 3, 3.899999, 0.0, 48000.0)
        high = self.module.design_high(
            self.image, 6, 1.8, 0.0, 2, 4.55, 48000.0)
        self.assertEqual(low["written"], (0, 19))
        self.assertEqual(len(low["coefficients"]), 5)
        self.assertEqual(high["written"], (0, 27))
        self.assertEqual(len(high["coefficients"]), 7)

    def test_big_vocal_48k_is_pinned_to_vendor_instruction_output(self):
        designed = self.module.design_eq(self.image, self.passive)[48000.0]
        self.assertEqual(
            designed["low-mid"],
            (1.0225366353988647, 0.2282530814409256,
             -0.16702279448509216, 0.7338700294494629,
             -0.697493851184845))
        self.assertEqual(
            designed["wide"],
            (0.7912453413009644, 0.2167043685913086,
             -0.022251157090067863, -0.4968438148498535,
             0.36978256702423096, 0.2143542468547821,
             -0.07308901101350784))

    def test_a_passive_record_is_designed_in_native_order_at_every_rate(self):
        designed = self.module.design_eq(self.image, self.passive)
        self.assertEqual(tuple(designed), (44100.0, 48000.0, 88200.0, 96000.0))
        for rate, bands in designed.items():
            with self.subTest(rate=rate):
                self.assertEqual(
                    tuple(bands), ("low-mid", "hi-mid", "high", "wide"))
                self.assertEqual(len(bands["low-mid"]), 5)
                self.assertEqual(bands["hi-mid"], (1.0, 0.0, 0.0, 0.0, 0.0))
                self.assertEqual(bands["high"], (1.0, 0.0, 0.0, 0.0, 0.0))
                self.assertEqual(len(bands["wide"]), 7)

    @unittest.skipUnless(FIRMWARE.is_file(), "firmware image not retained")
    def test_a_passive_record_replaces_only_native_eq_coefficient_bytes(self):
        import io24_native_stat as native
        import io24_native_strip as strip

        base = FIRMWARE.read_bytes()[0x69AB0:0x69EB4]
        decoded = native.decode_native_stat_record(base)
        top = {chunk.key: chunk.payload for chunk in decoded.chunks}
        channel = {chunk.key: chunk.payload for chunk in
                   native.decode_chunk_group(top[b"opt "])}
        original = channel[b"eq  "]
        rebuilt = self.module.build_eq_component(
            self.image, original, self.passive)
        differing = {index for index, pair in enumerate(zip(original, rebuilt))
                     if pair[0] != pair[1]}
        allowed = set()
        for index in range(4):
            main = index * strip.EQ_MAIN_UNIT + 4
            allowed.update(range(main, main + 3 * strip.BIQUAD * 4))
            wide = strip.EQ_EXTRA_AT + index * strip.EQ_EXTRA_UNIT + 4
            allowed.update(range(wide, wide + 7 * 4))
        self.assertTrue(differing)
        self.assertTrue(differing <= allowed)

    @unittest.skipUnless(FIRMWARE.is_file(), "firmware image not retained")
    def test_a_passive_record_builds_one_complete_valid_native_slot_body(self):
        import io24_native_stat as native

        base = FIRMWARE.read_bytes()[0x69AB0:0x69EB4]
        result = self.module.build_native_stat_record(
            self.image, base, 2, self.passive)
        self.assertEqual(native.validate_native_stat_record(result, 2), result)
        before = native.decode_native_stat_record(base)
        after = native.decode_native_stat_record(result)
        before_top = {chunk.key: chunk.payload for chunk in before.chunks}
        after_top = {chunk.key: chunk.payload for chunk in after.chunks}
        self.assertEqual(set(after_top), set(before_top))
        for key in set(before_top) - {b"opt "}:
            with self.subTest(top_key=key):
                self.assertEqual(after_top[key], before_top[key])
        before_channel = {chunk.key: chunk.payload for chunk in
                          native.decode_chunk_group(before_top[b"opt "])}
        after_channel = {chunk.key: chunk.payload for chunk in
                         native.decode_chunk_group(after_top[b"opt "])}
        for key in set(before_channel) - {b"eq  "}:
            with self.subTest(key=key):
                self.assertEqual(after_channel[key], before_channel[key])


if __name__ == "__main__":
    unittest.main()
