#!/usr/bin/env python3
"""Hardware-free contracts for the exact UC 4.7.2 Standard high shelf."""

import importlib.util
import json
import math
from pathlib import Path
import struct
import unittest
from unittest import mock

import io24
import io24gtk


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "uc472_standard_highshelf.py"
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
RUN = (
    ROOT
    / ".superpowers"
    / "sdd"
    / "2026-08-28-cp34-preset-effect-control"
    / "runs"
    / "20260907T192625-0700-uc472-standard-highshelf"
)
ANALYSIS = RUN / "ANALYSIS.json"
CAMPAIGN_RUN = ROOT / "runs" / "20260906T165749-0700-host-live-routing-repair"
MATRIX = CAMPAIGN_RUN / "PARAMETER-VERIFICATION-MATRIX.json"
INVENTORY = CAMPAIGN_RUN / "PARAMETER-INVENTORY.json"
PLAN = CAMPAIGN_RUN / "FULL-PARAMETER-VERIFICATION-PLAN.md"

GOLDEN_COEFFICIENT_HEX = (
    "ac5ce03f"  # b0
    "98b18e3f"  # -a1
    "f79b16c0"  # b1
    "8c69b6be"  # -a2
    "1c88573f"  # b2
)
GOLDEN_BITS = [
    "0x3fe05cac",
    "0x3f8eb198",
    "0xc0169bf7",
    "0xbeb6698c",
    "0x3f57881c",
]


def _load_analyzer(test_case):
    test_case.assertTrue(
        ANALYZER.is_file(), "UC 4.7.2 Standard high-shelf analyzer is missing")
    spec = importlib.util.spec_from_file_location(
        "uc472_standard_highshelf", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Uc472StandardHighShelfAnalyzerTests(unittest.TestCase):
    maxDiff = None

    def test_source_binds_descriptor_selector_and_standard_recompute_route(self):
        module = _load_analyzer(self)
        report = module.analyze(DSP.read_bytes(), FACTORY.read_bytes())

        self.assertEqual(report["status"],
                         "UC472_STANDARD_HIGHSHELF_SOURCE_BOUND")
        self.assertEqual(report["source"]["dsp"], {
            "image_base": "0x180000000",
            "sha256": (
                "de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28"
            ),
            "size": 4_979_672,
        })
        self.assertEqual(report["source"]["factory"], {
            "sha256": (
                "89b0572dd760b77831d012e2db0568b4f4eeb158985a4ca86126be28e934c73d"
            ),
            "size": 47_158,
        })
        self.assertEqual(report["descriptor"], {
            "actual_va": "0x1800ede48",
            "brief_va": "0x1800ef2e8",
            "brief_va_matches": False,
            "kind": 2,
            "name": "eqtype4",
            "parameter_id": 19,
            "minimum": 0.0,
            "maximum": 3.0,
            "default": 0.0,
            "ui_step": 2.0,
        })
        self.assertEqual(report["selector"], {
            "component_constructor": "0x180048aa3",
            "descriptor_registration": "0x180048bb3",
            "parameter_setter": "0x180015c80",
            "eqtype_case": "0x180015d84",
            "mapper": "0x180015c60",
            "mapper_vtable_slot": "0x1804343e0",
            "mapping_table": "0x1800e81e0",
            "ui_enum_to_designer": [3, 8, 9, 6],
            "high_shelf_ui_enum": 2,
            "high_shelf_designer_selector": 9,
        })
        self.assertEqual(report["recompute"]["standard_band_caller"],
                         "0x1800160c0")
        self.assertEqual(report["recompute"]["designer_setter"],
                         "0x1800167e0")
        self.assertEqual(report["recompute"]["full_recompute"],
                         "0x18000f8b0")
        self.assertEqual(report["recompute"]["full_selector_9_branch"],
                         "0x18001039d")
        self.assertEqual(report["recompute"]["incremental_selector_9_branch"],
                         "0x1800175cd")
        self.assertEqual(report["recompute"]["output_conversion"],
                         "0x180014396")
        self.assertEqual(report["algorithm"]["wire_order"],
                         ["b0", "-a1", "b1", "-a2", "b2"])
        self.assertEqual(report["algorithm"]["input_precision"],
                         "three binary32 values widened exactly to binary64")
        self.assertEqual(report["algorithm"]["internal_precision"],
                         "scalar binary64; no intermediate binary32 narrowing")
        self.assertEqual(report["algorithm"]["output_rounding"],
                         "five independent cvtpd2ps binary64-to-binary32 conversions")

    def test_factory_golden_is_exact_and_saved_artifact_matches(self):
        module = _load_analyzer(self)
        report = module.analyze(DSP.read_bytes(), FACTORY.read_bytes())
        golden = report["golden_vector"]

        self.assertEqual(golden["preset"], "Bright Vocal")
        self.assertEqual(golden["record_offset"], 154_728_487)
        self.assertEqual(golden["sample_rate_hz"], 48_000.0)
        self.assertEqual(golden["input_f32_bits"], {
            "frequency_hz": "0x45756608",
            "gain_db": "0x40c0fd5f",
            "q": "0x3f19999a",
        })
        self.assertEqual(golden["coefficient_f32_bits"], GOLDEN_BITS)
        self.assertEqual(golden["coefficient_bytes_le"],
                         GOLDEN_COEFFICIENT_HEX)
        self.assertEqual(
            struct.pack("<5f", *golden["coefficients"]).hex(),
            GOLDEN_COEFFICIENT_HEX,
        )
        self.assertTrue(ANALYSIS.is_file(), "stable analysis artifact is missing")
        self.assertEqual(report, json.loads(ANALYSIS.read_text()))

    def test_wrong_binary_identity_is_rejected_before_analysis(self):
        module = _load_analyzer(self)
        changed = bytearray(DSP.read_bytes())
        changed[-1] ^= 1
        with self.assertRaisesRegex(module.AnalysisError,
                                    "DSP SHA-256 differs"):
            module.analyze(bytes(changed), FACTORY.read_bytes())


class StandardHighShelfIntegrationTests(unittest.TestCase):
    @staticmethod
    def _packed(*args, **kwargs):
        return struct.pack("<5f", *io24.biquad_highshelf(*args, **kwargs))

    def test_production_helper_matches_retained_factory_golden_as_f32(self):
        coefficients = io24.biquad_highshelf(
            3926.376953, 6.030929, 48000.0, 0.6)

        self.assertEqual(struct.pack("<5f", *coefficients).hex(),
                         GOLDEN_COEFFICIENT_HEX)
        self.assertEqual(
            coefficients,
            [struct.unpack("<f", bytes.fromhex(word))[0]
             for word in (
                 "ac5ce03f", "98b18e3f", "f79b16c0", "8c69b6be",
                 "1c88573f")],
        )

    def test_public_set_eq_band_passes_exact_golden_to_bqdf_path(self):
        class Sink:
            EQ_BANDS = io24.Io24.EQ_BANDS
            set_eq_band = io24.Io24.set_eq_band

            def set_biquad(self, block, channel, coefficients, band=0):
                self.call = (block, channel, coefficients, band)
                return b"sent"

        sink = Sink()
        result = sink.set_eq_band(
            2, "high", shape="highshelf", freq_hz=3926.376953,
            gain_db=6.030929, q=0.6, fs=48000.0)

        self.assertEqual(result, b"sent")
        block, channel, coefficients, band = sink.call
        self.assertEqual((block, channel, band), ("eq  ", 2, 3))
        self.assertEqual(struct.pack("<5f", *coefficients).hex(),
                         GOLDEN_COEFFICIENT_HEX)

    def test_exact_descriptor_boundaries_are_finite_stable_f32(self):
        vectors = (
            ((20.0, -15.0, 48000.0, 0.1),
             "8533383e85d7fd3f638fb4be3baf7bbf02ec303e"),
            ((18000.0, 15.0, 48000.0, 10.0),
             "323fab3f5009d8bf1d228a3fb77873bf5c649c3f"),
        )
        for arguments, expected in vectors:
            with self.subTest(arguments=arguments):
                coefficients = io24.biquad_highshelf(*arguments)
                self.assertEqual(struct.pack("<5f", *coefficients).hex(),
                                 expected)
                self.assertTrue(all(math.isfinite(value)
                                    for value in coefficients))
                self.assertEqual(
                    coefficients,
                    [struct.unpack("<f", struct.pack("<f", value))[0]
                     for value in coefficients],
                )
                neg_a1, neg_a2 = coefficients[1], coefficients[3]
                discriminant = complex(neg_a1 * neg_a1 + 4.0 * neg_a2)
                root = discriminant ** 0.5
                poles = ((neg_a1 + root) / 2.0, (neg_a1 - root) / 2.0)
                self.assertLess(max(abs(pole) for pole in poles), 1.0)

    def test_invalid_direct_builder_inputs_raise_value_error(self):
        invalid = (
            (float("nan"), 0.0, 48000.0, 0.7),
            (20.0, float("inf"), 48000.0, 0.7),
            (19.999, 0.0, 48000.0, 0.7),
            (18000.001, 0.0, 48000.0, 0.7),
            (1000.0, -15.001, 48000.0, 0.7),
            (1000.0, 15.001, 48000.0, 0.7),
            (1000.0, 0.0, 48000.0, 0.099),
            (1000.0, 0.0, 48000.0, 10.001),
            (1000.0, 0.0, 0.0, 0.7),
            (17000.0, 0.0, 32000.0, 0.7),
        )
        for arguments in invalid:
            with self.subTest(arguments=arguments):
                try:
                    io24.biquad_highshelf(*arguments)
                except Exception as error:  # turn a wrong exception into RED
                    self.assertIs(type(error), ValueError)
                else:
                    self.fail("invalid high-shelf inputs were accepted")

    def test_gtk_highshelf_response_reuses_production_helper(self):
        band = {"shape": "highshelf", "freq": 3926.376953,
                "gain": 6.030929, "q": 0.6}
        wire = [1.0, 2.0, 3.0, 4.0, 5.0]
        with mock.patch.object(io24, "biquad_highshelf", return_value=wire) as helper:
            response = io24gtk.Win._biquad(object(), band, 48000.0)

        helper.assert_called_once_with(
            band["freq"], band["gain"], 48000.0, band["q"])
        self.assertEqual(response, (1.0, 3.0, 5.0, -2.0, -4.0))

    def test_only_standard_shape_rows_drop_the_recovery_blocker(self):
        matrix = json.loads(MATRIX.read_text())
        self.assertEqual(matrix["coverage"]["total_rows"], 709)
        standard_shape_rows = [
            row for row in matrix["rows"]
            if row["family"] == "fat_eq" and row["parameter"] == "shape"
        ]
        self.assertEqual(len(standard_shape_rows), 8)
        self.assertTrue(all(
            "exact_vendor_highshelf_bits_pending" not in row["blockers"]
            for row in standard_shape_rows
        ))
        self.assertFalse(any(
            "exact_vendor_highshelf_bits_pending" in row["blockers"]
            for row in matrix["rows"]
        ))

        alternate_rows = [
            row for row in matrix["rows"]
            if row["family"] == "fat_eq_alternate"
        ]
        self.assertEqual(len(alternate_rows), 34)
        self.assertTrue(all(
            "alternate_eq_exact_builder_pending" in row["blockers"]
            for row in alternate_rows
        ))
        passive_frequency = [
            row for row in alternate_rows
            if row["scope"]["model"] == "passive"
            and row["parameter"] == "bfreq"
        ]
        self.assertEqual(len(passive_frequency), 2)
        self.assertTrue(all(
            "vendor_20kHz_literal_requires_resolution" in row["blockers"]
            for row in passive_frequency
        ))

    def test_inventory_and_plan_mark_only_standard_highshelf_closed(self):
        inventory = json.loads(INVENTORY.read_text())
        self.assertNotIn(
            "standard_eq_exact_highshelf_builder",
            inventory["known_unimplemented_or_unresolved"],
        )
        self.assertEqual(
            inventory["supported_host_capabilities"]["standard_highshelf"],
            {
                "coefficient_format": ["b0", "-a1", "b1", "-a2", "b2"],
                "designer_selector": 9,
                "precision": "binary32 inputs, binary64 operations, binary32 outputs",
                "source": "exact retained UC 4.7.2 dspusbdevice.dll",
            },
        )
        plan = PLAN.read_text()
        self.assertIn("Standard high-shelf builder is source-bound and bit-exact", plan)
        self.assertIn("Passive/Vintage factory EQ is", plan)
        self.assertIn("fail-closed", plan)


if __name__ == "__main__":
    unittest.main()
