import unittest

import io24_rack_reference


class RackReferenceTests(unittest.TestCase):
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

        for key in ("source_size", "panel", "display", "lamp", "controls"):
            broken = dict(spec)
            broken.pop(key)
            with self.assertRaises(ValueError):
                io24_rack_reference.validate_rack(broken)

        broken = dict(spec)
        broken["controls"] = dict(spec["controls"])
        broken["controls"]["release"] = dict(spec["controls"]["threshold"])
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
