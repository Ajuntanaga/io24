#!/usr/bin/env python3
"""Hardware-free contracts for the direct-gate positive control.

A null is only evidence if the rig could have seen the effect. This probe
exists to prove the Main/Input-2 meter observes a Channel-2 gate change, so
its classifier must not be able to report success on a flat or drifting
measurement. Nothing here opens USB.
"""

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
RE_DIR = ROOT / "re"
for path in (str(ROOT), str(RE_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

SPEC = importlib.util.spec_from_file_location(
    "io24_direct_gate_positive_control",
    RE_DIR / "io24_direct_gate_positive_control.py")
CONTROL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROL)


def _window(label, ratio, mad=0.3):
    return {"meter": {"label": label,
                      "median_main_to_input2_db": ratio,
                      "mad_main_to_input2_db": mad}}


class ClassifierTests(unittest.TestCase):
    def test_a_large_symmetric_effect_is_detected(self):
        result = CONTROL.common_classify([
            _window("off_before", 4.89, 0.3494),
            _window("on", -23.25, 0.4486),
            _window("off_after", 4.77, 0.3001)])
        self.assertEqual(result["classification"], "DIRECT_GATE_EFFECT_DETECTED")
        self.assertTrue(result["effect_detected"])
        self.assertTrue(result["stable"])
        self.assertLess(result["effect_delta_db"], -25.0)

    def test_a_flat_measurement_is_not_a_detection(self):
        result = CONTROL.common_classify([
            _window("off_before", 0.98), _window("on", 0.97),
            _window("off_after", 1.09)])
        self.assertEqual(result["classification"],
                         "NO_DIRECT_GATE_EFFECT_DETECTED")
        self.assertFalse(result["effect_detected"])

    def test_an_effect_inside_the_noise_is_not_a_detection(self):
        # Delta 2.0 dB against MAD 0.5 needs 3.0 dB to count.
        result = CONTROL.common_classify([
            _window("off_before", 0.0, 0.5), _window("on", -2.0, 0.5),
            _window("off_after", 0.0, 0.5)])
        self.assertFalse(result["effect_detected"])
        self.assertAlmostEqual(result["detection_threshold_db"], 3.0)

    def test_a_drifting_baseline_is_refused_even_with_a_large_delta(self):
        result = CONTROL.common_classify([
            _window("off_before", 0.0), _window("on", -30.0),
            _window("off_after", 5.0)])
        self.assertEqual(result["classification"],
                         "INCONCLUSIVE_BASELINE_DRIFT")
        self.assertFalse(result["effect_detected"])

    def test_the_detection_threshold_never_falls_below_the_floor(self):
        result = CONTROL.common_classify([
            _window("off_before", 0.0, 0.0), _window("on", -0.5, 0.0),
            _window("off_after", 0.0, 0.0)])
        self.assertGreaterEqual(result["detection_threshold_db"], 1.0)
        self.assertFalse(result["effect_detected"])

    def test_the_meaning_tracks_the_verdict(self):
        detected = CONTROL.common_classify([
            _window("off_before", 4.89), _window("on", -23.25),
            _window("off_after", 4.77)])
        self.assertIn("observes a Channel-2 gate change", detected["meaning"])
        missed = CONTROL.common_classify([
            _window("off_before", 0.0), _window("on", 0.0),
            _window("off_after", 0.0)])
        self.assertIn("blind meter", missed["meaning"])


class BoundaryTests(unittest.TestCase):
    def test_the_probe_is_hardware_free_by_default(self):
        self.assertEqual(CONTROL.main([]), 0)

    def test_it_refuses_a_flat_battery_before_opening_the_device(self):
        import json, tempfile, io, contextlib, os
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "capacity")
            open(path, "w").write("7\n")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = CONTROL.main(["--execute", "--battery-path", path])
            self.assertEqual(code, 3)
            self.assertEqual(json.loads(buffer.getvalue())["status"],
                             "BLOCKED_BATTERY")

    def test_it_calls_only_the_four_authorized_device_writes(self):
        # Check what the code actually calls, not what the prose mentions --
        # the docstring names MemP precisely to say it is not used.
        import ast
        source = CONTROL.__file__ or str(
            Path(CONTROL.__spec__.origin))
        tree = ast.parse(Path(source).read_text(encoding="utf-8"))
        called = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                target = node.func
                if isinstance(target, ast.Attribute):
                    called.add(target.attr)
                elif isinstance(target, ast.Name):
                    called.add(target.id)
        for forbidden in ("save_device_slot", "save_known_device_slot",
                          "save_uc_device_slot", "set_preset_slot",
                          "recall_device_slot", "set_fx", "set_reverb",
                          "set_send_db", "set_mix_db"):
            self.assertNotIn(forbidden, called)
        # The writes it does make are exactly the authorized four.
        self.assertTrue({"set_main_volume", "set_gain", "set_gate",
                         "gate_off"}.issubset(called))


if __name__ == "__main__":
    unittest.main()
