#!/usr/bin/env python3
"""Hardware-free contracts for the Delay sample-rate configuration trace."""

import importlib.util
import os
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cp34_delay_rate_config_static",
    ROOT / "re" / "cp34_delay_rate_config_static.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

PACKAGE_SPEC = importlib.util.spec_from_file_location(
    "io24_firmware", ROOT / "io24_firmware.py")
PACKAGE = importlib.util.module_from_spec(PACKAGE_SPEC)
PACKAGE_SPEC.loader.exec_module(PACKAGE)

UC472_DLL = Path(os.environ.get(
    "IO24_UC472_DLL",
    Path.home() / ".cache" / "io24" / "re" / "uc472" /
    "dspusbdevice.dll"))


def pinned_package():
    dll = UC472_DLL.read_bytes()
    package = dll[PACKAGE.DLL_FW_START:PACKAGE.DLL_FW_END]
    PACKAGE.inspect_io24_recovery_package(package)
    return package


class DelayRateConfigStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not UC472_DLL.is_file():
            raise unittest.SkipTest("local UC 4.7.2 DLL is unavailable")
        cls.result = MODULE.analyze_firmware(pinned_package())

    def test_pins_exact_firmware_and_schema(self):
        self.assertEqual(self.result["schema"],
                         "cp34-delay-rate-config-v3")
        self.assertEqual(self.result["firmware"]["sha256"],
                         MODULE.FIRMWARE_SHA256)
        self.assertEqual(
            self.result["firmware"]["architecture_evidence"], {
                "format": "complete UC 4.7.2 ARM Cortex-M vendor package",
                "initial_stack_pointer": "0x20000600",
                "reset_vector": "0x60020335",
                "reset_vector_thumb_bit": 1,
                "vfp_in_delay_config": True,
            })

    def test_setu_reaches_selected_delay_runtime_config(self):
        path = self.result["setu_path"]
        self.assertEqual(path["tag"], "Setu")
        self.assertEqual(path["block_config_virtual_slot"], "vtable+0x30")
        self.assertEqual(path["selected_model_handler_virtual_slot"],
                         "vtable+0x00")
        self.assertEqual(path["delay_config_virtual_slot"], "vtable+0x30")
        self.assertEqual(path["delay_config_raw_offset"], "0x572d4")
        self.assertTrue(path["runs_on_each_setu"])

    def test_delay_buffers_double_their_rate_scaled_payload_at_96k(self):
        buffers = self.result["delay_buffers"]
        at_48k = buffers["at_48khz"]
        at_96k = buffers["at_96khz"]
        self.assertEqual(buffers["resize_raw_offset"], "0x3cf90")
        self.assertEqual(buffers["allocator_request_formula"],
                         "(requested_samples + 32) * sizeof(float)")
        self.assertEqual(at_48k["first_capacity_samples"], 16802)
        self.assertEqual(at_48k["second_capacity_samples"], 12002)
        self.assertEqual(at_48k["total_allocator_bytes"], 119568)
        self.assertEqual(at_96k["first_capacity_samples"], 33602)
        self.assertEqual(at_96k["second_capacity_samples"], 24002)
        self.assertEqual(at_96k["total_allocator_bytes"], 234768)
        self.assertEqual(
            buffers["additional_allocator_bytes_48_to_96"], 115200)

    def test_48k_first_does_not_skip_96k_reconfiguration(self):
        conclusion = self.result["conclusion"]
        self.assertFalse(
            conclusion["forty_eight_first_skips_96k_reconfiguration"])
        self.assertTrue(conclusion["rate_scaled_buffer_growth_source_bound"])

    def test_allocator_null_reaches_unchecked_length_division(self):
        path = self.result["allocation_failure_path"]
        self.assertEqual(path["allocator_null_branch_raw_offset"], "0x3d010")
        self.assertTrue(path["null_result_sets_logical_length_zero"])
        self.assertEqual(path["logical_length_field"], "buffer+0x14")
        self.assertEqual(path["process_length_load_raw_offset"], "0x4ec50")
        self.assertTrue(path["process_uses_length_as_divisor"])
        self.assertEqual(path["first_divide_raw_offset"], "0x4ec74")
        self.assertFalse(
            path["length_zero_guard_between_load_and_first_divide"])
        self.assertTrue(path["failure_is_viable_fault_path"])
        self.assertFalse(
            path["actual_96khz_allocation_failure_established"])
        self.assertTrue(
            self.result["conclusion"]
            ["unchecked_allocation_failure_path_source_bound"])

    def test_complete_package_pins_default_allocator_context(self):
        context = self.result["allocator_context"]
        self.assertEqual(context["delay_workspace_virtual_slot"],
                         "vtable+0x18")
        self.assertEqual(context["delay_reported_shared_workspace_bytes"], 0)
        self.assertEqual(context["default_resource_global"], "0x20216658")
        self.assertEqual(context["default_resource_object"], "0x202b0e54")
        self.assertEqual(context["default_resource_vtable"], "0x6008d354")
        self.assertEqual(context["default_resource_realloc_raw_offset"],
                         "0x3ce70")
        self.assertEqual(context["sbrk_heap_start"], "0x202b1860")
        self.assertEqual(context["sbrk_heap_limit"], "0x202b1860")
        self.assertEqual(context["sbrk_static_extendable_bytes"], 0)
        self.assertIn("remain unresolved", context["bounded_interpretation"])

    def test_root_cause_remains_unresolved(self):
        conclusion = self.result["conclusion"]
        self.assertFalse(conclusion["sigma_dsp_mips_overrun_established"])
        self.assertFalse(conclusion["allocation_failure_established"])
        self.assertEqual(conclusion["exact_reset_cause"], "UNRESOLVED")
        self.assertIn("never select hardware model 5",
                      conclusion["safe_host_policy"])
        self.assertEqual(self.result["architecture_string_markers"], {
            "SigmaDSP": False,
            "ADAU": False,
            "SHARC": False,
            "Blackfin": False,
        })

    def test_quiesce_replaces_the_delegate_before_requesting_96khz(self):
        transition = self.result["host_quiesce_transition"]
        self.assertEqual(transition["selector_tag"], "VoFx")
        self.assertEqual(transition["safe_replacement_model"], 0)
        self.assertEqual(transition["active_delegate_field"], "block+0x14")
        self.assertEqual(transition["nominal_transition_ms"], 40.0)
        self.assertEqual(transition["host_selector_settle_ms"], 60.0)
        self.assertEqual(
            transition["post_ack_audio_settle_formula"],
            "2 * old_rate_quantum_frames / old_rate_hz")
        self.assertAlmostEqual(
            transition["post_ack_audio_settle_ms_at_48khz_512"],
            2.0 * 512 / 48000.0 * 1000.0)
        self.assertIn("installer stores the new delegate",
                      transition["replayed_selector_action"])
        self.assertEqual(transition["safe_host_order"][-1],
                         "only then request 96 kHz")
        self.assertFalse(
            transition["usb_reply_is_audio_frame_fence_proven"])

    def test_analyzer_has_no_live_or_wine_dependency(self):
        source = (ROOT / "re" /
                  "cp34_delay_rate_config_static.py").read_text()
        self.assertNotIn("usb.core", source)
        self.assertNotIn("import io24", source)
        self.assertNotIn(".wine-io24", source)
        self.assertNotIn("/home/", source)


if __name__ == "__main__":
    unittest.main()
