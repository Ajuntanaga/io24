#!/usr/bin/env python3
"""Hardware-free contracts for the Device page's DSP amount and Bypass.

The io24 keeps one processing scalar per channel (wire id 4): exact zero
bypasses the channel and any positive value is the amount. Universal Control
shows it as two controls, `dspAmount` and `bypassDSP`, neither with a device
binding of its own. The Host composes them the same way; these pin the
composition, what each gesture sends, and that showing a known value sends
nothing.

Nothing here opens USB.
"""

import ast
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest import mock

import io24gtk
from io24gtk import ProcessingMix

ROOT = Path(__file__).resolve().parents[1]


class _Value:
    def __init__(self, value=0.0):
        self.value = value
        self.sensitive = True
        self.subtitle = None

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def get_active(self):
        return bool(self.value)

    def set_active(self, value):
        self.value = bool(value)

    def set_sensitive(self, on):
        self.sensitive = bool(on)

    def set_subtitle(self, text):
        self.subtitle = text


class _Device:
    def __init__(self):
        self.calls = []

    def has_send_level(self, _source, _bus):
        return True

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return call


WIN_METHODS = ("_set_processing_mix", "_set_processing_amount",
               "_processing_bypass_toggled", "_adopt_processing_mix",
               "_follow_recall_processing", "_mark_processing_mix_known",
               "_push_reverb")


def _host(amount=1.0, bypassed=False, reverb_on=False):
    device = _Device()
    host = SimpleNamespace(
        _adopt_mute=False,
        _fs=48000.0,
        processing_mix_controls={
            ch: ProcessingMix(_Value(amount), _Value(bypassed))
            for ch in (1, 2)},
        processing_mix_rows={ch: _Value() for ch in (1, 2)},
        rev_on=_Value(reverb_on),
        s_rsize=_Value(0.5), s_rmix=_Value(0.3),
        s_rhp=_Value(200.0), s_rpre=_Value(0.02),
        rev_return_controls={"main": _Value(-3.0)},
        ctl=SimpleNamespace(submit=lambda work: work(device)),
    )
    for name in WIN_METHODS:
        setattr(host, name, getattr(io24gtk.Win, name).__get__(host))
    return host, device


def _fx_mix_calls(device):
    return [args for name, args, _kw in device.calls if name == "set_fx_mix"]


class ProcessingMixTests(unittest.TestCase):
    def test_zero_is_written_while_bypassed_and_the_amount_otherwise(self):
        mix = ProcessingMix(_Value(0.4), _Value(False))
        self.assertEqual(mix.get_value(), 0.4)
        mix.bypass.set_active(True)
        self.assertEqual(mix.get_value(), 0.0)
        self.assertEqual(mix.amount.get_value(), 0.4)

    def test_adopting_zero_bypasses_and_keeps_the_remembered_amount(self):
        mix = ProcessingMix(_Value(0.6), _Value(False))
        mix.set_value(0.0)
        self.assertTrue(mix.bypassed())
        self.assertEqual(mix.amount.get_value(), 0.6)
        mix.set_value(0.25)
        self.assertFalse(mix.bypassed())
        self.assertEqual(mix.get_value(), 0.25)

    def test_the_amount_alone_never_reads_as_bypass(self):
        mix = ProcessingMix(_Value(1.0), _Value(False))
        mix.set_value(1e-6)
        self.assertFalse(mix.bypassed())
        self.assertEqual(mix.get_value(), ProcessingMix.AMOUNT_MIN)
        self.assertGreater(ProcessingMix.AMOUNT_MIN, 0.0)

    def test_labels_keep_small_amounts_distinguishable_from_zero(self):
        self.assertEqual(ProcessingMix.label(1.0), "100 %")
        self.assertEqual(ProcessingMix.label(0.25), "25 %")
        self.assertEqual(ProcessingMix.label(ProcessingMix.AMOUNT_MIN), "0.1 %")


class ProcessingGestureTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(
            io24gtk.GLib, "idle_add", side_effect=lambda fn, *a: fn(*a))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_bypass_sends_zero_and_release_sends_the_remembered_amount(self):
        host, device = _host(amount=0.7)
        control = host.processing_mix_controls[1]

        control.bypass.set_active(True)
        host._processing_bypass_toggled(1)
        self.assertEqual(_fx_mix_calls(device), [(1, 0.0)])
        self.assertFalse(host.processing_mix_rows[1].sensitive)

        control.bypass.set_active(False)
        host._processing_bypass_toggled(1)
        self.assertEqual(_fx_mix_calls(device), [(1, 0.0), (1, 0.7)])
        self.assertTrue(host.processing_mix_rows[1].sensitive)

    def test_a_moved_amount_is_sent_only_while_processing(self):
        host, device = _host(amount=0.7)
        host._set_processing_amount(2, 0.5)
        self.assertEqual(_fx_mix_calls(device), [(2, 0.5)])

        host.processing_mix_controls[2].bypass.set_active(True)
        host._set_processing_amount(2, 0.3)
        self.assertEqual(_fx_mix_calls(device), [(2, 0.5)])

    def test_adoption_moves_the_controls_and_sends_nothing(self):
        host, device = _host(amount=0.7)
        host._adopt_processing_mix(2, 0.0)
        # the switch's notify handler runs with the adoption flag raised
        host._adopt_mute = True
        host._processing_bypass_toggled(2)
        host._adopt_mute = False

        self.assertEqual(device.calls, [])
        self.assertTrue(host.processing_mix_controls[2].bypassed())
        self.assertEqual(host.processing_mix_controls[2].amount.get_value(), 0.7)
        self.assertFalse(host.processing_mix_rows[2].sensitive)
        self.assertIsNotNone(host.processing_mix_rows[2].subtitle)

    def test_adoption_restores_the_prior_mute(self):
        host, _device = _host()
        host._adopt_mute = True
        host._adopt_processing_mix(1, 0.4)
        self.assertTrue(host._adopt_mute)
        host._adopt_mute = False
        host._adopt_processing_mix(1, 0.4)
        self.assertFalse(host._adopt_mute)

    def test_a_recall_that_had_to_enable_the_channel_shows_it_processing(self):
        host, device = _host(amount=0.4, bypassed=True)
        host._follow_recall_processing(1, {"enable_asserted": True})
        self.assertFalse(host.processing_mix_controls[1].bypassed())
        self.assertEqual(host.processing_mix_controls[1].get_value(), 1.0)
        self.assertEqual(device.calls, [])

    def test_a_recall_on_a_processing_channel_leaves_the_controls_alone(self):
        host, _device = _host(amount=0.4)
        host._follow_recall_processing(1, {"enable_asserted": False})
        self.assertEqual(host.processing_mix_controls[1].get_value(), 0.4)

    def test_enabling_reverb_never_lifts_a_bypass(self):
        host, device = _host(amount=0.65, bypassed=True, reverb_on=True)
        host._push_reverb(establish_path=True)
        self.assertEqual(device.calls[0], ("set_fx_mix", (1, 0.0), {}))
        self.assertEqual(device.calls[-1][0], "set_reverb")


class DevicePageTests(unittest.TestCase):
    @staticmethod
    def _function(name):
        source = (ROOT / "io24gtk.py").read_text()
        node = next(
            n for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.FunctionDef) and n.name == name)
        return ast.get_source_segment(source, node)

    def test_dsp_amount_and_bypass_live_on_the_device_page_only(self):
        self.assertIn("self._processing_group()", self._function("_device_page"))
        self.assertNotIn("processing_mix_controls", self._function("_fx_page"))
        group = self._function("_processing_group")
        self.assertIn('title="Channel processing"', group)
        self.assertIn('"Channel %d DSP amount"', group)
        self.assertIn('"Channel %d bypass"', group)
        self.assertIn("ProcessingMix.AMOUNT_MIN", group)

    def test_every_recall_path_is_followed_on_the_processing_controls(self):
        self.assertIn("self._follow_recall_processing(ch, report)",
                      self._function("_slot_recalled"))
        self.assertIn("self._adopt_processing_mix(ch, value)",
                      self._function("_after_load"))


if __name__ == "__main__":
    unittest.main()
