"""Hardware-free contract for restoring UC VoiceFX component state."""

import struct
import unittest
from unittest import mock

import io24
import io24_fx
import io24_presets


CLASS_IDS = {
    "transformer": "{66A10093-D461-4CAC-A80C-91F6A1BB37E5}",
    "detuner": "{509018B0-0DE1-4D26-9DDF-D782476D3C98}",
    "vocoder": "{981F8B8F-D1D8-4634-BB04-2148AF2123E3}",
    "ringmod": "{4B4CAD90-7709-451F-A7DD-AF6F0E954F57}",
    "filters": "{491FED97-6761-4FF6-91E1-E155891291AA}",
    "delay": "{98A527BA-2D6E-4B35-BB26-251EC081A067}",
}

STATES = {
    "transformer": {
        "__classid": CLASS_IDS["transformer"], "on": 1,
        "lows": 0.06, "width": 0.405, "mix": 0.295,
    },
    "detuner": {
        "__classid": CLASS_IDS["detuner"], "on": 1,
        "detune": 4, "mix": 0.8,
    },
    "vocoder": {
        "__classid": CLASS_IDS["vocoder"], "on": 1,
        "avol": 0.7, "acarriertype": 2, "acarrierfreq": 123.0,
        "mix": 0.6,
    },
    "ringmod": {
        "__classid": CLASS_IDS["ringmod"], "on": 1,
        "bcarrierfreq": 31.0, "bcarrier2": 1,
        "bcarrier2freq": 53.0, "bdist": 0.4, "bvol": 0.9,
        "mix": 0.55,
    },
    "filters": {
        "__classid": CLASS_IDS["filters"], "on": 1,
        "ctune": 0.4, "cfb": 0.5, "cdamp": 0.45,
        "cdist": 0.35, "cvol": 0.8, "mix": 0.65,
    },
    "delay": {
        "__classid": CLASS_IDS["delay"], "on": 0,
        "time": 0.173, "feedback": 0.25, "mix": 0.5,
    },
}

EXPECTED_KWARGS = {
    "transformer": {
        "on": True, "lows": 0.06, "width": 0.405, "mix": 0.295,
    },
    "detuner": {"on": True, "detune": 4, "mix": 0.8},
    "vocoder": {
        "on": True, "vol": 0.7, "carrier_type": 2,
        "carrier_freq": 123.0, "mix": 0.6,
    },
    "ringmod": {
        "on": True, "carrier_hz": 31.0, "carrier2": True,
        "carrier2_hz": 53.0, "dist": 0.4, "vol": 0.9,
        "mix": 0.55,
    },
    "filters": {
        "on": True, "pitch": 0.4, "regeneration": 0.5,
        "damping": 0.45, "distortion": 0.35, "volume": 0.8,
        "mix": 0.65,
    },
    "delay": {
        "on": False, "time_s": 0.173, "feedback": 0.25, "mix": 0.5,
    },
}


class _RecordingDevice:
    def __init__(self):
        self.calls = []

    def set_fx(self, model, **kwargs):
        self.calls.append(("set_fx", model, kwargs))
        return {"transformer": 6, "detuner": 3, "vocoder": 3,
                "ringmod": 2, "filters": 2, "delay": 2}[model]

    def set_voicefx_channel(self, channel):
        self.calls.append(("set_voicefx_channel", channel))

    def establish_effects_return(self, bus="main", return_db=0.0, channel=1,
                                 channel_mix=None):
        self.calls.append(("establish_effects_return", bus, return_db,
                           channel_mix))
        return {"bus": bus, "return_db": return_db, "channel": channel,
                "channel_mix": channel_mix, "written": ["return_level",
                                                        "return_assigned"]}

    def set_comp_eq_order(self, channel, value):
        self.calls.append(("set_comp_eq_order", channel, value))


class _ProtocolDevice(io24.Io24):
    """Exercise the real model builder without opening a USB device."""

    def __init__(self):
        self._shadow = {}
        self._shadow_dirty = False
        self._shadow_flushed = 0.0
        self._shadow_persist = False
        self.writes = []

    def _exec(self, payload, wait=1.5):
        self.writes.append(bytes(payload))
        return b""


class VoiceFxPresetApplyTests(unittest.TestCase):
    def test_live_builder_arguments_round_trip_to_complete_slot_component(self):
        for model, kwargs in EXPECTED_KWARGS.items():
            with self.subTest(model=model):
                component = io24_fx.voicefx_preset_state(model, **kwargs)
                self.assertEqual(component["__classid"], CLASS_IDS[model])
                self.assertEqual(
                    io24_fx.voicefx_preset_call(component), (model, kwargs))

    def test_all_six_uc_class_ids_map_to_exact_builder_arguments(self):
        for model, state in STATES.items():
            with self.subTest(model=model):
                decoded = io24_fx.voicefx_preset_call(state)
                self.assertEqual(decoded, (model, EXPECTED_KWARGS[model]))

    def test_explicit_apply_assigns_channel_then_supplies_model_state(self):
        device = _RecordingDevice()

        done = io24_presets.apply_preset(
            device, {"voicefx": STATES["transformer"]}, channel=2,
            with_fx=True, fs=48000.0)

        self.assertEqual(device.calls, [
            ("set_voicefx_channel", 2),
            ("set_fx", "transformer", dict(
                EXPECTED_KWARGS["transformer"], fs=48000.0)),
        ])
        self.assertEqual(done, [
            "voicefx=transformer (6 writes; UC 4.7.2 state transaction)",
        ])

    def test_disabled_selected_model_is_still_restored(self):
        device = _RecordingDevice()

        done = io24_presets.apply_preset(
            device, {"voicefx": STATES["delay"]}, with_fx=True,
            fs=48000.0)

        # A model being restored in its off state needs no return opening.
        self.assertEqual(device.calls, [
            ("set_voicefx_channel", 1),
            ("set_fx", "delay", dict(
                EXPECTED_KWARGS["delay"], fs=48000.0)),
        ])
        self.assertEqual(done, ["voicefx=delay off (2 writes; off)"])

    def test_default_path_keeps_voicefx_record_resident_and_does_not_write(self):
        device = _RecordingDevice()

        done = io24_presets.apply_preset(
            device, {"voicefx": STATES["transformer"]})

        self.assertEqual(device.calls, [])
        self.assertEqual(done, [
            "[voicefx retained for device-slot save; direct replay omitted]",
        ])

    def test_delay_apply_without_current_rate_fails_before_assignment(self):
        device = _RecordingDevice()

        with self.assertRaisesRegex(RuntimeError, "current sample rate"):
            io24_presets.apply_preset(
                device, {"voicefx": STATES["delay"]}, with_fx=True)

        self.assertEqual(device.calls, [])

    def test_bad_voicefx_state_fails_before_any_fat_channel_write(self):
        device = _RecordingDevice()
        preset = {
            "opt": {"swapcompeq": 1},
            "voicefx": {"__classid": "{UNKNOWN}", "on": 1},
        }

        with self.assertRaisesRegex(ValueError, "unknown VoiceFX class id"):
            io24_presets.apply_preset(device, preset, with_fx=True)

        self.assertEqual(device.calls, [])

    def test_incomplete_selected_state_is_rejected_instead_of_defaulted(self):
        state = dict(STATES["transformer"])
        del state["mix"]

        with self.assertRaisesRegex(ValueError, "missing VoiceFX field: mix"):
            io24_fx.voicefx_preset_call(state)

    def test_voicefx_assignment_alias_uses_uc_owner_without_remapping_presets(self):
        device = _ProtocolDevice()

        with mock.patch.object(device, "set_processing_channel") as assign:
            device.set_voicefx_channel(2)

        assign.assert_called_once_with(1, 2)

    def test_assignment_change_forces_complete_model_materialization(self):
        device = _ProtocolDevice()
        device.set_fx("delay", fs=48000.0, **EXPECTED_KWARGS["delay"])
        device.writes.clear()

        device.set_voicefx_channel(2)
        device.set_fx("delay", fs=48000.0, **EXPECTED_KWARGS["delay"])

        block_201 = [payload for payload in device.writes
                     if struct.unpack_from("<I", payload, 4)[0] == 201]
        self.assertEqual(len(block_201), 2)
        self.assertEqual(struct.unpack_from("<I", block_201[0], 12)[0],
                         io24_fx.TAG_VOFX)

    def test_complete_snapshot_emits_model_selector_before_model_state(self):
        device = _ProtocolDevice()

        report = device.apply_voicefx_snapshot(
            STATES["transformer"], sample_rate_hz=48000.0)

        self.assertEqual(report, {
            "model": "transformer",
            "enabled": True,
            "parameter_writes": 6,
            "selection_order": "MODEL_BEFORE_STATE",
            "activation": "UNPROVED",
            "audibility": "UNPROVED",
        })
        self.assertEqual(len(device.writes), 6)
        self.assertTrue(all(struct.unpack_from("<I", payload, 4)[0] == 201
                            for payload in device.writes))
        self.assertEqual(struct.unpack_from("<I", device.writes[0], 12)[0],
                         io24_fx.TAG_VOFX)
        self.assertEqual(struct.unpack_from("<I", device.writes[0], 24)[0], 0)
        self.assertEqual(struct.unpack_from("<I", device.writes[-1], 12)[0],
                         io24_fx.TAG_GODV)

    def test_delay_snapshot_without_current_rate_writes_nothing(self):
        device = _ProtocolDevice()

        with self.assertRaisesRegex(RuntimeError, "current sample rate"):
            device.apply_voicefx_snapshot(STATES["delay"])

        self.assertEqual(device.writes, [])


if __name__ == "__main__":
    unittest.main()
