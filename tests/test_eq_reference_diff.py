#!/usr/bin/env python3
"""Hardware-free contracts for the alternate-EQ pixel-diff gate."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

import io24_eq_reference
import io24_rack_reference
from tools.eq_reference_diff import diff_images, model_regions, rack_regions


ROOT = Path(__file__).resolve().parents[1]


class EqReferenceDiffTests(unittest.TestCase):
    def test_limiter_regions_come_from_the_rack_manifest(self):
        spec = io24_rack_reference.rack("limiter")
        rectangles, circles = rack_regions(spec, (10, 20, 700, 210))

        self.assertEqual(len(rectangles), 1 + len(spec["cleanup_regions"]) +
                         len(spec["controls"]))
        self.assertEqual(len(circles), 3)
        self.assertEqual(circles[0][:2], (150, 132))

    def test_limiter_live_regions_cover_ticks_values_focus_and_lamp_at_both_widths(self):
        spec = io24_rack_reference.rack("limiter")
        style = spec["live_style"]
        for width in (600, 1040):
            rects, circles = rack_regions(spec, (0, 0, width, 180))
            def allowed(x, y):
                return any(rx <= x < rx + rw and ry <= y < ry + rh
                           for rx, ry, rw, rh in rects) or any(
                    (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2
                    for cx, cy, r in circles)
            geometry = io24_rack_reference.control_layout("limiter", width, 180)
            for cx, cy, radius in geometry.values():
                self.assertTrue(allowed(cx, cy - radius * style["tick_major_outer"]))
                self.assertTrue(allowed(cx + radius + style["knob_focus_px"], cy))
                self.assertTrue(allowed(cx, cy + radius + style["value_offset_px"] +
                                        style["value_height_px"] / 2))
            lx, ly, lr = spec["lamp"]
            scale = min(width / spec["source_size"][0],
                        180 / spec["source_size"][1])
            self.assertTrue(allowed(lx * width / spec["source_size"][0] +
                                    lr * scale + style["lamp_focus_px"],
                                    ly * 180 / spec["source_size"][1]))
            # Static rack hardware is outside every live allowance.
            sx, sy, _radius = spec["screws"][0]
            self.assertFalse(allowed(sx * width / spec["source_size"][0],
                                     sy * 180 / spec["source_size"][1]))

    def test_calibration_underlays_are_exact_reference_crops(self):
        for model in ("standard", "passive", "vintage"):
            with self.subTest(model=model):
                art = io24_eq_reference.rack(model)
                source = Image.open(
                    ROOT / "docs" / "design" / art["filename"]).convert(
                        "RGB")
                x, y, width, height = art["rack_crop"]
                source = np.asarray(source.crop(
                    (x, y, x + width, y + height)))
                underlay = np.asarray(Image.open(
                    ROOT / "docs" / "design" /
                    art["calibration_underlay_filename"]).convert("RGB"))
                self.assertTrue(np.array_equal(source, underlay))

    def test_alternate_faceplates_change_only_declared_dynamic_or_cleanup_regions(self):
        for model in ("passive", "vintage"):
            with self.subTest(model=model):
                art = io24_eq_reference.rack(model)
                source_image = Image.open(
                    ROOT / "docs" / "design" / art["filename"]).convert(
                        "RGB")
                crop_x, crop_y, width, height = art["rack_crop"]
                source = np.asarray(source_image.crop((
                    crop_x, crop_y, crop_x + width, crop_y + height)))
                faceplate = np.asarray(Image.open(
                    ROOT / "docs" / "design" /
                    art["faceplate_filename"]).convert("RGB"))
                changed = np.any(source != faceplate, axis=2)
                allowed = np.zeros((height, width), dtype=bool)
                padding = 12
                for x, y, region_width, region_height in \
                        art["control_clear_regions"]:
                    allowed[max(0, y - padding):
                            min(height, y + region_height + padding),
                            max(0, x - padding):
                            min(width, x + region_width + padding)] = True
                for x, y, region_width, region_height in \
                        art.get("faceplate_cleanup_regions", ()):
                    allowed[y:y + region_height,
                            x:x + region_width] = True
                x, y, plot_width, plot_height = art["plot"]
                allowed[y:y + plot_height, x:x + plot_width] = True
                lamp_x, lamp_y, lamp_radius = art["lamp"]
                yy, xx = np.ogrid[:height, :width]
                allowed |= ((xx - lamp_x) ** 2 + (yy - lamp_y) ** 2 <=
                            (lamp_radius * 2.35 + padding) ** 2)
                self.assertTrue(changed.any())
                self.assertFalse((changed & ~allowed).any())

    def test_node_overlays_are_transparent_and_reference_sized(self):
        for model in ("standard", "passive", "vintage"):
            with self.subTest(model=model):
                art = io24_eq_reference.rack(model)
                overlay = Image.open(
                    ROOT / "docs" / "design" /
                    art["calibration_nodes_filename"])
                self.assertEqual(overlay.mode, "RGBA")
                self.assertEqual(overlay.size, art["rack_crop"][2:])
                alpha = np.asarray(overlay)[:, :, 3]
                self.assertEqual(int(alpha.min()), 0)
                self.assertGreater(int(alpha.max()), 0)

    def test_model_regions_scale_the_shared_landmark_manifest(self):
        rectangles, circles = model_regions(
            "passive", (10, 20, 1078, 241))

        self.assertEqual(rectangles[0], (336, 69, 308, 142))
        self.assertEqual(rectangles[1], (47, 43, 251, 218))
        self.assertEqual(rectangles[2], (649, 43, 405, 218))
        self.assertEqual(circles, [(1026, 234, 25)])

    def test_scope_excludes_unrelated_host_animation(self):
        with tempfile.TemporaryDirectory(prefix="io24-eq-diff-") as temp:
            root = Path(temp)
            baseline = Image.new("RGBA", (8, 8), (0, 0, 0, 255))
            actual = baseline.copy()
            actual.putpixel((0, 0), (255, 0, 0, 255))
            actual.putpixel((4, 4), (0, 255, 0, 255))
            baseline_path = root / "baseline.png"
            actual_path = root / "actual.png"
            baseline.save(baseline_path)
            actual.save(actual_path)

            result, changed, _allowed, unexpected = diff_images(
                baseline_path, actual_path,
                allowed_rectangles=((4, 4, 1, 1),),
                scope_rectangle=(2, 2, 4, 4))

            self.assertEqual(result["source_changed_pixels"], 2)
            self.assertEqual(result["changed_pixels"], 1)
            self.assertEqual(result["allowed_changed_pixels"], 1)
            self.assertEqual(result["unexpected_pixels"], 0)
            self.assertFalse(changed[0, 0])
            self.assertFalse(unexpected.any())

    def test_tolerance_ignores_gpu_noise_but_not_real_panel_changes(self):
        with tempfile.TemporaryDirectory(prefix="io24-eq-diff-") as temp:
            root = Path(temp)
            baseline = Image.new("RGBA", (4, 2), (40, 40, 40, 255))
            actual = baseline.copy()
            actual.putpixel((0, 0), (47, 40, 40, 255))
            actual.putpixel((3, 1), (70, 40, 40, 255))
            baseline_path = root / "baseline.png"
            actual_path = root / "actual.png"
            baseline.save(baseline_path)
            actual.save(actual_path)

            result, _changed, _allowed, unexpected = diff_images(
                baseline_path, actual_path, max_channel_delta=10)

            self.assertEqual(result["changed_pixels"], 1)
            self.assertEqual(result["unexpected_bbox"], [3, 1, 4, 2])
            self.assertTrue(unexpected[1, 3])


if __name__ == "__main__":
    unittest.main()
