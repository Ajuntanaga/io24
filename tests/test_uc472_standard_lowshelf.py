#!/usr/bin/env python3
"""Hardware-free contracts for UC 4.7.2 Standard low shelf."""

import importlib.util
from pathlib import Path
import struct
import unittest
from unittest import mock

import io24
import io24gtk


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "uc472_standard_lowshelf.py"
DSP = (ROOT / ".superpowers" / "sdd" /
       "2026-08-28-cp34-preset-effect-control" / "runs" /
       "20260906T001130-0700-uc472-official-reacquisition" / "extracted" /
       "hwaccess" / "dspusbdevice.dll")
FACTORY = ROOT / "re" / "uc_factory_presets.json"

GOLDEN_HEX = "f8e57f3f3cf0fe3f70f0febfede47dbf8dfe7d3f"


def _load_analyzer(test_case):
    test_case.assertTrue(
        ANALYZER.is_file(), "UC 4.7.2 Standard low-shelf analyzer is missing")
    spec = importlib.util.spec_from_file_location(
        "uc472_standard_lowshelf", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Uc472StandardLowShelfAnalyzerTests(unittest.TestCase):
    def test_source_binds_enabled_first_band_to_selector_eight(self):
        module = _load_analyzer(self)
        report = module.analyze(DSP.read_bytes(), FACTORY.read_bytes())

        self.assertEqual(report["status"],
                         "UC472_STANDARD_LOWSHELF_SOURCE_BOUND")
        self.assertEqual(report["selector"], {
            "automatic_shape_setter": "0x180015be0",
            "designer_selector": 8,
            "enabled_first_band_table_index": 1,
            "full_branch": "0x18001028a",
            "selector_map": [3, 8, 9, 6],
            "standard_band_caller": "0x1800160c0",
            "standard_designer_setter": "0x1800167e0",
        })
        self.assertEqual(report["algorithm"]["wire_order"],
                         ["b0", "-a1", "b1", "-a2", "b2"])
        self.assertEqual(report["algorithm"]["input_precision"],
                         "three binary32 values widened exactly to binary64")

    def test_broadcast_low_band_is_the_stable_transcription_vector(self):
        module = _load_analyzer(self)
        golden = module.analyze(
            DSP.read_bytes(), FACTORY.read_bytes())["golden_vector"]

        self.assertEqual(golden["preset"], "Broadcast")
        self.assertEqual(golden["band"], 1)
        self.assertEqual(golden["inputs"], {
            "frequency_hz": 59.999992,
            "gain_db": -1.75,
            "q": 1.0,
        })
        self.assertEqual(golden["coefficient_bytes_le"], GOLDEN_HEX)


class StandardLowShelfIntegrationTests(unittest.TestCase):
    def test_production_helper_matches_factory_and_edge_transcriptions(self):
        vectors = (
            ((59.999992, -1.75, 48000.0, 1.0), GOLDEN_HEX),
            ((18000.0, 15.0, 48000.0, 10.0),
             "31818640747f4ebfcc03e34012cb69bf1dd87f40"),
        )
        for arguments, expected in vectors:
            with self.subTest(arguments=arguments):
                coefficients = io24.biquad_lowshelf(*arguments)
                self.assertEqual(
                    struct.pack("<5f", *coefficients).hex(), expected)

    def test_public_set_eq_band_uses_the_exact_standard_helper(self):
        class Sink:
            EQ_BANDS = io24.Io24.EQ_BANDS
            set_eq_band = io24.Io24.set_eq_band

            def set_biquad(self, block, channel, coefficients, band=0):
                self.call = (block, channel, coefficients, band)
                return b"sent"

        sink = Sink()
        result = sink.set_eq_band(
            1, "low", shape="lowshelf", freq_hz=59.999992,
            gain_db=-1.75, q=1.0, fs=48000.0)

        self.assertEqual(result, b"sent")
        block, channel, coefficients, band = sink.call
        self.assertEqual((block, channel, band), ("eq  ", 1, 0))
        self.assertEqual(struct.pack("<5f", *coefficients).hex(), GOLDEN_HEX)

    def test_gtk_lowshelf_response_reuses_the_production_helper(self):
        band = {"shape": "lowshelf", "freq": 59.999992,
                "gain": -1.75, "q": 1.0}
        wire = [1.0, 2.0, 3.0, 4.0, 5.0]
        with mock.patch.object(io24, "biquad_lowshelf",
                               return_value=wire) as helper:
            response = io24gtk.Win._biquad(object(), band, 48000.0)

        helper.assert_called_once_with(
            band["freq"], band["gain"], 48000.0, band["q"])
        self.assertEqual(response, (1.0, 3.0, 5.0, -2.0, -4.0))


if __name__ == "__main__":
    unittest.main()
