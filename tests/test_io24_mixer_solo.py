#!/usr/bin/env python3
"""Hardware-free contracts for the Host-side mixer solo.

Block 100 has no solo. The Host silences the rest of a bus by writing the off
sentinel for every other source while leaving their level, assign and pan
alone, so releasing the solo writes exactly the prior mix back.

Nothing here opens USB.
"""

import threading
import unittest
from types import SimpleNamespace
from unittest import mock

import io24
import io24gtk


class _MixerOnlyIo24(io24.Io24):
    """Host mixer bookkeeping with the one block-100 write recorded."""

    def __init__(self):
        self._shadow = {}
        self._shadow_dirty = False
        self._shadow_flushed = 0.0
        self._shadow_persist = False
        self._send_state = None
        self.writes = []

    def _write_mix(self, source, bus, gain_db):
        self.writes.append((source, bus, gain_db))
        return self.writes[-1]

    def last(self, bus):
        """The most recent wire value per source in one bus."""
        return {src: db for src, b, db in self.writes if b == bus}


def _mixed():
    dev = _MixerOnlyIo24()
    dev.set_send_db("line/ch1", "main", -6.0)
    dev.set_send_db("line/ch2", "main", -3.0)
    dev.set_send_db("return/ch1", "main", 0.0)
    dev.set_send_db("line/ch1", "mixa", -10.0)
    dev.writes.clear()
    return dev


class DriverSoloTests(unittest.TestCase):
    def test_solo_silences_only_the_rest_of_that_bus(self):
        dev = _mixed()
        dev.set_solo("line/ch1", "main")
        wire = dev.last("main")
        self.assertEqual(wire["line/ch1"], -6.0)
        for other in ("line/ch2", "return/ch1", "return/ch2", "return/ch3",
                      "fxreturn/ch1"):
            self.assertIsNone(wire[other], other)
        self.assertEqual(dev.last("mixa"), {})
        self.assertTrue(dev.soloed("line/ch1", "main"))
        self.assertFalse(dev.soloed("line/ch1", "mixa"))

    def test_release_writes_back_the_exact_prior_mix(self):
        dev = _mixed()
        dev.set_solo("line/ch1", "main")
        dev.writes.clear()
        dev.set_solo("line/ch1", "main", False)
        wire = dev.last("main")
        self.assertEqual(wire["line/ch1"], -6.0)
        self.assertEqual(wire["line/ch2"], -3.0)
        self.assertEqual(wire["return/ch1"], 0.0)
        # never set before the solo: materialised at the displayed unity
        self.assertEqual(wire["return/ch2"], io24.Io24.DEFAULT_SEND_DB)
        self.assertEqual(dev.send_db("line/ch2", "main"), -3.0)
        self.assertTrue(dev.send_assigned("line/ch2", "main"))
        self.assertFalse(dev.soloed("line/ch1", "main"))

    def test_an_unassigned_source_stays_out_after_release(self):
        dev = _mixed()
        dev.set_send_assigned("line/ch2", "main", False)
        dev.set_solo("line/ch1", "main")
        dev.set_solo("line/ch1", "main", False)
        self.assertIsNone(dev.last("main")["line/ch2"])
        self.assertFalse(dev.send_assigned("line/ch2", "main"))

    def test_fader_moves_while_soloed_stay_silent_then_apply(self):
        dev = _mixed()
        dev.set_solo("line/ch1", "main")
        dev.set_send_db("line/ch2", "main", -20.0)
        self.assertIsNone(dev.writes[-1][2])
        dev.set_solo("line/ch1", "main", False)
        self.assertEqual(dev.last("main")["line/ch2"], -20.0)

    def test_bus_master_moves_while_soloed_keep_the_rest_silent(self):
        dev = _mixed()
        dev.set_solo("line/ch1", "main")
        dev.writes.clear()
        dev.set_bus_master("main", -4.0)
        wire = dev.last("main")
        self.assertEqual(wire["line/ch1"], -10.0)
        self.assertIsNone(wire["line/ch2"])

    def test_two_solos_then_clear_everything(self):
        dev = _mixed()
        dev.set_solo("line/ch1", "main")
        dev.set_solo("return/ch1", "main")
        wire = dev.last("main")
        self.assertEqual(wire["line/ch1"], -6.0)
        self.assertEqual(wire["return/ch1"], 0.0)
        self.assertIsNone(wire["line/ch2"])
        dev.set_solo("line/ch2", "mixb")
        dev.writes.clear()
        self.assertGreater(dev.clear_solo(), 0)
        self.assertEqual(dev.last("main")["line/ch2"], -3.0)
        self.assertEqual(dev.last("mixb")["return/ch1"], 0.0)
        self.assertFalse(any(dev.soloed(s, b) for s in dev.SOLO_SOURCES
                             for b in ("main", "mixa", "mixb")))

    def test_repeating_the_current_state_writes_nothing(self):
        dev = _mixed()
        dev.set_solo("line/ch1", "main")
        dev.writes.clear()
        self.assertEqual(dev.set_solo("line/ch1", "main"), 0)
        self.assertEqual(dev.set_solo("line/ch2", "main", False), 0)
        self.assertEqual(dev.clear_solo("mixa"), 0)
        self.assertEqual(dev.writes, [])

    def test_solo_is_never_shadowed(self):
        dev = _mixed()
        dev.set_solo("line/ch1", "main")
        dev.clear_solo()
        names = {entry.get("fn") for entry in dev._shadow.values()}
        self.assertFalse(names & {"set_solo", "clear_solo"})
        self.assertNotIn("set_solo", io24._SHADOWED)
        self.assertNotIn("clear_solo", io24._SHADOWED)

    def test_solo_survives_a_send_model_rebuild(self):
        # A shadow reload resets the send model. Solo must not vanish with it
        # and let a replayed send un-silence the rest of the bus.
        dev = _mixed()
        dev.set_solo("line/ch1", "main")
        dev._send_state = None
        dev.set_send_db("line/ch2", "main", -3.0)
        self.assertIsNone(dev.writes[-1][2])

    def test_line_ch3_is_never_soloed_or_written(self):
        dev = _mixed()
        with self.assertRaises(ValueError):
            dev.set_solo("line/ch3", "main")
        dev.set_solo("line/ch1", "main")
        dev.set_solo("line/ch1", "main", False)
        self.assertNotIn("line/ch3", {src for src, _bus, _db in dev.writes})


class _Toggle:
    def __init__(self, active=False):
        self.active = active

    def get_active(self):
        return self.active

    def set_active(self, value):
        self.active = bool(value)


class HostSoloTests(unittest.TestCase):
    def _window(self, dev):
        window = io24gtk.Win.__new__(io24gtk.Win)
        window._mix_mute = False
        window.mix_widgets = {}
        window.bus_master_widgets = {}
        window.solo_widgets = {("line/ch1", "main"): _Toggle(),
                               ("line/ch2", "main"): _Toggle()}
        submitted = []
        window.ctl = SimpleNamespace(dev=SimpleNamespace(dev=dev),
                                     submit=submitted.append)
        return window, submitted

    def test_the_toggle_submits_the_driver_solo(self):
        dev = _mixed()
        window, submitted = self._window(dev)
        with mock.patch.object(io24gtk.GLib, "timeout_add") as later:
            window._solo_toggled(_Toggle(True), "line/ch1", "main")
        self.assertEqual(len(submitted), 1)
        submitted[0](dev)
        self.assertTrue(dev.soloed("line/ch1", "main"))
        later.assert_called_once_with(140, window._sync_mix_widgets)

    def test_a_programmatic_sync_does_not_echo_a_write(self):
        window, submitted = self._window(_mixed())
        window._mix_mute = True
        window._solo_toggled(_Toggle(True), "line/ch1", "main")
        self.assertEqual(submitted, [])

    def test_sync_shows_the_driver_solo_state(self):
        dev = _mixed()
        dev.set_solo("line/ch2", "main")
        window, _submitted = self._window(dev)
        window._sync_mix_widgets()
        self.assertFalse(window.solo_widgets[("line/ch1", "main")].active)
        self.assertTrue(window.solo_widgets[("line/ch2", "main")].active)
        self.assertFalse(window._mix_mute)

    def test_closing_the_host_releases_every_solo(self):
        dev = _mixed()
        dev.set_solo("line/ch1", "main")
        ctl = SimpleNamespace(dev=SimpleNamespace(dev=dev,
                                                  lock=threading.Lock()))
        self.assertGreater(io24gtk.release_host_solo(ctl), 0)
        self.assertFalse(dev.soloed("line/ch1", "main"))
        self.assertEqual(dev.last("main")["line/ch2"], -3.0)

    def test_closing_without_a_device_is_harmless(self):
        self.assertEqual(io24gtk.release_host_solo(SimpleNamespace(dev=None)), 0)


if __name__ == "__main__":
    unittest.main()
