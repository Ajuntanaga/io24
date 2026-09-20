#!/usr/bin/env python3
"""Hardware-free contracts for how wide the Host's pages are.

The user asked (2026-09-12) that the window be used instead of a narrow
centre column: at the size this Host opens at, roughly a third of the width
was empty on either side. Adw.PreferencesPage clamps its own content and
exposes no width API, so the Host walks a built page and widens every clamp
in it.

Nothing here opens a display, USB or audio.
"""

from pathlib import Path
import unittest

import io24gtk

ROOT = Path(__file__).resolve().parents[1]


class _Plain:
    """A widget with children and no width API — never touched."""

    def __init__(self, *children):
        self.sibling = None
        kids = list(children)
        for first, second in zip(kids, kids[1:]):
            first.sibling = second
        self.first = kids[0] if kids else None

    def get_first_child(self):
        return self.first

    def get_next_sibling(self):
        return self.sibling


class _Clamp(_Plain):
    """A clamp: it takes both a maximum size and a tightening threshold."""

    def __init__(self, *children):
        super().__init__(*children)
        self.maximum, self.tighten = 600, 400

    def set_maximum_size(self, value):
        self.maximum = value

    def set_tightening_threshold(self, value):
        self.tighten = value


class WidenPageTests(unittest.TestCase):
    def test_every_clamp_in_a_page_is_widened_however_deep(self):
        inner = _Clamp()
        outer = _Clamp(_Plain(inner))
        page = _Plain(_Plain(outer), _Plain())

        self.assertEqual(io24gtk.widen_page(page), 2)

        for clamp in (inner, outer):
            self.assertEqual(clamp.maximum, io24gtk.PAGE_WIDTH)
            self.assertEqual(clamp.tighten, io24gtk.PAGE_TIGHTEN)

    def test_a_page_with_no_clamp_is_left_alone(self):
        self.assertEqual(io24gtk.widen_page(_Plain(_Plain(), _Plain())), 0)

    def test_an_empty_page_is_not_an_error(self):
        self.assertEqual(io24gtk.widen_page(None), 0)


class PageWidthTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "io24gtk.py").read_text()

    def test_the_column_is_wider_than_the_libadwaita_default(self):
        # Adw.PreferencesPage clamps at 600sp; that was the complaint.
        self.assertGreater(io24gtk.PAGE_WIDTH, 600)
        self.assertGreaterEqual(io24gtk.PAGE_WIDTH, io24gtk.PAGE_TIGHTEN)

    def test_every_preferences_page_is_built_through_the_wide_one(self):
        self.assertEqual(self.source.count("page = wide_preferences_page()"), 3)
        # the only bare construction left is the one inside that helper
        self.assertEqual(self.source.count("Adw.PreferencesPage()"), 1)

    def test_the_pages_that_clamp_themselves_use_the_same_width(self):
        self.assertEqual(
            self.source.count("clamp = Adw.Clamp(maximum_size=PAGE_WIDTH"), 1)
        # the routing matrix is wider than the rest and says so
        self.assertIn("Adw.Clamp(maximum_size=ROUTING_WIDTH", self.source)
        self.assertGreater(io24gtk.ROUTING_WIDTH, io24gtk.PAGE_WIDTH)
        self.assertNotIn("Adw.Clamp(maximum_size=580", self.source)
        self.assertNotIn("Adw.Clamp(maximum_size=760", self.source)

    def test_routing_keeps_a_small_gutter_inside_the_window(self):
        method = self.source[self.source.index("    def _routing_page(self):"):
                             self.source.index("    def _solo_toggled(")]
        self.assertIn("outer.set_margin_start(16)", method)
        self.assertIn("outer.set_margin_end(16)", method)

    def test_routing_exposes_uc_source_and_output_mutes(self):
        method = self.source[self.source.index("    def _routing_page(self):"):
                             self.source.index("    def _solo_toggled(")]
        self.assertIn("self.source_mute_widgets", method)
        self.assertIn("self.bus_mute_widgets", method)
        self.assertIn("_source_mute_toggled", method)
        self.assertIn("_bus_mute_toggled", method)


if __name__ == "__main__":
    unittest.main()
