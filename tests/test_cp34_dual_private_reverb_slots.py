#!/usr/bin/env python3
"""Hardware-free contracts for paired Doubler private-reverb slot saves."""

import json
from pathlib import Path
import struct
import unittest

import io24
from io24_preset_record import (
    DOUBLER_CLASS_ID,
    decode_preset_record,
    doubler_private_reverb_state,
    normalized_doubler_lane_controls,
    paired_doubler_private_reverb_slots,
)


ROOT = Path(__file__).resolve().parents[1]


def reverb_factory_record():
    records = json.loads((ROOT / "re" / "uc_factory_presets.json").read_text())
    return next(record for record in records
                if record.get("preset_name") == "Reverb")


def record_from_frame(frame):
    fragment_size = struct.unpack_from("<H", frame, 35)[0]
    record_size = struct.unpack_from("<I", frame, 37)[0]
    assert fragment_size == record_size
    return decode_preset_record(frame[41:41 + fragment_size])


class _WireFake(io24.Io24):
    def __init__(self):
        self.payloads = []

    def _exec(self, payload, wait=1.5):
        self.payloads.append(bytes(payload))
        return struct.pack("<I", io24.RPLY)


class _SecondWriteFailsFake(_WireFake):
    def _exec(self, payload, wait=1.5):
        if self.payloads:
            raise OSError("synthetic second-slot transport failure")
        return super()._exec(payload, wait)


class DualPrivateReverbSlotTests(unittest.TestCase):
    def test_stock_doubler_record_has_exact_legacy_voicefx_surface(self):
        state = doubler_private_reverb_state(
            enabled=True, lows=0.12, width=0.34, mix=0.56)
        self.assertEqual(state, {
            "__classid": DOUBLER_CLASS_ID,
            "on": 1,
            "lows": 0.12,
            "width": 0.34,
            "mix": 0.56,
        })
        self.assertTrue({"vrvb", "FXA", "size", "predelay", "hp_freq"}
                        .isdisjoint(state))

    def test_pair_uses_one_identical_state_in_each_channel_slot(self):
        base = reverb_factory_record()
        before = json.loads(json.dumps(base))

        result = paired_doubler_private_reverb_slots(
            1, base, 3, base, enabled=True,
            lows=0.2, width=0.4, mix=0.6,
            preset_name="Private Reverb")

        self.assertEqual(list(result), [1, 3])
        self.assertEqual(result[1]["voicefx"], result[3]["voicefx"])
        self.assertEqual(result[1]["preset_name"], "Private Reverb")
        self.assertEqual(result[3]["preset_name"], "Private Reverb")
        self.assertNotIn("_offset", result[1])
        self.assertNotIn("_offset", result[3])
        self.assertEqual(base, before, "base record was mutated")

    def test_pair_rejects_cross_channel_or_incomplete_records(self):
        base = reverb_factory_record()
        for slots in ((2, 3), (0, 1), (True, 2)):
            with self.subTest(slots=slots), self.assertRaises(ValueError):
                paired_doubler_private_reverb_slots(
                    slots[0], base, slots[1], base)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            paired_doubler_private_reverb_slots(
                0, {"voicefx": {}}, 2, base)

    def test_normalized_parameters_are_strict(self):
        for values in ((-0.01, 0.5, 0.5), (0.5, 1.01, 0.5),
                       (0.5, 0.5, float("nan"))):
            with self.subTest(values=values), self.assertRaises(ValueError):
                doubler_private_reverb_state(
                    lows=values[0], width=values[1], mix=values[2])
        with self.assertRaises(TypeError):
            doubler_private_reverb_state(enabled=1)

    def test_pure_frame_builder_targets_one_slot_per_channel(self):
        base = reverb_factory_record()
        frame_sets = io24.build_paired_doubler_private_reverb_frames(
            0, base, 2, base, lows=0.25, width=0.5, mix=0.75)

        self.assertEqual(list(frame_sets), [0, 2])
        for slot, frames in frame_sets.items():
            self.assertEqual(len(frames), 1)
            frame = frames[0]
            self.assertEqual(struct.unpack_from("<IIII", frame, 0),
                             (io24.SETP, io24.APPL, 0, io24.MEMP))
            self.assertEqual(struct.unpack_from("<I", frame, 20)[0], io24.STAT)
            self.assertEqual(struct.unpack_from("<I", frame, 24)[0], slot)
        self.assertEqual(record_from_frame(frame_sets[0][0])["voicefx"],
                         record_from_frame(frame_sets[2][0])["voicefx"])

    def test_lane_controls_are_complete_identical_and_clamped_when_opted_in(self):
        base = reverb_factory_record()
        records = paired_doubler_private_reverb_slots(
            0, base, 2, base, wet_ch1=-0.2, wet_ch2=1.2,
            bypass_ch1=True, bypass_ch2=False,
            custom_firmware_lane_controls=True)
        expected = {
            "wet_ch1": 0.0,
            "wet_ch2": 1.0,
            "bypass_ch1": True,
            "bypass_ch2": False,
        }
        self.assertEqual(normalized_doubler_lane_controls(records[0]["voicefx"]),
                         expected)
        self.assertEqual(records[0]["voicefx"], records[2]["voicefx"])

    def test_legacy_record_uses_lane_control_defaults(self):
        self.assertEqual(normalized_doubler_lane_controls({"on": 1, "mix": 0.3}), {
            "wet_ch1": 1.0,
            "wet_ch2": 1.0,
            "bypass_ch1": False,
            "bypass_ch2": False,
        })

    def test_lane_controls_reject_nonfinite_gains_and_nonboolean_bypasses(self):
        with self.assertRaises(ValueError):
            doubler_private_reverb_state(wet_ch1=float("nan"))
        with self.assertRaises(TypeError):
            doubler_private_reverb_state(bypass_ch2=0)

    def test_lane_controls_require_explicit_custom_firmware_capability(self):
        with self.assertRaisesRegex(ValueError, "explicit custom firmware"):
            doubler_private_reverb_state(wet_ch1=0.5)
        state = doubler_private_reverb_state(
            wet_ch1=0.5, bypass_ch2=True,
            custom_firmware_lane_controls=True)
        self.assertEqual(normalized_doubler_lane_controls(state), {
            "wet_ch1": 0.5, "wet_ch2": 1.0,
            "bypass_ch1": False, "bypass_ch2": True,
        })

    def test_custom_lane_controls_survive_the_existing_stat_codec(self):
        base = reverb_factory_record()
        frame_sets = io24.build_paired_doubler_private_reverb_frames(
            1, base, 3, base, wet_ch1=0.25, wet_ch2=0.75,
            bypass_ch1=False, bypass_ch2=True,
            custom_firmware_lane_controls=True)
        voicefx = record_from_frame(frame_sets[1][0])["voicefx"]
        self.assertEqual(voicefx, record_from_frame(frame_sets[3][0])["voicefx"])
        self.assertEqual(normalized_doubler_lane_controls(voicefx), {
            "wet_ch1": 0.25,
            "wet_ch2": 0.75,
            "bypass_ch1": False,
            "bypass_ch2": True,
        })

    def test_live_method_refuses_obsolete_pair_before_first_write(self):
        base = reverb_factory_record()
        fake = _WireFake()

        with self.assertRaisesRegex(
                io24.HostActionError, "not atomic"):
            fake.save_paired_doubler_private_reverb(
                1, base, 3, base, lows=0.1, width=0.2, mix=0.3)

        self.assertEqual(fake.payloads, [])

    def test_live_method_never_reaches_a_second_write_failure(self):
        base = reverb_factory_record()
        fake = _SecondWriteFailsFake()

        with self.assertRaises(io24.HostActionError):
            fake.save_paired_doubler_private_reverb(1, base, 3, base)

        self.assertEqual(fake.payloads, [])


if __name__ == "__main__":
    unittest.main()
