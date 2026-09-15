#!/usr/bin/env python3
"""Hardware-free contracts for the block-201 delegate lifecycle trace."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cp34_block201_delegate_static",
    ROOT / "re" / "cp34_block201_delegate_static.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Block201DelegateStaticTests(unittest.TestCase):
    def test_schema_tracks_the_model5_extension(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        self.assertEqual(result["schema"],
                         "cp34-block201-delegate-lifecycle-v4")

    def test_constructor_path_lazily_installs_model_zero_delegate(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        lifecycle = result["delegate_lifecycle"]
        self.assertTrue(lifecycle["constructor_path_installs_delegate"])
        self.assertEqual(lifecycle["delegate_object_offset"], "block+0x60")
        self.assertEqual(lifecycle["delegate_pointer_field"], "block+0x14")
        self.assertEqual(lifecycle["initial_model"], 0)

    def test_bypass_target_is_cleared_after_lazy_install(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        lifecycle = result["delegate_lifecycle"]
        self.assertEqual(lifecycle["selector_requests_bypass"], "block+0x44=1")
        self.assertEqual(lifecycle["installer_requests_processing"], "block+0x44=0")
        self.assertEqual(lifecycle["plus_0x44_semantics"],
                         "target bypass state; 0 processes, 1 bypasses")

    def test_model_state_bypasses_rebuild_check_and_selector_must_replay(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        routing = result["message_routing"]
        self.assertEqual(routing["selector_tag"], "VoFx")
        self.assertEqual(routing["selector_path"],
                         "0x553d4 -> 0x55388")
        self.assertEqual(routing["model_state_path"],
                         "0x553d4 -> 0x5079c -> delegate vtable+0x00")
        self.assertFalse(routing["model_state_revisits_rebuild_check"])
        self.assertEqual(
            routing["required_deferred_rebuild_trigger"],
            "replay VoFx selector after bypass transition")

    def test_literal_pool_is_not_reported_as_a_delegate_store(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        pool = result["literal_pool_after_work"]
        self.assertEqual(pool["work_return_offset"], "0x5f248")
        self.assertEqual(pool["first_literal_offset"], "0x5f24c")
        self.assertEqual(pool["first_literal_u32"], "0x49466163")
        self.assertFalse(pool["first_literal_is_code"])

    def test_old_chain_installer_is_only_a_workspace_sizer(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        workspace = result["three_member_workspace_sizer"]
        self.assertEqual(workspace["function_offset"], "0x3e608")
        self.assertEqual(workspace["member_virtual_slot"], "vtable+0x18")
        self.assertEqual(workspace["destination_field"], "device+0x11d0")
        self.assertFalse(workspace["retains_member_pointers"])
        self.assertFalse(workspace["proves_signal_chain_installation"])

    def test_trace_claims_only_the_source_bound_audio_path(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        conclusion = result["conclusion"]
        self.assertFalse(conclusion["delegate_null_explains_live_inertness"])
        self.assertTrue(conclusion["signal_path_execution_proven"])
        self.assertTrue(conclusion["selector_state_replay_sequence_falsified"])
        self.assertEqual(
            conclusion["required_host_sequence"],
            "selector -> wait for bypass -> selector replay -> model state")
        source = (ROOT / "re" / "cp34_block201_delegate_static.py").read_text()
        self.assertNotIn("import io24", source)
        self.assertNotIn("usb.core", source)
        self.assertNotIn(".wine-io24", source)

    def test_block_process_virtual_invokes_selected_model_process_virtual(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        execution = result["audio_execution"]
        self.assertEqual(execution["block201_process_virtual_slot"],
                         "vtable+0x0c")
        self.assertEqual(execution["selected_model_process_virtual_slot"],
                         "vtable+0x0c")
        self.assertEqual(execution["model0_process_raw_offset"], "0x1e1a8")
        self.assertTrue(execution["block_process_reaches_model0_process"])

    def test_audio_root_directly_calls_block201_with_buffer_descriptor(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        root = result["audio_root_binding"]
        self.assertEqual(root["block201_object"], "device+0x11e0")
        self.assertEqual(root["buffer_descriptor"], "stack+0x40")
        self.assertEqual(root["direct_call_raw_offset"], "0x2054e")
        self.assertTrue(root["scheduler_and_buffer_handoff_source_bound"])

    def test_model5_handler_process_and_lane_descriptor_are_source_bound(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        model = result["model5_execution"]
        self.assertEqual(model["model_id"], 5)
        self.assertEqual(model["tag"], "vech")
        self.assertEqual(model["tagged_handler_raw_offset"], "0x57240")
        self.assertEqual(model["process_raw_offset"], "0x4ebd4")
        self.assertEqual(model["parameter_fields"], {
            "on": "model+0x10",
            "mix": "model+0x14",
            "feedback": "model+0x18",
            "time_seconds": "model+0x1c",
        })
        descriptor = model["buffer_descriptor"]
        self.assertEqual(descriptor["input_count"], 1)
        self.assertEqual(descriptor["output_count"], 2)
        self.assertEqual(descriptor["flags_at_plus_0x18_and_0x1c"], [0, 0])
        self.assertTrue(model["model5_state_and_lane_path_source_bound"])

    def test_model5_math_explains_why_the_delay_level_probe_was_underpowered(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        equation = result["model5_execution"]["process_equation"]
        self.assertEqual(equation["feedback_wire_value_for_api_1_0"], 0.5)
        self.assertAlmostEqual(
            equation["stationary_white_noise_gain_db_at_full_wet"],
            1.2493873660829993)

    def test_audio_root_call_gate_is_sample_rate_and_stereo_link(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        gate = result["audio_root_binding"]["call_gate"]
        self.assertEqual(gate["sample_rate_eligibility_field"],
                         "device+0x5e71")
        self.assertEqual(gate["sample_rate_rule_hz"], "sample_rate <= 96000")
        self.assertEqual(gate["stereo_link_field"], "device+0x5e58 bit 12")
        self.assertEqual(gate["call_condition"],
                         "sample-rate eligible and stereo link clear")

    def test_model_replacement_crossfade_exceeds_old_host_gap(self):
        result = MODULE.analyze_firmware(
            Path("/home/ajuntanaga/.cache/io24/re/io24_fw.bin").read_bytes())
        transition = result["model_replacement_transition"]
        self.assertEqual(transition["nominal_duration_ms"], 40.0)
        self.assertEqual(transition["blocks_at_96khz_512"], 8)
        self.assertEqual(transition["duration_at_96khz_512_ms"],
                         42.666666666666664)
        self.assertEqual(transition["rebuild_trigger_order"],
                         "replayed selector invokes rebuild after bypass")


if __name__ == "__main__":
    unittest.main()
