#!/usr/bin/env python3
"""Hardware-free contracts for the 96 kHz Voice FX Delay fallback."""

import ctypes
from pathlib import Path
import shutil
import tempfile
import unittest

import io24_mbc
import io24_voicefx_delay


class DelayStateTests(unittest.TestCase):
    def test_uc_vocal_echo_controls_map_one_to_one(self):
        state = {
            "on": True,
            "time_s": 0.173,
            "feedback": 0.82,
            "mix": 0.36,
        }
        self.assertEqual(io24_voicefx_delay.validate_state(state), state)
        self.assertEqual(io24_voicefx_delay.plugin_controls(state), {
            "On": 1.0,
            "Time (s)": 0.173,
            "Feedback": 0.82,
            "WetDry": 0.36,
        })

    def test_incomplete_nonfinite_and_out_of_range_states_are_refused(self):
        for state in (
                {"on": True, "time_s": 0.1, "feedback": 0.5},
                {"on": 1, "time_s": 0.1, "feedback": 0.5, "mix": 0.5},
                {"on": True, "time_s": float("nan"),
                 "feedback": 0.5, "mix": 0.5},
                {"on": True, "time_s": 0.3,
                 "feedback": 0.5, "mix": 0.5},
                {"on": True, "time_s": 0.1,
                 "feedback": 1.1, "mix": 0.5}):
            with self.subTest(state=state), self.assertRaises(ValueError):
                io24_voicefx_delay.validate_state(state)

    def test_host_feature_keeps_the_input_and_exact_delay_state(self):
        state = {
            "version": 1,
            "target": 2,
            "state": {
                "on": False, "time_s": 0.173,
                "feedback": 0.25, "mix": 0.8,
            },
        }
        self.assertEqual(
            io24_voicefx_delay.validate_host_feature(state), state)

    def test_host_feature_rejects_unknown_shape_or_owner(self):
        state = {
            "version": 1,
            "target": 3,
            "state": io24_voicefx_delay.default_state(),
        }
        with self.assertRaisesRegex(ValueError, "target"):
            io24_voicefx_delay.validate_host_feature(state)
        state["target"] = 1
        state["extra"] = True
        with self.assertRaisesRegex(ValueError, "must contain"):
            io24_voicefx_delay.validate_host_feature(state)
        state.pop("extra")
        state["target"] = 1.0
        with self.assertRaisesRegex(ValueError, "target"):
            io24_voicefx_delay.validate_host_feature(state)


@unittest.skipUnless(shutil.which("cc"), "requires a C compiler")
class DelayProcessorTests(unittest.TestCase):
    def test_impulse_timing_and_feedback_are_correct_at_96khz(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin = io24_voicefx_delay.build_plugin(directory)
            self.assertTrue(Path(plugin).is_file())
            library = ctypes.CDLL(str(plugin))
            process = library.io24_voicefx_delay_process
            pointer = ctypes.POINTER(ctypes.c_float)
            process.argtypes = [pointer, pointer, ctypes.c_ulong,
                                ctypes.c_ulong, pointer]
            process.restype = ctypes.c_int

            frames = 2200
            source = (ctypes.c_float * frames)()
            output = (ctypes.c_float * frames)()
            controls = (ctypes.c_float * 4)(1.0, 0.01, 0.5, 1.0)
            source[0] = 1.0

            self.assertEqual(
                process(source, output, frames, 96000, controls), 0)
            self.assertAlmostEqual(output[0], 0.0, places=6)
            self.assertAlmostEqual(output[959], 0.0, places=6)
            self.assertAlmostEqual(output[960], 1.0, places=6)
            self.assertAlmostEqual(output[1920], 0.5, places=6)

    def test_bypass_is_bitwise_dry_at_96khz(self):
        with tempfile.TemporaryDirectory() as directory:
            library = ctypes.CDLL(str(
                io24_voicefx_delay.build_plugin(directory)))
            process = library.io24_voicefx_delay_process
            pointer = ctypes.POINTER(ctypes.c_float)
            process.argtypes = [pointer, pointer, ctypes.c_ulong,
                                ctypes.c_ulong, pointer]
            process.restype = ctypes.c_int
            values = (0.25, -0.5, 0.75, 0.0)
            source = (ctypes.c_float * len(values))(*values)
            output = (ctypes.c_float * len(values))()
            controls = (ctypes.c_float * 4)(0.0, 0.125, 1.0, 1.0)

            self.assertEqual(process(source, output, len(values), 96000,
                                     controls), 0)
            self.assertEqual(tuple(output), values)


class DelayInsertGraphTests(unittest.TestCase):
    def test_delay_only_processes_the_selected_input(self):
        state = io24_voicefx_delay.default_state()
        graph = io24_mbc.build_insert_graph(
            {}, delays={2: state}, delay_plugin="test-delay")
        nodes = {node["name"]: node for node in graph["nodes"]}
        links = {(link["output"], link["input"])
                 for link in graph["links"]}

        self.assertNotIn("in1_delay", nodes)
        self.assertEqual(nodes["in2_delay"]["plugin"], "test-delay")
        self.assertIn(("src0:Out", "out1:In"), links)
        self.assertIn(("src1:Out", "in2_delay:Input"), links)
        self.assertIn(("in2_delay:Output", "out2:In"), links)

    def test_multiband_precedes_delay_in_one_shared_channel_graph(self):
        graph = io24_mbc.build_insert_graph(
            {1: io24_mbc.default_snapshot()},
            delays={1: io24_voicefx_delay.default_state()},
            delay_plugin="test-delay")
        links = {(link["output"], link["input"])
                 for link in graph["links"]}
        self.assertIn(("in1_sum:Out", "in1_delay:Input"), links)
        self.assertIn(("in1_delay:Output", "out1:In"), links)

    def test_return_contains_union_of_multiband_and_delay_channels(self):
        conf = io24_mbc.build_insert_conf(
            {1: io24_mbc.default_snapshot()},
            "alsa_input.io24", "alsa_output.io24", with_comp=True,
            delays={2: io24_voicefx_delay.default_state()},
            delay_plugin="test-delay")
        self.assertIn('"Gain 1": 1.0', conf)
        self.assertIn('"Gain 2": 1.0', conf)


if __name__ == "__main__":
    unittest.main()
