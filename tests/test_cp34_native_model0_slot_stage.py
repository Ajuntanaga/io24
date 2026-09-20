#!/usr/bin/env python3
"""Hardware-free contracts for the bounded native model-0 staging command."""

import hashlib
import importlib.util
from pathlib import Path
import struct
import unittest

import io24_fx
from io24_native_stat import (
    CHANNEL_COMPONENT_SIZES,
    NativeChunk,
    NativeStatRecord,
    build_native_model0_stat_record,
    encode_chunk_group,
    encode_native_stat_record,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "re" / "cp34_native_model0_slot_stage.py"
SPEC = importlib.util.spec_from_file_location(
    "cp34_native_model0_slot_stage_test", SCRIPT)
STAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STAGE)


def _record(slot_index=1):
    channel = encode_chunk_group([
        (key, bytes([index + 1]) * size)
        for index, (key, size) in enumerate(CHANNEL_COMPONENT_SIZES.items())
    ])
    voicefx = (
        struct.pack("<II", 6, 5) +
        encode_chunk_group([(
            b"\x00\x00\x00\x05",
            struct.pack("<I", 16) +
            io24_fx.fx_delay(False, 0.125, 0.5, 0.5)[12:],
        )])
    )
    base = encode_native_stat_record(NativeStatRecord(2, (
        NativeChunk(b"opt ", channel),
        NativeChunk(b"\x00\x00\x00\xc9", voicefx),
    )))
    return build_native_model0_stat_record(base, slot_index)


class _Identity:
    serial_number = "AB7C22200355"
    bcdDevice = 0x0128


class _FakeDevice:
    def __init__(self, shadow=False):
        self.dev = _Identity()
        self.calls = []
        self.closed = False
        self.params = {
            "flags": 1 << 5,
            "input1SlotIndex": 0,
            "input2SlotIndex": 3,
            "input1ProcessingChannel": 0,
            "input2ProcessingChannel": 1,
        }

    def read_params(self):
        self.calls.append(("read_params",))
        return dict(self.params)

    def save_device_slot(self, slot, record):
        self.calls.append(("save_device_slot", slot, bytes(record)))
        return {"slot": slot, "fragments_sent": 1, "replies_received": 0}

    def set_processing_channel(self, channel, source_input):
        self.calls.append(("set_processing_channel", channel, source_input))
        self.params["input1ProcessingChannel"] = source_input - 1
        self.params["input2ProcessingChannel"] = 0 if source_input == 2 else 1

    def set_preset_mode(self, mode):
        self.calls.append(("set_preset_mode", mode))

    def set_preset_enabled(self, channel, on):
        self.calls.append(("set_preset_enabled", channel, on))
        if on:
            self.params["flags"] &= ~(1 << 5)
        else:
            self.params["flags"] |= 1 << 5

    def set_preset_slot(self, channel, slot):
        self.calls.append(("set_preset_slot", channel, slot))
        self.params["input1SlotIndex"] = slot

    def close(self):
        self.closed = True


class NativeModel0SlotStageTests(unittest.TestCase):
    def setUp(self):
        self.record = _record(1)
        self.allowed = {1: hashlib.sha256(self.record).hexdigest()}

    def test_offline_plan_has_no_claim_of_physical_success(self):
        plan = STAGE.build_plan(
            1, self.record, 2, allowed_hashes=self.allowed)

        self.assertEqual(plan["status"], "OFFLINE_READY")
        self.assertEqual(plan["slot_index"], 1)
        self.assertEqual(plan["processing_input"], 2)
        self.assertEqual(plan["standalone_audibility"],
                         "REQUIRES_USER_LISTENING_AFTER_STAGE")
        self.assertFalse(plan["power_cycle"])

    def test_wrong_hash_or_slot_is_rejected_before_device_factory(self):
        factories = []

        result = STAGE.run_stage(
            lambda **_kwargs: factories.append(True),
            80, "AB7C22200355", 0, self.record, 2,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            allowed_hashes=self.allowed,
        )

        self.assertEqual(result["status"], "BLOCKED_TARGET")
        self.assertEqual(factories, [])

    def test_overwrite_acknowledgement_is_required_before_open(self):
        factories = []

        result = STAGE.run_stage(
            lambda **_kwargs: factories.append(True),
            80, "AB7C22200355", 1, self.record, 2, "",
            allowed_hashes=self.allowed,
            prohibited_live_slots=(),
        )

        self.assertEqual(
            result["status"],
            "BLOCKED_UNREADABLE_OVERWRITE_NOT_ACCEPTED",
        )
        self.assertEqual(factories, [])

    def test_ten_percent_battery_blocks_before_open(self):
        factories = []

        result = STAGE.run_stage(
            lambda **_kwargs: factories.append(True),
            10, "AB7C22200355", 1, self.record, 2,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            allowed_hashes=self.allowed,
            prohibited_live_slots=(),
        )

        self.assertEqual(result["status"], "BLOCKED_BATTERY")
        self.assertEqual(factories, [])

    def test_live_sequence_writes_then_routes_enables_and_recalls(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory,
            80,
            "AB7C22200355",
            1,
            self.record,
            2,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
            allowed_hashes=self.allowed,
            prohibited_live_slots=(),
        )

        self.assertEqual(result["status"],
                         "STAGED_FOR_STANDALONE_LISTENING")
        self.assertEqual(result["physical_commit"], "UNPROVED")
        self.assertEqual(result["standalone_recall"], "UNPROVED")
        self.assertEqual(result["audibility"], "UNPROVED")
        self.assertEqual(result["post_state"]["voicefx_chain_physical_input"],
                         2)
        device, = created
        self.assertEqual(
            [call[0] for call in device.calls],
            ["read_params", "set_preset_enabled", "save_device_slot",
             "set_processing_channel", "set_preset_mode",
             "set_preset_slot", "set_preset_enabled", "read_params"],
        )
        self.assertTrue(device.closed)

    def test_active_target_is_bypassed_and_dislodged_before_write(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            device.params["input1SlotIndex"] = 1
            device.params["flags"] = 0
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory,
            80,
            "AB7C22200355",
            1,
            self.record,
            1,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
            allowed_hashes=self.allowed,
            prohibited_live_slots=(),
        )

        self.assertEqual(result["status"],
                         "STAGED_FOR_STANDALONE_LISTENING")
        self.assertTrue(result["dislodged_from_active_target"])
        self.assertFalse(result["prewrite_state"][
            "voicefx_storage_enabled"])
        names = [call[0] for call in created[0].calls]
        self.assertEqual(names[:5], [
            "read_params", "set_preset_enabled", "set_preset_slot",
            "read_params", "save_device_slot",
        ])
        self.assertEqual(created[0].calls[2], ("set_preset_slot", 1, 0))

    def test_selector_outside_owning_pair_is_blocked_before_write(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            device.params["input1SlotIndex"] = 2
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory,
            80,
            "AB7C22200355",
            1,
            self.record,
            1,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
            allowed_hashes=self.allowed,
            prohibited_live_slots=(),
        )

        self.assertEqual(result["status"], "STAGE_FAILED")
        self.assertEqual(result["failed_stage"], "baseline")
        self.assertNotIn("save_device_slot",
                         [call[0] for call in created[0].calls])

    def test_failed_active_target_dislodge_blocks_before_write(self):
        created = []

        class StuckSelectorDevice(_FakeDevice):
            def set_preset_slot(self, channel, slot):
                self.calls.append(("set_preset_slot", channel, slot))

        def factory(shadow=False):
            device = StuckSelectorDevice(shadow=shadow)
            device.params["input1SlotIndex"] = 1
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory,
            80,
            "AB7C22200355",
            1,
            self.record,
            1,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
            allowed_hashes=self.allowed,
            prohibited_live_slots=(),
        )

        self.assertEqual(result["status"], "STAGE_FAILED")
        self.assertEqual(result["failed_stage"], "alternate_slot_verify")
        self.assertNotIn("save_device_slot",
                         [call[0] for call in created[0].calls])

    def test_user_channel2_requirement_blocks_all_stock_owning_slots(self):
        factories = []

        result = STAGE.run_stage(
            lambda **_kwargs: factories.append(True),
            80,
            "AB7C22200355",
            1,
            self.record,
            1,
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            allowed_hashes=self.allowed,
        )

        self.assertEqual(
            result["status"],
            "BLOCKED_USER_REQUIRES_CHANNEL2_STORAGE",
        )
        self.assertEqual(factories, [])


if __name__ == "__main__":
    unittest.main()
