#!/usr/bin/env python3
"""Hardware-free contracts for the Channel-2 slot-3 Reverb stage."""

import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "re" / "cp34_channel2_reverb_slot_stage.py"
SPEC = importlib.util.spec_from_file_location(
    "cp34_channel2_reverb_slot_stage_test", SCRIPT)
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
            # VoiceFX is assigned to physical Input 2. This selection layer
            # must not renumber either physical preset-control API.
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
            # Exact firmware 1.28 behavior: changing Pari/12 also replays
            # Pari/16 twice with the two current active slot indexes exchanged.
            self.params["input1SlotIndex"], self.params["input2SlotIndex"] = (
                self.params["input2SlotIndex"],
                self.params["input1SlotIndex"],
            )
        self.params["input1ProcessingChannel"] = new_input1
        self.params["input2ProcessingChannel"] = 0 if source_input == 2 else 1

    def save_uc_device_slot(self, slot, record):
        self.calls.append(("save_uc_device_slot", slot, copy.deepcopy(record)))
        return {"slot": slot, "fragments_sent": 1, "replies_received": 0}

    def set_preset_mode(self, mode):
        self.calls.append(("set_preset_mode", mode))

    def close(self):
        self.closed = True


class Channel2ReverbSlotStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory_path = ROOT / "re" / "uc_factory_presets.json"
        cls.record = STAGE.load_factory_reverb(cls.factory_path)

    def test_plan_is_exactly_channel2_slot3_and_never_slot0(self):
        plan = STAGE.build_plan(self.record)

        self.assertEqual(plan["status"], "OFFLINE_READY")
        self.assertEqual(plan["target_channel"], 2)
        self.assertEqual(plan["target_slot"], 3)
        self.assertFalse(plan["slot_zero_targeted"])
        self.assertEqual(plan["standalone_preset_button"], "CHANNEL_2")
        self.assertEqual(plan["record"]["sha256"],
                         STAGE.EXPECTED_RECORD_SHA256)
        self.assertEqual(plan["record"]["wire_prefix_hex"], "7b")
        self.assertEqual(plan["memp_payload_sha256"],
                         [STAGE.EXPECTED_FRAME_SHA256])
        self.assertEqual(plan["uc_voicefx_assignment"], {
            "property": "line/ch1/processingChannel",
            "wire_control": "Pari/12 index 0",
            "value": 1,
            "label": "Ch2",
            "assigned_physical_input": 2,
            "preset_control_namespace": "INDEPENDENT_PHYSICAL_CHANNELS",
            "reassert_same_assignment_before_model": True,
            "firmware_slot_side_effect":
                "swap the two active slot indexes when assignment changes",
        })
        self.assertFalse(plan["direct_voicefx_parameter_write"])

    def test_factory_reverb_is_hash_pinned_enabled_and_maximum_wet(self):
        plan = STAGE.build_plan(self.record)

        self.assertEqual(plan["record"]["preset_name"], "Reverb")
        self.assertEqual(plan["record"]["target_profile"],
                         "FACTORY_DERIVED_MAXIMUM_WET")
        self.assertEqual(plan["record"]["bytes"], 842)
        self.assertEqual(plan["record"]["voicefx"], {
            "__classid": "{66A10093-D461-4CAC-A80C-91F6A1BB37E5}",
            "on": 1,
            "lows": 0.06,
            "width": 0.405,
            "mix": 1.0,
        })

    def test_changed_record_is_rejected_before_device_open(self):
        changed = copy.deepcopy(self.record)
        changed["voicefx"]["mix"] = 0.3
        factories = []

        result = STAGE.run_stage(
            lambda **_kwargs: factories.append(True),
            80,
            changed,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
        )

        self.assertEqual(result["status"], "BLOCKED_TARGET")
        self.assertEqual(factories, [])

    def test_overwrite_acknowledgement_is_required_before_device_open(self):
        factories = []

        result = STAGE.run_stage(
            lambda **_kwargs: factories.append(True),
            80,
            self.record,
            "",
        )

        self.assertEqual(
            result["status"],
            "BLOCKED_UNREADABLE_OVERWRITE_NOT_ACCEPTED",
        )
        self.assertEqual(factories, [])

    def test_ten_percent_battery_blocks_before_device_open(self):
        factories = []

        result = STAGE.run_stage(
            lambda **_kwargs: factories.append(True),
            10,
            self.record,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
        )

        self.assertEqual(result["status"], "BLOCKED_BATTERY")
        self.assertEqual(factories, [])

    def test_exact_sequence_validates_fx_then_writes_and_recalls_slot3(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory,
            80,
            self.record,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"],
                         "STAGED_FOR_STANDALONE_LISTENING")
        self.assertEqual(result["post_state"]["input1_slot_index"], 0)
        self.assertFalse(result["post_state"]["input1_preset_enabled"])
        self.assertEqual(result["post_state"]["input2_slot_index"], 3)
        self.assertTrue(result["post_state"]["input2_preset_enabled"])
        self.assertEqual(
            result["post_state"]["voicefx_assigned_physical_input"], 2)
        self.assertEqual(result["target_physical_channel"], 2)
        self.assertEqual(result["target_preset_control_channel"], 2)
        self.assertFalse(result["assignment_changed"])
        self.assertEqual(
            result["assignment_action"],
            "VALIDATED_AND_REASSERTED_SAME_VALUE",
        )
        self.assertEqual(result["physical_commit"], "UNPROVED")
        self.assertEqual(result["standalone_recall"], "UNPROVED")
        self.assertEqual(result["audibility"], "UNPROVED")
        device, = created
        self.assertEqual([call[0] for call in device.calls], [
            "read_params",
            "set_processing_channel",
            "read_params",
            "set_preset_enabled",
            "read_params",
            "save_uc_device_slot",
            "set_preset_mode",
            "set_preset_slot",
            "set_preset_enabled",
            "read_params",
        ])
        self.assertEqual(device.calls[1], ("set_processing_channel", 1, 2))
        self.assertEqual(device.calls[3], ("set_preset_enabled", 2, False))
        self.assertEqual(device.calls[5][1], 3)
        self.assertEqual(device.calls[7], ("set_preset_slot", 2, 3))
        self.assertEqual(device.calls[8], ("set_preset_enabled", 2, True))
        self.assertEqual(
            [call[1] for call in device.calls
             if call[0] in {"set_preset_enabled", "set_preset_slot"}],
            [2, 2, 2],
        )
        self.assertNotIn(
            0,
            [call[2] for call in device.calls
             if call[0] == "set_preset_slot"],
        )
        self.assertTrue(device.closed)

    def test_active_slot3_is_dislodged_to_channel2_slot2_before_write(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            device.params["input2SlotIndex"] = 3
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory,
            80,
            self.record,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"],
                         "STAGED_FOR_STANDALONE_LISTENING")
        self.assertTrue(result["dislodged_from_active_target"])
        names = [call[0] for call in created[0].calls]
        self.assertLess(names.index("set_preset_slot"),
                        names.index("save_uc_device_slot"))
        self.assertEqual(
            next(call for call in created[0].calls
                 if call[0] == "set_preset_slot"),
            ("set_preset_slot", 2, 2),
        )

    def test_voicefx_assignment_never_renumbers_physical_preset_controls(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory,
            80,
            self.record,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"],
                         "STAGED_FOR_STANDALONE_LISTENING")
        self.assertFalse(result["assignment_changed"])
        self.assertEqual(result["post_state"]["input1_slot_index"], 0)
        self.assertEqual(result["post_state"]["input2_slot_index"], 3)
        self.assertEqual(
            [call for call in created[0].calls
             if call[0] == "set_processing_channel"],
            [("set_processing_channel", 1, 2)],
        )
        for call in created[0].calls:
            if call[0] in {"set_preset_enabled", "set_preset_slot"}:
                self.assertEqual(call[1], 2)

    def test_already_assigned_stale_power_on_slot_is_normalized_to_slot2(self):
        """A retained Ch2 assignment may coexist with reset 0/1 selectors."""
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
            factory,
            80,
            self.record,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"],
                         "STAGED_FOR_STANDALONE_LISTENING")
        self.assertFalse(result["assignment_changed"])
        self.assertTrue(result["target_slot_normalized"])
        self.assertEqual(result["target_slot_before_normalization"], 0)
        slot_calls = [call for call in created[0].calls
                      if call[0] == "set_preset_slot"]
        self.assertEqual(slot_calls, [
            ("set_preset_slot", 2, 2),
            ("set_preset_slot", 2, 3),
        ])
        self.assertNotIn(0, [call[2] for call in slot_calls])
        self.assertEqual(result["post_state"]["input1_slot_index"], 0)
        self.assertEqual(result["post_state"]["input2_slot_index"], 3)
        self.assertTrue(result["post_state"]["input2_preset_enabled"])

    def test_wrong_voicefx_assignment_refuses_before_every_write(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            device.params.update({
                "input1ProcessingChannel": 0,
                "input2ProcessingChannel": 1,
            })
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory,
            80,
            self.record,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"], "BLOCKED_VOICEFX_ASSIGNMENT")
        self.assertFalse(result["record_write_attempted"])
        self.assertEqual(created[0].calls, [("read_params",)])
        self.assertTrue(created[0].closed)

    def test_linked_baseline_refuses_before_every_write(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            device.params["flags"] |= 1 << 12
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory,
            80,
            self.record,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"], "STAGE_FAILED")
        self.assertEqual(result["failed_stage"], "baseline")
        self.assertEqual(created[0].calls, [("read_params",)])
        self.assertTrue(created[0].closed)

    def test_wrong_identity_closes_without_mutation(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            device.dev = type("WrongIdentity", (), {
                "serial_number": "NOT-THE-TARGET",
                "bcdDevice": STAGE.EXPECTED_FIRMWARE_VERSION,
            })()
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory,
            80,
            self.record,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
        )

        self.assertEqual(result["status"], "IDENTITY_MISMATCH")
        self.assertEqual(created[0].calls, [])
        self.assertTrue(created[0].closed)

    def test_failure_after_verified_assignment_bypasses_physical_channel2(self):
        created = []

        class FailedWrite(_FakeDevice):
            def save_uc_device_slot(self, slot, record):
                self.calls.append(
                    ("save_uc_device_slot", slot, copy.deepcopy(record)))
                raise RuntimeError("simulated transport failure")

        def factory(shadow=False):
            device = FailedWrite(shadow=shadow)
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory,
            80,
            self.record,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"], "STAGE_FAILED")
        self.assertEqual(result["failed_stage"], "uc_tagged_slot3_write")
        self.assertTrue(result["record_write_attempted"])
        self.assertEqual(result["failure_channel2_bypass"],
                         "WRITE_SENT_NOT_READABLE")
        self.assertEqual(result["failure_bypass_channel"], 2)
        self.assertEqual(created[0].calls[-1],
                         ("set_preset_enabled", 2, False))


if __name__ == "__main__":
    unittest.main()
