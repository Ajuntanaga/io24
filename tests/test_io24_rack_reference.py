import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

import io24_rack_reference
from tools.eq_reference_diff import diff_images, rack_regions
from tools import render_rack_assets


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs" / "design"


class RackReferenceTests(unittest.TestCase):
    def test_limiter_faceplate_changes_stay_in_live_or_cleanup_regions(self):
        spec = io24_rack_reference.rack("limiter")
        rectangles, circles = rack_regions(
            spec, (0, 0) + tuple(spec["source_size"]))
        result, _changed, _allowed, _unexpected = diff_images(
            DESIGN / spec["source"], DESIGN / spec["output"],
            allowed_rectangles=rectangles + list(spec["cleanup_regions"]),
            allowed_circles=circles,
            scope_rectangle=(0, 0) + tuple(spec["source_size"]))

        self.assertGreater(result["changed_pixels"], 0)
        self.assertEqual(result["unexpected_pixels"], 0)

    def test_compiler_outputs_every_declared_asset(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = render_rack_assets.compile_rack(
                "limiter", DESIGN, Path(temp))
            self.assertEqual(receipt["rack_id"], "limiter")
            for filename in (
                    "limiter-faceplate.png",
                    "limiter-calibration-underlay.png",
                    "limiter-calibration-nodes.png",
                    "limiter-knob.png",
                    "limiter-rack-assets.json"):
                self.assertTrue((Path(temp) / filename).is_file())

    def test_compiler_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as first:
            with tempfile.TemporaryDirectory() as second:
                render_rack_assets.compile_rack(
                    "limiter", DESIGN, Path(first))
                render_rack_assets.compile_rack(
                    "limiter", DESIGN, Path(second))
                for filename in io24_rack_reference.rack("limiter")["generated"]:
                    self.assertEqual(
                        (Path(first) / filename).read_bytes(),
                        (Path(second) / filename).read_bytes())

    def test_compiler_receipt_hashes_every_asset(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            receipt = render_rack_assets.compile_rack(
                "limiter", DESIGN, output)
            persisted = json.loads(
                (output / "limiter-rack-assets.json").read_text())
            self.assertEqual(persisted, receipt)
            self.assertEqual(set(receipt), {
                "rack_id", "source_sha256", "outputs", "manifest_sha256"})
            self.assertEqual(set(receipt["outputs"]), {
                "limiter-faceplate.png",
                "limiter-calibration-underlay.png",
                "limiter-calibration-nodes.png",
                "limiter-knob.png",
            })
            for filename, digest in receipt["outputs"].items():
                self.assertEqual(
                    digest,
                    hashlib.sha256((output / filename).read_bytes()).hexdigest())
            self.assertEqual(
                receipt["source_sha256"],
                hashlib.sha256(
                    (output / "limiter-reference.png").read_bytes()).hexdigest())
            manifest_bytes = json.dumps(
                io24_rack_reference.rack("limiter"), sort_keys=True,
                separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            self.assertEqual(
                receipt["manifest_sha256"],
                hashlib.sha256(manifest_bytes).hexdigest())

    def test_check_mode_does_not_write_design_assets(self):
        filenames = ("limiter-reference.png",) + tuple(
            io24_rack_reference.rack("limiter")["generated"])
        before = {
            filename: ((DESIGN / filename).read_bytes(),
                       (DESIGN / filename).stat().st_mtime_ns)
            for filename in filenames
        }
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "render_rack_assets.py"),
             "limiter", "--check"],
            cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("limiter assets match", result.stdout)
        after = {
            filename: ((DESIGN / filename).read_bytes(),
                       (DESIGN / filename).stat().st_mtime_ns)
            for filename in filenames
        }
        self.assertEqual(after, before)

    def test_check_mode_mismatch_is_nonwriting_and_nonzero(self):
        with tempfile.TemporaryDirectory() as temp:
            design = Path(temp)
            for filename in ("vintage-eq-reference.png",
                             "vintage-lowmid-knob.png"):
                shutil.copyfile(DESIGN / filename, design / filename)
            render_rack_assets.compile_rack("limiter", design)
            mismatch = design / "limiter-faceplate.png"
            mismatch.write_bytes(b"intentional mismatch")
            filenames = ("limiter-reference.png",) + tuple(
                io24_rack_reference.rack("limiter")["generated"])
            before = {
                filename: ((design / filename).read_bytes(),
                           (design / filename).stat().st_mtime_ns)
                for filename in filenames
            }
            returncode = render_rack_assets.main(
                ["limiter", "--check"], design_root=design)
            after = {
                filename: ((design / filename).read_bytes(),
                           (design / filename).stat().st_mtime_ns)
                for filename in filenames
            }
            self.assertNotEqual(returncode, 0)
            self.assertEqual(after, before)

    def test_isolated_knob_rejects_opaque_rectangular_alpha(self):
        with tempfile.TemporaryDirectory() as temp:
            design = Path(temp)
            Image.new("RGBA", (32, 32), (40, 50, 60, 255)).save(
                design / "opaque.png")
            spec = io24_rack_reference.rack("limiter")
            spec["knob_source"] = "opaque.png"
            with self.assertRaisesRegex(ValueError, "transparent"):
                render_rack_assets._isolated_knob(spec, design)

    def test_limiter_contract_is_exact(self):
        spec = io24_rack_reference.rack("limiter")
        self.assertEqual(tuple(spec["controls"]), ("threshold", "release"))
        self.assertEqual(spec["controls"]["threshold"]["range"], (-40.0, 0.0))
        self.assertEqual(spec["controls"]["threshold"]["step"], 0.01)
        self.assertEqual(spec["controls"]["threshold"]["default"], -28.0)
        self.assertEqual(spec["controls"]["release"]["range"], (0.05, 1.5))
        self.assertEqual(spec["controls"]["release"]["step"], 0.01)
        self.assertEqual(spec["controls"]["release"]["default"], 0.4)

    def test_geometry_scales_from_one_coordinate_authority(self):
        small = io24_rack_reference.control_layout("limiter", 600, 180)
        large = io24_rack_reference.control_layout("limiter", 1200, 360)
        for field in ("threshold", "release"):
            self.assertAlmostEqual(large[field][0], small[field][0] * 2)
            self.assertAlmostEqual(large[field][1], small[field][1] * 2)
            self.assertAlmostEqual(large[field][2], small[field][2] * 2)

    def test_value_angle_round_trip_clamps_at_contract_bounds(self):
        control = io24_rack_reference.rack("limiter")["controls"]["threshold"]
        for value in (-50.0, -40.0, -28.0, 0.0, 4.0):
            fraction = io24_rack_reference.value_fraction(control, value)
            restored = io24_rack_reference.fraction_value(control, fraction)
            self.assertGreaterEqual(restored, -40.0)
            self.assertLessEqual(restored, 0.0)

    def test_scaled_rect_and_pointer_angle(self):
        self.assertEqual(
            io24_rack_reference.scaled_rect((485, 104, 430, 241), 700, 210, "limiter"),
            (242.5, 52.0, 215.0, 120.5),
        )
        control = io24_rack_reference.rack("limiter")["controls"]["threshold"]
        self.assertAlmostEqual(io24_rack_reference.pointer_angle(control, -40.0), 135.0)
        self.assertAlmostEqual(io24_rack_reference.pointer_angle(control, 0.0), 405.0)

    def test_validation_rejects_structural_errors(self):
        spec = io24_rack_reference.rack("limiter")
        self.assertEqual(io24_rack_reference.validate_rack(spec)["rack_id"], "limiter")

        for key in ("source_size", "panel", "display", "lamp", "controls",
                    "ears", "slots", "screws"):
            broken = dict(spec)
            broken.pop(key)
            with self.assertRaises(ValueError):
                io24_rack_reference.validate_rack(broken)

        broken = dict(spec)
        broken["controls"] = dict(spec["controls"])
        broken["controls"]["release"] = dict(spec["controls"]["threshold"])
        with self.assertRaises(ValueError):
            io24_rack_reference.validate_rack(broken)

    def test_validation_rejects_bad_rack_hardware_geometry(self):
        bad_values = {
            "ears": (((0, 0, 38),), ((-1, 0, 38, 420),)),
            "slots": (((9, 34, 0, 52),), ((1390, 34, 20, 52),)),
            "screws": (((63, 37),), ((5, 37, 9),)),
        }
        for field, candidates in bad_values.items():
            for value in candidates:
                broken = io24_rack_reference.rack("limiter")
                broken[field] = value
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        io24_rack_reference.validate_rack(broken)

    def test_validation_rejects_paths_and_bad_geometry(self):
        spec = io24_rack_reference.rack("limiter")
        for field in ("source", "output"):
            broken = dict(spec)
            broken[field] = "../escape.png"
            with self.assertRaises(ValueError):
                io24_rack_reference.validate_rack(broken)

        broken = dict(spec)
        broken["display"] = (0, 0, 0, 1)
        with self.assertRaises(ValueError):
            io24_rack_reference.validate_rack(broken)

        for lamp in ((5, 20, 10), (20, 5, 10), (1395, 20, 10), (20, 415, 10)):
            broken = dict(spec)
            broken["lamp"] = lamp
            with self.assertRaises(ValueError):
                io24_rack_reference.validate_rack(broken)

    def test_validation_rejects_nonfinite_step_geometry_and_sweep(self):
        broken = io24_rack_reference.rack("limiter")
        broken["controls"]["threshold"]["step"] = float("nan")
        with self.assertRaises(ValueError):
            io24_rack_reference.validate_rack(broken)

        broken = io24_rack_reference.rack("limiter")
        broken["display"] = (float("nan"), 0, 10, 10)
        with self.assertRaises(ValueError):
            io24_rack_reference.validate_rack(broken)

        broken = io24_rack_reference.rack("limiter")
        broken["controls"]["release"]["sweep"] = (135.0, float("inf"))
        with self.assertRaises(ValueError):
            io24_rack_reference.validate_rack(broken)


if __name__ == "__main__":
    unittest.main()
