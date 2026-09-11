#!/usr/bin/env python3
"""Hardware-free contracts for Host-side automatic preamp gain.

Universal Control's Automatic Preamp Gain is a per-input switch, but the
firmware has no descriptor behind it (re/UCNET_SHIM_SPEC.md 4c), so the Host
keeps the gain itself while the switch is on. These pin the controller's
decisions and the wiring that turns them into gain writes -- with no prompt
and no message at any point.

Nothing here opens USB.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

import io24gtk
from io24gtk import AutoGain


TICK = 0.05


def _feed(controller, pattern, gains, start=0.0, count=AutoGain.MIN_READINGS):
    """Feed cycling readings; return (time, gain) of the first change."""
    for i in range(count):
        t = start + i * TICK
        levels = {c: seq[i % len(seq)] for c, seq in pattern.items()}
        new = controller.step(t, levels, gains)
        if new is not None:
            return t, new
    return None, None


class AutoGainControllerTests(unittest.TestCase):
    def test_a_quiet_performance_is_lifted_gently(self):
        _t, new = _feed(AutoGain((1,)), {1: [-24.0, -45.0]}, {1: 30.0})
        self.assertEqual(new, 30.0 + AutoGain.MAX_RISE_DB)

    def test_a_hot_performance_comes_down_faster(self):
        _t, new = _feed(AutoGain((1,)), {1: [-4.0, -30.0]}, {1: 30.0})
        self.assertEqual(new, 30.0 - AutoGain.MAX_FALL_DB)

    def test_a_level_inside_the_deadband_is_left_alone(self):
        _t, new = _feed(AutoGain((1,)), {1: [-13.5, -40.0]}, {1: 30.0},
                        count=200)
        self.assertIsNone(new)

    def test_a_clip_drops_the_gain_at_once(self):
        controller = AutoGain((1,))
        self.assertEqual(controller.step(0.0, {1: -0.2}, {1: 30.0}), 24.0)
        # still settling: the next reading belongs to the old gain
        self.assertIsNone(controller.step(TICK, {1: -0.2}, {1: 30.0}))

    def test_silence_and_steady_noise_are_never_lifted(self):
        for pattern in ([-99.0], [-50.0], [-48.0, -50.0]):
            with self.subTest(pattern=pattern):
                _t, new = _feed(AutoGain((1,)), {1: pattern}, {1: 30.0},
                                count=200)
                self.assertIsNone(new)

    def test_corrections_are_spaced_and_never_reuse_old_readings(self):
        controller = AutoGain((1,))
        t1, first = _feed(controller, {1: [-24.0, -45.0]}, {1: 30.0})
        self.assertEqual(first, 32.0)
        self.assertTrue(all(not w for w in controller.readings.values()))
        t2, second = _feed(controller, {1: [-22.0, -43.0]}, {1: first},
                           start=t1 + TICK, count=200)
        self.assertEqual(second, 34.0)
        self.assertGreaterEqual(t2 - t1, AutoGain.HOLD_S)

    def test_the_ends_of_the_range_stop_corrections_quietly(self):
        _t, new = _feed(AutoGain((1,)), {1: [-40.0, -60.0]}, {1: 60.0},
                        count=200)
        self.assertIsNone(new)
        self.assertIsNone(AutoGain((1,)).step(0.0, {1: -0.1}, {1: 0.0}))

    def test_linked_inputs_follow_the_louder_one(self):
        _t, new = _feed(AutoGain((1, 2)),
                        {1: [-40.0, -60.0], 2: [-4.0, -30.0]},
                        {1: 30.0, 2: 30.0})
        self.assertEqual(new, 26.0)

    def test_non_finite_readings_are_ignored(self):
        controller = AutoGain((1,))
        self.assertIsNone(controller.step(0.0, {1: float("nan")}, {1: 30.0}))
        self.assertIsNone(controller.step(0.0, {1: float("inf")}, {1: 30.0}))
        self.assertEqual(controller.readings[1], [])

    def test_a_real_source_settles_on_the_target_and_stays(self):
        # A voice whose loud moments sit at -40 dBFS before gain, with pauses
        # 25 dB lower. What the meter reads is source + gain.
        controller, gain, changes = AutoGain((1,)), 10.0, []
        for i in range(int(90 / TICK)):
            t = i * TICK
            source = -65.0 if i % 3 == 0 else -40.0
            new = controller.step(t, {1: source + gain}, {1: gain})
            if new is not None:
                changes.append((t, new))
                gain = new
            self.assertTrue(AutoGain.GAIN_MIN_DB <= gain <= AutoGain.GAIN_MAX_DB)
        self.assertLessEqual(abs(-40.0 + gain - AutoGain.TARGET_DB),
                             AutoGain.DEADBAND_DB)
        self.assertTrue(all(later - earlier >= AutoGain.HOLD_S
                            for (earlier, _g1), (later, _g2)
                            in zip(changes, changes[1:])))
        self.assertEqual([c for c in changes if c[0] > 45.0], [])


class _Toggle:
    def __init__(self):
        self.active = False
        self.on_change = None

    def get_active(self):
        return self.active

    def set_active(self, value):
        self.active = bool(value)
        if self.on_change is not None:        # GTK emits "toggled" here
            self.on_change(self)


class _Fader:
    def __init__(self):
        self.w = self
        self.sensitive = True

    def set_sensitive(self, value):
        self.sensitive = bool(value)


def _window(alive=True, gains=(30.0, 30.0), levels=(-99.0, -99.0),
            linked=False):
    window = io24gtk.Win.__new__(io24gtk.Win)
    window.ctl = SimpleNamespace(snap={"alive": alive, "gain": list(gains),
                                       "in": list(levels)})
    window.link_both = linked
    window.gain_faders = {1: _Fader(), 2: _Fader()}
    window.autogain_toggles = {}
    for c in (1, 2):
        toggle = _Toggle()
        toggle.on_change = lambda button, c=c: window._autogain_toggled(button, c)
        window.autogain_toggles[c] = toggle
    window.messages = []
    window.say = window.messages.append
    window.writes = []
    window._set = lambda param, channel, value: window.writes.append(
        (param, channel, value))
    return window


def _perform(window, loud, quiet, channel=1, ticks=AutoGain.MIN_READINGS):
    for i in range(ticks):
        window.ctl.snap["in"][channel - 1] = loud if i % 2 == 0 else quiet
        window._autogain_tick()


class AutoGainHostTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(io24gtk.GLib, "timeout_add",
                                    return_value=7)
        self.timeout_add = patcher.start()
        self.addCleanup(patcher.stop)

    def test_switching_on_locks_the_fader_and_starts_one_timer(self):
        window = _window()
        window.autogain_toggles[1].set_active(True)
        window.autogain_toggles[2].set_active(True)
        self.assertFalse(window.gain_faders[1].sensitive)
        self.assertFalse(window.gain_faders[2].sensitive)
        self.timeout_add.assert_called_once_with(
            io24gtk.Win.AUTOGAIN_TICK_MS, window._autogain_tick)

    def test_it_corrects_by_itself_without_a_word(self):
        window = _window()
        window.autogain_toggles[1].set_active(True)
        _perform(window, -24.0, -45.0)
        self.assertEqual(window.writes, [("gain", 1, 32.0)])
        self.assertEqual(window.messages, [])

    def test_a_clip_is_pulled_down_on_the_next_tick(self):
        window = _window(levels=(-0.1, -99.0))
        window.autogain_toggles[1].set_active(True)
        window._autogain_tick()
        self.assertEqual(window.writes, [("gain", 1, 24.0)])

    def test_switching_off_unlocks_and_stops_the_timer(self):
        window = _window()
        window.autogain_toggles[1].set_active(True)
        window.autogain_toggles[1].set_active(False)
        self.assertTrue(window.gain_faders[1].sensitive)
        self.assertFalse(window._autogain_tick())
        self.assertIsNone(window._autogain_timer)
        self.assertEqual(window.writes, [])

    def test_linked_switches_move_together_and_write_both(self):
        window = _window(linked=True)
        window.autogain_toggles[1].set_active(True)
        self.assertTrue(window.autogain_toggles[2].get_active())
        self.assertFalse(window.gain_faders[2].sensitive)
        _perform(window, -4.0, -30.0, channel=2)
        self.assertEqual(window.writes, [("gain", 1, 26.0), ("gain", 2, 26.0)])

    def test_nothing_is_heard_or_written_while_offline(self):
        window = _window(alive=False, levels=(-0.1, -0.1))
        window.autogain_toggles[1].set_active(True)
        self.assertTrue(window._autogain_tick())
        self.assertEqual(window.writes, [])
        self.assertEqual(window.messages, [])


if __name__ == "__main__":
    unittest.main()
