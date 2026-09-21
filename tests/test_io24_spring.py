#!/usr/bin/env python3
"""Hardware-free contracts for the Host spring reverb."""

import ctypes
import math
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

import io24
import io24_spring
import io24gtk


class SpringStateTests(unittest.TestCase):
    def test_default_state_is_complete_and_off(self):
        state = io24_spring.default_state()
        self.assertEqual(set(state), {
            "version", "enabled", "input1_db", "input2_db", "dwell",
            "tone", "drip", "width", "predelay_s", "output_db", "routing",
        })
        self.assertFalse(state["enabled"])
        self.assertIsNone(state["routing"])
        self.assertEqual(io24_spring.validate_state(state), state)

    def test_validation_rejects_unknown_nonfinite_and_out_of_range_values(self):
        for key, value in (
                ("dwell", float("nan")), ("tone", 1.01),
                ("input1_db", -61.0), ("predelay_s", 0.101),
                ("width", True)):
            state = io24_spring.default_state()
            state[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                io24_spring.validate_state(state)
        state = io24_spring.default_state()
        state["surprise"] = 1
        with self.assertRaises(ValueError):
            io24_spring.validate_state(state)

    def test_host_feature_normalizer_keeps_valid_spring_state(self):
        state = io24_spring.default_state(enabled=True)
        normalized, migrations = io24._normalise_host_features(
            {"spring_reverb": state})
        self.assertEqual(normalized, {"spring_reverb": state})
        self.assertEqual(migrations, [])

    def test_host_feature_normalizer_migrates_v1_spring_return_gain(self):
        state = io24_spring.default_state(enabled=True)
        state["version"] = 1
        state.pop("output_db", None)

        normalized, migrations = io24._normalise_host_features(
            {"spring_reverb": state})

        self.assertEqual(
            normalized["spring_reverb"]["output_db"],
            io24_spring.DEFAULT_RETURN_DB)
        self.assertEqual(normalized["spring_reverb"]["version"],
                         io24_spring.VERSION)
        self.assertEqual(migrations, [
            "legacy Host spring return migrated to schema v2",
        ])

    def test_named_snapshot_keeps_settings_but_not_session_route_ownership(self):
        state = io24_spring.default_state(enabled=True)
        state["routing"] = {
            "source": "return/ch3",
            "exclusive": True,
            "buses": {
                bus: {"assigned": bus == "mixa", "known": True,
                      "level_db": -3.0}
                for bus in io24_spring.RETURN_BUSES
            },
        }
        features = io24gtk.snapshot_host_features({"spring_reverb": state})
        self.assertTrue(features["spring_reverb"]["enabled"])
        self.assertIsNone(features["spring_reverb"]["routing"])
        self.assertIsNotNone(state["routing"])

    def test_gtk_host_state_reads_each_visible_spring_control(self):
        class Value:
            def __init__(self, value):
                self.value = value

            def get_value(self):
                return self.value

        state = io24_spring.default_state(enabled=True)
        host = SimpleNamespace(
            spring_on=SimpleNamespace(get_active=lambda: True),
            spring_controls={name: Value(state[name]) for name in (
                "input1_db", "input2_db", "dwell", "tone", "drip",
                "width", "predelay_s", "output_db")},
            _spring_routing=None,
        )
        self.assertEqual(io24gtk.Win._spring_state(host), state)

    def test_reconnect_restarts_the_spring_graph(self):
        restarts = []
        host = SimpleNamespace(
            _resume_session=lambda first: None,
            _insert_reconcile=lambda restart=False: None,
            _spring_reconcile=lambda restart=False: restarts.append(restart),
        )
        host._maybe_resume = io24gtk.Win._maybe_resume.__get__(host)
        host._maybe_resume({"alive": True, "attach_generation": 1})
        host._maybe_resume({"alive": True, "attach_generation": 2})
        self.assertEqual(restarts, [True])


class SpringPipeWireTests(unittest.TestCase):
    def test_graph_is_one_stereo_wet_only_ladspa_tank(self):
        state = io24_spring.default_state(enabled=True)
        graph = io24_spring.build_graph(
            state, positions=("FL", "FR", "FC"),
            plugin="io24-spring-test")
        tanks = [node for node in graph["nodes"]
                 if node.get("label") == io24_spring.PLUGIN_LABEL]
        self.assertEqual(len(tanks), 1)
        self.assertEqual(tanks[0]["plugin"], "io24-spring-test")
        self.assertEqual(tanks[0]["control"],
                         io24_spring.plugin_controls(state))
        self.assertEqual(graph["inputs"], [
            "src0:In", "src1:In", "src2:In",
        ])
        self.assertEqual(graph["outputs"], [
            "tank:Output L", "tank:Output R",
        ])
        self.assertEqual(graph["links"][:2], [
            {"output": "src0:Out", "input": "tank:Input 1"},
            {"output": "src1:Out", "input": "tank:Input 2"},
        ])

    def test_config_targets_capture_and_usb_playback_5_6(self):
        conf = io24_spring.build_conf(
            io24_spring.default_state(enabled=True),
            "alsa_input.io24", "alsa_output.io24",
            capture_positions=("FL", "FR", "FC", "LFE", "RL", "RR"),
            playback_positions=("AUX0", "AUX1", "AUX2", "AUX3", "AUX4", "AUX5"),
            plugin="io24-spring-test")
        self.assertIn('"target.object": "alsa_input.io24"', conf)
        self.assertIn('"target.object": "alsa_output.io24"', conf)
        self.assertIn('"AUX4",\n      "AUX5"', conf)
        self.assertIn('"stream.dont-remix": true', conf)
        self.assertIn('"node.dont-fallback": true', conf)

    def test_three_channel_profile_returns_on_normal_main_playback_pair(self):
        positions = ("FL", "FR", "LFE")

        lane = io24_spring.playback_lane(positions)
        conf = io24_spring.build_conf(
            io24_spring.default_state(), "capture", "playback",
            capture_positions=("FL", "FR"),
            playback_positions=positions, plugin="test")

        self.assertEqual(lane["positions"], ("FL", "FR"))
        self.assertEqual(lane["source"], "return/ch1")
        self.assertFalse(lane["exclusive"])
        self.assertIn('"FL",\n      "FR"', conf)

    def test_six_channel_profile_keeps_the_dedicated_usb_5_6_lane(self):
        lane = io24_spring.playback_lane(
            ("AUX0", "AUX1", "AUX2", "AUX3", "AUX4", "AUX5"))

        self.assertEqual(lane["positions"], ("AUX4", "AUX5"))
        self.assertEqual(lane["source"], "return/ch3")
        self.assertTrue(lane["exclusive"])


class FakeMixer:
    DEFAULT_SEND_DB = 0.0

    def __init__(self):
        self.level = {}
        self.known = {}
        self.assigned = {}
        self.writes = []
        for source in ("return/ch1", "return/ch2", "return/ch3"):
            for bus in io24_spring.RETURN_BUSES:
                self.level[(source, bus)] = -6.0
                self.known[(source, bus)] = True
                self.assigned[(source, bus)] = bus != "mixb"
        self.level[("return/ch3", "main")] = None
        self.known[("return/ch3", "main")] = False
        self.assigned[("return/ch3", "main")] = False
        self.level[("return/ch3", "mixa")] = -4.0
        self.level[("return/ch3", "mixb")] = -8.0

    def send_db(self, source, bus):
        return self.level[(source, bus)]

    def has_send_level(self, source, bus):
        return self.known[(source, bus)]

    def send_assigned(self, source, bus):
        return self.assigned[(source, bus)]

    def set_send_db(self, source, bus, value):
        self.writes.append(("level", source, bus, value))
        self.level[(source, bus)] = value
        self.known[(source, bus)] = True

    def set_send_assigned(self, source, bus, value):
        self.writes.append(("assign", source, bus, bool(value)))
        self.assigned[(source, bus)] = bool(value)


class SpringRoutingTests(unittest.TestCase):
    def test_enable_uses_main_only_and_disable_restores_prior_routes(self):
        dev = FakeMixer()
        lane = io24_spring.playback_lane(
            ("AUX0", "AUX1", "AUX2", "AUX3", "AUX4", "AUX5"))
        prior = io24_spring.route_main_only(dev, lane=lane)
        self.assertTrue(dev.assigned[("return/ch3", "main")])
        self.assertEqual(dev.level[("return/ch3", "main")], 0.0)
        self.assertFalse(dev.assigned[("return/ch3", "mixa")])
        self.assertFalse(dev.assigned[("return/ch3", "mixb")])

        self.assertIsNone(io24_spring.restore_routes(dev, prior))
        self.assertFalse(dev.assigned[("return/ch3", "main")])
        self.assertTrue(dev.assigned[("return/ch3", "mixa")])
        self.assertFalse(dev.assigned[("return/ch3", "mixb")])
        self.assertEqual(dev.level[("return/ch3", "mixa")], -4.0)
        self.assertEqual(dev.level[("return/ch3", "mixb")], -8.0)

    def test_shared_main_pair_does_not_rewrite_desktop_playback_routes(self):
        dev = FakeMixer()
        before = (dict(dev.level), dict(dev.known), dict(dev.assigned))
        lane = io24_spring.playback_lane(("FL", "FR", "LFE"))

        prior = io24_spring.route_main_only(dev, lane=lane)
        self.assertEqual(dev.writes, [])
        self.assertEqual((dev.level, dev.known, dev.assigned), before)

        self.assertIsNone(io24_spring.restore_routes(dev, prior))
        self.assertEqual(dev.writes, [])
        self.assertEqual((dev.level, dev.known, dev.assigned), before)

    def test_changing_to_shared_main_restores_a_dedicated_lane_once(self):
        dev = FakeMixer()
        dedicated = io24_spring.playback_lane(
            ("AUX0", "AUX1", "AUX2", "AUX3", "AUX4", "AUX5"))
        prior = io24_spring.route_main_only(dev, lane=dedicated)
        dev.writes.clear()

        shared = io24_spring.playback_lane(("FL", "FR", "LFE"))
        routing = io24_spring.route_main_only(dev, prior, lane=shared)

        self.assertEqual(routing, {
            "source": "return/ch1", "exclusive": False, "buses": {},
        })
        self.assertEqual(dev.writes, [
            ("assign", "return/ch3", "main", False),
            ("level", "return/ch3", "mixa", -4.0),
            ("assign", "return/ch3", "mixa", True),
            ("level", "return/ch3", "mixb", -8.0),
            ("assign", "return/ch3", "mixb", False),
        ])


class SpringNativePluginTests(unittest.TestCase):
    @staticmethod
    def _process(state, frames=96000, impulse=True):
        with tempfile.TemporaryDirectory(prefix="io24-spring-test-") as directory:
            library = io24_spring.build_plugin(Path(directory))
            dll = ctypes.CDLL(str(library))
            process = dll.io24_spring_process
            pointer = ctypes.POINTER(ctypes.c_float)
            process.argtypes = [pointer, pointer, pointer, pointer,
                                ctypes.c_ulong, ctypes.c_ulong, pointer]
            process.restype = ctypes.c_int
            left_in = (ctypes.c_float * frames)()
            right_in = (ctypes.c_float * frames)()
            if impulse:
                left_in[0] = 0.75
            left_out = (ctypes.c_float * frames)()
            right_out = (ctypes.c_float * frames)()
            controls = io24_spring.plugin_controls(state)
            ordered = (ctypes.c_float * len(io24_spring.CONTROL_PORTS))(*(
                controls[name] for name in io24_spring.CONTROL_PORTS))
            result = process(left_in, right_in, left_out, right_out,
                             frames, 48000, ordered)
            return result, list(left_out), list(right_out)

    def test_ladspa_descriptor_has_exact_stereo_ports(self):
        class PortRangeHint(ctypes.Structure):
            _fields_ = [("descriptor", ctypes.c_int),
                        ("lower", ctypes.c_float), ("upper", ctypes.c_float)]

        class Descriptor(ctypes.Structure):
            _fields_ = [
                ("unique_id", ctypes.c_ulong), ("label", ctypes.c_char_p),
                ("properties", ctypes.c_int), ("name", ctypes.c_char_p),
                ("maker", ctypes.c_char_p), ("copyright", ctypes.c_char_p),
                ("port_count", ctypes.c_ulong),
                ("port_descriptors", ctypes.POINTER(ctypes.c_int)),
                ("port_names", ctypes.POINTER(ctypes.c_char_p)),
                ("port_hints", ctypes.POINTER(PortRangeHint)),
                ("implementation_data", ctypes.c_void_p),
            ]

        with tempfile.TemporaryDirectory(prefix="io24-spring-abi-") as directory:
            dll = ctypes.CDLL(str(io24_spring.build_plugin(Path(directory))))
            descriptor = dll.ladspa_descriptor
            descriptor.argtypes = [ctypes.c_ulong]
            descriptor.restype = ctypes.POINTER(Descriptor)
            plugin = descriptor(0).contents
            self.assertEqual(plugin.unique_id, 422025)
            self.assertEqual(plugin.label, b"io24_spring")
            self.assertEqual(tuple(plugin.port_names[i].decode()
                                   for i in range(plugin.port_count)),
                             io24_spring.CONTROL_PORTS + (
                                 "Input 1", "Input 2", "Output L", "Output R"))
            self.assertEqual(tuple(plugin.port_descriptors[i]
                                   for i in range(plugin.port_count)),
                             (0x5,) * len(io24_spring.CONTROL_PORTS) +
                             (0x9, 0x9, 0xA, 0xA))

    def test_impulse_has_bounded_decorrelated_decaying_tail(self):
        state = io24_spring.default_state(enabled=True)
        result, left, right = self._process(state)
        self.assertEqual(result, 0)
        self.assertTrue(all(math.isfinite(v) for v in left + right))
        self.assertLess(max(abs(v) for v in left + right), 1.01)
        # It is wet-only and has pre-delay: no dry impulse at sample zero.
        self.assertAlmostEqual(left[0], 0.0, places=7)
        self.assertGreater(sum(v * v for v in left[2400:24000]), 1.0e-7)
        self.assertNotEqual(left[2400:12000], right[2400:12000])
        self.assertGreater(
            sum(v * v for v in left[24000:48000]) / 24000.0, 3.0e-9)
        self.assertGreater(sum(v * v for v in left[12000:24000]),
                           sum(v * v for v in left[84000:96000]))

    def test_zero_width_is_mono_and_silence_stays_silent(self):
        state = io24_spring.default_state(enabled=True)
        state["width"] = 0.0
        result, left, right = self._process(state)
        self.assertEqual(result, 0)
        self.assertEqual(left, right)
        result, left, right = self._process(state, frames=4096, impulse=False)
        self.assertEqual(result, 0)
        self.assertEqual(max(map(abs, left + right)), 0.0)

    def test_output_gain_is_part_of_the_wet_processor(self):
        state = io24_spring.default_state(enabled=True)
        state["output_db"] = -60.0

        result, left, right = self._process(state)

        self.assertEqual(result, 0)
        self.assertLess(max(map(abs, left + right)), 0.002)


if __name__ == "__main__":
    unittest.main()
