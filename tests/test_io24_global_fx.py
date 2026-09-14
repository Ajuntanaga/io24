#!/usr/bin/env python3
"""Hardware-free contracts for the shared, two-lane FX control surface."""

import ast
import inspect
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import io24_presets
import io24_fx
import io24gtk


ROOT = Path(__file__).parents[1]


class _Value:
    def __init__(self, value):
        self.value = value

    def get_active(self):
        return bool(self.value)

    def get_selected(self):
        return int(self.value)

    def get_value(self):
        return self.value


class GlobalFxTests(unittest.TestCase):
    def test_fx_page_exposes_one_active_switch_without_owner_or_readiness(self):
        source = (ROOT / "io24gtk.py").read_text()
        tree = ast.parse(source)
        page = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef)
                    and node.name == "_fx_page")
        rendered = ast.get_source_segment(source, page)

        self.assertIn('title="FX active"', rendered)
        self.assertNotIn('title="Target input"', rendered)
        self.assertNotIn('title="Device activation"', rendered)
        self.assertNotIn('label="Presets…"', rendered)

    def test_fx_edit_sends_the_global_singleton_once_without_routing_mutation(self):
        calls = []

        class Device:
            def set_voicefx_channel(self, _channel):
                raise AssertionError("global FX must not change processing routing")

            def set_fx(self, model, **kwargs):
                calls.append((model, kwargs))
                return 2

        device = Device()
        host = SimpleNamespace(
            _fx_mute=False,
            ctl=SimpleNamespace(dev=device, submit=lambda fn: fn(device)),
            fx_arm=_Value(True),
            fx_model=_Value(5),
            fx_params={"delay": {
                "time_s": _Value(0.173),
                "feedback": _Value(0.82),
                "mix": _Value(1.0),
            }},
            FX_ORDER=io24gtk.Win.FX_ORDER,
            say=lambda _message: None,
        )

        with mock.patch.object(io24gtk.GLib, "idle_add", return_value=1):
            io24gtk.Win._push_fx(host)

        self.assertEqual(calls, [("delay", {
            "on": True,
            "time_s": 0.173,
            "feedback": 0.82,
            "mix": 1.0,
        })])

    def test_either_channel_preset_records_the_same_global_fx_state(self):
        host = SimpleNamespace(
            FX_ORDER=["transformer", "detuner"],
            fx_model=_Value(1),
            _fx_live_params=lambda: {"detune": 1.0},
            fx_arm=_Value(True),
        )

        first = io24gtk.Win._record_voicefx(host, 1)
        second = io24gtk.Win._record_voicefx(host, 2)

        self.assertEqual(first, second)
        self.assertTrue(first[1]["on"])

    def test_direct_preset_apply_sends_global_fx_without_owner_assignment(self):
        calls = []

        class Device:
            def set_voicefx_channel(self, _channel):
                raise AssertionError("preset FX must not change processing routing")

            def set_fx(self, model, **kwargs):
                calls.append((model, kwargs))
                return 2

        preset = {
            "voicefx": {
                "__classid": io24_fx.VOICEFX_CLASS_IDS["delay"],
                "on": 1,
                "time": 0.173,
                "feedback": 0.82,
                "mix": 1.0,
            },
        }

        io24_presets.apply_preset(Device(), preset, channel=2, with_fx=True)

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "delay")

    def test_automatic_resume_neither_recalls_a_slot_nor_replays_old_owner(self):
        source = inspect.getsource(io24gtk.Win._resume_session)
        self.assertNotIn("recall_device_slot", source)
        self.assertNotIn('state["voicefx_target"]', source)
        self.assertIn("set_processing_channel", io24gtk.RESUME_SKIP)

    def test_legacy_owner_shadow_is_not_projected_as_fx_state(self):
        state = io24gtk.shadow_ui_state({
            "old-owner": {
                "fn": "set_processing_channel",
                "kwargs": {"channel": 1, "source_input": 2},
            },
            "fx": {
                "fn": "set_fx",
                "kwargs": {"model": "delay", "on": True},
            },
        })

        self.assertNotIn("voicefx_target", state)
        self.assertEqual(state["voicefx"], {"model": "delay", "on": True})


if __name__ == "__main__":
    unittest.main()
