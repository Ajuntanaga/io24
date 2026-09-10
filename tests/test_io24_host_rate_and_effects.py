#!/usr/bin/env python3
"""Hardware-free contracts for clock-correct DSP writes and effect state.

The device stores coefficients, not the Hz and seconds they were computed
from, so every write is a function of the clock. The Host used to pass none,
which left every biquad and time constant built for 48 kHz whatever the
interface was running at. These tests pin the rate through the write path,
the limiter release the page never exposed, and the Host-only reverb
character that no save carried.

Nothing here opens USB.
"""

import unittest

import io24gtk


class _Value:
    def __init__(self, value=0.0):
        self.value = value

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def get_active(self):
        return bool(self.value)

    def set_active(self, value):
        self.value = bool(value)

    def get_selected(self):
        return int(self.value)

    def set_selected(self, value):
        self.value = int(value)


class _Adjustment:
    def __init__(self, lower, upper):
        self._lower, self._upper = lower, upper

    def get_lower(self):
        return self._lower

    def get_upper(self):
        return self._upper


class _Depth(_Value):
    def get_adjustment(self):
        return _Adjustment(0.0, 0.30)


class _Draws:
    def queue_draw(self):
        pass


class _Ctl:
    def __init__(self, dev=None):
        self.dev = dev
        self.sent = []

    def submit(self, fn):
        self.sent.append(fn)

    def run(self, dev):
        for fn in self.sent:
            fn(dev)


class _Device:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return record


def _window():
    window = io24gtk.Win.__new__(io24gtk.Win)
    window._fs = 48000.0
    window._fs_seen = False
    window._adopt_mute = False
    window._rev_mute = False
    window.link_both = False
    window.racks = {}
    window.messages = []
    window.say = window.messages.append
    window.hpf_by_ch = {1: 80.0, 2: 24.0}
    window.dyn_by_ch = {1: {"gate": False, "comp": False, "lim": True},
                        2: {"gate": False, "comp": False, "lim": False}}
    window.bands_by_ch = {
        ch: [{"shape": "peaking", "freq": 1000.0, "gain": 0.0, "q": 0.7}
             for _ in range(4)]
        for ch in (1, 2)
    }
    window.w = {
        ch: {"lth": _Value(-28.0), "lrel": _Value(0.4),
             "gth": _Value(-40.0), "grange": _Value(-60.0),
             "gatk": _Value(0.01), "grel": _Value(0.3),
             "gkey": _Value(24.0), "gklisten": _Value(False),
             "gexp": _Value(True),
             "comp_curve": _Draws(), "curve": _Draws(),
             "lim_on": _Value(False)}
        for ch in (1, 2)
    }
    window._compressor_kwargs = lambda ch: (0, {"threshold_db": -24.0})
    window.ctl = _Ctl()
    return window


class DeviceClockTests(unittest.TestCase):
    def test_first_sighting_is_adopted_without_a_resend(self):
        window = _window()
        # Nothing has been pushed yet, so there is nothing built at 48 kHz.
        self.assertFalse(window._set_device_fs(96000))
        self.assertEqual(window._fs, 96000.0)

    def test_a_later_change_asks_for_a_resend(self):
        window = _window()
        window._set_device_fs(48000)
        self.assertTrue(window._set_device_fs(44100))
        self.assertEqual(window._fs, 44100.0)

    def test_an_unchanged_rate_never_resends(self):
        window = _window()
        window._set_device_fs(48000)
        for _ in range(5):
            self.assertFalse(window._set_device_fs(48000))

    def test_an_implausible_rate_is_ignored(self):
        window = _window()
        window._set_device_fs(48000)
        for bad in (0, -1, "not a rate", None, 7999, 192001):
            self.assertFalse(window._set_device_fs(bad))
        self.assertEqual(window._fs, 48000.0)

    def test_resend_is_a_no_op_without_a_device(self):
        window = _window()
        window.ctl.dev = None
        self.assertFalse(window._resend_rate_dependent_state())
        self.assertEqual(window.ctl.sent, [])


class RateDependentWriteTests(unittest.TestCase):
    def test_every_resent_write_carries_the_new_rate(self):
        window = _window()
        window.ctl.dev = object()
        window._fs = 96000.0
        window._push_reverb = lambda *a, **k: None
        window._push_fx = lambda *a, **k: None
        window._adopt_band = lambda ch: None
        window.invalidate_curve = lambda: None
        window._resend_rate_dependent_state()

        device = _Device()
        window.ctl.run(device)
        rate_bearing = [call for call in device.calls if "fs" in call[2]]
        self.assertTrue(rate_bearing)
        for name, _args, kwargs in rate_bearing:
            self.assertEqual(kwargs["fs"], 96000.0,
                             "%s was sent at the wrong rate" % name)
        names = {call[0] for call in device.calls}
        self.assertIn("set_eq_band", names)
        self.assertIn("set_highpass_freq", names)
        self.assertIn("set_limiter", names)
        # All four bands of both channels, not just the selected one.
        self.assertEqual(
            len([c for c in device.calls if c[0] == "set_eq_band"]), 8)

    def test_the_limiter_now_sends_its_release_and_rate(self):
        window = _window()
        window._fs = 44100.0
        window.w[1]["lrel"].set_value(0.75)
        window.w[1]["lth"].set_value(-12.0)
        window._dyn_push("lim", 1)

        device = _Device()
        window.ctl.run(device)
        name, args, kwargs = device.calls[0]
        self.assertEqual(name, "set_limiter")
        self.assertEqual(args[0], 1)
        self.assertTrue(args[1])
        self.assertAlmostEqual(args[2], -12.0)
        self.assertAlmostEqual(kwargs["release_s"], 0.75)
        self.assertEqual(kwargs["fs"], 44100.0)


class ReverbRateTests(unittest.TestCase):
    def test_the_reverb_engine_is_built_at_the_device_clock(self):
        window = _window()
        window._fs = 88200.0
        window._adopt_mute = False
        window.rev_on = _Value(True)
        window.s_rsize = _Value(0.5)
        window.s_rmix = _Value(0.3)
        window.s_rhp = _Value(200.0)
        window.s_rpre = _Value(0.02)
        window.processing_mix_controls = {1: _Value(1.0)}
        window.rev_return_controls = {"main": _Value(0.0)}
        window._push_reverb()

        device = _Device()
        window.ctl.run(device)
        name, _args, kwargs = device.calls[-1]
        self.assertEqual(name, "set_reverb")
        self.assertEqual(kwargs["fs"], 88200.0)


class ReverbCharacterTests(unittest.TestCase):
    def _reverb_window(self):
        window = _window()
        window.rev_type = _Value(0)
        window.rev_mod = _Value(False)
        window.s_rmoddep = _Depth(0.08)
        return window

    def test_character_state_captures_the_host_only_half(self):
        window = self._reverb_window()
        window.rev_type.set_selected(3)
        window.rev_mod.set_active(True)
        window.s_rmoddep.set_value(0.12)
        state = window._reverb_character_state()
        self.assertEqual(state["type"], 3)
        self.assertTrue(state["movement"])
        self.assertAlmostEqual(state["movement_depth"], 0.12)

    def test_character_round_trips_through_adoption(self):
        window = self._reverb_window()
        window.rev_type.set_selected(5)
        window.rev_mod.set_active(True)
        window.s_rmoddep.set_value(0.2)
        saved = window._reverb_character_state()

        window.rev_type.set_selected(0)
        window.rev_mod.set_active(False)
        window.s_rmoddep.set_value(0.0)
        self.assertIsNone(window._adopt_reverb_character(saved))
        self.assertEqual(window.rev_type.get_selected(), 5)
        self.assertTrue(window.rev_mod.get_active())
        self.assertAlmostEqual(window.s_rmoddep.get_value(), 0.2)

    def test_adoption_leaves_the_mutes_as_it_found_them(self):
        window = self._reverb_window()
        window._adopt_reverb_character(window._reverb_character_state())
        self.assertFalse(window._rev_mute)
        self.assertFalse(window._adopt_mute)

    def test_an_unknown_character_is_refused_with_a_notice(self):
        window = self._reverb_window()
        notice = window._adopt_reverb_character(
            {"type": 99, "movement": True, "movement_depth": 0.1})
        self.assertIn("unknown character", notice)
        self.assertEqual(window.rev_type.get_selected(), 0)

    def test_an_out_of_range_depth_is_refused_with_a_notice(self):
        window = self._reverb_window()
        notice = window._adopt_reverb_character(
            {"type": 1, "movement": True, "movement_depth": 0.9})
        self.assertIn("outside the control", notice)
        self.assertAlmostEqual(window.s_rmoddep.get_value(), 0.08)

    def test_incomplete_saved_values_are_refused_with_a_notice(self):
        window = self._reverb_window()
        notice = window._adopt_reverb_character({"type": 1})
        self.assertIn("incomplete", notice)

    def test_a_missing_section_is_silent(self):
        window = self._reverb_window()
        self.assertIsNone(window._adopt_reverb_character(None))


if __name__ == "__main__":
    unittest.main()
