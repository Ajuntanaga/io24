"""Hardware-free contracts for complete UC scene import."""
import unittest

import io24_fx
import io24_scene


def _delay(mix=0.5):
    return io24_fx.voicefx_preset_state(
        "delay", on=True, time_s=0.125, feedback=0.25, mix=mix)


def _standard_eq():
    eq = {
        "__classid": io24_scene.EQ_PARAMETRIC,
        "eqallon": 1, "eqbandop1": 1, "eqbandop4": 1,
    }
    for band, frequency in enumerate((130.0, 320.0, 1400.0, 5000.0), 1):
        eq["eqbandon%d" % band] = 1
        eq["eqfreq%d" % band] = frequency
        eq["eqgain%d" % band] = 0.0
        eq["eqq%d" % band] = 0.6
    return eq


def _scene():
    return {
        "global": {
            "phonesSrc": 2, "aux1_mirror_main": 1,
            "aux2_mirror_main": 0, "outputDelay": 0.02,
            "outputDelayBus": 1, "presetButtonMode": 1,
            "auxMuteMode": 1,
        },
        "line": {
            "ch1": {
                "link": 0, "preampgain": 11.0, "48v": 0, "mute": 0,
                "processingChannel": 0, "volume": -3.0, "lr": 1,
                "aux1": -12.0, "assign_aux1": 1, "aux2": -18.0,
                "assign_aux2": 1, "dspAmount": 0.75, "solo": 0,
                "pan": 0.5, "stereopan": 0.0, "FXA": 0.0,
                "dawpostdsp": 1, "opt": {"swapcompeq": 1},
                "filter": {"hpf": 80.0},
                "gate": {"on": 0, "threshold": -40.0, "range": -60.0,
                         "attack": 0.01, "release": 0.3,
                         "keyfilter": 0.0, "expander": 1, "keylisten": 0},
                "comp": {
                    "__classid": "{870D04F7-212E-4F9C-ADBB-39A97216433F}",
                    "on": 1, "threshold": -24.0, "ratio": 3.0,
                    "attack": 0.02, "release": 0.15, "gain": 0.0,
                    "softknee": 0, "automode": 0, "keyfilter": 40.0,
                    "keylisten": 0,
                },
                "eq": _standard_eq(),
                "limit": {"limiteron": 1, "threshold": -1.0},
                "voicefx": _delay(),
            },
        },
        "return": {
            "ch1": {"mute": 1, "solo": 0, "volume": 0.0, "lr": 1,
                    "aux1": -20.0, "assign_aux1": 1,
                    "aux2": -30.0, "assign_aux2": 0},
        },
        "fxreturn": {
            "ch1": {"mute": 0, "solo": 0, "volume": -10.0, "lr": 1,
                    "aux1": -20.0, "assign_aux1": 1,
                    "aux2": -20.0, "assign_aux2": 1},
        },
        "aux": {
            "ch1": {"mute": 0, "volume": -2.0, "mono": 0},
            "ch2": {"mute": 1, "volume": -4.0, "mono": 0},
        },
        "main": {"ch1": {"mute": 0, "volume": -1.0, "mono": 0}},
        "fx": {"ch1": {"reverb": {
            "on": 1, "size": 0.5, "mix": 1.0,
            "hp_freq": 200.0, "predelay": 0.02,
        }}},
        "presets": {"slots": {}, "userpresets": {}},
    }


class ScenePlanTests(unittest.TestCase):
    def test_complete_uc_sections_map_to_linux_host_setters(self):
        calls, skips = io24_scene.plan(_scene(), sample_rate_hz=96000.0)
        names = [call[0] for call in calls]

        for expected in (
                "set_mute_mode", "set_preset_mode", "set_comp_eq_order",
                "set_fx_mix", "set_fx", "set_reverb", "set_source_mute",
                "set_bus_mute", "set_bus_master", "mirror_main"):
            self.assertIn(expected, names)
        self.assertEqual(names.count("set_fx"), 1)
        self.assertEqual(names.count("set_eq_band"), 4)
        fx = next(call for call in calls if call[0] == "set_fx")
        self.assertEqual(fx[1], ("delay",))
        self.assertTrue(fx[2]["on"])
        reverb = next(call for call in calls if call[0] == "set_reverb")
        self.assertEqual(reverb[2]["fs"], 96000.0)
        self.assertTrue(any("pan is not representable" in skip for skip in skips))
        self.assertFalse(any("voicefx" in skip.lower() for skip in skips))

    def test_conflicting_channel_voicefx_fails_before_a_plan_is_returned(self):
        scene = _scene()
        scene["line"]["ch2"] = {"voicefx": _delay(mix=0.75)}

        with self.assertRaisesRegex(ValueError, "one shared VoiceFX"):
            io24_scene.plan(scene)

    def test_invalid_scene_toggle_is_not_coerced_from_text(self):
        scene = _scene()
        scene["global"]["auxMuteMode"] = "0"

        with self.assertRaisesRegex(ValueError, "boolean or 0/1"):
            io24_scene.plan(scene)

    def test_apply_checks_every_setter_before_the_first_call(self):
        invoked = []

        class Device:
            def set_gain(self, *args, **kwargs):
                invoked.append((args, kwargs))

        calls = [
            ("set_gain", (1, 10.0), {}, "gain"),
            ("missing_setter", (), {}, "missing"),
        ]
        with self.assertRaisesRegex(AttributeError, "missing_setter"):
            io24_scene.apply(Device(), calls)
        self.assertEqual(invoked, [])

    def test_apply_stops_after_the_first_runtime_failure(self):
        invoked = []

        class Device:
            def first(self):
                invoked.append("first")
                raise RuntimeError("transport stopped")

            def second(self):
                invoked.append("second")

        done, failed = io24_scene.apply(Device(), [
            ("first", (), {}, "first call"),
            ("second", (), {}, "second call"),
        ])
        self.assertEqual((done, failed), (0, 1))
        self.assertEqual(invoked, ["first"])


if __name__ == "__main__":
    unittest.main()
