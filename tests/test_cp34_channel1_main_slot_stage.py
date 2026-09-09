#!/usr/bin/env python3
"""Hardware-free contract for the Channel-1 MAIN device-slot stage."""

import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "re" / "cp34_channel1_main_slot_stage.py"
SPEC = importlib.util.spec_from_file_location(
    "cp34_channel1_main_slot_stage_test", SCRIPT)
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
            "flags": (1 << 5) | (1 << 6),
            "input1Gain": 37.0,
            "input2Gain": 24.0,
            "input1SlotIndex": 0,
            "input2SlotIndex": 3,
            "input1ProcessingChannel": 0,
            "input2ProcessingChannel": 1,
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

    def save_uc_device_slot(self, slot, record):
        self.calls.append(("save_uc_device_slot", slot, copy.deepcopy(record)))
        return {"slot": slot, "fragments_sent": 1, "replies_received": 0}

    def set_comp_eq_order(self, channel, eq_first):
        self.calls.append(("set_comp_eq_order", channel, bool(eq_first)))

    def set_highpass_freq(self, channel, hz):
        self.calls.append(("set_highpass_freq", channel, float(hz)))

    def set_highpass(self, channel, on):
        self.calls.append(("set_highpass", channel, bool(on)))

    def gate_off(self, channel):
        self.calls.append(("gate_off", channel))

    def set_compressor(self, channel, **kwargs):
        self.calls.append(("set_compressor", channel, copy.deepcopy(kwargs)))

    def set_eq_band(self, channel, band, shape, freq_hz, gain_db, q):
        self.calls.append(("set_eq_band", channel, band, shape,
                           float(freq_hz), float(gain_db), float(q)))

    def set_limiter(self, channel, on, threshold):
        self.calls.append(("set_limiter", channel, bool(on), float(threshold)))

    def close(self):
        self.closed = True


class Channel1MainSlotStageTests(unittest.TestCase):
    def test_main_record_has_the_requested_complete_profile(self):
        record = STAGE.build_main_record()

        self.assertEqual(record["preset_name"], "MAIN")
        self.assertEqual(record["filter"], {"hpf": 24.0})
        self.assertEqual(record["gate"]["on"], 0)
        self.assertEqual(record["comp"], {
            "__classid": "{870D04F7-212E-4F9C-ADBB-39A97216433F}",
            "on": 1,
            "softknee": 1,
            "automode": 0,
            "threshold": -24.0,
            "ratio": 2.0,
            "attack": 0.03,
            "release": 0.12,
            "gain": 2.0,
            "keyfilter": 20.0,
            "keylisten": 0,
        })
        self.assertEqual(record["limit"], {
            "limiteron": 1, "threshold": -0.6})
        self.assertEqual(record["eq"], {
            "__classid": "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}",
            "eqallon": 1,
            "eqgain1": 1.0, "eqq1": 0.7, "eqfreq1": 90.0,
            "eqbandon1": 1, "eqbandop1": 1,
            "eqgain2": -2.0, "eqq2": 1.1, "eqfreq2": 300.0,
            "eqbandon2": 1,
            "eqgain3": 1.25, "eqq3": 0.9, "eqfreq3": 1800.0,
            "eqbandon3": 1,
            "eqgain4": 1.0, "eqq4": 0.7, "eqfreq4": 7000.0,
            "eqbandon4": 1, "eqbandop4": 1,
        })
        self.assertEqual(record["voicefx"]["on"], 0)

    def test_plan_targets_only_channel1_first_slot_without_mode_write(self):
        plan = STAGE.build_plan(STAGE.build_main_record())

        self.assertEqual(plan["target_channel"], 1)
        self.assertEqual(plan["target_slot"], 0)
        self.assertEqual(plan["preset_name"], "MAIN")
        self.assertFalse(plan["changes_preset_mode"])
        self.assertEqual(plan["preserved_channel"], 2)

    def test_stage_writes_slot0_then_applies_same_profile_only_to_channel1(self):
        created = []

        def factory(shadow=False):
            device = _FakeDevice(shadow=shadow)
            created.append(device)
            return device

        result = STAGE.run_stage(
            factory, 96, STAGE.build_main_record(),
            STAGE.OVERWRITE_ACKNOWLEDGEMENT,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"], "MAIN_ACTIVE_WRITE_SENT")
        self.assertEqual(result["post_state"]["input1_slot_index"], 0)
        self.assertTrue(result["post_state"]["input1_preset_enabled"])
        self.assertEqual(result["post_state"]["input2_slot_index"], 3)
        self.assertFalse(result["post_state"]["input2_preset_enabled"])
        device, = created
        self.assertNotIn("set_preset_mode", [call[0] for call in device.calls])
        self.assertEqual(
            [call[1] for call in device.calls
             if call[0] in {"set_preset_enabled", "set_preset_slot"}],
            [1, 1, 1, 1],
        )
        self.assertEqual(
            next(call for call in device.calls if call[0] == "save_uc_device_slot")[1],
            0,
        )
        compressor = next(call for call in device.calls
                          if call[0] == "set_compressor")
        self.assertEqual(compressor[1], 1)
        self.assertEqual(compressor[2]["model"], 0)
        self.assertEqual(compressor[2]["threshold_db"], -24.0)
        self.assertEqual(compressor[2]["ratio"], 2.0)
        self.assertEqual(compressor[2]["attack_s"], 0.03)
        self.assertEqual(compressor[2]["release_s"], 0.12)
        self.assertEqual(
            [call for call in device.calls if call[0] == "set_highpass"][-1],
            ("set_highpass", 1, False),
        )
        self.assertTrue(device.closed)

    def test_stage_blocks_without_explicit_slot0_acknowledgement(self):
        opened = []
        result = STAGE.run_stage(
            lambda **_kwargs: opened.append(True),
            96,
            STAGE.build_main_record(),
            "",
        )

        self.assertEqual(result["status"],
                         "BLOCKED_SLOT0_OVERWRITE_NOT_ACCEPTED")
        self.assertEqual(opened, [])


if __name__ == "__main__":
    unittest.main()
