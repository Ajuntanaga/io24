#!/usr/bin/env python3
"""Hardware-free contracts for UC 4.7.2 Standard peaking EQ."""

import importlib.util
import json
from pathlib import Path
import struct
import unittest
from unittest import mock

import io24
import io24gtk


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "uc472_standard_peaking.py"
DSP = (
    ROOT
    / ".superpowers"
    / "sdd"
    / "2026-08-28-cp34-preset-effect-control"
    / "runs"
    / "20260906T001130-0700-uc472-official-reacquisition"
    / "extracted"
    / "hwaccess"
    / "dspusbdevice.dll"
)
FACTORY = ROOT / "re" / "uc_factory_presets.json"

GOLDEN_HEX = "6ca37d3f6908f53f6908f5bf1d976abfb2f36c3f"


def _load_analyzer(test_case):
    test_case.assertTrue(
        ANALYZER.is_file(), "UC 4.7.2 Standard peaking analyzer is missing")
    spec = importlib.util.spec_from_file_location(
        "uc472_standard_peaking", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Uc472StandardPeakingAnalyzerTests(unittest.TestCase):
    maxDiff = None

    def test_source_binds_standard_middle_bands_to_selector_six(self):
        module = _load_analyzer(self)
        report = module.analyze(DSP.read_bytes(), FACTORY.read_bytes())

        self.assertEqual(report["status"],
                         "UC472_STANDARD_PEAKING_SOURCE_BOUND")
        self.assertEqual(report["selector"], {
            "automatic_shape_setter": "0x180015be0",
            "designer_selector": 6,
            "full_branch": "0x18000fe4c",
            "middle_band_default_table_index": 3,
            "selector_map": [3, 8, 9, 6],
            "standard_band_caller": "0x1800160c0",
            "standard_designer_setter": "0x1800167e0",
        })
        self.assertEqual(report["algorithm"]["wire_order"],
                         ["b0", "-a1", "b1", "-a2", "b2"])
        self.assertEqual(report["algorithm"]["input_precision"],
                         "three binary32 values widened exactly to binary64")
        self.assertEqual(report["algorithm"]["internal_precision"],
                         "scalar binary64; no intermediate binary32 narrowing")

    def test_bright_vocal_middle_band_is_the_stable_transcription_vector(self):
        module = _load_analyzer(self)
        report = module.analyze(DSP.read_bytes(), FACTORY.read_bytes())
        golden = report["golden_vector"]

        self.assertEqual(golden["preset"], "Bright Vocal")
        self.assertEqual(golden["band"], 2)
        self.assertEqual(golden["inputs"], {
            "frequency_hz": 353.317841,
            "gain_db": -2.164948,
            "q": 0.6,
        })
        self.assertEqual(golden["sample_rate_hz"], 48000.0)
        self.assertEqual(golden["coefficient_bytes_le"], GOLDEN_HEX)

    def test_wrong_dll_identity_is_rejected_before_analysis(self):
        module = _load_analyzer(self)
        changed = bytearray(DSP.read_bytes())
        changed[-1] ^= 1
        with self.assertRaisesRegex(module.AnalysisError,
                                    "DSP SHA-256 differs"):
            module.analyze(bytes(changed), FACTORY.read_bytes())


class StandardPeakingIntegrationTests(unittest.TestCase):
    def test_production_helper_matches_the_source_bound_transcription(self):
        coefficients = io24.biquad_peaking(
            353.317841, -2.164948, 48000.0, 0.6)

        self.assertEqual(struct.pack("<5f", *coefficients).hex(), GOLDEN_HEX)

    def test_public_set_eq_band_uses_the_exact_standard_helper(self):
        class Sink:
            EQ_BANDS = io24.Io24.EQ_BANDS
            set_eq_band = io24.Io24.set_eq_band

            def set_biquad(self, block, channel, coefficients, band=0):
                self.call = (block, channel, coefficients, band)
                return b"sent"

        sink = Sink()
        result = sink.set_eq_band(
            2, "lowmid", shape="peaking", freq_hz=353.317841,
            gain_db=-2.164948, q=0.6, fs=48000.0)

        self.assertEqual(result, b"sent")
        block, channel, coefficients, band = sink.call
        self.assertEqual((block, channel, band), ("eq  ", 2, 1))
        self.assertEqual(struct.pack("<5f", *coefficients).hex(), GOLDEN_HEX)

    def test_gtk_peaking_response_reuses_the_production_helper(self):
        band = {"shape": "peaking", "freq": 353.317841,
                "gain": -2.164948, "q": 0.6}
        wire = [1.0, 2.0, 3.0, 4.0, 5.0]
        with mock.patch.object(io24, "biquad_peaking",
                               return_value=wire) as helper:
            response = io24gtk.Win._biquad(object(), band, 48000.0)

        helper.assert_called_once_with(
            band["freq"], band["gain"], 48000.0, band["q"])
        self.assertEqual(response, (1.0, 3.0, 5.0, -2.0, -4.0))


if __name__ == "__main__":
    unittest.main()
