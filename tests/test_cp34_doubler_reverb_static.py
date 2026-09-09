#!/usr/bin/env python3
"""Hardware-free contracts for the CP34 Doubler private-reverb analyzer."""

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
RE_DIR = ROOT / "re"
SPEC = importlib.util.spec_from_file_location(
    "cp34_doubler_reverb_static",
    RE_DIR / "cp34_doubler_reverb_static.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DoublerPrivateReverbStaticTests(unittest.TestCase):
    def test_factory_reverb_is_doubler_json_not_shared_reverb(self):
        result = MODULE.analyze_factory_json(
            (RE_DIR / "uc_factory_presets.json").read_bytes())
        record = result["reverb_named_record"]
        self.assertEqual(record["index"], 30)
        self.assertEqual(record["voicefx"], MODULE.EXPECTED_REVERB_VOICEFX)
        self.assertEqual(result["forbidden_keys_present"], [])

    def test_component_model_separates_doubler_and_shared_reverb(self):
        result = MODULE.analyze_fx_params_xml(
            (RE_DIR / "uc_component_model" / "dsp_fx_params.xml").read_bytes())
        self.assertEqual(
            result["doubler_storable_fields"],
            ["on", "lows", "width", "mix"],
        )
        self.assertEqual(
            result["shared_reverb_fields"],
            ["on", "size", "mix", "hp_freq", "predelay"],
        )
        self.assertTrue(result["component_models_are_distinct"])

    def test_firmware_anchors_pin_one_core_implementation_two_instances(self):
        self.assertEqual(
            MODULE.FIRMWARE_CALL_ANCHORS["block202_constructs_shared_core"],
            (0x5B274, 0x5AF14),
        )
        self.assertEqual(
            MODULE.FIRMWARE_CALL_ANCHORS["doubler_constructs_private_core"],
            (0x5E37C, 0x5AF14),
        )
        self.assertEqual(
            MODULE.FIRMWARE_CALL_ANCHORS["block202_configures_shared_core"],
            (0x5ADE6, 0x5A6A8),
        )
        self.assertEqual(
            MODULE.FIRMWARE_CALL_ANCHORS["doubler_configures_private_core"],
            (0x5AE0E, 0x5A6A8),
        )

    def test_firmware_anchors_pin_two_hardware_lanes_one_settings_instance(self):
        self.assertEqual(
            MODULE.FIRMWARE_CALL_ANCHORS["device_sets_up_voicefx_two_lanes"],
            (0x3DC1C, 0x553D4),
        )
        self.assertEqual(
            MODULE.FIRMWARE_CALL_ANCHORS[
                "doubler_binds_indexed_private_core_lane"],
            (0x5AEAC, 0x56CC8),
        )
        self.assertEqual(
            MODULE.FIRMWARE_INSTRUCTION_ANCHORS[
                "voicefx_setup_two_equal_counts"],
            (0x3DC10, "strd", "r2, r2, [sp, #0x1c]"),
        )
        self.assertEqual(
            MODULE.FIRMWARE_INSTRUCTION_ANCHORS[
                "first_physical_input_map"][0],
            0x3F8A4,
        )
        self.assertEqual(
            MODULE.FIRMWARE_INSTRUCTION_ANCHORS[
                "second_physical_input_map"][0],
            0x3F8AA,
        )
        self.assertEqual(
            MODULE.FIRMWARE_INSTRUCTION_ANCHORS[
                "private_core_advances_to_lane_one"],
            (0x5AEB2, "movs", "r4, #1"),
        )

    def test_processing_assignment_replays_wire16_for_both_slot_indexes(self):
        self.assertEqual(
            MODULE.FIRMWARE_CODE_SLICES[
                "processing_assignment_active_slot_swap"],
            (0x2E77A, 0x42,
             "4fed3b4674f89b8a94498cf064f9e38fc8f5336da454bff5aeb399b9c4ae1093"),
        )
        self.assertEqual(
            MODULE.FIRMWARE_INSTRUCTION_ANCHORS[
                "processing_assignment_first_slot_target"],
            (0x2E7A0, "mov", "r3, r8"),
        )
        self.assertEqual(
            MODULE.FIRMWARE_INSTRUCTION_ANCHORS[
                "processing_assignment_second_slot_target"],
            (0x2E7B0, "mov", "r3, sb"),
        )
        self.assertEqual(
            MODULE.FIRMWARE_INSTRUCTION_ANCHORS[
                "processing_assignment_first_slot_wire_id"],
            (0x2E7A4, "movs", "r1, #0x10"),
        )
        self.assertEqual(
            MODULE.FIRMWARE_INSTRUCTION_ANCHORS[
                "processing_assignment_second_slot_wire_id"],
            (0x2E7B8, "movs", "r1, #0x10"),
        )

    def test_doubler_handler_surface_is_not_block202_reverb(self):
        self.assertEqual(
            MODULE.FIRMWARE_LITERAL_ANCHORS["doubler_handler_godv"],
            (0x5BD38, 0x676F6476),
        )
        self.assertNotIn("vrvb", MODULE.FIRMWARE_LITERAL_ANCHORS)

    def test_nested_key_scan_cannot_hide_reverb_send_fields(self):
        sample = [{"voicefx": {"mix": 0.2}}, {"nested": [{"FXA": -10.0}]}]
        self.assertEqual(
            MODULE._nested_keys(sample),
            {"voicefx", "mix", "nested", "FXA"},
        )

    def test_static_contract_keeps_live_action_out_of_scope(self):
        source = (RE_DIR / "cp34_doubler_reverb_static.py").read_text()
        self.assertIn("private reverb-core instance", source)
        self.assertIn("UNPROVED_RUNTIME_GATE", source)
        self.assertIn("not two independently", source)
        self.assertIn("including 96 kHz", source)
        self.assertIn("does not prove physical nonvolatile commit", source)
        self.assertNotIn("import io24", source)
        self.assertNotIn("usb.core", source)
        self.assertNotIn(".wine-io24", source)

    def test_factory_json_fixture_remains_valid_json(self):
        records = json.loads((RE_DIR / "uc_factory_presets.json").read_text())
        self.assertEqual(len(records), 41)
        self.assertEqual(
            [record["preset_name"] for record in records].count("Reverb"), 1)


if __name__ == "__main__":
    unittest.main()
