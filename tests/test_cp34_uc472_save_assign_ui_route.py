#!/usr/bin/env python3
"""Hardware-free contract for the UC 4.7.2 Save/Assign UI route."""

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "cp34_uc472_save_assign_ui_route.py"
RUN = (
    ROOT
    / ".superpowers"
    / "sdd"
    / "2026-08-28-cp34-preset-effect-control"
    / "runs"
    / "20260906T010449-0700-uc472-save-assign-ui-route"
)
OFFICIAL_RUN = RUN.parent / "20260906T001130-0700-uc472-official-reacquisition"
ANALYSIS = RUN / "ANALYSIS.json"
INPUTS = {
    "panel": RUN / "extracted" / "Plugins" / "studiolivepanel.dll",
    "service": RUN / "extracted" / "PreSonusHardwareAccessService.exe",
    "universal_control": RUN / "extracted" / "Universal Control.exe",
    "ucnet": RUN / "extracted" / "ucnet.dll",
    "dsp": OFFICIAL_RUN / "extracted" / "hwaccess" / "dspusbdevice.dll",
}


def _load_analyzer(test_case):
    test_case.assertTrue(
        ANALYZER.is_file(), "UC 4.7.2 Save/Assign route analyzer is missing")
    spec = importlib.util.spec_from_file_location(
        "cp34_uc472_save_assign_ui_route", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_inputs(test_case):
    for name, path in INPUTS.items():
        test_case.assertTrue(path.is_file(), "%s input is missing: %s" % (name, path))
    return {name: path.read_bytes() for name, path in INPUTS.items()}


class Uc472SaveAssignUiRouteTests(unittest.TestCase):
    maxDiff = None

    def test_source_binds_ui_actions_to_existing_dsp_preset_routes(self):
        module = _load_analyzer(self)
        report = module.analyze(**_read_inputs(self))

        self.assertEqual(
            report["status"],
            "UC472_SAVE_ASSIGN_UI_ROUTE_SOURCE_BOUND_TO_EXISTING_"
            "DEVICE_LIBRARY_AND_SLOT_STATE_PATHS",
        )
        self.assertEqual(
            report["boundary"],
            "STATIC_UI_AND_HOST_MESSAGE_ROUTE_RESOLVED_RUNTIME_UCNET_"
            "DELIVERY_FORMAT_TRANSFORMATION_PHYSICAL_COMMIT_RECALL_AND_"
            "AUDIBILITY_UNOBSERVED",
        )
        self.assertEqual(
            report["embedded_ui"],
            {
                "container": "DEFAULT.SKIN/PACKAGEF",
                "member": "uceasy/uceasy.xml",
                "member_count": 275,
                "preset_slot_values": [1, 2, 3, 4],
                "remote_list_label": "Device Presets",
                "send_to_mixer_binding": "sendToMixer",
                "store_binding": "storeNamedRemotePreset",
            },
        )
        self.assertEqual(
            report["ui_actions"]["send_to_mixer"],
            {
                "action_id": "0x452",
                "event_target": "0x1800f9178",
                "helper": "0x1800fe080",
                "transfer_helper": "0x180113ba0",
                "direction": "Local Presets -> Device Presets",
                "serialized_item_tag": "ZStr",
            },
        )
        self.assertEqual(
            report["ui_actions"]["store_named_remote_preset"],
            {
                "action_id": "0x45f",
                "event_target": "0x1800f94a3",
                "helper": "0x180103ba0",
                "network_manager_import": "UCGetNetworkManager",
                "file_transfer_manager_import": "UCGetFileTransferManager",
            },
        )
        self.assertEqual(
            report["high_level_store_proxy"],
            {
                "function": "0x18006ef10",
                "message": "StorePreset",
                "keys": ["presets", "presetFile", "presetTarget"],
                "dispatch": "object+0x298 vtable+0x80",
                "builds_low_level_memp_stat_bytes": False,
            },
        )
        self.assertEqual(
            report["dsp_receiver"],
            {
                "function": "0x18003aef0",
                "messages": ["RestorePreset", "StorePreset"],
                "store_serializer_call": "0x18003b5b3 -> 0x18002e270",
                "store_send_call": "0x18003b5dc -> 0x180037250",
                "device_library_route": "MemP/PrsM indexes 16..27",
                "active_slot_route": "MemP/Stat indexes 0..3",
                "stat_record_first_byte": "0x7b",
            },
        )
        self.assertEqual(
            report["reconciliation"],
            {
                "device_library_and_fast_access_slot_are_distinct": True,
                "explicit_assign_frame_located": False,
                "native_u32_two_producer_located": False,
                "simple_wine_syscall_or_dll_workaround_source_bound": False,
                "linux_native_direction": (
                    "reproduce the high-level preset/state-machine route after "
                    "resolving the remaining runtime format boundary"
                ),
            },
        )
        self.assertEqual(report, json.loads(ANALYSIS.read_text()))

    def test_rejects_mutated_panel_and_dsp_sources(self):
        module = _load_analyzer(self)
        inputs = _read_inputs(self)

        changed_panel = bytearray(inputs["panel"])
        changed_panel[-1] ^= 1
        with self.assertRaisesRegex(module.AnalysisError, "panel SHA-256 differs"):
            module.analyze(**dict(inputs, panel=bytes(changed_panel)))

        changed_dsp = bytearray(inputs["dsp"])
        changed_dsp[-1] ^= 1
        with self.assertRaisesRegex(module.AnalysisError, "dsp SHA-256 differs"):
            module.analyze(**dict(inputs, dsp=bytes(changed_dsp)))


if __name__ == "__main__":
    unittest.main()
