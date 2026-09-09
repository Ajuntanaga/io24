#!/usr/bin/env python3
"""Hardware-free contract for UC 4.7.2 Hot Key and VoiceFX selection."""

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "re" / "cp34_uc472_hotkey_voicefx_route.py"
TASK = (
    ROOT
    / ".superpowers"
    / "sdd"
    / "2026-08-28-cp34-preset-effect-control"
)
RUN = TASK / "runs" / "20260906T090317-0700-hotkey-voicefx-state-route"
OFFICIAL_RUN = TASK / "runs" / "20260906T001130-0700-uc472-official-reacquisition"
SAVE_ASSIGN_RUN = TASK / "runs" / "20260906T010449-0700-uc472-save-assign-ui-route"
INPUTS = {
    "dsp": OFFICIAL_RUN / "extracted" / "hwaccess" / "dspusbdevice.dll",
    "panel": SAVE_ASSIGN_RUN / "extracted" / "Plugins" / "studiolivepanel.dll",
    "component_model": ROOT / "re" / "uc_component_model" / "dspusb_component_model.xml",
    "fx_params": ROOT / "re" / "uc_component_model" / "dsp_fx_params.xml",
}
ANALYSIS = RUN / "ANALYSIS.json"


def _load_analyzer(test_case):
    test_case.assertTrue(ANALYZER.is_file(), "Hot Key analyzer is missing")
    spec = importlib.util.spec_from_file_location(
        "cp34_uc472_hotkey_voicefx_route", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_inputs(test_case):
    for name, path in INPUTS.items():
        test_case.assertTrue(path.is_file(), "%s input is missing: %s" % (name, path))
    return {name: path.read_bytes() for name, path in INPUTS.items()}


class Uc472HotKeyVoiceFxRouteTests(unittest.TestCase):
    maxDiff = None

    def test_source_binds_hotkey_override_to_voicefx_selection_route(self):
        module = _load_analyzer(self)
        report = module.analyze(**_read_inputs(self))

        self.assertEqual(
            report["status"],
            "UC472_HOTKEY_FULL_CHANNEL_OVERRIDE_AND_VOICEFX_SELECTION_"
            "ROUTE_SOURCE_BOUND",
        )
        self.assertEqual(
            report["boundary"],
            "STATIC_HOST_STATE_ROUTE_SOURCE_BOUND_RUNTIME_EVENT_PROPAGATION_"
            "DEVICE_STORAGE_RECALL_GATE_AND_AUDIBILITY_UNOBSERVED",
        )
        self.assertEqual(
            report["component_model"],
            {
                "processingChannel": 149,
                "activePresetSlotIndex": 150,
                "presetHotKey": 151,
                "presetHotKeyTitle": 152,
                "fxmodel": 450,
                "voicefx_child_mutable": True,
                "voicefx_selector_component": "voicefxopt",
            },
        )
        self.assertEqual(
            report["embedded_ui"],
            {
                "hotkey_control": "presetHotKey",
                "hotkey_options": ["momentary", "transparent"],
                "normal_slot_values": [1, 2, 3, 4],
                "preset_select_path": "presets/preset",
                "hotkey_selector_style": "BigKnobSelectBox.HotKey",
                "same_endless_knob_path": True,
            },
        )
        self.assertEqual(
            report["hotkey_toggle"],
            {
                "parameter_change_dispatch": "0x180041160",
                "parameter_id": 151,
                "dispatch_index": 42,
                "dispatch_case": 7,
                "handler": "0x1800412b0",
                "on_source": "complete channel object +0x180 Hot Key snapshot",
                "off_source": "active normal slot selected by parameter 150",
                "deserializer_apply": "0x180041348 -> 0x18002e690",
                "post_apply": "channel vtable +0x130",
            },
        )
        self.assertEqual(
            report["hotkey_persistence"],
            {
                "channel_load": "0x1800424b0",
                "channel_save": "0x180042680",
                "record_key": "hotkey",
                "snapshot_offset": "complete channel object +0x180",
                "active_capture": "0x180042624 -> 0x18002e270",
                "store_preset_capture": "0x18003b5b3 -> 0x18002e270",
                "same_serializer": True,
            },
        )
        self.assertEqual(
            report["voicefx_channel_ownership"],
            {
                "selector_parameter": "processingChannel",
                "selector_parameter_id": 149,
                "parameter_change_handler": "0x18004145e",
                "ownership_switch": "0x18003e6c0",
                "owning_predicate": "processingChannel == 0",
                "owning_channel_action": (
                    "activate voicefxopt/fxmodel and select its current model"
                ),
                "nonowning_channel_action": (
                    "deactivate voicefxopt/fxmodel and select host model -1"
                ),
                "initial_apply": "0x180040729 -> 0x18003e6c0",
                "change_refresh": "0x18004193f -> 0x18003e6c0",
                "voicefx_on_role": (
                    "separate storable enable inside the selected model state"
                ),
                "stock_instance_count": 1,
            },
        )
        self.assertEqual(
            report["voicefx_selection"],
            {
                "serialized_parent": "voicefx",
                "serialized_selector": "__classid",
                "deserialize_function": "0x180049870",
                "selector_parameter": "voicefxopt/fxmodel",
                "selector_parameter_id": 450,
                "parameter_handler": "0x1800491f0",
                "model_factory": "0x180049260",
                "valid_values": [-1, 0, 1, 2, 3, 4, 5],
                "no_model_value": -1,
                "model_zero_is_off": False,
                "model_zero": "Transformer/Doubler",
                "wire_selector": {
                    "block": 201,
                    "block_index": 0,
                    "tag": "VoFx",
                    "size": 16,
                    "send": "0x1800497c1 -> 0x180053420",
                },
                "enable_is_separate": "voicefx.on",
                "save_source": "host component state, not a readable DSP register",
            },
        )
        self.assertEqual(
            report["model_class_ids"],
            {
                "0": "{66A10093-D461-4CAC-A80C-91F6A1BB37E5}",
                "1": "{509018B0-0DE1-4D26-9DDF-D782476D3C98}",
                "2": "{981F8B8F-D1D8-4634-BB04-2148AF2123E3}",
                "3": "{4B4CAD90-7709-451F-A7DD-AF6F0E954F57}",
                "4": "{491FED97-6761-4FF6-91E1-E155891291AA}",
                "5": "{98A527BA-2D6E-4B35-BB26-251EC081A067}",
            },
        )
        self.assertEqual(
            report["linux_host_implication"],
            {
                "save": (
                    "persist model/class id, voicefx.on, and only the selected "
                    "model state"
                ),
                "apply": (
                    "instantiate/select the model before applying its state; "
                    "preserve the full-channel Hot Key/normal-slot transition"
                ),
                "unknown_attached_state": (
                    "cannot be recovered from block 201 readback; explicitly "
                    "select a model or consume a complete known snapshot"
                ),
                "prior_channel2_trial_gap": "direct VoiceFX parameter write was omitted",
            },
        )
        self.assertEqual(report, json.loads(ANALYSIS.read_text()))

    def test_rejects_mutated_sources(self):
        module = _load_analyzer(self)
        inputs = _read_inputs(self)

        changed_dsp = bytearray(inputs["dsp"])
        changed_dsp[-1] ^= 1
        with self.assertRaisesRegex(module.AnalysisError, "DSP SHA-256 differs"):
            module.analyze(**dict(inputs, dsp=bytes(changed_dsp)))

        changed_xml = inputs["component_model"].replace(
            b'id="presetHotKey"', b'id="presetBadKey"', 1)
        with self.assertRaisesRegex(module.AnalysisError, "component model SHA-256"):
            module.analyze(**dict(inputs, component_model=changed_xml))


if __name__ == "__main__":
    unittest.main()
