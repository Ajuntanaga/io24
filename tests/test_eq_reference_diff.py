#!/usr/bin/env python3
"""Hardware-free contracts for the alternate-EQ pixel-diff gate."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.eq_reference_diff import diff_images


class EqReferenceDiffTests(unittest.TestCase):
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
