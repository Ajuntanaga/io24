#!/usr/bin/env python3
"""Hardware-free contracts for editable Passive/Vintage EQ bodies.

The Host keeps each model in its own UC semantic form, exposes the exact
switches and amounts, draws the vendor-designed response, and carries that
state through save/reconnect without coercing it into Standard bands.

Nothing here opens USB.
"""

import math
import os
import queue
import inspect
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

from PIL import Image, ImageChops

import io24
import io24_alt_eq
import io24_presets
import io24gtk


VINTAGE = {
    "__classid": "{E1C5E024-C5CD-473C-B08A-6EC177812E01}",
    "eqallon": 1, "lowgain": 1.76, "lowfreq": 0, "lowmidgain": -3.84,
    "lowmidfreq": 0, "himidgain": 1.6, "himidfreq": 1, "higain": 0.96,
}

PASSIVE = {
    "__classid": "{C0730CBB-5135-4558-9222-C40BDBA036ED}",
    "eqallon": 1, "bboost": 3.899999, "batten": 0.0, "bfreq": 3,
    "mboost": 1.8, "bbwidth": 4.55, "mfreq": 6, "hatten": 0.0,
    "hsfreq": 2,
}

FLAT = [{"shape": "off", "freq": f, "gain": 0.0, "q": 0.7}
        for f in (120.0, 600.0, 2500.0, 8000.0)]

STANDARD = {
    "__classid": "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}",
    "eqallon": 1,
}

COMPLETE_BASE = {
    "preset_name": "public-test-base",
    "opt": {},
    "filter": {},
    "gate": {},
    "limit": {},
    "eq": STANDARD,
    "comp": {},
}

EXACT_ALT_EQ_AVAILABLE = io24_alt_eq.designer_status()[0]


def _slot_kwargs(**extra):
    kwargs = dict(
        bands=[dict(band) for band in FLAT], hpf_hz=24.0, eq_first=False,
        gate={"on": True, "threshold_db": -48.7, "range_db": -60.0,
              "attack_s": .005, "release_s": .3, "keyfilter_hz": 325.0,
              "keylisten": False, "expander": True},
        compressor_model=2,
        compressor={"on": True, "input_db": -30.0, "output_db": -3.0,
                    "attack_s": .0001, "release_s": .25, "ratio_index": 3,
                    "keyfilter_hz": 0.0, "keylisten": False},
        limiter={"on": True, "threshold_db": -.8},
        voicefx_model="delay",
        voicefx={"on": False, "time_s": .0351, "feedback": .25, "mix": .4})
    kwargs.update(extra)
    return kwargs


class AlternateEqViewTests(unittest.TestCase):
    def test_a_vintage_body_is_listed_as_stored(self):
        view = io24_presets.alternate_eq_view({"eq": dict(VINTAGE)})
        self.assertEqual(view["model"], "vintage")
        self.assertTrue(view["on"])
        self.assertEqual(view["rows"], [
            ("Low shelf", "position 1 of 4 (35 Hz)", "+1.8 dB"),
            ("Low mid", "position 1 of 3 (360 Hz)", "-3.8 dB"),
            ("High mid", "position 2 of 3 (4800 Hz)", "+1.6 dB"),
            ("High shelf", "fixed frequency", "+1.0 dB"),
        ])
        self.assertEqual(view["eq"], VINTAGE)
        self.assertIsNot(view["eq"], VINTAGE)

    def test_a_passive_body_uses_the_recovered_switch_labels(self):
        view = io24_presets.alternate_eq_view({"eq": dict(PASSIVE)})
        self.assertEqual(view["model"], "passive")
        self.assertEqual(view["rows"], [
            ("Low boost", "position 4 of 4 (100 Hz)", "3.9 / 10"),
            ("Low attenuation", "position 4 of 4 (100 Hz)", "0.0 / 10"),
            ("High boost", "position 7 of 7 (16000 Hz)",
             "1.8 / 10; bandwidth 4.5 / 10"),
            ("High attenuation", "position 3 of 3 (20000 Hz)", "0.0 / 10"),
        ])

    def test_standard_and_absent_eq_have_no_alternate_view(self):
        self.assertEqual(io24_presets.eq_model(STANDARD), "standard")
        self.assertIsNone(io24_presets.alternate_eq_view({"eq": STANDARD}))
        self.assertIsNone(io24_presets.alternate_eq_view({}))
        self.assertIsNone(io24_presets.alternate_eq_view({"eq": {}}))

    def test_an_out_of_range_switch_is_rejected_not_guessed(self):
        with self.assertRaisesRegex(ValueError, "lowfreq must be in"):
            io24_presets.alternate_eq_view(
                {"eq": dict(VINTAGE, lowfreq=7)})

    def test_saving_carries_the_stored_vintage_eq_verbatim(self):
        kept = io24_presets.current_slot_record(
            COMPLETE_BASE, "MAIN", **_slot_kwargs(alternate_eq=dict(VINTAGE)))
        self.assertEqual(kept["eq"], VINTAGE)
        rebuilt = io24_presets.current_slot_record(
            COMPLETE_BASE, "MAIN", **_slot_kwargs())
        self.assertEqual(io24_presets.eq_model(rebuilt["eq"]), "standard")

    def test_a_standard_section_is_refused_as_alternate_eq(self):
        with self.assertRaises(ValueError):
            io24_presets.current_slot_record(
                COMPLETE_BASE, "MAIN",
                **_slot_kwargs(alternate_eq=dict(STANDARD)))


class _Widget:
    def __init__(self):
        self.sensitive, self.visible, self.text, self.draws = True, None, "", 0
        self.active = False
        self.value = 0.0
        self.selected = 0

    def set_sensitive(self, value):
        self.sensitive = bool(value)

    def set_visible(self, value):
        self.visible = bool(value)

    def set_text(self, text):
        self.text = text

    def set_active(self, value):
        self.active = bool(value)

    def get_active(self):
        return self.active

    def set_value(self, value):
        self.value = float(value)

    def get_value(self):
        return self.value

    def set_selected(self, value):
        self.selected = int(value)

    def get_selected(self):
        return self.selected

    def queue_draw(self):
        self.draws += 1


class _Value:
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def get_active(self):
        return bool(self.value)

    def get_selected(self):
        return int(self.value)


def _eq_widgets():
    W = {key: _Widget() for key in (
        "curve", "curve_row", "alternate_eq_rack", "alternate_eq_rack_row",
        "eq_on", "eq_model", "band_on", "shelf", "freq",
        "gain", "q", "eq_flat", "p_bboost", "p_batten", "p_bfreq",
        "p_mboost", "p_bbwidth", "p_mfreq", "p_hatten", "p_hsfreq",
        "v_lowgain", "v_lowfreq", "v_lowmidgain", "v_lowmidfreq",
        "v_himidgain", "v_himidfreq", "v_higain")}
    W["bands"] = [_Widget() for _ in range(4)]
    W["_standard_eq_rows"] = [_Widget() for _ in range(7)]
    W["_passive_eq_rows"] = [_Widget() for _ in range(8)]
    W["_vintage_eq_rows"] = [_Widget() for _ in range(7)]
    return W


class AlternateEqRackContractTests(unittest.TestCase):
    def test_calibration_layers_are_opt_in_and_invalid_values_fail_closed(self):
        with mock.patch.dict(os.environ, {
                "IO24_EQ_REFERENCE_CALIBRATION": "nodes"}):
            self.assertEqual(io24gtk.eq_reference_calibration_mode(), "nodes")
        with mock.patch.dict(os.environ, {
                "IO24_EQ_REFERENCE_CALIBRATION": "typo"}):
            self.assertEqual(io24gtk.eq_reference_calibration_mode(), "")

    def test_model_combo_is_state_only_because_context_menu_is_the_picker(self):
        source = inspect.getsource(io24gtk.Win._channel_column)
        self.assertIn('W["eq_model"] = Adw.ComboRow', source)
        self.assertNotIn('e.add(W["eq_model"])', source)

    def test_reference_geometry_drives_underlays_controls_and_hit_regions(self):
        passive = io24gtk.ALTERNATE_EQ_REFERENCE_ART["passive"]
        vintage = io24gtk.ALTERNATE_EQ_REFERENCE_ART["vintage"]

        # Passive runs y=123..605 in its reference; 454 px cut it off at 571.
        self.assertEqual(passive["rack_crop"], (8, 123, 2156, 482))
        self.assertEqual(vintage["rack_crop"], (8, 174, 2156, 377))
        self.assertEqual(passive["plot"], (663, 110, 591, 261))
        self.assertEqual(vintage["plot"], (858, 102, 557, 175))
        self.assertEqual(passive["controls"]["bfreq"], (360, 422, 58))
        self.assertEqual(passive["controls"]["hsfreq"], (1858, 422, 58))
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for art in (passive, vintage):
            for key in ("filename", "faceplate_filename",
                        "calibration_underlay_filename",
                        "calibration_nodes_filename"):
                self.assertTrue(os.path.isfile(
                    os.path.join(root, "docs", "design", art[key])),
                    art[key])

            # The developer underlay is an exact crop, while the production
            # faceplate is value-free and therefore intentionally differs.
            source = Image.open(os.path.join(
                root, "docs", "design", art["filename"])).convert("RGB")
            x, y, width, height = art["rack_crop"]
            source = source.crop((x, y, x + width, y + height))
            underlay = Image.open(os.path.join(
                root, "docs", "design",
                art["calibration_underlay_filename"])).convert("RGB")
            faceplate = Image.open(os.path.join(
                root, "docs", "design",
                art["faceplate_filename"])).convert("RGB")
            self.assertIsNone(ImageChops.difference(
                source, underlay).getbbox())
            self.assertIsNotNone(ImageChops.difference(
                source, faceplate).getbbox())

    def test_passive_selectors_and_their_values_fit_inside_the_plate(self):
        _x, _y, width, height = io24gtk.ALTERNATE_EQ_REFERENCE_ART[
            "passive"]["rack_crop"]
        layout = io24gtk.alternate_eq_reference_control_layout(
            "passive", width, height)
        specs = {spec["field"]: spec for spec in
                 io24gtk.ALTERNATE_EQ_RACK_SPECS["passive"]}
        for field, (cx, cy, radius) in layout.items():
            with self.subTest(field=field):
                body = radius * (.78 if specs[field].get("style") ==
                                 "selector" else .96)
                self.assertLessEqual(cy + body, height)
                for mx, my, _text in io24gtk.alternate_eq_mark_points(
                        specs[field], cx, cy, radius):
                    self.assertTrue(0 < mx < width and 0 < my < height)
        # Stepped selectors print beside and above the knob only.
        for field in ("bfreq", "hsfreq"):
            cx, cy, radius = layout[field]
            self.assertTrue(all(
                my <= cy + radius * .20 for _mx, my, _text in
                io24gtk.alternate_eq_mark_points(
                    specs[field], cx, cy, radius)))

    def test_high_row_printed_values_do_not_collide(self):
        width = 1350.0
        height = width / io24gtk.ALTERNATE_EQ_REFERENCE_GEOMETRY[
            "passive"]["aspect"]
        layout = io24gtk.alternate_eq_reference_control_layout(
            "passive", width, height)
        specs = {spec["field"]: spec for spec in
                 io24gtk.ALTERNATE_EQ_RACK_SPECS["passive"]}
        boxes = []
        for field in ("mboost", "bbwidth", "mfreq", "hatten"):
            cx, cy, radius = layout[field]
            size = max(5.6, min(9.5, radius * .20))
            for mx, my, text in io24gtk.alternate_eq_mark_points(
                    specs[field], cx, cy, radius):
                half_w = len(text) * size * .26 + 1.0
                half_h = size * .58
                boxes.append((field, text, mx - half_w, my - half_h,
                              mx + half_w, my + half_h))
        for index, first in enumerate(boxes):
            for second in boxes[index + 1:]:
                overlap = (first[2] < second[4] and second[2] < first[4]
                           and first[3] < second[5] and second[3] < first[5])
                self.assertFalse(overlap, (first[:2], second[:2]))

    def test_every_reference_control_has_its_own_source_knob(self):
        for model, specs in io24gtk.ALTERNATE_EQ_RACK_SPECS.items():
            with self.subTest(model=model):
                controls = io24gtk.ALTERNATE_EQ_REFERENCE_ART[model][
                    "controls"]
                self.assertEqual(
                    set(controls), {spec["field"] for spec in specs})
                for source_x, source_y, radius in controls.values():
                    self.assertGreater(source_x, 0)
                    self.assertGreater(source_y, 0)
                    self.assertGreater(radius, 40)

    def test_reference_hit_geometry_comes_from_the_same_knob_pixels(self):
        passive = io24gtk.alternate_eq_reference_control_layout(
            "passive", 2156, 482)
        vintage = io24gtk.alternate_eq_reference_control_layout(
            "vintage", 2156, 377)

        self.assertEqual(passive["bboost"], (243.0, 213.0, 66.0))
        self.assertEqual(passive["hsfreq"], (1858.0, 422.0, 58.0))
        self.assertEqual(vintage["lowgain"], (182.0, 186.0, 55.0))
        self.assertEqual(vintage["higain"], (1939.0, 186.0, 55.0))

    def test_passive_rack_exposes_every_exact_uc_control(self):
        specs = io24gtk.ALTERNATE_EQ_RACK_SPECS["passive"]
        self.assertEqual([spec["field"] for spec in specs], [
            "bboost", "batten", "bfreq", "mboost", "bbwidth", "mfreq",
            "hatten", "hsfreq",
        ])
        self.assertEqual(specs[2]["choices"],
                         ("20 Hz", "30 Hz", "60 Hz", "100 Hz"))
        self.assertEqual(specs[5]["choices"],
                         ("3 kHz", "4 kHz", "5 kHz", "8 kHz", "10 kHz",
                          "12 kHz", "16 kHz"))
        self.assertEqual(specs[7]["choices"],
                         ("5 kHz", "10 kHz", "20 kHz"))

    def test_vintage_rack_exposes_every_exact_uc_control(self):
        specs = io24gtk.ALTERNATE_EQ_RACK_SPECS["vintage"]
        self.assertEqual([spec["field"] for spec in specs], [
            "lowgain", "lowfreq", "lowmidgain", "lowmidfreq",
            "himidgain", "himidfreq", "higain",
        ])
        self.assertEqual(specs[1]["choices"],
                         ("35 Hz", "60 Hz", "110 Hz", "220 Hz"))
        self.assertEqual(specs[3]["choices"],
                         ("360 Hz", "700 Hz", "1.6 kHz"))
        self.assertEqual(specs[5]["choices"],
                         ("3.2 kHz", "4.8 kHz", "7.2 kHz"))

    def test_every_rack_parameter_has_a_distinct_visual_position(self):
        for model, specs in io24gtk.ALTERNATE_EQ_RACK_SPECS.items():
            with self.subTest(model=model):
                points = {(spec["x"], spec["y"]) for spec in specs}
                self.assertEqual(len(points), len(specs))
                for spec in specs:
                    lo = spec.get("lo", 0)
                    hi = spec.get("hi", len(spec.get("choices", ())) - 1)
                    self.assertEqual(
                        io24gtk.alternate_eq_control_fraction(spec, lo), 0.0)
                    self.assertEqual(
                        io24gtk.alternate_eq_control_fraction(spec, hi), 1.0)

    def test_each_faceplate_keeps_the_approved_reference_geometry(self):
        passive = io24gtk.ALTERNATE_EQ_REFERENCE_GEOMETRY["passive"]
        vintage = io24gtk.ALTERNATE_EQ_REFERENCE_GEOMETRY["vintage"]
        self.assertEqual(passive["aspect"], 2156 / 482)
        self.assertEqual(vintage["aspect"], 2156 / 377)
        self.assertEqual(passive["graph"], (
            663 / 2156, 110 / 482, 591 / 2156, 261 / 482))
        self.assertEqual(vintage["graph"], (
            858 / 2156, 102 / 377, 557 / 2156, 175 / 377))

        px, py, pw, ph = io24gtk.alternate_eq_rack_bounds(
            "passive", 950, 240)
        self.assertEqual((px, pw), (0.0, 950.0))
        self.assertAlmostEqual(ph, 950 * 482 / 2156)
        self.assertAlmostEqual(py, (240 - ph) / 2)

        # Runtime presentation is one common 2U bay. Vintage keeps its
        # measured source landmarks, but its rack occupies the same outer
        # rectangle as Passive instead of floating as a shorter strip.
        vintage_bounds = io24gtk.alternate_eq_rack_bounds(
            "vintage", 950, 240)
        self.assertEqual(vintage_bounds, (px, py, pw, ph))
        self.assertEqual(
            io24gtk.standard_eq_rack_bounds(950, 240),
            (px, py, pw, ph))

        self.assertEqual(
            io24gtk.alternate_eq_canvas_height("passive", 950),
            io24gtk.alternate_eq_canvas_height("vintage", 950))
        self.assertEqual(
            io24gtk.alternate_eq_canvas_height("passive", 950),
            math.ceil(950 * 482 / 2156 +
                      io24gtk.ALTERNATE_EQ_RACK_SHADOW_ROOM))

        self.assertEqual(
            tuple((spec["x"], spec["y"])
                  for spec in io24gtk.ALTERNATE_EQ_RACK_SPECS["passive"]),
            ((243 / 2156, 213 / 482), (467 / 2156, 213 / 482),
             (360 / 2156, 422 / 482), (1421 / 2156, 213 / 482),
             (1607 / 2156, 213 / 482), (1785 / 2156, 213 / 482),
             (1964 / 2156, 213 / 482), (1858 / 2156, 422 / 482)),
        )
        self.assertEqual(
            tuple((spec["x"], spec["y"])
                  for spec in io24gtk.ALTERNATE_EQ_RACK_SPECS["vintage"]),
            ((182 / 2156, 186 / 377), (342 / 2156, 188 / 377),
             (514 / 2156, 186 / 377), (665 / 2156, 186 / 377),
             (1577 / 2156, 186 / 377), (1737 / 2156, 187 / 377),
             (1939 / 2156, 186 / 377)),
        )

    def test_control_labels_follow_each_reference_faceplate(self):
        self.assertAlmostEqual(
            io24gtk.alternate_eq_control_label_y("passive", 100, 20), 59)
        self.assertAlmostEqual(
            io24gtk.alternate_eq_control_label_y("vintage", 100, 20), 137.6)
        self.assertAlmostEqual(
            io24gtk.alternate_eq_control_value_y("passive", 100, 20), 130)
        self.assertAlmostEqual(
            io24gtk.alternate_eq_control_value_y("vintage", 100, 20), 149)

    def test_rack_fraction_snaps_selector_fields_and_scales_amounts(self):
        passive = {s["field"]: s for s in
                   io24gtk.ALTERNATE_EQ_RACK_SPECS["passive"]}
        self.assertEqual(io24gtk.alternate_eq_control_value(
            passive["bfreq"], 0.49), 1)
        self.assertEqual(io24gtk.alternate_eq_control_value(
            passive["bfreq"], 0.51), 2)
        self.assertAlmostEqual(io24gtk.alternate_eq_control_value(
            passive["bboost"], 0.55), 5.5)

    def test_faceplate_scale_marks_use_exact_decoded_ranges(self):
        passive = {s["field"]: s for s in
                   io24gtk.ALTERNATE_EQ_RACK_SPECS["passive"]}
        vintage = {s["field"]: s for s in
                   io24gtk.ALTERNATE_EQ_RACK_SPECS["vintage"]}
        self.assertEqual(io24gtk.alternate_eq_scale_marks(
            passive["bboost"]), (
                (0.0, "0"), (0.2, "2"), (0.4, "4"),
                (0.6, "6"), (0.8, "8"), (1.0, "10")))
        self.assertEqual(io24gtk.alternate_eq_scale_marks(
            vintage["lowgain"]), (
                (0.0, "-16"), (0.25, "-8"), (0.5, "0"),
                (0.75, "+8"), (1.0, "+16")))
        self.assertEqual(io24gtk.alternate_eq_scale_marks(
            passive["bfreq"]), (
                (0.0, "20"), (1 / 3, "30"), (2 / 3, "60"),
                (1.0, "100")))

    def test_each_reference_keeps_its_original_graph_scale(self):
        self.assertEqual(io24gtk.alternate_eq_graph_levels("passive"),
                         (-18, -12, -6, 0, 6, 12, 18))
        self.assertEqual(io24gtk.alternate_eq_graph_levels("vintage"),
                         (-12, -6, 0, 6, 12))

    def test_vintage_trace_uses_its_twelve_db_faceplate_scale(self):
        window = _window()
        window.eq_enabled = lambda _channel: True
        window.response_for = lambda *_args, **_kwargs: 12.0

        points = io24gtk.Win.curve_points(
            window, 100, 120, 1, db_range=12.0)

        self.assertTrue(points)
        self.assertTrue(all(y == 1 for _x, y in points))

    def test_knob_drag_has_a_smooth_full_height_travel(self):
        self.assertAlmostEqual(
            io24gtk.alternate_eq_drag_fraction(.5, -60.0), .75)
        self.assertEqual(
            io24gtk.alternate_eq_drag_fraction(.5, 240.0), 0.0)

        passive = {spec["field"]: spec for spec in
                   io24gtk.ALTERNATE_EQ_RACK_SPECS["passive"]}
        self.assertEqual(io24gtk.alternate_eq_drag_travel(
            passive["bboost"]), 240.0)
        self.assertEqual(io24gtk.alternate_eq_drag_travel(
            passive["bfreq"]), 165.0)
        self.assertEqual(io24gtk.alternate_eq_drag_travel(
            passive["hsfreq"]), 110.0)

    def test_knob_motion_follows_each_painted_control_arc(self):
        passive = {spec["field"]: spec for spec in
                   io24gtk.ALTERNATE_EQ_RACK_SPECS["passive"]}
        vintage = {spec["field"]: spec for spec in
                   io24gtk.ALTERNATE_EQ_RACK_SPECS["vintage"]}
        self.assertAlmostEqual(
            io24gtk.alternate_eq_knob_angle(
                passive["bboost"], 0.0), math.radians(-225))
        self.assertAlmostEqual(
            io24gtk.alternate_eq_knob_angle(
                passive["bboost"], 1.0), math.radians(45))
        self.assertAlmostEqual(
            io24gtk.alternate_eq_knob_angle(
                passive["bfreq"], 0.0), math.radians(-185))
        self.assertAlmostEqual(
            io24gtk.alternate_eq_knob_angle(
                passive["bfreq"], 1.0), math.radians(5))
        self.assertAlmostEqual(
            io24gtk.alternate_eq_knob_angle(
                vintage["himidfreq"], 0.0), math.radians(-225))
        self.assertAlmostEqual(
            io24gtk.alternate_eq_knob_angle(
                vintage["himidfreq"], 1.0), math.radians(45))

    def test_click_selection_does_not_claim_the_drag_sequence(self):
        states = []
        rack = SimpleNamespace(
            _power_at=lambda _x, _y: False,
            _knob_at=lambda _x, _y: "bboost",
            _select=lambda field: field == "bboost",
            _view=lambda: None,
        )
        gesture = SimpleNamespace(set_state=states.append)
        io24gtk.AlternateEqRack._clicked(rack, gesture, 1, 10, 10)
        self.assertEqual(states, [])

    def test_rack_lamp_is_the_alternate_eq_power_control(self):
        changes = []
        rack = SimpleNamespace(
            _power_at=lambda _x, _y: True,
            _knob_at=lambda _x, _y: None,
            _select=lambda _field: False,
            selected_field=None,
            POWER_FIELD=io24gtk.AlternateEqRack.POWER_FIELD,
            channel=1,
            win=SimpleNamespace(
                eq_enabled=lambda _channel: False,
                _set_eq_enabled=lambda channel, on:
                changes.append((channel, on))),
            grab_focus=lambda: None,
            queue_draw=lambda: None,
        )

        io24gtk.AlternateEqRack._clicked(rack, None, 1, 10, 10)

        self.assertEqual(changes, [(1, True)])
        self.assertEqual(rack.selected_field,
                         io24gtk.AlternateEqRack.POWER_FIELD)

    def test_alternate_rack_wheel_requires_a_hovered_knob(self):
        selections = []
        nudges = []
        rack = SimpleNamespace(
            hover_field=None,
            _select=selections.append,
            _nudge=lambda direction: nudges.append(direction) or True,
        )

        self.assertFalse(io24gtk.AlternateEqRack._scroll(
            rack, None, 0.0, 1.0))
        self.assertEqual((selections, nudges), ([], []))

        rack.hover_field = "bboost"
        self.assertTrue(io24gtk.AlternateEqRack._scroll(
            rack, None, 0.0, -1.0))
        self.assertEqual(selections, ["bboost"])
        self.assertEqual(nudges, [1])

    def test_standard_rack_wheel_requires_a_hovered_node_or_encoder(self):
        band = {"shape": "peaking", "freq": 1000.0,
                "gain": 0.0, "q": 0.7}
        curve = SimpleNamespace(
            win=SimpleNamespace(
                _alt_eq=lambda _channel: None,
                invalidate_curve=lambda: None,
                _push_band=lambda _channel: None),
            channel=1,
            hover=None,
            cur_band=0,
            bands=[band],
            wid=lambda _key: SimpleNamespace(set_value=lambda _value: None),
            queue_draw=lambda: None,
        )

        self.assertFalse(io24gtk.EQCurve._scroll(
            curve, None, 0.0, -1.0))
        self.assertEqual(band["q"], 0.7)

        curve.hover = 0
        self.assertTrue(io24gtk.EQCurve._scroll(
            curve, None, 0.0, -1.0))
        self.assertGreater(band["q"], 0.7)

    def test_standard_wheel_selects_the_band_whose_q_it_writes(self):
        calls = []
        bands = [{"shape": "peaking", "freq": 100.0, "gain": 0.0, "q": .7},
                 {"shape": "peaking", "freq": 1000.0, "gain": 0.0, "q": .7}]
        curve = SimpleNamespace(
            channel=1, hover=1, cur_band=0, bands=bands,
            queue_draw=lambda: None,
            wid=lambda key: SimpleNamespace(
                set_value=lambda value: calls.append(("row", key, value))))
        curve.win = SimpleNamespace(
            _alt_eq=lambda _channel: None,
            _adopt_mute=False,
            invalidate_curve=lambda: None,
            select_band=lambda index, channel: (
                calls.append(("select", index, channel)),
                setattr(curve, "cur_band", index)),
            _push_band=lambda channel: calls.append(
                ("push", channel, curve.cur_band)))

        self.assertTrue(io24gtk.EQCurve._scroll(curve, None, 0.0, -1.0))

        self.assertEqual(calls[0], ("select", 1, 1))
        self.assertEqual(calls[1][:2], ("row", "q"))
        self.assertAlmostEqual(calls[1][2], .7 * 1.08)
        # The write goes out for the band now shown in the rows.
        self.assertEqual(calls[2], ("push", 1, 1))
        self.assertEqual(curve.cur_band, 1)
        self.assertEqual(bands[0]["q"], .7)

    def test_standard_node_pinned_to_the_screen_edge_can_be_grabbed(self):
        band = {"shape": "peaking", "freq": 1000.0, "gain": 15.0, "q": 1.0}
        curve = SimpleNamespace(
            channel=1, bands=[band],
            get_width=lambda: 1200, get_height=lambda: 240,
            win=SimpleNamespace(
                _fs=48000.0,
                # A combined boost above the screen's +18 dB range.
                response_for=lambda *_args, **_kwargs: 30.0))
        curve._x = lambda f, w: io24gtk.EQCurve._x(curve, f, w)
        curve._node_y = lambda b, gy, gh: io24gtk.EQCurve._node_y(
            curve, b, gy, gh)
        curve._graph_bounds = lambda w=None, h=None: \
            io24gtk.EQCurve._graph_bounds(curve, w, h)
        curve._knob_at = lambda _x, _y, _w=None, _h=None: None
        curve._q_knob_at = lambda _x, _y, _w=None, _h=None: None
        gx, gy, gw, _gh = curve._graph_bounds()
        drawn_x = gx + curve._x(band["freq"], gw)

        self.assertEqual(
            io24gtk.EQCurve._hit_band(curve, drawn_x, gy + 7), 0)

    def test_plain_standard_rack_click_does_not_enable_or_write_a_band(self):
        calls = []
        band = {"shape": "off", "on": False, "mode": "peaking",
                "freq": 1000.0, "gain": 0.0, "q": 0.7}
        host = SimpleNamespace(
            _alt_eq=lambda _channel: None,
            select_band=lambda index, channel: calls.append(
                ("select", index, channel)),
            eq_enabled=lambda _channel: False,
            _set_eq_enabled=lambda channel, on: calls.append(
                ("power", channel, on)),
            _standard_band_mode=lambda _channel, _index: "peaking",
            _adopt_mute=False,
        )
        curve = SimpleNamespace(
            win=host,
            channel=1,
            drag_band=None,
            bands=[band],
            _hit_band=lambda _x, _y: 0,
            _q_knob_at=lambda _x, _y: None,
            _knob_at=lambda _x, _y: None,
            _band_at=lambda _x, _y: 0,
            _power_at=lambda _x, _y: False,
            _graph_bounds=lambda: (0.0, 0.0, 100.0, 50.0),
            wid=lambda _key: SimpleNamespace(set_active=lambda _value: None),
        )

        io24gtk.EQCurve._drag_begin(curve, None, 30.0, 30.0)

        self.assertEqual(calls, [("select", 0, 1)])
        self.assertEqual((band["shape"], band["on"]), ("off", False))

    def test_standard_side_knob_drag_changes_gain_without_frequency(self):
        band = {"shape": "peaking", "on": True, "mode": "peaking",
                "freq": 2400.0, "gain": 4.5, "q": 1.2}
        curve = SimpleNamespace(
            win=SimpleNamespace(
                _alt_eq=lambda _channel: None,
                select_band=lambda _index, _channel: None,
                eq_enabled=lambda _channel: True),
            channel=1,
            bands=[band],
            drag_band=None,
            _power_at=lambda _x, _y: False,
            _q_knob_at=lambda _x, _y: None,
            _knob_at=lambda _x, _y: 0,
            _hit_band=lambda _x, _y: 0,
            _graph_bounds=lambda: (400.0, 80.0, 500.0, 180.0),
        )

        io24gtk.EQCurve._drag_begin(curve, None, 150.0, 170.0)

        self.assertTrue(curve._drag_encoder)
        self.assertEqual(curve._drag_control, "gain")
        self.assertEqual(curve.drag_band, 0)
        self.assertEqual(curve._start,
                         (150.0, 170.0, 2400.0, 4.5, 1.2))

    def test_standard_q_knob_drag_is_independent_of_gain_and_frequency(self):
        band = {"shape": "peaking", "on": True, "mode": "peaking",
                "freq": 2400.0, "gain": 4.5, "q": 1.2}
        curve = SimpleNamespace(
            win=SimpleNamespace(
                _alt_eq=lambda _channel: None,
                select_band=lambda _index, _channel: None,
                eq_enabled=lambda _channel: True),
            channel=1,
            bands=[band],
            drag_band=None,
            _power_at=lambda _x, _y: False,
            _q_knob_at=lambda _x, _y: 0,
            _knob_at=lambda _x, _y: None,
            _hit_band=lambda _x, _y: 0,
            _graph_bounds=lambda: (400.0, 80.0, 500.0, 180.0),
        )

        io24gtk.EQCurve._drag_begin(curve, None, 150.0, 360.0)

        self.assertFalse(curve._drag_encoder)
        self.assertEqual(curve._drag_control, "q")
        self.assertEqual(curve.drag_band, 0)
        self.assertEqual(curve._start,
                         (150.0, 360.0, 2400.0, 4.5, 1.2))
        changed = io24gtk.standard_eq_q_drag_value(1.2, -90.0)
        self.assertGreater(changed, 1.2)
        self.assertEqual((band["freq"], band["gain"]), (2400.0, 4.5))

    def test_standard_q_drag_writes_only_q_through_the_existing_band_path(self):
        band = {"shape": "peaking", "on": True, "mode": "peaking",
                "freq": 2400.0, "gain": 4.5, "q": 1.2}
        rows = {key: _Widget() for key in ("freq", "gain", "q")}
        pushes = []
        curve = SimpleNamespace(
            channel=1,
            bands=[band],
            drag_band=0,
            _drag_control="q",
            _start=(150.0, 360.0, 2400.0, 4.5, 1.2),
            _enable_dragged_band=lambda: None,
            _graph_bounds=lambda: (400.0, 80.0, 500.0, 180.0),
            _drag_push=lambda: pushes.append("write"),
            wid=rows.__getitem__,
            queue_draw=lambda: None,
        )
        curve.win = SimpleNamespace(
            invalidate_curve=lambda: None,
            _adopt_mute=False,
            racks={},
        )

        io24gtk.EQCurve._drag_update(curve, None, 80.0, -90.0)

        self.assertEqual((band["freq"], band["gain"]), (2400.0, 4.5))
        self.assertGreater(band["q"], 1.2)
        self.assertAlmostEqual(rows["q"].value, band["q"])
        self.assertEqual(pushes, ["write"])

    def test_standard_rack_has_its_own_power_control(self):
        layout = io24gtk.standard_eq_rack_layout(1200, 240)
        self.assertIn("power", layout)
        px, py, radius = layout["power"]
        self.assertGreater(radius, 8)

        changes = []
        curve = SimpleNamespace(
            win=SimpleNamespace(
                _alt_eq=lambda _channel: None,
                eq_enabled=lambda _channel: False,
                _set_eq_enabled=lambda channel, on:
                changes.append((channel, on))),
            channel=1,
            _power_at=lambda x, y: math.hypot(x - px, y - py) <= radius,
            _hit_band=lambda _x, _y: None,
            queue_draw=lambda: None,
        )

        io24gtk.EQCurve._clicked(curve, None, 1, px, py)
        self.assertEqual(changes, [(1, True)])

    def test_standard_rack_uses_the_measured_reference_geometry(self):
        art = io24gtk.STANDARD_EQ_REFERENCE_ART
        self.assertEqual(art["rack_crop"], (8, 121, 2156, 482))
        self.assertEqual(art["screen"], (612, 65, 932, 384))
        self.assertEqual(art["glass"], (638, 91, 880, 332))
        self.assertEqual(art["plot"], (654, 103, 848, 308))

        layout = io24gtk.standard_eq_rack_layout(2156, 482)
        self.assertEqual(layout["panel"], (0.0, 0.0, 2156.0, 482.0))
        self.assertEqual(layout["display"], (638.0, 91.0, 880.0, 332.0))
        self.assertEqual(layout["graph"], (654.0, 103.0, 848.0, 308.0))
        self.assertEqual(layout["encoders"], (
            (224.0, 229.0), (474.0, 229.0),
            (1682.0, 229.0), (1932.0, 229.0)))
        self.assertEqual(layout["q_encoders"], (
            (224.0, 376.0), (474.0, 376.0),
            (1682.0, 376.0), (1932.0, 376.0)))
        self.assertEqual(layout["q_radius"], 29.0)
        self.assertEqual(len(layout["band_power"]), 4)
        self.assertEqual(len(layout["band_mode"]), 4)
        self.assertEqual(layout["flatten"], (1450.0, 72.0, 58.0, 24.0))
        self.assertEqual(layout["power"], (2032.0, 441.0, 20.0))
        self.assertTrue(os.path.isfile(io24gtk.standard_eq_faceplate_path()))

    def test_standard_q_knobs_cover_the_exact_existing_range_logarithmically(self):
        low, high = io24_presets.STANDARD_EQ_Q_RANGE
        self.assertEqual(io24gtk.standard_eq_q_fraction(low), 0.0)
        self.assertEqual(io24gtk.standard_eq_q_fraction(high), 1.0)
        self.assertAlmostEqual(
            io24gtk.standard_eq_q_value(
                io24gtk.standard_eq_q_fraction(0.6)),
            0.6, places=6)
        self.assertAlmostEqual(
            io24gtk.standard_eq_q_angle(low), math.radians(-225.0))
        self.assertAlmostEqual(
            io24gtk.standard_eq_q_angle(high), math.radians(45.0))

    def test_standard_q_knob_has_its_own_hit_target(self):
        layout = io24gtk.standard_eq_rack_layout(2156, 482)
        qx, qy = layout["q_encoders"][2]
        curve = SimpleNamespace(
            get_width=lambda: 2156,
            get_height=lambda: 482,
        )
        self.assertEqual(
            io24gtk.EQCurve._q_knob_at(curve, qx, qy), 2)
        self.assertIsNone(
            io24gtk.EQCurve._q_knob_at(curve, 1078, 241))

    def test_standard_gain_pointer_uses_the_exact_existing_range(self):
        self.assertAlmostEqual(
            io24gtk.standard_eq_knob_angle(-15.0), math.radians(-225.0))
        self.assertAlmostEqual(
            io24gtk.standard_eq_knob_angle(0.0), math.radians(-90.0))
        self.assertAlmostEqual(
            io24gtk.standard_eq_knob_angle(15.0), math.radians(45.0))

    def test_miniature_curve_offsets_the_same_live_response(self):
        window = SimpleNamespace(
            curve_points=lambda width, height, channel: (
                [(0, height / 2), (width, height / 4)]
                if channel == 1 else []))
        self.assertEqual(
            io24gtk.eq_miniature_points(window, 1, 10, 20, 80, 40),
            [(10, 40.0), (90, 30.0)],
        )


def _window():
    window = io24gtk.Win.__new__(io24gtk.Win)
    window._adopt_mute = False
    window.messages = []
    window.say = window.messages.append
    window.link_both = False
    window._fs = 48000.0
    window.eq_on_by_ch = {1: False, 2: False}
    window.bands_by_ch = {
        1: io24_presets.default_standard_eq_bands(),
        2: io24_presets.default_standard_eq_bands(),
    }
    window.alt_eq_by_ch = {1: None, 2: None}
    window._curves = {}
    window.racks = {}
    window.w = {}
    window.submitted = []
    window.ctl = SimpleNamespace(submit=window.submitted.append)
    return window


class LatestControlSubmissionTests(unittest.TestCase):
    def test_repeated_parameter_writes_keep_only_the_latest_value(self):
        ctl = io24gtk.Ctl.__new__(io24gtk.Ctl)
        ctl.q = queue.Queue()
        ctl._latest = {}
        ctl._latest_lock = threading.Lock()
        seen = []

        ctl.submit_latest(("alternate-eq", 1),
                          lambda _dev: seen.append("old"))
        ctl.submit_latest(("alternate-eq", 1),
                          lambda _dev: seen.append("new"))

        self.assertEqual(ctl.q.qsize(), 1)
        callback = ctl._take_submission(ctl.q.get_nowait())
        callback(None)
        self.assertEqual(seen, ["new"])


class RecalledVintageBodyHostTests(unittest.TestCase):
    @unittest.skipUnless(
        EXACT_ALT_EQ_AVAILABLE,
        "requires a local UC 4.7.2 dspusbdevice.dll",
    )
    def test_a_recall_shows_the_rest_and_lists_the_eq(self):
        record = {"preset_name": "MAIN", "eq": dict(VINTAGE),
                  "voicefx": {"on": 0}}
        window = _window()
        window.PR = io24_presets
        window._host_slot_entry = lambda slot: {"record": record}
        adopted = []
        window._adopt_preset_record = \
            lambda rec, chans, fx_channel=None: (
                adopted.append((rec, chans, fx_channel)),
                window._show_alternate_eq(
                    chans[0], io24_presets.alternate_eq_view(rec)),
                True)[-1]
        self.assertTrue(window._adopt_recalled_slot(1, 0))
        self.assertEqual(len(adopted), 1)
        shown, chans, fx_channel = adopted[0]
        self.assertEqual(shown["eq"], VINTAGE)
        self.assertEqual((chans, fx_channel), ((1,), 1))
        self.assertEqual(window._alt_eq(1)["eq"], VINTAGE)
        self.assertIsNone(window._alt_eq(2))
        self.assertEqual(window.messages[-1], "Input 1 · Vintage EQ")
        self.assertEqual(record["eq"], VINTAGE)      # the entry is untouched

    @unittest.skipUnless(
        EXACT_ALT_EQ_AVAILABLE,
        "requires a local UC 4.7.2 dspusbdevice.dll",
    )
    def test_vintage_controls_are_editable_and_send_the_exact_model(self):
        window = _window()
        window.w = {1: _eq_widgets()}
        view = io24_presets.alternate_eq_view({"eq": dict(VINTAGE)})
        window._show_alternate_eq(1, view)
        W = window.w[1]
        self.assertEqual(W["eq_model"].selected, 2)
        self.assertFalse(any(row.visible for row in W["_standard_eq_rows"]))
        self.assertFalse(any(row.visible for row in W["_vintage_eq_rows"]))
        self.assertFalse(any(row.visible for row in W["_passive_eq_rows"]))
        self.assertFalse(W["curve_row"].visible)
        self.assertTrue(W["alternate_eq_rack_row"].visible)
        self.assertFalse(W["eq_on"].visible)
        self.assertTrue(W["eq_on"].active)
        self.assertEqual(W["v_lowfreq"].selected, 0)
        self.assertAlmostEqual(W["v_lowgain"].value, 1.76)
        self.assertIsNone(window._alt_eq(1)["sections"])
        self.assertNotEqual(window.response_for(1, 35.0), 0.0)

        window._alternate_eq_set(1, "higain", 4.0)
        self.assertEqual(len(window.submitted), 1)

        class Device:
            calls = []

            def set_alternate_eq(self, channel, eq, fs):
                self.calls.append((channel, eq, fs))

        device = Device()
        window.submitted.pop()(device)
        self.assertEqual(device.calls[0][0], 1)
        self.assertEqual(device.calls[0][1]["higain"], 4.0)
        self.assertEqual(device.calls[0][2], 48000.0)

    @unittest.skipUnless(
        EXACT_ALT_EQ_AVAILABLE,
        "requires a local UC 4.7.2 dspusbdevice.dll",
    )
    def test_alternate_edit_redraws_the_faceplate_curve_and_chain_tile(self):
        window = _window()
        window.w = {1: _eq_widgets()}
        window.racks = {1: _Widget()}
        window._show_alternate_eq(
            1, io24_presets.alternate_eq_view({"eq": dict(PASSIVE)}))
        window.racks[1].draws = 0
        before = window.curve_points(320, 120, 1)

        window._alternate_eq_set(1, "bboost", 8.5)

        after = window.curve_points(320, 120, 1)
        self.assertNotEqual(before, after)
        self.assertEqual(window.racks[1].draws, 1)

    def test_alternate_edit_never_runs_the_uc_designer_on_the_ui_thread(self):
        window = _window()
        window.w = {1: _eq_widgets()}
        view = io24_presets.alternate_eq_view({"eq": dict(PASSIVE)})

        with mock.patch.object(
                io24_alt_eq, "design_live_sections",
                side_effect=AssertionError("designer ran on UI thread")) as design:
            window._show_alternate_eq(1, view)
            before = window.curve_points(320, 120, 1)
            window._alternate_eq_set(1, "bboost", 8.5)
            after = window.curve_points(320, 120, 1)

        self.assertEqual(design.call_count, 0)
        self.assertNotEqual(before, after)
        self.assertEqual(len(window.submitted), 1)

    @unittest.skipUnless(
        EXACT_ALT_EQ_AVAILABLE,
        "requires a local UC 4.7.2 dspusbdevice.dll",
    )
    def test_direct_model_choice_uses_the_same_application_path_as_the_row(self):
        window = _window()
        window.w = {1: _eq_widgets()}

        window.select_eq_model(1, "passive")
        self.assertEqual(window._eq_model_name(1), "passive")
        self.assertEqual(window.w[1]["eq_model"].selected, 1)

        window.select_eq_model(1, "standard")
        self.assertEqual(window._eq_model_name(1), "standard")
        self.assertEqual(window.w[1]["eq_model"].selected, 0)

    def test_reselecting_a_model_is_a_noop_and_each_model_keeps_its_values(self):
        window = _window()
        window.w = {1: _eq_widgets()}

        window.select_eq_model(1, "passive")
        window._alternate_eq_set(1, "bboost", 7.3)
        writes_after_edit = len(window.submitted)

        window.select_eq_model(1, "passive")
        self.assertEqual(window._alt_eq(1)["eq"]["bboost"], 7.3)
        self.assertEqual(len(window.submitted), writes_after_edit)

        window.select_eq_model(1, "vintage")
        window._alternate_eq_set(1, "lowgain", -5.5)
        window.select_eq_model(1, "passive")
        self.assertEqual(window._alt_eq(1)["eq"]["bboost"], 7.3)
        window.select_eq_model(1, "vintage")
        self.assertEqual(window._alt_eq(1)["eq"]["lowgain"], -5.5)

    def test_alternate_write_failure_is_kept_in_the_view_and_shown(self):
        window = _window()
        window.w = {1: _eq_widgets()}
        window._show_alternate_eq(
            1, io24_presets.alternate_eq_view({"eq": dict(PASSIVE)}))
        window._eq_write_generation = {1: 4, 2: 0}

        with mock.patch.object(
                io24gtk.GLib, "idle_add",
                side_effect=lambda callback, *args: callback(*args)):
            callback = window._alternate_eq_write_callback(
                1, dict(PASSIVE), 48000.0, 4)
            with self.assertRaisesRegex(RuntimeError, "designer unavailable"):
                callback(SimpleNamespace(
                    set_alternate_eq=lambda *_args, **_kwargs:
                    (_ for _ in ()).throw(RuntimeError(
                        "designer unavailable"))))

        self.assertIn("designer unavailable", window._alt_eq(1)["error"])
        self.assertIn("could not be applied", window.messages[-1])

    def test_stale_alternate_write_completion_cannot_replace_newer_state(self):
        window = _window()
        window.w = {1: _eq_widgets()}
        window._show_alternate_eq(
            1, io24_presets.alternate_eq_view({"eq": dict(PASSIVE)}))
        window._eq_write_generation = {1: 8, 2: 0}
        old_sections = (("biquad", 1, (1.0, 0.0, 0.0, 0.0, 0.0)),)

        self.assertFalse(window._alternate_eq_write_finished(
            1, "passive", 7, old_sections, None))
        self.assertIsNone(window._alt_eq(1)["sections"])

    def test_exact_sections_replace_the_preview_after_a_successful_write(self):
        window = _window()
        window.w = {1: _eq_widgets()}
        window._show_alternate_eq(
            1, io24_presets.alternate_eq_view({"eq": dict(PASSIVE)}))
        window._eq_write_generation = {1: 2, 2: 0}
        sections = (("biquad", 1, (1.0, 0.0, 0.0, 0.0, 0.0)),)

        window._alternate_eq_write_finished(
            1, "passive", 2, sections, None)

        self.assertEqual(window._alt_eq(1)["sections"], sections)
        with mock.patch.object(io24_alt_eq, "response_db", return_value=4.25) \
                as exact:
            self.assertEqual(window.response_for(1, 1000.0), 4.25)
        exact.assert_called_once_with(sections, 1000.0, 48000.0)

    def test_standard_band_edit_redraws_its_chain_tile(self):
        window = _window()
        window.w = {1: _eq_widgets()}
        window.cur_band_by_ch = {1: 0}
        window.racks = {1: _Widget()}

        window._push_band(1)

        self.assertEqual(window.racks[1].draws, 1)

    def test_clearing_a_channel_that_was_never_marked_touches_nothing(self):
        window = _window()
        window.w = {1: _eq_widgets()}
        window._show_alternate_eq(1, None)
        self.assertEqual(window.w[1]["curve"].draws, 1)
        self.assertFalse(any(row.visible
                             for row in window.w[1]["_standard_eq_rows"]))
        self.assertFalse(window.w[1]["eq_on"].visible)
        self.assertTrue(window.w[1]["curve_row"].visible)
        self.assertFalse(window.w[1]["alternate_eq_rack_row"].visible)

    def test_linked_edits_skip_a_held_channel_and_say_so_once(self):
        window = _window()
        window.link_both = True
        window._show_alternate_eq(
            2, io24_presets.alternate_eq_view({"eq": dict(VINTAGE)}))
        self.assertEqual(window._eq_write_targets(1), (1,))
        self.assertEqual(window._eq_write_targets(1), (1,))
        self.assertEqual(len(window.messages), 1)
        self.assertIn("skipped Channel 2 because its EQ model differs",
                      window.messages[0])

    def test_saving_passes_the_stored_eq_through(self):
        window = _window()
        window.fx_target = _Value(0)
        window.w = {1: {"gth": _Value(-48.7), "grange": _Value(-60.0),
                        "gatk": _Value(.005), "grel": _Value(.3),
                        "gkey": _Value(325.0), "gklisten": _Value(False),
                        "gexp": _Value(True), "lth": _Value(-.8)}}
        window.dyn_by_ch = {1: {"gate": True, "comp": True, "lim": True}}
        window._compressor_kwargs = lambda target: (2, {})
        window.fx_model = _Value(0)
        window._fx_live_params = lambda: {}
        window.fx_arm = _Value(False)
        window.bands_by_ch = {1: [dict(band) for band in FLAT]}
        window.hpf_by_ch = {1: 24.0}
        window.order_by_ch = {1: False}
        seen = []
        window.PR = SimpleNamespace(
            load=lambda: {"base": {}},
            current_slot_record=lambda base, name, **kw: seen.append(kw) or kw)

        window._current_slot_record("base", 1, "MAIN")
        self.assertIsNone(seen[-1]["alternate_eq"])
        window.alt_eq_by_ch = {
            1: io24_presets.alternate_eq_view({"eq": dict(VINTAGE)}), 2: None}
        window._current_slot_record("base", 1, "MAIN")
        self.assertEqual(seen[-1]["alternate_eq"], VINTAGE)

    def test_snapshot_keeps_dormant_standard_settings_behind_alternate_eq(self):
        window = _window()
        window.alt_eq_by_ch = {
            1: io24_presets.alternate_eq_view({"eq": dict(VINTAGE)}),
            2: None,
        }
        window.bands_by_ch[1][0].update(
            shape="lowshelf", on=True, gain=3.5, freq=90.0)
        window.eq_on_by_ch[1] = True

        state = window._standard_eq_state()

        self.assertIn("1", state["channels"])
        self.assertEqual(state["channels"]["1"]["bands"][0]["gain"], 3.5)

    def test_host_snapshot_round_trips_two_independent_alternate_models(self):
        window = _window()
        window.w = {1: _eq_widgets(), 2: _eq_widgets()}
        window._show_alternate_eq(
            1, io24_presets.alternate_eq_view({"eq": dict(PASSIVE)}))
        window._show_alternate_eq(
            2, io24_presets.alternate_eq_view({"eq": dict(VINTAGE)}))

        state = window._alternate_eq_state()
        normalized, migrations = io24._normalise_host_features(
            {"alternate_eq": state})
        self.assertEqual(migrations, [])
        self.assertEqual(normalized["alternate_eq"], state)

        restored = _window()
        restored.w = {1: _eq_widgets(), 2: _eq_widgets()}
        message = restored._adopt_alternate_eq_state(state)
        self.assertEqual(restored._eq_model_name(1), "passive")
        self.assertEqual(restored._eq_model_name(2), "vintage")
        self.assertEqual(restored._alt_eq(1)["eq"], PASSIVE)
        self.assertEqual(restored._alt_eq(2)["eq"], VINTAGE)
        self.assertEqual(restored.submitted, [])
        self.assertIn("Input 1 and 2", message)

    @unittest.skipUnless(
        EXACT_ALT_EQ_AVAILABLE,
        "requires a local UC 4.7.2 dspusbdevice.dll",
    )
    def test_power_changes_only_the_selected_model_on_one_input(self):
        window = _window()
        window.w = {1: _eq_widgets(), 2: _eq_widgets()}
        passive_off = dict(PASSIVE, eqallon=0)
        window._show_alternate_eq(
            1, io24_presets.alternate_eq_view({"eq": passive_off}))

        window._set_eq_enabled(1, True)
        self.assertTrue(window.eq_enabled(1))
        self.assertFalse(window.eq_enabled(2))
        self.assertEqual(window._alt_eq(1)["eq"]["eqallon"], 1)
        self.assertEqual(len(window.submitted), 1)


if __name__ == "__main__":
    unittest.main()
