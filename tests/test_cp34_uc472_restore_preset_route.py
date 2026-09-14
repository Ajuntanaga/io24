#!/usr/bin/env python3
"""Hardware-free contract for UC 4.7.2's RestorePreset route."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "cp34_uc472_restore_preset_route.py"
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


def _load_analyzer(test_case):
    test_case.assertTrue(
        ANALYZER.is_file(), "UC 4.7.2 RestorePreset route analyzer is missing")
    spec = importlib.util.spec_from_file_location(
        "cp34_uc472_restore_preset_route", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Uc472RestorePresetRouteTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.assertTrue(DSP.is_file(), "dspusbdevice.dll input is missing: %s" % DSP)
        self.module = _load_analyzer(self)
        self.report = self.module.analyze(DSP.read_bytes())

    def test_classification_and_boundary_are_exact(self):
        self.assertEqual(
            self.report["status"],
            "UC472_CHANNEL_PRESET_RECALL_IS_A_HOST_SIDE_MODEL_APPLY_"
            "NOT_A_DEVICE_RECORD_RECALL",
        )
        self.assertEqual(
            self.report["boundary"],
            "STATIC_DIRECT_CALL_EVIDENCE_ONLY_THE_APPLIER_SUBTREE_RETAINS_"
            "INDIRECT_CALL_SITES_AND_NO_LIVE_OR_DEVICE_OBSERVATION_WAS_MADE",
        )

    def test_receiver_understands_exactly_three_messages(self):
        self.assertEqual(
            self.report["receiver"]["messages"],
            ["GetPresetFileDescriptions", "RestorePreset", "StorePreset"],
        )
        self.assertEqual(
            self.report["receiver"]["parameter_keys"],
            ["presetFile", "presetTarget", "presetType"],
        )
        self.assertEqual(self.report["receiver"]["function"], "0x18003aef0")

    def test_restore_preset_has_two_targets_and_writes_no_record(self):
        self.assertEqual(
            self.report["restore_preset"]["preset_targets"], ["channel", "scene"])
        self.assertFalse(
            self.report["restore_preset"]["channel_branch_builds_a_device_record"])

    def test_channel_branch_indexes_the_host_side_device_model(self):
        self.assertEqual(
            self.report["channel_apply"],
            {
                "applier": "0x18002e690",
                "brackets_work_in_channel_virtual": "+0x8",
                "channel_array_header": "0xe8",
                "channel_array_pointer": "0x158",
                "channel_count_field": "0x160",
                "channel_stride": "0x120",
                "component_filter": ["voicefx", "comp", "opt", "voicefxopt"],
                "component_filter_appends": 3,
                "component_filter_builder": "0x18002e810",
                "guard": "0x18003c8a0",
                "index_parser": "0x18003c580",
            },
        )

    def test_the_applier_reaches_no_record_builder(self):
        reachability = self.report["reachability"]
        self.assertFalse(reachability["applier_reaches_record_builder"])
        self.assertEqual(reachability["applier_direct_call_functions"], 80)
        # The claim is direct-call only; the honest caveat travels with it.
        self.assertEqual(reachability["applier_indirect_call_sites"], 97)
        # The positive control: StorePreset does reach one.
        self.assertEqual(
            reachability["store_reaches_record_builder"], ["0x180037250"])
        self.assertIn("0x1800335ae", reachability["record_builders"])
        self.assertEqual(
            reachability["record_builders"]["0x1800335ae"], ["PrsM", "Stat"])

    def test_one_parameter_frame_builder_shares_the_record_encoder(self):
        builder = self.report["parameter_frame_builder"]
        self.assertEqual(builder["function"], "0x1800541d0")
        self.assertEqual(builder["setp_sites"], ["0x18005423c"])
        self.assertEqual(builder["encoder_vtable"], "0x1804393e0")
        self.assertEqual(builder["memp_fragmenter"], "0x180050f10")
        self.assertEqual(builder["memp_slot"], "0x10")
        self.assertEqual(builder["parameter_slot"], "0xd8")
        self.assertEqual(builder["protocol_version_gate"], "[this+0x68] == 2")

    def test_store_preset_is_the_branch_that_writes_a_record(self):
        self.assertEqual(
            self.report["store_preset"],
            {
                "library_sender": "0x180037250",
                "serializer": "0x18002e270",
                "writes_a_device_record": True,
            },
        )

    def test_a_different_image_is_refused(self):
        mutated = bytearray(DSP.read_bytes())
        mutated[-1] ^= 0xFF
        with self.assertRaises(self.module.AnalysisError):
            self.module.analyze(bytes(mutated))


if __name__ == "__main__":
    unittest.main()
