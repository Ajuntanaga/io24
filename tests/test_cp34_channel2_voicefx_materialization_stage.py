#!/usr/bin/env python3
"""Hardware-free contracts for the final stock Channel-2 VoiceFX stage."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "re" / "cp34_channel2_voicefx_materialization_stage.py"
PLAN = (ROOT / ".superpowers" / "sdd" /
        "2026-08-28-cp34-preset-effect-control" / "runs" /
        "20260906T100100-0700-channel2-voicefx-materialization" /
        "PLAN.json")
SPEC = importlib.util.spec_from_file_location(
    "cp34_channel2_voicefx_materialization_stage_test", SCRIPT)
STAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STAGE)


class _Identity:
    serial_number = STAGE.EXPECTED_SERIAL
    bcdDevice = STAGE.EXPECTED_FIRMWARE_VERSION


class _FakeDevice:
    def __init__(self, shadow=False):
        self.dev = _Identity()
        self.calls = []
        self.closed = False
        self.params = {
            "flags": 1 << 5,
            "input1Gain": 37.0,
            "input2Gain": 0.0,
            "input1SlotIndex": 0,
            "input2SlotIndex": 2,
            "input1ProcessingChannel": 1,
            "input2ProcessingChannel": 0,
        }

    def read_params(self):
        self.calls.append(("read_params",))
        return copy.deepcopy(self.params)

    def set_preset_enabled(self, channel, on):
        self.calls.append(("set_preset_enabled", channel, bool(on)))
        bit = 5 if channel == 1 else 6
        if on:
            self.params["flags"] &= ~(1 << bit)
        else:
            self.params["flags"] |= 1 << bit

    def set_preset_slot(self, channel, slot):
        self.calls.append(("set_preset_slot", channel, slot))
        self.params["input%dSlotIndex" % channel] = slot

    def set_processing_channel(self, channel, source_input):
        self.calls.append(("set_processing_channel", channel, source_input))
        new_input1 = source_input - 1
        if self.params["input1ProcessingChannel"] != new_input1:
            self.params["input1SlotIndex"], self.params["input2SlotIndex"] = (
                self.params["input2SlotIndex"],
                self.params["input1SlotIndex"],
            )
        self.params["input1ProcessingChannel"] = new_input1
        self.params["input2ProcessingChannel"] = 0 if source_input == 2 else 1

    def apply_voicefx_snapshot(self, state):
        self.calls.append(("apply_voicefx_snapshot", copy.deepcopy(state)))
        return {
            "model": "transformer",
            "enabled": True,
            "parameter_writes": 6,
            "selection_order": "MODEL_BEFORE_STATE",
            "activation": "UNPROVED",
            "audibility": "UNPROVED",
        }

    def save_uc_device_slot(self, slot, record):
        self.calls.append(("save_uc_device_slot", slot, copy.deepcopy(record)))
        return {"slot": slot, "fragments_sent": 1, "replies_received": 0}

    def set_preset_mode(self, mode):
        self.calls.append(("set_preset_mode", mode))

    def close(self):
        self.closed = True


class Channel2VoiceFxMaterializationStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = STAGE.load_factory_reverb(
            ROOT / "re" / "uc_factory_presets.json")

    def test_plan_pins_model_before_state_and_defers_custom_firmware(self):
        plan = STAGE.build_plan(self.record)

        self.assertEqual(plan["status"], "OFFLINE_READY")
        self.assertEqual(plan["schema"],
                         "cp34-channel2-voicefx-materialization-stage-v1")
        self.assertEqual(plan["target_channel"], 2)
        self.assertEqual(plan["target_slot"], 3)
        self.assertFalse(plan["slot_zero_targeted"])
        self.assertTrue(plan["direct_voicefx_parameter_write"])
        self.assertEqual(plan["voicefx_apply"], {
            "model": "transformer",
            "enabled": True,
            "selection_order": "MODEL_BEFORE_STATE",
            "wire_messages": 6,
            "wire_message_sha256": list(STAGE.EXPECTED_VOICEFX_MESSAGE_SHA256),
            "processing_gate": "UNPROVED",
            "audibility": "UNPROVED",
        })
        self.assertEqual(plan["custom_firmware"],
                         "DEFERRED_UNTIL_AFTER_INITIAL_GITHUB_PUBLICATION")
        self.assertEqual(plan, json.loads(PLAN.read_text()))

    def test_exact_sequence_materializes_voicefx_before_slot_write(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory, 80, self.record, STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None)

        self.assertEqual(result["status"],
                         "STAGED_FOR_STANDALONE_LISTENING")
        self.assertEqual(result["direct_voicefx_apply"], {
            "model": "transformer",
            "enabled": True,
            "parameter_writes": 6,
            "selection_order": "MODEL_BEFORE_STATE",
            "activation": "UNPROVED",
            "audibility": "UNPROVED",
        })
        device, = created
        names = [call[0] for call in device.calls]
        self.assertLess(names.index("apply_voicefx_snapshot"),
                        names.index("save_uc_device_slot"))
        applied_state = next(
            call[1] for call in device.calls
            if call[0] == "apply_voicefx_snapshot")
        self.assertEqual(applied_state["mix"], 1.0)
        self.assertEqual(names, [
            "read_params",
            "set_processing_channel",
            "read_params",
            "set_preset_enabled",
            "read_params",
            "apply_voicefx_snapshot",
            "save_uc_device_slot",
            "set_preset_mode",
            "set_preset_slot",
            "set_preset_enabled",
            "read_params",
        ])
        self.assertEqual(
            [call for call in device.calls
             if call[0] == "set_processing_channel"],
            [("set_processing_channel", 1, 2)],
        )
        self.assertEqual(
            [call[1] for call in device.calls
             if call[0] in {"set_preset_enabled", "set_preset_slot"}],
            [2, 2, 2],
        )
        self.assertEqual(result["post_state"]["input1_slot_index"], 0)
        self.assertFalse(result["post_state"]["input1_preset_enabled"])
        self.assertEqual(result["post_state"]["input2_slot_index"], 3)
        self.assertTrue(result["post_state"]["input2_preset_enabled"])
        self.assertTrue(result["record_write_attempted"])
        self.assertTrue(device.closed)

    def test_model_apply_failure_never_attempts_the_slot_write(self):
        created = []

        class FailedModelApply(_FakeDevice):
            def apply_voicefx_snapshot(self, state):
                self.calls.append(
                    ("apply_voicefx_snapshot", copy.deepcopy(state)))
                raise RuntimeError("simulated model-selection failure")

        def factory(shadow=False):
            device = FailedModelApply(shadow=shadow)
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory, 80, self.record, STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None)

        self.assertEqual(result["status"], "STAGE_FAILED")
        self.assertEqual(result["failed_stage"],
                         "voicefx_model_and_state_apply")
        self.assertFalse(result["record_write_attempted"])
        self.assertNotIn("save_uc_device_slot",
                         [call[0] for call in created[0].calls])
        self.assertEqual(result["failure_channel2_bypass"],
                         "WRITE_SENT_NOT_READABLE")
        self.assertEqual(result["failure_bypass_channel"], 2)
        self.assertEqual(created[0].calls[-1],
                         ("set_preset_enabled", 2, False))
        self.assertTrue(created[0].closed)

    def test_stale_power_on_slot_normalizes_before_model_apply_and_write(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            device.params.update({
                "input1SlotIndex": 0,
                "input2SlotIndex": 0,
            })
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory, 80, self.record, STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None)

        self.assertEqual(result["status"],
                         "STAGED_FOR_STANDALONE_LISTENING")
        self.assertTrue(result["target_slot_normalized"])
        names = [call[0] for call in created[0].calls]
        first_slot = names.index("set_preset_slot")
        self.assertLess(first_slot, names.index("apply_voicefx_snapshot"))
        self.assertLess(names.index("apply_voicefx_snapshot"),
                        names.index("save_uc_device_slot"))
        slot_calls = [call for call in created[0].calls
                      if call[0] == "set_preset_slot"]
        self.assertEqual(slot_calls, [
            ("set_preset_slot", 2, 2),
            ("set_preset_slot", 2, 3),
        ])

    def test_existing_battery_identity_and_overwrite_gates_are_retained(self):
        for battery, acknowledgement, status in (
                (10, STAGE.OVERWRITE_ACKNOWLEDGEMENT, "BLOCKED_BATTERY"),
                (80, "", "BLOCKED_UNREADABLE_OVERWRITE_NOT_ACCEPTED")):
            with self.subTest(status=status):
                factories = []
                result = STAGE.run_stage(
                    lambda **_kwargs: factories.append(True),
                    battery, self.record, acknowledgement)
                self.assertEqual(result["status"], status)
                self.assertEqual(factories, [])


if __name__ == "__main__":
    unittest.main()
