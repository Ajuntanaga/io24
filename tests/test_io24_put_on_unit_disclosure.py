#!/usr/bin/env python3
"""The Presets menu must not offer a unit write the driver refuses.

On 2026-09-14 a known body written to an inactive block produced no recall
effect, and `Io24.save_known_device_slot` now refuses a tagged body before
transport: firmware 1.28 loads only native version-2 records. The menu used to
promise "This replaces X ... then loads it there" and fail only after the user
confirmed. These contracts keep the menu and the driver saying the same thing.

Nothing here opens USB, audio or a display.
"""

import ast
from pathlib import Path
import unittest

import io24
import io24gtk

ROOT = Path(__file__).resolve().parents[1]


def _function(name):
    source = (ROOT / "io24gtk.py").read_text()
    node = next(n for n in ast.walk(ast.parse(source))
                if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(source, node)


class PutOnUnitDisclosureTests(unittest.TestCase):
    @staticmethod
    def _driver_refuses():
        """Whether the driver refuses a saved JSON body, without any device."""
        device = object.__new__(io24.Io24)
        try:
            device.save_known_device_slot(
                1, {"preset_name": "probe"}, {}, "test")
        except io24.HostActionError:
            return True
        except Exception:
            return False          # some other failure is not a refusal
        return False

    def test_the_driver_refuses_a_saved_preset_body_before_transport(self):
        self.assertTrue(self._driver_refuses())

    def test_the_menu_and_the_driver_agree(self):
        if self._driver_refuses():
            self.assertTrue(
                io24gtk.PUT_ON_UNIT_UNAVAILABLE,
                "the driver refuses saved bodies, so the menu must say so")
        else:
            self.assertFalse(
                io24gtk.PUT_ON_UNIT_UNAVAILABLE,
                "the driver takes saved bodies again: clear "
                "PUT_ON_UNIT_UNAVAILABLE so the menu offers the write")

    def test_the_menu_disables_the_item_and_gives_the_reason(self):
        source = _function("_preset_menu")
        self.assertIn("if PUT_ON_UNIT_UNAVAILABLE:", source)
        self.assertIn("button.set_sensitive(False)", source)
        self.assertIn("set_tooltip_text(PUT_ON_UNIT_UNAVAILABLE)", source)

    def test_the_reason_is_the_native_record(self):
        self.assertIn("native record", io24gtk.PUT_ON_UNIT_UNAVAILABLE)
