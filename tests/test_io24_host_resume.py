#!/usr/bin/env python3
"""Hardware-free contracts for picking up where the last session left off.

The user asked (2026-09-11) that the Host always resume where it was, as
Universal Control did. The io24 keeps its gains, selected block, enable and
stereo link through a power cycle and loses every write-only DSP setting. So
on each connection the Host re-sends what it last sent, except what the unit
reports itself, and restores its own Host-only features once per launch.

Nothing here opens USB.
"""

import ast
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import io24
import io24gtk

ROOT = Path(__file__).resolve().parents[1]


def _function(name):
    source = (ROOT / "io24gtk.py").read_text()
    node = next(n for n in ast.walk(ast.parse(source))
                if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(source, node)


def _bind(host, *names):
    for name in names:
        setattr(host, name, getattr(io24gtk.Win, name).__get__(host))
    return host


class _ReplayIo24(io24.Io24):
    """Records replayed setters without opening USB."""

    def __init__(self, shadow):
        self._shadow = dict(shadow)
        self._shadow_dirty = False
        self._shadow_flushed = 0.0
        self._shadow_persist = False
        self._send_state = None
        self.sent = []

    def set_mute(self, **kwargs):
        self.sent.append("set_mute")

    def set_highpass(self, **kwargs):
        self.sent.append("set_highpass")

    def set_channel_link(self, **kwargs):
        self.sent.append("set_channel_link")


def _replay_shadow():
    return {
        "set_mute#channel=1": {"fn": "set_mute",
                               "kwargs": {"channel": 1, "on": True}},
        "set_highpass#channel=1": {"fn": "set_highpass",
                                   "kwargs": {"channel": 1, "on": True}},
        "set_channel_link": {"fn": "set_channel_link",
                             "kwargs": {"on": False}},
    }


class ReplaySkipTests(unittest.TestCase):
    def test_settings_the_unit_reports_are_not_replayed(self):
        dev = _ReplayIo24(_replay_shadow())
        report = dev.reapply_shadow(skip=io24gtk.RESUME_SKIP)
        self.assertEqual(dev.sent, ["set_highpass"])
        self.assertEqual(report["skipped_by_request"], 2)

    def test_a_plain_reapply_still_sends_everything(self):
        dev = _ReplayIo24(_replay_shadow())
        dev.reapply_shadow()
        self.assertEqual(sorted(dev.sent),
                         ["set_channel_link", "set_highpass", "set_mute"])

    def test_the_skipped_settings_are_the_ones_the_unit_reports(self):
        self.assertEqual(set(io24gtk.RESUME_SKIP),
                         {"set_mute", "set_hp_mute", "set_channel_link"})


class LastSessionFileTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "last-session.json"

    def _host(self, features):
        return _bind(SimpleNamespace(_host_features_state=lambda: features),
                     "_save_last_session")

    def test_the_session_round_trips(self):
        features = {"reverb_character": {"version": 1, "type": 2}}
        self.assertTrue(self._host(features)._save_last_session(self.path))
        self.assertEqual(io24gtk.load_last_session(self.path),
                         {"version": 1, "host_features": features})

    def test_an_unchanged_session_is_not_rewritten(self):
        host = self._host({"multiband": {"on": False}})
        self.assertTrue(host._save_last_session(self.path))
        self.assertFalse(host._save_last_session(self.path))

    def test_a_missing_or_damaged_session_is_no_session(self):
        self.assertIsNone(io24gtk.load_last_session(self.path))
        self.path.write_text("{bad")
        self.assertIsNone(io24gtk.load_last_session(self.path))

    def test_host_features_gather_multiband_and_reverb_character(self):
        host = _bind(SimpleNamespace(
            _mbc_snapshot_state=lambda: {"on": False},
            _reverb_character_state=lambda: None), "_host_features_state")
        self.assertEqual(host._host_features_state(),
                         {"multiband": {"on": False}})

    def test_the_snapshot_dialog_uses_the_same_gathering(self):
        self.assertIn("self._host_features_state()", _function("_pick"))


class ResumeTriggerTests(unittest.TestCase):
    def _host(self):
        calls = []
        host = SimpleNamespace(_resume_session=lambda first: calls.append(first))
        return _bind(host, "_maybe_resume"), calls

    def test_each_connection_resumes_once_and_only_the_first_restores_host_features(self):
        host, calls = self._host()
        host._maybe_resume({"alive": True, "attach_generation": 1})
        host._maybe_resume({"alive": True, "attach_generation": 1})
        host._maybe_resume({"alive": True, "attach_generation": 2})
        self.assertEqual(calls, [True, False])

    def test_nothing_resumes_while_the_unit_is_not_answering(self):
        host, calls = self._host()
        host._maybe_resume({"alive": False, "attach_generation": 1})
        self.assertEqual(calls, [])

    def test_the_tick_resumes_only_after_its_alive_gate(self):
        tick = _function("_tick")
        self.assertLess(tick.index('if not s["alive"]:'),
                        tick.index("self._maybe_resume(s)"))

    def test_the_session_is_saved_on_the_way_out(self):
        self.assertIn("_save_last_session", _function("do_shutdown"))


class _Backend:
    """Stands in for the Io24 driver the Host's worker passes to each job."""

    def __init__(self, shadow):
        self._shadow = shadow
        self.calls = []
        # Like the real driver, it carries its raw USB handle as `.dev`; a
        # resume that unwrapped `.dev` again would reach this and fail.
        self.dev = object()

    def reapply_shadow(self, include_device_preset_state=False, skip=()):
        self.calls.append(("reapply", tuple(skip)))
        return {"applied": 3, "failed": []}

    def recall_device_slot(self, channel, slot):
        self.calls.append(("recall", channel, slot))
        return {}

    def set_fx_mix(self, channel, value):
        self.calls.append(("set_fx_mix", channel, value))


class ResumeSessionTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(
            io24gtk.GLib, "idle_add", side_effect=lambda fn, *a: fn(*a))
        patcher.start()
        self.addCleanup(patcher.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "last-session.json"
        self.path.write_text(json.dumps({
            "version": 1,
            "host_features": {"reverb_character": {"version": 1}}}))

    def _host(self, shadow, preset_slot=(0, 2)):
        backend = _Backend(shadow)
        adopted = []
        host = SimpleNamespace(
            ctl=SimpleNamespace(snap={"preset_slot": list(preset_slot)},
                                submit=lambda work: work(backend)),
            _after_load=lambda mirror, features, migrations, message:
            adopted.append((mirror, features, message)),
            say=lambda _message: None)
        return _bind(host, "_resume_session"), backend, adopted

    def test_first_resume_restores_host_features_and_skips_readable_settings(self):
        host, backend, adopted = self._host({})
        host._resume_session(first=True, path=self.path)
        self.assertEqual(backend.calls, [("reapply", io24gtk.RESUME_SKIP)])
        self.assertEqual(adopted[0][1], {"reverb_character": {"version": 1}})

    def test_a_reconnect_restores_the_unit_but_not_host_features(self):
        host, _backend, adopted = self._host({})
        host._resume_session(first=False, path=self.path)
        self.assertIsNone(adopted[0][1])

    def test_voice_fx_on_loads_the_owners_block_first_and_keeps_its_amount(self):
        shadow = {
            "set_fx": {"fn": "set_fx",
                       "kwargs": {"model": "detuner", "on": True}},
            "set_processing_channel#channel=1": {
                "fn": "set_processing_channel",
                "kwargs": {"channel": 1, "source_input": 2}},
            "set_fx_mix#channel=2": {"fn": "set_fx_mix",
                                     "kwargs": {"channel": 2, "value": 0.4}},
        }
        host, backend, _adopted = self._host(shadow, preset_slot=(0, 3))
        host._resume_session(first=False, path=self.path)
        self.assertEqual(backend.calls, [
            ("recall", 2, 3),
            ("reapply", io24gtk.RESUME_SKIP),
            ("set_fx_mix", 2, 0.4),
        ])

    def test_voice_fx_off_loads_no_block(self):
        shadow = {"set_fx": {"fn": "set_fx",
                             "kwargs": {"model": "detuner", "on": False}}}
        host, backend, _adopted = self._host(shadow)
        host._resume_session(first=False, path=self.path)
        self.assertEqual(backend.calls, [("reapply", io24gtk.RESUME_SKIP)])


if __name__ == "__main__":
    unittest.main()
