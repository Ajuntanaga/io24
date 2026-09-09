#!/usr/bin/env python3
"""Hardware-free contracts for the Channel-2 Slap Echo discriminator."""

import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "re" / "cp34_channel2_slap_echo_discriminator.py"
SPEC = importlib.util.spec_from_file_location(
    "cp34_channel2_slap_echo_discriminator_test", SCRIPT)
STAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STAGE)


class _Identity:
    serial_number = STAGE.BASE.EXPECTED_SERIAL
    bcdDevice = STAGE.BASE.EXPECTED_FIRMWARE_VERSION


class _FakeDevice:
    def __init__(self, shadow=False):
        self.dev = _Identity()
        self.calls = []
        self.closed = False
        self.params = {
            "flags": 1 << 5,
            "input1Gain": 37.0,
            "input2Gain": 1.0,
            "input1SlotIndex": 0,
            "input2SlotIndex": 0,
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
        self.params["input1ProcessingChannel"] = source_input - 1
        self.params["input2ProcessingChannel"] = 0 if source_input == 2 else 1

    def save_uc_device_slot(self, slot, record):
        self.calls.append(("save_uc_device_slot", slot, copy.deepcopy(record)))
        return {"slot": slot, "fragments_sent": 1, "replies_received": 0}

    def set_preset_mode(self, mode):
        self.calls.append(("set_preset_mode", mode))

    def close(self):
        self.closed = True


class Channel2SlapEchoDiscriminatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = STAGE.load_factory_slap_echo(
            ROOT / "re" / "uc_factory_presets.json")

    def test_plan_pins_obvious_150ms_effect_in_channel2_slot3(self):
        plan = STAGE.build_plan(self.record)

        self.assertEqual(plan["status"], "OFFLINE_READY")
        self.assertEqual(plan["target_channel"], 2)
        self.assertEqual(plan["target_slot"], 3)
        self.assertFalse(plan["slot_zero_targeted"])
        self.assertEqual(plan["record"]["preset_name"], "Slap Echo")
        self.assertEqual(plan["record"]["bytes"], 850)
        self.assertEqual(plan["record"]["sha256"],
                         STAGE.EXPECTED_RECORD_SHA256)
        self.assertEqual(plan["memp_payload_sha256"],
                         [STAGE.EXPECTED_FRAME_SHA256])
        self.assertEqual(plan["record"]["voicefx"], STAGE.EXPECTED_VOICEFX)
        self.assertEqual(plan["expected_signature"]["delay_seconds"], 0.15)

    def test_changed_effect_is_rejected_before_device_open(self):
        changed = copy.deepcopy(self.record)
        changed["voicefx"]["time"] = 0.151
        factories = []

        result = STAGE.run_stage(
            lambda **_kwargs: factories.append(True),
            80,
            changed,
            STAGE.BASE.OVERWRITE_ACKNOWLEDGEMENT,
        )

        self.assertEqual(result["status"], "BLOCKED_TARGET")
        self.assertEqual(factories, [])

    def test_exact_stage_reuses_assignment_and_never_targets_slot0(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory,
            80,
            self.record,
            STAGE.BASE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"],
                         "STAGED_FOR_SLAP_ECHO_LISTENING")
        self.assertFalse(result["assignment_changed"])
        self.assertEqual(result["target_physical_channel"], 2)
        self.assertEqual(result["target_preset_control_channel"], 2)
        self.assertEqual(result["post_state"]["input1_slot_index"], 0)
        self.assertFalse(result["post_state"]["input1_preset_enabled"])
        self.assertEqual(result["post_state"]["input2_slot_index"], 3)
        self.assertTrue(result["post_state"]["input2_preset_enabled"])
        self.assertEqual(result["audibility"],
                         "UNPROVED_PENDING_150MS_REPEAT_LISTENING")

        device, = created
        writes = [call for call in device.calls
                  if call[0] == "save_uc_device_slot"]
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][1], 3)
        self.assertEqual(writes[0][2]["preset_name"], "Slap Echo")
        self.assertNotIn(
            0,
            [call[2] for call in device.calls
             if call[0] == "set_preset_slot"],
        )
        self.assertTrue(all(
            call[1] == 2 for call in device.calls
            if call[0] in {"set_preset_enabled", "set_preset_slot"}
        ))
        self.assertTrue(device.closed)

    def test_live_flags_are_required_before_device_open(self):
        self.assertEqual(STAGE.main([]), 0)
        self.assertEqual(STAGE.main(["--execute"]), 3)


if __name__ == "__main__":
    unittest.main()
