#!/usr/bin/env python3
"""Hardware-free contracts for the sustained-loop block-201 A/B."""

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _directory in (ROOT, ROOT / "re"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

probe = importlib.import_module("io24_fx_sustained_loop_probe")


def _stage(input1=-15.0, mixa=-18.0, mixb=-18.0, input2=-89.0):
    return {"input1": input1, "mixa": mixa, "mixb": mixb, "input2": input2,
            "channel_rms_dbfs": [input1, input2, mixa, mixa, mixb, mixb]}


def _stages(fx_delta=0.0, control_delta=6.0, drift=0.0):
    quiet = _stage()
    return {
        "initial": quiet,
        "fx_off": quiet,
        "fx_on": _stage(input1=-15.0 + fx_delta, mixa=-18.0 + fx_delta,
                        mixb=-18.0 + fx_delta),
        "reverb_off": quiet,
        "reverb_on": _stage(input1=-15.0 + control_delta,
                            mixa=-18.0 + control_delta,
                            mixb=-18.0 + control_delta),
        "final": _stage(input1=-15.0 + drift, mixa=-18.0 + drift,
                        mixb=-18.0 + drift),
    }


class ClassifyTests(unittest.TestCase):
    def test_a_moving_block201_reads_as_contributing(self):
        verdict = probe.classify(_stages(fx_delta=7.0))
        self.assertEqual(verdict["status"], "BLOCK201_CONTRIBUTES_TO_MAIN")
        self.assertTrue(verdict["run_valid"])
        self.assertTrue(verdict["block201"]["detected"])

    def test_an_inert_block201_reads_as_not_contributing(self):
        verdict = probe.classify(_stages(fx_delta=0.2))
        self.assertEqual(verdict["status"],
                         "BLOCK201_DOES_NOT_CONTRIBUTE_TO_MAIN")
        self.assertTrue(verdict["run_valid"])

    def test_a_dead_control_invalidates_the_run(self):
        """A loop that the reverb cannot move is not an instrument."""
        verdict = probe.classify(_stages(fx_delta=0.0, control_delta=0.3))
        self.assertEqual(verdict["status"],
                         "INVALID_REVERB_CONTROL_DID_NOT_MOVE_THE_LOOP")
        self.assertFalse(verdict["run_valid"])

    def test_a_drifting_loop_invalidates_the_run(self):
        """A regenerative loop can wander; if it wanders further than the
        effect window, no A/B taken across it means anything."""
        verdict = probe.classify(_stages(fx_delta=0.0, drift=5.0))
        self.assertEqual(verdict["status"],
                         "INVALID_LOOP_DRIFTED_MORE_THAN_THE_EFFECT_WINDOW")
        self.assertFalse(verdict["run_valid"])

    def test_the_silent_input_never_decides_anything(self):
        """Input 2 has nothing plugged into it; its noise floor must not vote."""
        stages = _stages(fx_delta=0.0)
        stages["fx_on"]["input2"] = -50.0
        verdict = probe.classify(stages)
        self.assertEqual(verdict["status"],
                         "BLOCK201_DOES_NOT_CONTRIBUTE_TO_MAIN")


class SequenceTests(unittest.TestCase):
    class Device:
        def __init__(self):
            self.calls = []

        def set_fx(self, model, **kwargs):
            self.calls.append(("set_fx", model, kwargs["on"], kwargs))

        def set_reverb(self, **kwargs):
            self.calls.append(("set_reverb", kwargs["on"]))

        def reverb_off(self):
            self.calls.append(("reverb_off",))

    def _run(self):
        device = self.Device()
        stages = {}
        probe.run_sequence(
            device, Path("."),
            ("delay", {"on": True, "time_s": 0.25, "feedback": 1.0,
                       "mix": 1.0}),
            {"on": True, "size": 0.96, "mix": 1.0},
            capture=lambda label, _out: label,
            measure=lambda label: dict(_stage(), capture=label),
            settle=lambda _s: None, stages=stages)
        return device, stages

    def test_only_the_on_flag_varies(self):
        """Every other field of the Host-known call is resent unchanged, so the
        single variable is whether the engine is running."""
        device, _stages = self._run()
        fx = [call for call in device.calls if call[0] == "set_fx"]
        self.assertEqual([call[2] for call in fx], [False, True])
        for call in fx:
            self.assertEqual(call[3]["time_s"], 0.25)
            self.assertEqual(call[3]["feedback"], 1.0)
            self.assertEqual(call[3]["mix"], 1.0)

    def test_it_writes_no_routing_and_no_appl_parameter(self):
        device, _stages = self._run()
        names = {call[0] for call in device.calls}
        self.assertEqual(names, {"set_fx", "set_reverb", "reverb_off"})

    def test_both_engines_end_on_and_every_stage_is_captured(self):
        device, stages = self._run()
        self.assertEqual(device.calls[-1], ("set_reverb", True))
        self.assertEqual(sorted(stages), ["final", "fx_off", "fx_on",
                                          "initial", "reverb_off",
                                          "reverb_on"])

    def test_measure_reads_every_bus(self):
        self.assertEqual(sorted(probe.BUSES),
                         ["input1", "input2", "mixa", "mixb"])
        self.assertEqual(probe.BUSES["mixa"], (2, 3))


class GateTests(unittest.TestCase):
    def test_live_execution_requires_an_explicit_flag(self):
        self.assertEqual(probe.main([]), 0)

    def test_a_capture_failure_fails_closed(self):
        def runner(_argv, **_kwargs):
            class Result:
                returncode = 1
                stderr = "device busy"
            return Result()

        with self.assertRaises(probe.LoopProbeError) as caught:
            probe.capture_stage("s", Path("/nonexistent-dir-xyz"),
                                runner=runner)
        self.assertIn("device busy", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
