#!/usr/bin/env python3
"""Contracts for the offline CP34 per-lane firmware-patch design gate."""

import importlib.util
import json
from pathlib import Path
import unittest

from io24_preset_record import encode_preset_record


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cp34_lane_control_firmware_static",
    ROOT / "re" / "cp34_lane_control_firmware_static.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

PACKAGE_SPEC = importlib.util.spec_from_file_location(
    "io24_firmware", ROOT / "io24_firmware.py")
PACKAGE = importlib.util.module_from_spec(PACKAGE_SPEC)
PACKAGE_SPEC.loader.exec_module(PACKAGE)

UC472_DLL = Path(
    "/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll")


def pinned_application():
    """Return the pinned application span directly from the local UC DLL."""
    dll = UC472_DLL.read_bytes()
    package = dll[PACKAGE.DLL_FW_START:PACKAGE.DLL_FW_END]
    PACKAGE.inspect_io24_recovery_package(package)
    return package[:MODULE.FIRMWARE_SIZE]


class LaneControlFirmwareStaticTests(unittest.TestCase):
    def test_public_schema_is_explicit_and_backward_compatible(self):
        self.assertEqual(MODULE.MODEL_ZERO, 0)
        self.assertEqual(MODULE.LANE_FIELDS,
                         ("wet_ch1", "wet_ch2", "bypass_ch1", "bypass_ch2"))
        self.assertEqual(MODULE.LANE_DEFAULTS, {
            "wet_ch1": 1.0,
            "wet_ch2": 1.0,
            "bypass_ch1": False,
            "bypass_ch2": False,
        })

    def test_design_pins_state_and_two_lane_anchors(self):
        self.assertEqual(
            MODULE.FIRMWARE_CALL_ANCHORS[
                "doubler_private_core_configuration"],
            (0x5AE0E, 0x5A6A8))
        self.assertEqual(
            MODULE.FIRMWARE_CALL_ANCHORS[
                "doubler_binds_lane_zero_then_one"],
            (0x5AEAC, 0x56CC8))
        self.assertEqual(
            MODULE.FIRMWARE_CALL_ANCHORS[
                "block201_dispatches_model_zero"],
            (0x5F260, 0x5E270))
        self.assertIn("block201_structured_state_apply",
                      MODULE.FIRMWARE_CODE_SLICES)
        self.assertIn("doubler_stock_godv_handler",
                      MODULE.FIRMWARE_CODE_SLICES)

    def test_reset_relocation_maps_low_veneer_targets_to_their_raw_code(self):
        self.assertEqual(MODULE.RESET_RELOCATION, {
            "source_raw_start": 0x0FD8,
            "source_raw_end_inclusive": 0x205D0,
            "source_raw_end_exclusive": 0x205D1,
            "itcm_runtime_start": 0x2C0,
            "itcm_runtime_end": 0x1F8B8,
        })
        self.assertEqual(MODULE.RESET_COPY_TABLE, {
            "raw_offset": 0x2C8,
            "source_address": 0x60020FD8,
            "destination_address": 0x2C0,
            "length": 0x1F5F9,
            "next_section_raw_offset": 0x205E0,
        })
        self.assertEqual(MODULE.ITCM_FILE_TO_RUNTIME_DELTA, 0xD18)
        self.assertEqual(MODULE.itcm_runtime_address(0x1E1A8), 0x1D490)
        self.assertEqual(MODULE.itcm_raw_offset(0x1D491), 0x1E1A8)
        self.assertEqual(MODULE.itcm_raw_offset(0x1B6F1), 0x1C408)
        self.assertEqual(MODULE.VENEER_TARGET_CANDIDATES[
            "model0_lane_graph_configuration"],
            (0x10D8F8, 0x00002C41))
        self.assertEqual(MODULE.VENEER_TARGET_CANDIDATES[
            "shared_reverb_audio_path_a"],
            (0x10D868, 0x0001B319))
        self.assertEqual(MODULE.VENEER_TARGET_CANDIDATES[
            "model0_private_core_final_blend"],
            (0x10D910, 0x0001B6F1))

    def test_source_bound_hook_separates_frame_count_mix_and_core_scalar(self):
        self.assertEqual(MODULE.MODEL0_PROCESS_VTABLE_ENTRY, 0x1D491)
        self.assertEqual(MODULE.MODEL0_PROCESS_RAW_OFFSET, 0x1E1A8)
        self.assertEqual(MODULE.MODEL0_RUNTIME_CONFIG_RAW_OFFSET, 0x5BFE0)
        self.assertEqual(MODULE.MODEL0_FRAME_COUNT_WRITE_RAW_OFFSET, 0x5C004)
        self.assertEqual(MODULE.MODEL0_FRAME_COUNT_OFFSET, 0x338)
        self.assertEqual(MODULE.MODEL0_FRAME_COUNT_CONFIG_OFFSET, 0x0C)
        self.assertEqual(MODULE.MODEL0_USER_MIX_LOAD_RAW_OFFSET, 0x1E1CC)
        self.assertEqual(MODULE.MODEL0_USER_MIX_OFFSET, 0x350)
        self.assertEqual(MODULE.MODEL0_CORE_SCALAR_LOAD_RAW_OFFSET, 0x1E2BE)
        self.assertEqual(MODULE.MODEL0_CORE_SCALAR_OFFSET, 0x358)
        self.assertEqual(MODULE.MODEL0_PRIVATE_CORE_CALL_RAW_OFFSET, 0x1E2CC)
        self.assertEqual(MODULE.MODEL0_PRIVATE_CORE_RAW_OFFSET, 0x1C408)

    def test_unexplained_coefficient_arrays_are_explicitly_off_limits(self):
        self.assertEqual(MODULE.UNSAFE_COEFFICIENT_REGIONS, (
            {"offset": "+0x6a4..+0x6b3", "initial_value": 0.5},
            {"offset": "+0x6b4..+0x6c3", "initial_value": 0.5},
        ))

    def test_parent_owned_sidecar_has_exact_in_bounds_layout_and_defaults(self):
        self.assertEqual(MODULE.VOICEFX_PARENT_CONSTRUCTOR_RAW_OFFSET, 0x591BC)
        self.assertEqual(MODULE.MODEL0_EMBEDDED_IN_PARENT_RAW_OFFSET, 0x5DA12)
        self.assertEqual(MODULE.VOICEFX_PARENT_MODEL0_OFFSET, 0x11E0)
        self.assertEqual(MODULE.VOICEFX_PARENT_SIZE, 0x2890)
        self.assertEqual(MODULE.VOICEFX_LANE_SIDECAR, {
            "bypass_ch1": 0x2885,
            "bypass_ch2": 0x2886,
            "padding": 0x2887,
            "wet_ch1": 0x2888,
            "wet_ch2": 0x288C,
        })
        self.assertEqual(MODULE.VOICEFX_SIDECAR_DEFAULT_SITES, {
            "after_parent_constructor": 0x59246,
            "reset": 0x54EC0,
        })
        self.assertLess(0x2885, MODULE.VOICEFX_PARENT_SIZE)
        self.assertLess(0x288C + 4, MODULE.VOICEFX_PARENT_SIZE + 1)

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_reports_verified_parent_sidecar_lifetime(self):
        report = MODULE.analyze_firmware(pinned_application())
        sidecar = report["parent_owned_sidecar"]
        self.assertIn("lifetime_evidence", sidecar)
        self.assertEqual(sidecar["lifetime_evidence"], {
            "embedded_parent": {
                "call_raw_offset": "0x5da12",
                "target_raw_offset": "0x591bc",
                "parent_offset": "0x11e0",
                "next_sibling_offset": "0x3a70",
                "derived_extent": "0x2890",
            },
            "stock_reserved_byte": {
                "offset": "0x2884",
                "constructor_write_raw_offset": "0x59246",
                "reset_write_raw_offset": "0x54ec8",
                "initialized_value": 0,
            },
            "extension_tail": {
                "start": "0x2885",
                "end_exclusive": "0x2890",
                "available_bytes": 11,
            },
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_reports_two_vtable_routes_to_state_apply_entry(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["state_apply_entry"], {
            "primary_vtable_slot_raw_offset": "0x10c6e4",
            "primary_vtable_target_raw_offset": "0x5545c",
            "state_interface_vtable_slot_raw_offset": "0x10c704",
            "state_interface_adjustor_raw_offset": "0x555b8",
            "adjustor_this_delta": -4,
            "adjustor_target_raw_offset": "0x5545c",
            "status": "TOP_LEVEL_STATE_APPLY_SOURCE_BOUND",
        })
        self.assertEqual(
            MODULE.analyze_firmware(pinned_application())["parent_owned_sidecar"]
            ["parser_status"],
            "TOP_LEVEL_AND_MODEL_ZERO_STATE_APPLY_SOURCE_BOUND; "
            "OPTIONAL_FIELD_LOOKUP_UNRESOLVED")

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_reports_model_zero_state_apply_dispatch(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["model_zero_state_apply"], {
            "parent_dispatch_call_raw_offset": "0x5559a",
            "model_state_interface_offset": 4,
            "model_state_interface_vtable_raw_offset": "0x10c8d0",
            "model_state_apply_vtable_slot_raw_offset": "0x10c8d4",
            "model_state_apply_adjustor_raw_offset": "0x548dc",
            "adjustor_this_delta": -4,
            "adjustor_target_raw_offset": "0x546ec",
            "status": "MODEL_ZERO_STATE_APPLY_SOURCE_BOUND",
        })
        self.assertEqual(
            MODULE.analyze_firmware(pinned_application())["parent_owned_sidecar"]
            ["parser_status"],
            "TOP_LEVEL_AND_MODEL_ZERO_STATE_APPLY_SOURCE_BOUND; "
            "OPTIONAL_FIELD_LOOKUP_UNRESOLVED")

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_keeps_stock_godv_callback_distinct_from_state_apply(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["stock_godv_tagged_handler"], {
            "primary_vtable_raw_offset": "0x10c890",
            "primary_handler_vtable_slot_raw_offset": "0x10c890",
            "primary_handler_raw_offset": "0x5bb6c",
            "tag_literal_raw_offset": "0x5bd38",
            "tag_literal": "godv",
            "tag_compare_raw_offset": "0x5bc06",
            "first_stock_state_store_raw_offset": "0x5bc1a",
            "stock_state_offsets": ["0x340", "0x344", "0x348", "0x34c", "0x350"],
            "derived_core_scalar_offset": "0x358",
            "derived_core_scalar_formula": "0.2 * (1 + width)",
            "status": "STOCK_GODV_TAGGED_HANDLER_SOURCE_BOUND",
            "relation_to_structured_state_apply": "UNRESOLVED",
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_corrects_model0_runtime_field_semantics(self):
        report = MODULE.analyze_firmware(pinned_application())
        fields = report["parser_patch"]["model0_runtime_fields"]
        self.assertEqual(fields["frame_count"], {
            "config_offset": "0xc",
            "model_offset": "0x338",
            "write_raw_offset": "0x5c004",
            "process_load_raw_offset": "0x1e1e6",
            "process_use": "buffer stride",
            "lane_selector": False,
        })
        self.assertEqual(fields["user_wet_dry"], {
            "model_offset": "0x350",
            "load_raw_offset": "0x1e1cc",
            "register": "s17",
        })
        self.assertEqual(fields["private_core_scalar"], {
            "model_offset": "0x358",
            "load_raw_offset": "0x1e2be",
            "register": "s0",
            "formula": "0.2 * (1 + width)",
            "user_wet_dry": False,
        })
        self.assertEqual(report["dsp_patch"]["per_lane_blend_control_hook"],
                         "UNRESOLVED")

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_limits_no_direct_edge_claim_to_two_code_slices(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["state_apply_godv_direct_edge_evidence"], {
            "model_zero_state_apply": {
                "raw_start": "0x546ec",
                "raw_end_exclusive": "0x548cc",
                "immediate_edges_to_stock_godv_tagged_handler": [],
                "indirect_blx_sites": [
                    "0x54730", "0x54776", "0x54788", "0x5479c", "0x5480e", "0x548b4",
                ],
            },
            "stock_godv_tagged_handler": {
                "raw_start": "0x5bb6c",
                "raw_end_exclusive": "0x5bd30",
                "immediate_edges_to_model_zero_state_apply": [],
                "indirect_blx_sites": [],
            },
            "status": "NO_IMMEDIATE_CROSS_EDGE_IN_VALIDATED_SLICES",
            "boundary": "INDIRECT_OR_INTERPROCEDURAL_RELATIONSHIP_UNRESOLVED",
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_binds_receiver_but_not_target_of_state_apply_call_54730(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["state_apply_indirect_call_0x54730"], {
            "top_level_receiver_capture_raw_offset": "0x55462",
            "model_state_call_argument_raw_offset": "0x55592",
            "model_state_receiver_capture_raw_offset": "0x546f0",
            "model_capture_raw_offset": "0x546f6",
            "receiver_stack_save_raw_offset": "0x54708",
            "receiver_stack_reload_raw_offset": "0x54726",
            "output_argument_setup_raw_offset": "0x54728",
            "output_argument_model_offset": "0x340",
            "receiver_vtable_load_raw_offset": "0x5472c",
            "vtable_slot_offset": 8,
            "target_load_raw_offset": "0x5472e",
            "call_raw_offset": "0x54730",
            "return_compare_raw_offset": "0x54732",
            "return_compare_immediate": 0x14,
            "status": "CALLER_SUPPLIED_RECEIVER_VTABLE_TARGET_UNRESOLVED",
            "relation_to_stock_godv_tagged_handler": "UNRESOLVED",
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_keeps_receiver_type_unresolved_across_apply_entries(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["state_apply_receiver_type_boundary"], {
            "top_level_apply_entry_literal_raw_offsets": ["0x10c520", "0x10c6e4"],
            "top_level_receiver_capture_raw_offset": "0x55462",
            "top_level_receiver_virtual_calls": [
                {
                    "receiver_vtable_load_raw_offset": "0x554c8",
                    "target_load_raw_offset": "0x554d0",
                    "vtable_slot_offset": 0,
                    "call_raw_offset": "0x554d4",
                },
                {
                    "receiver_vtable_load_raw_offset": "0x554e4",
                    "target_load_raw_offset": "0x554f6",
                    "vtable_slot_offset": 4,
                    "call_raw_offset": "0x554fa",
                },
            ],
            "model_zero_receiver_call_raw_offset": "0x54730",
            "model_zero_receiver_vtable_slot_offset": 8,
            "receiver_type": "UNRESOLVED",
            "receiver_vtable_target": "UNRESOLVED",
            "status": "NO_CONCRETE_RECEIVER_TYPE_IN_VALIDATED_TOP_LEVEL_FLOW",
            "boundary": (
                "TOP_LEVEL_APPLY_ENTRY_LITERALS_DO_NOT_BIND_"
                "THE_CALLER_SUPPLIED_RECEIVER_TYPE"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_keeps_owner_installations_separate_from_input_receiver(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["state_apply_owner_construction_boundary"], {
            "shared_apply_entry_raw_offset": "0x5545c",
            "owner_installations": [
                {
                    "primary_vtable_raw_offset": "0x10c4e8",
                    "apply_entry_vtable_slot_raw_offset": "0x10c520",
                    "apply_entry_vtable_offset": "0x38",
                    "installation_sites": [
                        {
                            "vtable_literal_raw_offset": "0x3d708",
                            "vtable_load_raw_offset": "0x3d684",
                            "vtable_store_raw_offset": "0x3d686",
                            "owner_base_register": "r8",
                            "owner_offset": "0x22c",
                        },
                        {
                            "vtable_literal_raw_offset": "0x3d868",
                            "vtable_load_raw_offset": "0x3d7dc",
                            "vtable_store_raw_offset": "0x3d7de",
                            "owner_base_register": "r8",
                            "owner_offset": "0x22c",
                        },
                    ],
                    "owner_identity": "UNRESOLVED",
                },
                {
                    "primary_vtable_raw_offset": "0x10c6bc",
                    "apply_entry_vtable_slot_raw_offset": "0x10c6e4",
                    "apply_entry_vtable_offset": "0x28",
                    "installation_sites": [
                        {
                            "vtable_literal_raw_offset": "0x418fc",
                            "vtable_load_raw_offset": "0x41888",
                            "owner_address_setup_raw_offset": "0x4188a",
                            "vtable_store_raw_offset": "0x4189a",
                            "owner_base_register": "r4",
                            "owner_offset": "0x11e0",
                        },
                    ],
                    "owner_identity": "VOICEFX_OWNER_ENTRY_SOURCE_BOUND",
                },
            ],
            "incoming_receiver_register": "r1",
            "incoming_receiver_capture_raw_offset": "0x55462",
            "owner_entry_constrains_input_receiver": False,
            "status": "OWNER_INSTALLATIONS_DO_NOT_BIND_INPUT_RECEIVER_TYPE",
            "boundary": (
                "SEPARATE_R1_RECEIVER_IS_NOT_MATERIALIZED_BY_EITHER_"
                "VALIDATED_OWNER_INSTALLATION"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_binds_secondary_interface_owner_but_not_caller_r1(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["voicefx_secondary_state_interface_caller_boundary"], {
            "embedded_owner_primary_offset": "0x11e0",
            "embedded_owner_secondary_state_interface_offset": "0x11e4",
            "constructor_vtable_literal_raw_offset": "0x418fc",
            "constructor_primary_vtable_load_raw_offset": "0x41888",
            "constructor_primary_state_address_raw_offset": "0x4188a",
            "constructor_secondary_state_offset_setup_raw_offset": "0x4188e",
            "constructor_secondary_vtable_setup_raw_offset": "0x41896",
            "constructor_primary_vtable_store_raw_offset": "0x4189a",
            "constructor_secondary_vtable_store_raw_offset": "0x418a0",
            "primary_vtable_raw_offset": "0x10c6bc",
            "secondary_vtable_raw_offset": "0x10c700",
            "secondary_apply_vtable_slot_raw_offset": "0x10c704",
            "secondary_apply_vtable_slot_offset": "0x4",
            "secondary_apply_adjustor_raw_offset": "0x555b8",
            "adjustor_this_delta": -4,
            "top_level_apply_raw_offset": "0x5545c",
            "top_level_apply_this_embedded_owner_offset": "0x11e0",
            "caller_dispatch": "UNRESOLVED",
            "r1_argument_provenance": "UNRESOLVED",
            "status": (
                "SECONDARY_INTERFACE_ROUTE_SOURCE_BOUND_"
                "CALLER_AND_R1_UNRESOLVED"),
            "boundary": (
                "SECONDARY_INTERFACE_CONSTRUCTION_BINDS_R0_TO_EMBEDDED_OWNER_BUT_NO_"
                "VALIDATED_STATIC_CALLER_MATERIALIZES_R1"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_keeps_primary_slot_dispatches_unbound_to_embedded_owner(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["primary_apply_embedded_owner_caller_boundary"], {
            "embedded_owner_primary_offset": "0x11e0",
            "required_primary_vtable_raw_offset": "0x10c6bc",
            "required_primary_apply_vtable_slot_raw_offset": "0x10c6e4",
            "required_primary_apply_vtable_slot_offset": "0x28",
            "local_straight_line_primary_slot_dispatches": [
                {
                    "receiver_vtable_load_raw_offset": "0x27442",
                    "slot_load_raw_offset": "0x27452",
                    "call_raw_offset": "0x27458",
                },
                {
                    "receiver_vtable_load_raw_offset": "0x27c82",
                    "slot_load_raw_offset": "0x27c90",
                    "call_raw_offset": "0x27c9a",
                },
                {
                    "receiver_vtable_load_raw_offset": "0x281d6",
                    "slot_load_raw_offset": "0x281e4",
                    "call_raw_offset": "0x281f0",
                },
                {
                    "receiver_vtable_load_raw_offset": "0x2dfa4",
                    "slot_load_raw_offset": "0x2dfaa",
                    "call_raw_offset": "0x2dfb2",
                },
                {
                    "receiver_vtable_load_raw_offset": "0x3041a",
                    "slot_load_raw_offset": "0x3041c",
                    "call_raw_offset": "0x3041e",
                },
                {
                    "receiver_vtable_load_raw_offset": "0x30568",
                    "slot_load_raw_offset": "0x3056c",
                    "call_raw_offset": "0x30572",
                },
                {
                    "receiver_vtable_load_raw_offset": "0x30cc8",
                    "slot_load_raw_offset": "0x30cd8",
                    "call_raw_offset": "0x30ce2",
                },
                {
                    "receiver_vtable_load_raw_offset": "0x30d36",
                    "slot_load_raw_offset": "0x30d40",
                    "call_raw_offset": "0x30d44",
                },
                {
                    "receiver_vtable_load_raw_offset": "0x30d80",
                    "slot_load_raw_offset": "0x30d8a",
                    "call_raw_offset": "0x30d8c",
                },
                {
                    "receiver_vtable_load_raw_offset": "0x5344c",
                    "slot_load_raw_offset": "0x5344e",
                    "call_raw_offset": "0x53450",
                },
            ],
            "source_bound_embedded_owner_dispatches": [],
            "status": "NO_LOCAL_STRAIGHT_LINE_EMBEDDED_OWNER_PRIMARY_APPLY_CALLER",
            "boundary": (
                "PRIMARY_SLOT_MATCHES_DO_NOT_IDENTIFY_0X10C6BC_OR_"
                "R1_PROVENANCE"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_keeps_stat_tag_sites_distinct_from_apply_dispatch(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["structured_state_dispatcher_boundary"], {
            "fourcc": "Stat",
            "fourcc_big_endian_value": "0x53746174",
            "literal_raw_offsets": [
                "0x2f278", "0x30a10", "0x30a60", "0x30bdc", "0x30c30",
                "0x41ea0", "0x423d4",
            ],
            "tag_comparisons": [
                {
                    "tag_literal_raw_offset": "0x2f278",
                    "literal_load_raw_offset": "0x2f22a",
                    "record_tag_load_raw_offset": "0x2f230",
                    "tag_compare_raw_offset": "0x2f232",
                },
                {
                    "tag_literal_raw_offset": "0x30a10",
                    "literal_load_raw_offset": "0x309aa",
                    "record_tag_load_raw_offset": "0x309a2",
                    "tag_compare_raw_offset": "0x309ac",
                },
                {
                    "tag_literal_raw_offset": "0x30a60",
                    "literal_load_raw_offset": "0x30a1a",
                    "record_tag_load_raw_offset": "0x30a1c",
                    "tag_compare_raw_offset": "0x30a20",
                },
                {
                    "tag_literal_raw_offset": "0x30bdc",
                    "literal_load_raw_offset": "0x30b84",
                    "record_tag_load_raw_offset": "0x30b76",
                    "tag_compare_raw_offset": "0x30b8a",
                },
                {
                    "tag_literal_raw_offset": "0x30c30",
                    "literal_load_raw_offset": "0x30be2",
                    "record_tag_load_raw_offset": "0x30be6",
                    "tag_compare_raw_offset": "0x30bea",
                },
                {
                    "tag_literal_raw_offset": "0x41ea0",
                    "literal_load_raw_offset": "0x41c5e",
                    "record_tag_load_raw_offset": "0x41c5c",
                    "tag_compare_raw_offset": "0x41c60",
                },
                {
                    "tag_literal_raw_offset": "0x423d4",
                    "literal_load_raw_offset": "0x420e6",
                    "record_tag_load_raw_offset": "0x420e4",
                    "tag_compare_raw_offset": "0x420e8",
                },
            ],
            "linear_decode_immediate_apply_edges": [
                {
                    "source_raw_offset": "0x555bc",
                    "mnemonic": "b.w",
                    "target_raw_offset": "0x5545c",
                },
            ],
            "known_state_interface_adjustor_tail_branch_raw_offset": "0x555bc",
            "stat_tag_sites_at_immediate_apply_edge_sources": [],
            "caller_dispatch": "UNRESOLVED",
            "r1_argument_provenance": "UNRESOLVED",
            "status": (
                "STRUCTURED_STATE_TAG_SITES_SOURCE_BOUND_DIRECT_APPLY_ROUTE_"
                "UNRESOLVED"),
            "boundary": (
                "TAG_COMPARISONS_DO_NOT_BIND_A_DYNAMIC_DISPATCH_TARGET_OR_"
                "R1_PROVENANCE"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_zero_selector_route_binds_final_derived_structured_state_slot(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["zero_selector_recall_vtable_correction"], {
            "zero_selector": {
                "query": "{0, 0}",
                "result": "final derived device global 0x20216660",
                "final_primary_vtable": "0x6012cb40",
            },
            "construction_order": {
                "lazy_initializer": "0x3d4f0",
                "derived_constructor_call": "0x3d52a -> 0x5e014",
                "base_constructor_call": "0x5e018 -> 0x5d990",
                "transient_base_vtable": "0x6008d3a8",
                "final_vtable_header": "0x5e08c -> 0x6012cb38",
                "final_vtable_formation": (
                    "0x5e02a: 0x6012cb38 + 8 -> 0x6012cb40"
                ),
                "final_vtable_store": "0x5e036 -> [global+0]",
                "registered_teardown": "0x41580",
            },
            "final_primary_vtable": {
                "dispatcher_slot": "0x10cb40 -> 0x420bc",
                "callback_slot_0x38": "0x10cb78 -> 0x531e0",
            },
            "callbacks": {
                "first": "0x42266 -> 0x531e0",
                "second": "0x42280 -> 0x531e0",
                "structured_state_0x531e0_reached": True,
            },
            "retraction": {
                "intermediate_primary_noop_claim": "RETRACTED",
                "root_cause": (
                    "transient base-construction and teardown writes were "
                    "mistaken for final derived state"
                ),
            },
            "status": (
                "ZERO_SELECTOR_STAT_ROUTE_SOURCE_BOUND_FINAL_DERIVED_SLOT_"
                "0X38_0X531E0"
            ),
            "boundary": (
                "0X531E0_RUNTIME_COMPLETION_SELECTED_COMPONENT_AND_PHYSICAL_"
                "OUTCOMES_REMAIN_UNRESOLVED"
            ),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_binds_stat_first_handoff_to_structured_state(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["stat_dispatcher_first_handoff_boundary"], {
            "live_dispatcher_vtable_raw_offset": "0x10cb40",
            "live_dispatcher_raw_offset": "0x420bc",
            "stat_tag": {
                "outer_input_r1_capture_raw_offset": "0x420c4",
                "record_tag_load_raw_offset": "0x420e4",
                "literal_load_raw_offset": "0x420e6",
                "compare_raw_offset": "0x420e8",
                "branch_raw_offset": "0x420ea",
                "branch_target_raw_offset": "0x42200",
            },
            "first_vtable_handoff": {
                "receiver_capture_raw_offset": "0x420c8",
                "r6_byte_load_raw_offset": "0x4222c",
                "r2_argument_setup_raw_offset": "0x4225e",
                "r1_argument_setup_raw_offset": "0x42260",
                "vtable_target_load_raw_offset": "0x42262",
                "vtable_offset": "0x38",
                "call_raw_offset": "0x42266",
                "pinned_vtable_slot_raw_offset": "0x10cb78",
                "pinned_target_raw_offset": "0x531e0",
            },
            "structured_state_entry": {
                "r1_capture_raw_offset": "0x531e8",
                "r2_capture_raw_offset": "0x531ee",
            },
            "top_level_apply_raw_offset": "0x5545c",
            "top_level_apply_r1_provenance": "UNRESOLVED",
            "status": (
                "STAT_DISPATCHER_FIRST_VTABLE_HANDOFF_SOURCE_BOUND_TOP_LEVEL_"
                "R1_UNRESOLVED"),
            "boundary": (
                "FIRST_HANDOFF_DOES_NOT_BIND_COMPONENT_SELECTION_OR_TOP_LEVEL_"
                "R1"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_binds_indexed_state_dispatch_but_not_selected_component(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["indexed_component_dispatch_boundary"], {
            "indexed_dispatch": {
                "device_receiver_capture_raw_offset": "0x531e6",
                "device_receiver_stack_save_raw_offset": "0x531f2",
                "table_offset_setup_raw_offset": "0x53228",
                "table_base_store_raw_offset": "0x53230",
                "selection_loop_counter_init_raw_offset": "0x532b0",
                "selection_index_init_raw_offset": "0x532b4",
                "selection_loop_counter_increment_raw_offset": "0x532f0",
                "selected_index_capture_raw_offset": "0x5332a",
                "table_base_reload_raw_offset": "0x53370",
                "record_argument_setup_raw_offset": "0x53372",
                "indexed_object_load_raw_offset": "0x53374",
                "object_vtable_load_raw_offset": "0x53378",
                "state_interface_slot_load_raw_offset": "0x5337a",
                "call_raw_offset": "0x5337c",
                "table_device_offset": "0x5e78",
                "entry_stride": 8,
                "selected_index_register": "r7",
                "selected_index": "DYNAMIC_UNRESOLVED",
            },
            "voicefx_slot_one_constructor_binding": {
                "constructor_device_capture_raw_offset": "0x5e016",
                "state_interface_offset_setup_raw_offset": "0x5e022",
                "table_offset_setup_raw_offset": "0x5e026",
                "state_interface_address_setup_raw_offset": "0x5e030",
                "slot_address_setup_raw_offset": "0x5e044",
                "slot_store_raw_offset": "0x5e058",
                "table_device_offset": "0x5e78",
                "slot_index": 1,
                "slot_device_offset": "0x5e80",
                "voicefx_state_interface_device_offset": "0x11e4",
            },
            "voicefx_slot_one_state_apply_route": {
                "state_interface_vtable_raw_offset": "0x10c700",
                "state_interface_vtable_slot_raw_offset": "0x10c704",
                "state_interface_vtable_slot_offset": "0x4",
                "adjustor_raw_offset": "0x555b8",
                "adjustor_tail_branch_raw_offset": "0x555bc",
                "top_level_apply_raw_offset": "0x5545c",
            },
            "top_level_apply_r1_provenance": "UNRESOLVED",
            "status": (
                "INDEXED_COMPONENT_DISPATCH_SOURCE_BOUND_VOICEFX_SLOT_ONE_ROUTE_"
                "SELECTED_INDEX_UNRESOLVED"),
            "boundary": (
                "DYNAMIC_R7_SELECTION_DOES_NOT_PROVE_BLOCK201_OR_"
                "0X5545C_R1_PROVENANCE"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_binds_component_key_compare_but_not_voicefx_selection(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["structured_state_component_key_compare_boundary"], {
            "candidate_key_layout": {
                "key_table_device_offset": "0x5e7c",
                "entry_stride": 8,
                "selection_index_register": "r8",
                "selection_index_init_raw_offset": "0x5324a",
                "selection_index_initial_value": 0,
                "indexed_key_load_raw_offset": "0x5326e",
                "key_stack_store_raw_offset": "0x53272",
                "key_stack_slot": "sp+0x8",
                "slot_zero_key_constructor_literal_load_raw_offset": "0x5e04c",
                "slot_zero_key_literal_raw_offset": "0x5e090",
                "slot_zero_key_value": "0x6f707420",
                "slot_zero_key_fourcc": "opt ",
                "voicefx_slot_one_key_store_raw_offset": "0x5e05e",
                "voicefx_slot_one_key_device_offset": "0x5e84",
                "voicefx_slot_one_key_value": "0xc9",
            },
            "decoded_key_reader": {
                "output_stack_slot": "sp+0x4c",
                "output_zero_raw_offset": "0x53300",
                "output_pointer_setup_raw_offset": "0x532fc",
                "call_raw_offset": "0x53308",
                "reader_raw_offset": "0x2cf58",
                "required_read_length": 4,
                "read_length_compare_raw_offset": "0x2cf70",
                "byte_reverse_raw_offset": "0x2cf78",
                "output_store_raw_offset": "0x2cf7a",
            },
            "key_compare": {
                "decoded_key_load_raw_offset": "0x53322",
                "candidate_key_load_raw_offset": "0x53324",
                "compare_raw_offset": "0x53326",
                "mismatch_branch_raw_offset": "0x53328",
                "selected_index_capture_raw_offset": "0x5332a",
            },
            "selection_index_runtime_value": "UNRESOLVED",
            "voicefx_slot_one_selection": "UNRESOLVED",
            "status": (
                "COMPONENT_KEY_COMPARE_SOURCE_BOUND_DYNAMIC_SLOT_SELECTION_"
                "UNRESOLVED"),
            "boundary": (
                "KEY_MATCH_AND_SLOT_ONE_KEY_LITERAL_DO_NOT_BIND_R7_TO_SLOT_ONE_"
                "OR_BLOCK201"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_structured_state_requires_u32_two_before_component_selection(self):
        records = json.loads((ROOT / "re" / "uc_factory_presets.json").read_text())
        slap_echo = dict(records[4])
        slap_echo.pop("_offset")
        encoded = encode_preset_record(slap_echo)
        self.assertEqual(len(encoded), 850)
        self.assertEqual(encoded[:4], bytes.fromhex("7b690b70"))

        application = pinned_application()
        embedded = application[0x6B1C8:0x6B1C8 + 850]
        self.assertEqual(len(embedded), 850)
        self.assertEqual(embedded[:4], bytes.fromhex("7b690b70"))
        self.assertEqual(encoded[:4], embedded[:4])
        parser = MODULE.analyze_firmware(application)["parser_patch"]
        self.assertIn("structured_state_record_prefix_gate_boundary", parser)
        self.assertEqual(parser["structured_state_record_prefix_gate_boundary"], {
            "record_stream_adapter": {
                "wrapper_constructor_call_raw_offset": "0x531f6",
                "wrapper_constructor_raw_offset": "0x2cd30",
                "underlying_stream_store_raw_offset": "0x53200",
                "specialized_vtable_literal_load_raw_offset": "0x531fa",
                "specialized_vtable_literal_raw_offset": "0x534c4",
                "specialized_vtable_raw_offset": "0x66b54",
                "specialized_vtable_store_raw_offset": "0x53202",
                "read_slot_target_raw_offset": "0x2cd20",
            },
            "four_byte_entry_read": {
                "output_stack_slot": "sp+0x48",
                "output_zero_raw_offset": "0x53204",
                "reader_call_raw_offset": "0x53206",
                "reader_raw_offset": "0x2ce10",
                "required_read_length": 4,
                "underlying_read_slot_offset": "0x8",
                "wrapper_byte_reverse_enabled": False,
            },
            "entry_gate": {
                "value_load_raw_offset": "0x5320e",
                "required_value": 2,
                "compare_raw_offset": "0x53212",
                "accepted_branch_raw_offset": "0x53216",
                "accepted_target_raw_offset": "0x53222",
                "rejected_result_setup_raw_offset": "0x53218",
                "rejected_return_raw_offset": "0x5321a",
            },
            "factory_slap_echo_raw_archive": {
                "raw_offset": "0x6b1c8",
                "size": 850,
                "prefix_hex": "7b690b70",
                "prefix_native_u32": "0x700b697b",
                "direct_entry_gate_match": False,
            },
            "status": (
                "STRUCTURED_STATE_PREFIX_GATE_SOURCE_BOUND_RAW_FACTORY_ARCHIVE_"
                "NOT_DIRECTLY_ELIGIBLE"),
            "boundary": (
                "STORAGE_OR_RECALL_TRANSFORMATION_AND_COMPONENT_SELECTION_"
                "REMAIN_UNRESOLVED"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_stat_handoff_binds_cursor_zero_stream_to_structured_state(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertIn("stat_record_stream_cursor_boundary", parser)
        self.assertEqual(parser["stat_record_stream_cursor_boundary"], {
            "fragment_accumulation": {
                "stat_branch_target_raw_offset": "0x42200",
                "input_record_register": "r4",
                "copy_extent_word_load_raw_offset": "0x42200",
                "copy_extent_word_object_offset": "0x19",
                "fragment_offset_load_raw_offset": "0x42208",
                "fragment_offset_object_offset": "0x12",
                "device_buffer_base_setup_raw_offset": "0x4220c",
                "device_buffer_offset": "0x18",
                "buffer_capacity_setup_raw_offset": "0x42204",
                "buffer_capacity": "0xc1c",
                "fragment_data_advance_raw_offset": "0x42210",
                "fragment_data_object_offset": "0x1d",
                "copy_extent_end_add_raw_offset": "0x42212",
                "copy_extent_cap_compare_raw_offset": "0x42214",
                "copy_extent_cap_subtract_raw_offset": "0x42218",
                "copy_destination_offset_add_raw_offset": "0x4221a",
                "copy_length_setup_raw_offset": "0x4221c",
                "copy_call_raw_offset": "0x4221e",
                "copy_target_raw_offset": "0x10d930",
                "fragment_offset_reload_raw_offset": "0x42222",
                "completed_length_add_raw_offset": "0x42226",
                "completed_length_store_raw_offset": "0x42228",
                "completed_length_device_offset": "0xc34",
                "completion_byte_load_raw_offset": "0x4222c",
                "completion_byte_object_offset": "0x16",
                "required_completion_value": 0,
            },
            "stack_stream": {
                "buffer_argument_setup_raw_offset": "0x42234",
                "stream_address_setup_raw_offset": "0x42236",
                "constructor_call_raw_offset": "0x42238",
                "constructor_raw_offset": "0x2ccf4",
                "span_constructor_raw_offset": "0x2ca5c",
                "span_receiver_setup_raw_offset": "0x2cd06",
                "span_constructor_call_raw_offset": "0x2cd0c",
                "data_pointer_and_length_store_raw_offset": "0x2ca78",
                "data_pointer_receiver_offset": "0x8",
                "data_length_receiver_offset": "0xc",
                "limit_store_raw_offset": "0x2cd14",
                "limit_receiver_offset": "0x20",
                "cursor_zero_store_raw_offset": "0x2cd16",
                "cursor_receiver_offset": "0x1c",
                "data_pointer_source": "DEVICE_PLUS_0X18",
            },
            "caller_cursor_reset": {
                "r2_zero_setup_raw_offset": "0x42240",
                "zero_stack_argument_store_raw_offset": "0x42242",
                "cursor_adjust_call_raw_offset": "0x42244",
                "cursor_adjust_raw_offset": "0x2cb60",
                "stack_argument_load_raw_offset": "0x2cb62",
                "zero_mode_branch_raw_offset": "0x2cb6e",
                "zero_cursor_store_raw_offset": "0x2cb8c",
                "cursor_value_at_handoff": 0,
            },
            "structured_state_handoff": {
                "stream_argument_setup_raw_offset": "0x4225e",
                "call_raw_offset": "0x42266",
                "callee_raw_offset": "0x531e0",
                "stream_capture_raw_offset": "0x531ee",
                "wrapper_stream_store_raw_offset": (
                    "0x53200"
                ),
            },
            "first_read": {
                "underlying_vtable_raw_offset": "0x669ec",
                "read_vtable_slot_raw_offset": "0x669f4",
                "read_raw_offset": "0x2cbb4",
                "cursor_and_limit_load_raw_offset": "0x2cbb6",
                "data_pointer_load_raw_offset": "0x2cbc8",
                "data_plus_cursor_add_raw_offset": "0x2cbd0",
                "copy_call_raw_offset": "0x2cbd2",
                "copy_target_raw_offset": "0x10d930",
                "cursor_reload_raw_offset": "0x2cbd6",
                "cursor_advance_raw_offset": "0x2cbd8",
                "cursor_store_raw_offset": "0x2cbda",
                "requested_bytes": 4,
            },
            "first_word_source": (
                "CALLER_SUPPLIED_STAT_BYTES_AT_DEVICE_PLUS_0X18_OFFSET_ZERO"),
            "first_word_runtime_value": "CALLER_SUPPLIED_DYNAMIC_UNRESOLVED",
            "status": (
                "STAT_STREAM_CURSOR_ZERO_SOURCE_BOUND_FIRST_WORD_FROM_"
                "ACCUMULATION_BUFFER"),
            "boundary": (
                "FIRST_WORD_RUNTIME_VALUE_AND_PHYSICAL_EFFECT_REMAIN_"
                "UNRESOLVED"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_stat_handoff_enables_selector_gate_if_reached(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["stat_selector_enable_boundary"], {
            "direct_stat_handoff": {
                "r0_vtable_load_raw_offset": "0x4225a",
                "r3_enable_setup_raw_offset": "0x4225c",
                "r3_enable_value": 1,
                "r2_argument_setup_raw_offset": "0x4225e",
                "r1_argument_setup_raw_offset": "0x42260",
                "vtable_target_load_raw_offset": "0x42262",
                "r0_receiver_setup_raw_offset": "0x42264",
                "call_raw_offset": "0x42266",
                "pinned_vtable_slot_raw_offset": "0x10cb78",
                "target_raw_offset": "0x531e0",
            },
            "structured_state_gate": {
                "r3_capture_raw_offset": "0x531f4",
                "selector_gate_compare_raw_offset": "0x53232",
                "selector_disabled_branch_raw_offset": "0x53234",
                "selector_disabled_branch_target_raw_offset": "0x534ba",
                "selector_enabled_fallthrough_raw_offset": "0x53238",
            },
            "selector_gate": "ENABLED_IF_REACHED",
            "selected_component": "UNRESOLVED",
            "top_level_apply_r1_provenance": "UNRESOLVED",
            "status": (
                "DIRECT_STAT_HANDOFF_ENABLES_SELECTOR_GATE_IF_REACHED_"
                "COMPONENT_SELECTION_UNRESOLVED"),
            "boundary": (
                "EARLIER_HELPER_COMPLETION_AND_SELECTED_COMPONENT_REMAIN_"
                "UNRESOLVED"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_stat_pair_binds_arguments_to_structured_state_gates(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["paired_stat_handoff_entry_gates_boundary"], {
            "caller_zero_gate": {
                "r6_byte_load_raw_offset": "0x4222c",
                "zero_compare_raw_offset": "0x4222e",
                "nonzero_exit_branch_raw_offset": "0x42230",
                "zero_continuation_raw_offset": "0x42234",
                "r6_value_on_zero_continuation": 0,
                "continuation_qualification": (
                    "NORMAL_RETURN_AND_AAPCS_CALLEE_SAVED_R6"),
            },
            "first_handoff": {
                "r1_setup_raw_offset": "0x42260",
                "r1_source_register": "r6",
                "r1_value_on_zero_continuation": 0,
                "r3_setup_raw_offset": "0x4225c",
                "r3_value": 1,
                "call_raw_offset": "0x42266",
                "entry_gate_if_reached": (
                    "R1_ZERO_THEN_R3_SELECTOR_GATE_ENABLED"),
            },
            "second_handoff": {
                "r3_setup_raw_offset": "0x42276",
                "r3_source_register": "r6",
                "r3_value_on_zero_continuation": 0,
                "r1_setup_raw_offset": "0x4227e",
                "r1_value": 1,
                "call_raw_offset": "0x42280",
                "entry_gate_if_reached": (
                    "R1_NONZERO_TAKES_ALTERNATE_BRANCH_BEFORE_R3_SELECTOR_GATE"),
            },
            "structured_state_target": {
                "vtable_slot_raw_offset": "0x10cb78",
                "target_raw_offset": "0x531e0",
                "r1_capture_raw_offset": "0x531e8",
                "r1_alternate_gate_compare_raw_offset": "0x53222",
                "r1_alternate_branch_raw_offset": "0x53224",
                "r1_alternate_branch_target_raw_offset": "0x5338e",
                "r3_capture_raw_offset": "0x531f4",
                "r3_selector_gate_compare_raw_offset": "0x53232",
                "r3_selector_disabled_branch_raw_offset": "0x53234",
            },
            "selector_completion": "UNRESOLVED",
            "selected_component": "UNRESOLVED",
            "top_level_apply_r1_provenance": "UNRESOLVED",
            "status": (
                "PAIRED_STAT_HANDOFF_ENTRY_GATES_SOURCE_BOUND_COMPONENT_"
                "SELECTION_UNRESOLVED"),
            "boundary": (
                "ENTRY_GATE_CONFIGURATION_DOES_NOT_PROVE_HELPER_COMPLETION_"
                "OR_COMPONENT_SELECTION"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_alternate_callback_is_constructed_cursor_snapshot_not_parser_semantics(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["alternate_cursor_callback_boundary"], {
            "stack_receiver_construction": {
                "caller_stack_address_setup_raw_offset": "0x42236",
                "constructor_call_raw_offset": "0x42238",
                "constructor_raw_offset": "0x2ccf4",
                "constructor_vtable_literal_load_raw_offset": "0x2ccf6",
                "constructor_vtable_literal_raw_offset": "0x2cd1c",
                "constructor_vtable_base_address": "0x600869e4",
                "stored_vtable_address": "0x600869ec",
                "constructor_vtable_store_raw_offset": "0x2cd04",
                "post_constructor_cursor_adjust_call_raw_offset": "0x42244",
                "post_constructor_cursor_adjust_raw_offset": "0x2cb60",
                "cursor_only_store_raw_offsets": [
                    "0x2cb8c", "0x2cb9a", "0x2cba2", "0x2cbae"],
                "receiver_continuation_qualification": "AAPCS_CALLEE_SAVED_R4",
            },
            "alternate_callback": {
                "structured_state_r2_capture_raw_offset": "0x531ee",
                "alternate_branch_target_raw_offset": "0x5338e",
                "receiver_vtable_load_raw_offset": "0x5338e",
                "receiver_setup_raw_offset": "0x53390",
                "first_vtable_entry_load_raw_offset": "0x53396",
                "call_raw_offset": "0x53398",
                "vtable_raw_offset": "0x669ec",
                "vtable_first_entry_raw_offset": "0x669ec",
                "callback_raw_offset": "0x2cb58",
                "returned_word_receiver_offset": "0x1c",
                "callback_word_load_raw_offset": "0x2cb58",
                "callback_sign_extend_raw_offset": "0x2cb5a",
                "callback_return_raw_offset": "0x2cb5c",
                "returned_low_capture_raw_offset": "0x5339e",
                "returned_high_capture_raw_offset": "0x533a6",
            },
            "returned_word_semantics": "UNRESOLVED",
            "selected_component": "UNRESOLVED",
            "top_level_apply_r1_provenance": "UNRESOLVED",
            "status": (
                "ALTERNATE_CONSTRUCTED_CURSOR_CALLBACK_SOURCE_BOUND_IF_REACHED_"
                "SEMANTICS_UNRESOLVED"),
            "boundary": (
                "SIGN_EXTENDED_RECEIVER_PLUS_0X1C_VALUE_DOES_NOT_BIND_PARSER_"
                "STATE_R7_OR_VOICEFX_SLOT_ONE"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_alternate_cursor_adjust_is_zero_argument_but_not_semantic_parser_proof(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["alternate_cursor_adjust_boundary"], {
            "alternate_call": {
                "r5_zero_setup_raw_offset": "0x531ea",
                "r5_zero_capture_raw_offset": "0x531f0",
                "r5_continuation_qualification": "AAPCS_CALLEE_SAVED_R5",
                "receiver_vtable_load_raw_offset": "0x533b0",
                "r2_setup_raw_offset": "0x533b4",
                "r2_source_register": "r6",
                "r3_setup_raw_offset": "0x533b8",
                "r3_source_register": "r7",
                "stack_argument_store_raw_offset": "0x533ba",
                "stack_argument_source_register": "r5",
                "stack_argument_value_under_abi": 0,
                "receiver_setup_raw_offset": "0x533bc",
                "vtable_slot_load_raw_offset": "0x533c2",
                "call_raw_offset": "0x533c6",
                "vtable_slot_raw_offset": "0x669f0",
                "callback_raw_offset": "0x2cb60",
            },
            "zero_argument_callback_path": {
                "stack_argument_load_raw_offset": "0x2cb62",
                "zero_branch_raw_offset": "0x2cb6e",
                "zero_branch_target_raw_offset": "0x2cb8a",
                "receiver_word_load_raw_offset": "0x2cb86",
                "r2_add_raw_offset": "0x2cb88",
                "signed_compare_raw_offset": "0x2cb8a",
                "nonnegative_branch_raw_offset": "0x2cb8e",
                "negative_zero_store_raw_offset": "0x2cb9a",
                "nonnegative_cursor_store_raw_offset": "0x2cb8c",
                "limit_load_raw_offset": "0x2cb76",
                "limit_compare_raw_offset": "0x2cb78",
                "limit_cursor_store_raw_offset": "0x2cba2",
            },
            "cursor_value_semantics": "UNRESOLVED",
            "selected_component": "UNRESOLVED",
            "top_level_apply_r1_provenance": "UNRESOLVED",
            "status": (
                "ALTERNATE_CURSOR_ADJUST_SOURCE_BOUND_IF_REACHED_SEMANTICS_"
                "UNRESOLVED"),
            "boundary": (
                "ZERO_STACK_ARGUMENT_AND_RECEIVER_PLUS_0X1C_UPDATE_DO_NOT_BIND_"
                "PARSER_STATE_R7_OR_VOICEFX_SLOT_ONE"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_alternate_key_compare_has_static_default_but_no_parser_identity(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["alternate_key_compare_boundary"], {
            "current_device_expected_key": {
                "table_slot_base_setup_raw_offset": "0x53392",
                "device_receiver_load_raw_offset": "0x5339a",
                "key_address_setup_raw_offset": "0x533a0",
                "key_load_raw_offset": "0x533a8",
                "key_stack_store_raw_offset": "0x533aa",
                "device_offset": "0x5e8c",
                "stack_slot": "sp+0x18",
            },
            "constructor_default_key": {
                "literal_load_raw_offset": "0x5e04c",
                "literal_raw_offset": "0x5e090",
                "literal_value": "0x6f707420",
                "literal_fourcc": "opt ",
                "key_offset_setup_raw_offset": "0x5e060",
                "key_store_raw_offset": "0x5e072",
                "device_offset": "0x5e8c",
            },
            "reader_and_compare": {
                "output_pointer_setup_raw_offset": "0x5340c",
                "reader_input_setup_raw_offset": "0x53414",
                "output_zero_raw_offset": "0x53416",
                "output_stack_slot": "sp+0x4c",
                "reader_call_raw_offset": "0x5341c",
                "reader_raw_offset": "0x2cf58",
                "reader_success_compare_raw_offset": "0x53420",
                "decoded_key_load_raw_offset": "0x53430",
                "expected_key_load_raw_offset": "0x53432",
                "compare_raw_offset": "0x53434",
                "equal_branch_raw_offset": "0x53436",
                "equal_branch_target_raw_offset": "0x5345a",
            },
            "reader_key_semantics": "UNRESOLVED",
            "selected_component": "UNRESOLVED",
            "top_level_apply_r1_provenance": "UNRESOLVED",
            "status": (
                "ALTERNATE_STATIC_KEY_COMPARE_SOURCE_BOUND_IF_REACHED_"
                "SEMANTICS_UNRESOLVED"),
            "boundary": (
                "CURRENT_DEVICE_KEY_AND_CONSTRUCTOR_OPT_DEFAULT_DO_NOT_BIND_"
                "PARSER_FIELD_RECORD_ORDER_OR_VOICEFX_SLOT_ONE"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_alternate_equal_branch_dispatches_slot_two_not_voicefx(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["alternate_slot_two_dispatch_boundary"], {
            "retained_table_offset": {
                "setup_raw_offset": "0x53392",
                "register": "fp",
                "device_offset": "0x5e88",
                "continuation_qualification": "AAPCS_CALLEE_SAVED_FP",
            },
            "slot_two_constructor_binding": {
                "object_offset_setup_raw_offset": "0x5e03e",
                "object_address_setup_raw_offset": "0x5e04a",
                "slot_offset_setup_raw_offset": "0x5e05a",
                "slot_store_raw_offset": "0x5e064",
                "slot_device_offset": "0x5e88",
                "object_device_offset": "0x5090",
                "slot_index": 2,
            },
            "equal_branch_dispatch": {
                "device_receiver_load_raw_offset": "0x53470",
                "record_argument_setup_raw_offset": "0x53472",
                "indexed_object_load_raw_offset": "0x53474",
                "object_vtable_load_raw_offset": "0x53478",
                "interface_slot_load_raw_offset": "0x5347a",
                "interface_slot_offset": "0x4",
                "call_raw_offset": "0x5347c",
            },
            "voicefx_slot_one_exclusion": {
                "voicefx_slot_index": 1,
                "voicefx_slot_device_offset": "0x5e80",
                "selected_slot_index": 2,
                "selected_slot_device_offset": "0x5e88",
            },
            "slot_two_target": "DYNAMIC_UNRESOLVED",
            "slot_two_semantics": "UNRESOLVED",
            "top_level_apply_r1_provenance": "UNRESOLVED",
            "status": (
                "ALTERNATE_EQUAL_BRANCH_SLOT_TWO_DISPATCH_SOURCE_BOUND_NOT_"
                "VOICEFX"),
            "boundary": (
                "SLOT_TWO_INTERFACE_CALL_DOES_NOT_BIND_ITS_DYNAMIC_TARGET_OR_"
                "PARSER_SEMANTICS"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_unlinked_stat_slots_bind_channel2_to_slot_two_channel_strip(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["unlinked_stat_pair_dispatch_boundary"], {
            "link_gate": {
                "flags_offset_setup_raw_offset": "0x42248",
                "flags_load_raw_offset": "0x4224c",
                "flags_device_offset": "0x5e58",
                "link_bit_test_raw_offset": "0x4224e",
                "link_bit": 12,
                "unlinked_branch_raw_offset": "0x42250",
                "unlinked_branch_target_raw_offset": "0x424d6",
                "unlinked_condition": "FLAGS_BIT_12_CLEAR",
            },
            "unlinked_handoff": {
                "slot_index_load_raw_offset": "0x424d6",
                "record_argument_setup_raw_offset": "0x424d8",
                "vtable_load_raw_offset": "0x424da",
                "receiver_setup_raw_offset": "0x424dc",
                "slot_sign_compare_raw_offset": "0x424de",
                "target_load_raw_offset": "0x424e0",
                "selector_disable_setup_raw_offset": "0x424e2",
                "negative_slot_it_raw_offset": "0x424e6",
                "negative_slot_adjust_raw_offset": "0x424e8",
                "slot_pair_collapse_raw_offset": "0x424ea",
                "call_raw_offset": "0x424ec",
                "r3_value": 0,
                "r1_by_stat_slot": {"0": 0, "1": 0, "2": 1, "3": 1},
            },
            "structured_state_diversion": {
                "r1_capture_raw_offset": "0x531e8",
                "r3_capture_raw_offset": "0x531f4",
                "r1_compare_raw_offset": "0x53222",
                "alternate_branch_raw_offset": "0x53224",
                "alternate_branch_target_raw_offset": "0x5338e",
                "selector_gate_compare_raw_offset": "0x53232",
                "selector_disabled_branch_raw_offset": "0x53234",
                "selector_disabled_branch_target_raw_offset": "0x534ba",
                "channel1_slots": [0, 1],
                "channel1_entry_path": "NORMAL_SELECTOR_DISABLED",
                "channel2_slots": [2, 3],
                "channel2_entry_path": "ALTERNATE_SLOT_TWO",
            },
            "channel2_component": {
                "slot_index": 2,
                "slot_device_offset": "0x5e88",
                "voicefx_slot_index": 1,
                "voicefx_slot_device_offset": "0x5e80",
                "direct_voicefx_slot_one_route": False,
            },
            "slot_two_resolution": {
                "component": "SECOND_CHANNEL_STRIP_STATE_APPLY",
                "component_keys": ["filt", "gate", "comp", "eq  ", "lim "],
                "voicefx_in_dispatch_table": False,
            },
            "status": (
                "UNLINKED_STAT_PAIR_DISPATCH_SOURCE_BOUND_CHANNEL2_SLOT_TWO_"
                "CHANNEL_STRIP"),
            "boundary": (
                "RUNTIME_COMPLETION_AND_PHYSICAL_EFFECT_REMAIN_UNRESOLVED"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_linked_positive_stat_slot_reaches_two_structured_state_paths(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["linked_positive_stat_dual_dispatch_boundary"], {
            "link_gate": {
                "flags_offset_setup_raw_offset": "0x42248",
                "flags_load_raw_offset": "0x4224c",
                "flags_device_offset": "0x5e58",
                "link_bit_test_raw_offset": "0x4224e",
                "link_bit": 12,
                "unlinked_branch_raw_offset": "0x42250",
                "linked_condition": "FLAGS_BIT_12_SET_FALLTHROUGH",
            },
            "positive_slot_gate": {
                "slot_index_load_raw_offset": "0x42254",
                "slot_compare_raw_offset": "0x42256",
                "nonpositive_skip_branch_raw_offset": "0x42258",
                "nonpositive_skip_target_raw_offset": "0x42282",
                "required_slot_condition": "STAT_SLOT_GT_ZERO",
                "channel2_slot3_value": 3,
                "channel2_slot3_result": "TAKES_DUAL_HANDOFF",
            },
            "first_handoff": {
                "zero_continuation_requirement": "R6_ZERO",
                "r1_value": 0,
                "r3_value": 1,
                "call_raw_offset": "0x42266",
                "target_raw_offset": "0x531e0",
                "entry_path": (
                    "NORMAL_INDEXED_SELECTOR_ENABLED"
                ),
                "voicefx_component_table_slot": 1,
                "voicefx_component_device_offset": (
                    "0x5e80"
                ),
                "selected_index": (
                    "DATA_DEPENDENT_UNRESOLVED"
                ),
            },
            "second_handoff": {
                "r1_value": 1,
                "r3_value": 0,
                "call_raw_offset": "0x42280",
                "target_raw_offset": "0x531e0",
                "entry_path": "ALTERNATE_SLOT_TWO",
                "slot_two_component": (
                    "SECOND_CHANNEL_STRIP_STATE_APPLY"
                ),
                "voicefx_in_slot_two_dispatch_table": (
                    False
                ),
            },
            "status": (
                "LINKED_POSITIVE_STAT_DUAL_DISPATCH_SOURCE_BOUND"),
            "boundary": (
                "FIRST_HANDOFF_SELECTED_INDEX_AND_RUNTIME_COMPLETION_REMAIN_"
                "UNRESOLVED"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_slot_two_is_the_second_channel_strip_not_voicefx(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["slot_two_channel_strip_state_apply_boundary"], {
            "two_instance_constructor_loop": {
                "first_owner_offset_setup_raw_offset": "0x5dc2a",
                "first_owner_address_add_raw_offset": "0x5dc44",
                "loop_receiver_setup_raw_offset": "0x5dc70",
                "owner_stride_raw_offset": "0x5dc8a",
                "owner_stride": "0xcec",
                "constructor_call_raw_offset": "0x5dc8e",
                "constructor_target_raw_offset": "0x5d8ac",
                "loop_end_offset_setup_raw_offset": "0x5dc34",
                "loop_end_address_add_raw_offset": "0x5dc42",
                "loop_end_capture_raw_offset": "0x5dc5a",
                "loop_compare_raw_offset": "0x5dc96",
                "owner_device_offsets": ["0x43a0", "0x508c"],
            },
            "slot_two_interface_construction": {
                "receiver_capture_raw_offset": "0x5d8b2",
                "vtable_literal_load_raw_offset": "0x5d8b0",
                "vtable_literal_raw_offset": "0x5d980",
                "vtable_family_raw_offset": "0x10cacc",
                "secondary_vtable_setup_raw_offset": "0x5d8be",
                "secondary_vtable_store_raw_offset": "0x5d8c8",
                "second_owner_device_offset": "0x508c",
                "interface_delta": "0x4",
                "slot_two_object_device_offset": "0x5090",
                "interface_vtable_raw_offset": "0x10cb18",
                "state_apply_vtable_slot_raw_offset": "0x10cb1c",
                "state_apply_adjustor_raw_offset": "0x52aec",
            },
            "state_apply_adjustor": {
                "receiver_adjust_raw_offset": "0x52aec",
                "receiver_adjustment": "-0x4",
                "tail_branch_raw_offset": "0x52af0",
                "state_apply_raw_offset": "0x52978",
            },
            "channel_component_table": {
                "table_base_setup_raw_offset": "0x52986",
                "table_base_store_raw_offset": "0x5298c",
                "first_key_load_raw_offset": "0x529a2",
                "loop_zero_setup_raw_offset": "0x529aa",
                "loop_index_capture_raw_offset": "0x529fc",
                "loop_index_increment_raw_offset": "0x52a22",
                "entry_count_compare_raw_offset": "0x52a26",
                "entry_count": 5,
                "keys": ["filt", "gate", "comp", "eq  ", "lim "],
                "selected_object_load_raw_offset": "0x52aa4",
                "selected_interface_call_raw_offset": "0x52aac",
            },
            "voicefx_exclusion": {
                "voicefx_component_key": 201,
                "voicefx_component_table_slot": 1,
                "voicefx_component_device_offset": "0x11e4",
                "voicefx_present_in_channel_component_keys": False,
                "voicefx_in_slot_two_dispatch_table": False,
                "transitive_component_method_forwarding": "NOT_TRAVERSED",
            },
            "supersedes": [
                "alternate_slot_two_dispatch_boundary.slot_two_target",
                "slot_two_base_initializer_vtable_boundary.slot_two_vtable",
            ],
            "status": (
                "SLOT_TWO_TARGET_SOURCE_BOUND_TO_SECOND_CHANNEL_STRIP_STATE_"
                "APPLY_NOT_VOICEFX"),
            "boundary": (
                "FIVE_CHANNEL_COMPONENT_METHODS_ARE_DYNAMIC_BUT_VOICEFX_IS_"
                "NOT_A_MEMBER_OF_THIS_DISPATCH_TABLE"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_slot_two_base_initializer_keeps_outer_vtables_separate(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["slot_two_base_initializer_vtable_boundary"], {
            "caller": {
                "receiver_capture_raw_offset": "0x5e016",
                "direct_call_raw_offset": "0x5e018",
                "direct_callee_raw_offset": "0x5d990",
                "call_receiver": "OUTER_DEVICE_R0_UNADJUSTED",
            },
            "callee_outer_vtable_install": {
                "receiver_capture_raw_offset": "0x5d9a0",
                "primary_vtable_literal_load_raw_offset": "0x5d990",
                "primary_vtable_literal_raw_offset": "0x5dd10",
                "primary_vtable_raw_offset": "0x6d3a8",
                "secondary_vtable_delta_setup_raw_offset": "0x5d998",
                "secondary_vtable_delta": "0x48",
                "secondary_vtable_raw_offset": "0x6d3f0",
                "direct_vtable_store_raw_offset": "0x5d9b6",
                "store_receiver_offset": "0x0",
                "stored_vtable_offsets": ["0x0", "0x4"],
            },
            "slot_two_separation": {
                "slot_two_address_setup_raw_offset": "0x5e03e",
                "slot_two_address_add_raw_offset": "0x5e04a",
                "slot_two_object_device_offset": "0x5090",
                "slot_two_materialized_after_base_call": True,
                "base_initializer_receiver_adjustment_to_slot_two": "NONE",
                "slot_two_vtable": "UNRESOLVED",
            },
            "status": (
                "OUTER_RECEIVER_BASE_VTABLES_SOURCE_BOUND_"
                "SLOT_TWO_VTABLE_UNRESOLVED"),
            "boundary": (
                "BASE_CALLER_DOES_NOT_ADJUST_R0_TO_SLOT_TWO_OR_BIND_"
                "THE_DYNAMIC_TARGET_OR_SEMANTICS"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_slot_two_constructor_tail_has_no_direct_subconstructor(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["slot_two_local_construction_route_boundary"], {
            "slot_two_table_retention": {
                "object_address_add_raw_offset": "0x5e04a",
                "slot_table_store_raw_offset": "0x5e064",
                "slot_device_offset": "0x5e88",
                "object_device_offset": "0x5090",
            },
            "post_store_tail": {
                "first_r0_overwrite_raw_offset": "0x5e066",
                "first_r0_value": "0x5da0",
                "return_receiver_setup_raw_offset": "0x5e086",
                "return_receiver": "OUTER_DEVICE_R4",
                "return_raw_offset": "0x5e08a",
                "direct_calls_after_slot_store": [],
            },
            "local_slot_two_subconstructor_route": "NONE_IN_0X5E04A_0X5E08A",
            "status": "NO_LOCAL_DIRECT_SLOT_TWO_SUBCONSTRUCTOR_CALL",
            "boundary": (
                "CONSTRUCTOR_TAIL_RETURN_DOES_NOT_EXCLUDE_CONSTRUCTION_ELSEWHERE_"
                "OR_BIND_TARGET_OR_SEMANTICS"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_slot_two_immediate_inventory_has_no_additional_route(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(
            parser["slot_two_immediate_materialization_inventory_boundary"], {
                "raw_halfword_aligned_inventory": {
                    "immediate": "0x5090",
                    "candidate_count": 1,
                    "candidates": [{
                        "raw_offset": "0x5e03e",
                        "bytes": "45f29002",
                        "instruction": "movw r2, #0x5090",
                    }],
                },
                "source_bound_component_table_candidate": {
                    "raw_offset": "0x5e03e",
                    "object_address_add_raw_offset": "0x5e04a",
                    "slot_table_store_raw_offset": "0x5e064",
                    "slot_device_offset": "0x5e88",
                    "object_device_offset": "0x5090",
                },
                "additional_source_bound_immediate_routes": [],
                "status": (
                    "ONLY_EXISTING_COMPONENT_TABLE_SLOT_TWO_IMMEDIATE_"
                    "MATERIALIZATION_SOURCE_BOUND"),
                "boundary": (
                    "IMMEDIATE_INVENTORY_DOES_NOT_EXCLUDE_NON_IMMEDIATE_OR_"
                    "DYNAMIC_CONSTRUCTION_OR_BIND_TARGET_OR_SEMANTICS"),
            })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_base_initializer_prologue_members_exclude_slot_two(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["base_initializer_member_call_map_boundary"], {
            "reachable_cfg": {
                "entry_raw_offset": "0x5d990",
                "reachable_instruction_count": 510,
                "reachable_direct_call_count": 43,
                "return_sites": [{
                    "raw_offset": "0x5df6a",
                    "instruction": "pop.w {r4, r5, r6, r7, r8, sb, sl, fp, pc}",
                }],
                "dynamic_pc_transfers": [],
            },
            "outer_receiver_capture_raw_offset": "0x5d9a0",
            "entry_prologue_member_calls": [
                {
                    "call_raw_offset": "0x5d9ec",
                    "target_raw_offset": "0x4a9fc",
                    "receiver_setup_raw_offset": "0x5d9e8",
                    "outer_device_offset": "0xc38",
                },
                {
                    "call_raw_offset": "0x5d9f6",
                    "target_raw_offset": "0x5c160",
                    "outer_member_setup_raw_offset": "0x5d9aa",
                    "stack_save_raw_offset": "0x5d9c8",
                    "receiver_restore_raw_offset": "0x5d9f4",
                    "outer_device_offset": "0xc5c",
                },
                {
                    "call_raw_offset": "0x5da12",
                    "target_raw_offset": "0x591bc",
                    "outer_member_setup_raw_offset": "0x5d9bc",
                    "member_alias_raw_offset": "0x5d9cc",
                    "receiver_setup_raw_offset": "0x5da00",
                    "outer_device_offset": "0x11e0",
                },
                {
                    "call_raw_offset": "0x5da1e",
                    "target_raw_offset": "0x5b258",
                    "offset_setup_raw_offset": "0x5da16",
                    "receiver_add_raw_offset": "0x5da1c",
                    "outer_device_offset": "0x3a70",
                },
            ],
            "slot_two_prologue_receiver": "NOT_PRESENT",
            "status": (
                "BASE_INITIALIZER_ENTRY_PROLOGUE_MEMBER_CALLS_SOURCE_BOUND_"
                "SLOT_TWO_ABSENT"),
            "boundary": (
                "ENTRY_PROLOGUE_ONLY_DOES_NOT_EXCLUDE_LATER_OR_NONLOCAL_"
                "CONSTRUCTION_OR_BIND_TARGET_OR_SEMANTICS"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_adjacent_pre_slot_two_receiver_is_source_bound(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["adjacent_pre_slot_two_receiver_boundary"], {
            "function_stack_slot": {
                "allocate_raw_offset": "0x5d9ba",
                "frame_size": "0x24",
                "slot": "sp+0x4",
                "store_raw_offsets": ["0x5dc2e"],
                "load_raw_offsets": ["0x5dc50", "0x5df36"],
                "release_raw_offset": "0x5df64",
            },
            "receiver_source": {
                "outer_offset_setup_raw_offset": "0x5dc18",
                "outer_offset": "0x5074",
                "outer_address_add_raw_offset": "0x5dc20",
                "stack_store_raw_offset": "0x5dc2e",
                "call_receiver_load_raw_offset": "0x5df36",
                "receiver_add_raw_offset": "0x5df3c",
                "receiver_addend": "0x18",
                "receiver_outer_offset": "0x508c",
            },
            "direct_call": {
                "call_raw_offset": "0x5df3e",
                "target_raw_offset": "0x5d2cc",
            },
            "slot_two_adjacency": {
                "slot_two_object_outer_offset": "0x5090",
                "pre_slot_receiver_outer_offset": "0x508c",
                "delta": "0x4",
                "object_identity": "UNRESOLVED",
                "vtable": "UNRESOLVED",
            },
            "status": (
                "ADJACENT_PRE_SLOT_TWO_RECEIVER_SOURCE_BOUND_"
                "TARGET_UNRESOLVED"),
            "boundary": (
                "FOUR_BYTE_ADJACENCY_DOES_NOT_BIND_OBJECT_IDENTITY_VTABLE_"
                "TARGET_OR_SEMANTICS"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_pre_slot_two_target_captures_receiver_before_branch(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["pre_slot_two_target_prologue_boundary"], {
            "caller": {
                "call_raw_offset": "0x5df3e",
                "target_raw_offset": "0x5d2cc",
                "source_bound_receiver_outer_offset": "0x508c",
            },
            "target_prologue": {
                "entry_raw_offset": "0x5d2cc",
                "receiver_capture_raw_offset": "0x5d2d6",
                "receiver_capture": "r4 <- r0",
                "receiver_adjustment_before_first_branch": "NONE",
                "receiver_relative_stores_before_first_branch": [],
                "first_control_transfer_raw_offset": "0x5d2da",
                "first_control_transfer": "ble #0x6007d3b0",
                "first_control_target_raw_offset": "0x5d3b0",
            },
            "slot_two_relation": {
                "slot_two_object_outer_offset": "0x5090",
                "target_receiver_outer_offset": "0x508c",
                "delta": "0x4",
                "object_identity": "UNRESOLVED",
                "vtable": "UNRESOLVED",
            },
            "status": (
                "PRE_SLOT_TWO_TARGET_CAPTURES_CALLER_RECEIVER_UNADJUSTED_"
                "BEFORE_FIRST_BRANCH"),
            "boundary": (
                "TARGET_PROLOGUE_DOES_NOT_BIND_OBJECT_IDENTITY_VTABLE_"
                "TARGET_SEMANTICS_OR_PARSER"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_doubler_decoder_first_helper_uses_local_descriptors(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["doubler_decoder_first_helper_boundary"], {
            "decoder_entry": {
                "raw_offset": "0x5e0ec",
                "receiver_capture_raw_offset": "0x5e0f6",
                "input_pointer_capture_raw_offset": "0x5e0f8",
                "input_count_guard_raw_offset": "0x5e0ec",
            },
            "first_direct_helper_call": {
                "first_descriptor_setup_raw_offset": "0x5e16a",
                "first_descriptor_stack_slot": "sp+0x2c",
                "second_descriptor_setup_raw_offset": "0x5e168",
                "second_descriptor_stack_slot": "sp+0x4",
                "call_raw_offset": "0x5e192",
                "target_raw_offset": "0x5e094",
            },
            "local_descriptor_initialization": {
                "zero_source_raw_offset": "0x5e156",
                "second_descriptor_head_setup_raw_offset": "0x5e166",
                "second_descriptor_head_stack_slot": "sp+0xc",
                "second_descriptor_count_zero_store_raw_offset": "0x5e18c",
                "first_descriptor_head_setup_raw_offset": "0x5e160",
                "first_descriptor_head_stack_slot": "sp+0x34",
                "first_descriptor_store_raw_offset": "0x5e18e",
            },
            "helper_prefix": {
                "entry_raw_offset": "0x5e094",
                "first_descriptor_count_load_raw_offset": "0x5e094",
                "count_limit_compare_raw_offset": "0x5e096",
                "count_limit_reject_branch_raw_offset": "0x5e098",
                "second_descriptor_count_load_raw_offset": "0x5e0b0",
                "zero_count_success_branch_raw_offset": "0x5e0b4",
                "success_return_raw_offset": "0x5e0e2",
                "reject_return_raw_offset": "0x5e0e8",
            },
            "optional_field_lookup": "UNRESOLVED",
            "status": (
                "DOUBLER_DECODER_FIRST_HELPER_LOCAL_DESCRIPTORS_SOURCE_BOUND_"
                "OPTIONAL_FIELD_LOOKUP_UNRESOLVED"),
            "boundary": (
                "LOCAL_DESCRIPTOR_SETUP_AND_COUNT_BRANCHES_DO_NOT_BIND_"
                "SERIALIZED_FIELD_NAMES_OR_MODEL_ZERO_OPTIONAL_FIELDS"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_doubler_decoder_iterates_input_words_in_fp_registers(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["doubler_decoder_input_iteration_boundary"], {
            "decoder_entry": {
                "raw_offset": "0x5e0ec",
                "input_pointer_capture_raw_offset": "0x5e0f8",
                "input_count_guard_raw_offset": "0x5e0ec",
                "input_end_setup_raw_offset": "0x5e0fe",
                "input_word_stride_bytes": 4,
            },
            "input_word_iteration": {
                "first_fp_register_load_raw_offset": "0x5e110",
                "postincrement_register": "r6",
                "zero_compare_raw_offset": "0x5e114",
                "zero_compare_branch_raw_offset": "0x5e11c",
                "zero_compare_branch_target_raw_offset": "0x5e144",
                "endpoint_compare_raw_offset": "0x5e144",
                "next_input_branch_raw_offset": "0x5e146",
                "next_input_branch_target_raw_offset": "0x5e110",
            },
            "model_local_candidate_scan": {
                "candidate_count_load_raw_offset": "0x5e11e",
                "candidate_base_load_raw_offset": "0x5e126",
                "candidate_stride_bytes": "0x58",
                "candidate_fp_register_load_raw_offset": "0x5e132",
                "fp_register_compare_raw_offset": "0x5e13a",
                "mismatch_branch_raw_offset": "0x5e142",
                "mismatch_branch_target_raw_offset": "0x5e12e",
            },
            "serialized_field_semantics": "UNRESOLVED",
            "optional_field_lookup": "UNRESOLVED",
            "status": (
                "DOUBLER_DECODER_FP_REGISTER_WORD_ITERATION_AND_MODEL_"
                "CANDIDATE_SCAN_SOURCE_BOUND_OPTIONAL_FIELD_LOOKUP_UNRESOLVED"),
            "boundary": (
                "WORD_ITERATION_AND_FP_COMPARISON_DO_NOT_BIND_SERIALIZED_FIELD_"
                "NAMES_RECORD_LAYOUT_OR_MODEL_ZERO_OPTIONAL_FIELDS"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_model_zero_decoder_has_direct_and_adjustor_entries(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["model_zero_decoder_entry_routes_boundary"], {
            "model_primary_vtable": {
                "raw_offset": "0x10c890",
                "decoder_slot_raw_offset": "0x10c8c4",
                "decoder_slot_offset": "0x34",
                "target_raw_offset": "0x5e0ec",
            },
            "adjustor_route": {
                "vtable_slot_raw_offset": "0x10c8e0",
                "adjustor_raw_offset": "0x5e268",
                "this_delta": -0x1c0,
                "tail_branch_raw_offset": "0x5e26c",
                "target_raw_offset": "0x5e0ec",
            },
            "decoder_receiver_capture": {
                "raw_offset": "0x5e0f6",
                "capture": "sl <- r0",
            },
            "caller": "UNRESOLVED",
            "optional_field_lookup": "UNRESOLVED",
            "status": (
                "MODEL_ZERO_DECODER_PRIMARY_AND_ADJUSTOR_ENTRY_ROUTES_SOURCE_"
                "BOUND_OPTIONAL_FIELD_LOOKUP_UNRESOLVED"),
            "boundary": (
                "VIRTUAL_ENTRY_ROUTES_DO_NOT_BIND_CALLER_RECORD_FIELDS_OR_"
                "MODEL_ZERO_OPTIONAL_FIELDS"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_decoder_has_no_immediate_static_caller_beyond_adjustor(self):
        parser = MODULE.analyze_firmware(pinned_application())["parser_patch"]
        self.assertEqual(parser["model_zero_decoder_direct_edge_inventory_boundary"], {
            "decoder_raw_offset": "0x5e0ec",
            "linear_decode_immediate_edges": [
                {
                    "source_raw_offset": "0x5e26c",
                    "mnemonic": "b.w",
                    "target_raw_offset": "0x5e0ec",
                },
            ],
            "immediate_bl_callers": [],
            "known_adjustor_tail_branch_raw_offset": "0x5e26c",
            "caller": "DYNAMIC_OR_INTERPROCEDURAL_UNRESOLVED",
            "optional_field_lookup": "UNRESOLVED",
            "status": (
                "MODEL_ZERO_DECODER_LINEAR_IMMEDIATE_EDGE_INVENTORY_SOURCE_"
                "BOUND_DYNAMIC_CALLER_UNRESOLVED"),
            "boundary": (
                "NO_LINEAR_IMMEDIATE_CALLER_BEYOND_THE_ADJUSTOR_DOES_NOT_"
                "EXCLUDE_DYNAMIC_OR_INTERPROCEDURAL_CALLERS_OR_BIND_OPTIONAL_FIELDS"),
        })

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_reports_verified_placement_candidate_bytes(self):
        placement = MODULE.analyze_firmware(pinned_application())["release_gate"][
            "placement_evidence"]
        self.assertIn("raw_bytes_verified", placement["itcm_ff_span"])
        self.assertTrue(placement["itcm_ff_span"]["raw_bytes_verified"])
        self.assertEqual(placement["itcm_ff_span"]["placement"],
                         "TRAMPOLINE_ONLY")
        self.assertIn("raw_bytes_verified",
                      placement["trailing_raw_candidate"])
        self.assertTrue(
            placement["trailing_raw_candidate"]["raw_bytes_verified"])
        self.assertEqual(placement["trailing_raw_candidate"]["raw_start"],
                         "0x10d9e4")
        self.assertEqual(placement["trailing_raw_candidate"]["size"], 92)
        self.assertEqual(placement["trailing_raw_candidate"]["status"],
                         "UNPROVEN_NOT_EXECUTABLE_HOME")
        self.assertEqual(placement["trailing_zero_fill"], {
            "raw_start": "0x10d948",
            "raw_end": "0x10d9e3",
            "size": 156,
            "fill": 0,
            "status": "NOT_A_CANDIDATE",
            "raw_bytes_verified": True,
        })
        self.assertEqual(placement["extension_body"], "NO_SAFE_HOME")

    def test_placement_gate_allows_only_a_trampoline_and_keeps_model5_live(self):
        self.assertEqual(MODULE.ITCM_TRAMPOLINE_ONLY_SPAN, {
            "raw_start": 0x19F4,
            "raw_end": 0x1A17,
            "size": 36,
            "fill": 0xFF,
            "placement": "TRAMPOLINE_ONLY",
        })
        self.assertEqual(MODULE.MODEL5_PLACEMENT_STATUS,
                         "STOCK_DISPATCHABLE_NOT_RECLAIMABLE")
        self.assertEqual(MODULE.TRAILING_RAW_ZERO_FILL, {
            "raw_start": 0x10D948,
            "raw_end": 0x10D9E3,
            "fill": 0x00,
            "status": "NOT_A_CANDIDATE",
        })
        self.assertEqual(MODULE.TRAILING_RAW_PLACEMENT_CANDIDATE, {
            "raw_start": 0x10D9E4,
            "raw_end": 0x10DA3F,
            "status": "UNPROVEN_NOT_EXECUTABLE_HOME",
        })

    def test_contract_rejects_adjacent_but_wrong_stock_control_names(self):
        source = (ROOT / "re" / "cp34_lane_control_firmware_static.py").read_text()
        self.assertIn("rejected_stock_controls", source)
        self.assertIn("host-schema shadow field", source)
        self.assertIn("shared block-202 reverb send", source)

    def test_analyzer_cannot_be_an_image_emitter_or_device_tool(self):
        source = (ROOT / "re" / "cp34_lane_control_firmware_static.py").read_text()
        self.assertIn("image_emission\": \"BLOCKED", source)
        self.assertIn("parser interception/default storage", source)
        self.assertIn("36-byte all-FF ITCM span is trampoline-only", source)
        self.assertIn("TRAMPOLINE_ONLY", source)
        self.assertIn("STOCK_DISPATCHABLE_NOT_RECLAIMABLE", source)
        self.assertNotIn("dfu-util", source)
        self.assertNotIn("usb.core", source)
        self.assertNotIn("import io24", source)
        self.assertNotIn("write_bytes", source)

    @unittest.skipUnless(UC472_DLL.is_file(),
                         "local UC 4.7.2 DLL is unavailable")
    def test_pinned_image_reports_model5_stock_dispatch_evidence(self):
        model5 = MODULE.analyze_firmware(pinned_application())["release_gate"][
            "placement_evidence"]["model5"]
        self.assertIsInstance(model5, dict)
        self.assertEqual(model5, {
            "selector_raw_offset": "0x55388",
            "rejection_threshold": 6,
            "accepted_model_ids": [0, 1, 2, 3, 4, 5],
            "status": "STOCK_DISPATCHABLE_NOT_RECLAIMABLE",
            "raw_bytes_verified": True,
        })


if __name__ == "__main__":
    unittest.main()
