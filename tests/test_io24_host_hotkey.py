#!/usr/bin/env python3
"""Hardware-free contract for the source-bound momentary Host Hot Key."""

import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

import io24
import io24gtk


def _call(fn, **kwargs):
    return {"fn": fn, "kwargs": kwargs}


def _full_snapshot(ch1_gain=8.0, ch2_gain=18.0, owner=2, fx_time=0.17,
                   ch1_mix=1.0, ch2_mix=0.0):
    return {
        "version": 1,
        "live": {
            "input1Gain": ch1_gain,
            "input2Gain": ch2_gain,
            "input1PhantomPower": False,
            "input2PhantomPower": True,
            "hpVolume": 0.4,
        },
        "calls": {
            "ch1-slot": _call("set_preset_slot", channel=1, slot=1),
            "ch1-mix": _call("set_fx_mix", channel=1, value=ch1_mix),
            "ch1-eq": _call(
                "set_eq_band", channel=1, band=0, shape="peaking",
                freq_hz=120.0, gain_db=2.0, q=0.7),
            "ch1-send": _call(
                "set_send_db", source="line/ch1", bus="mixa", gain_db=-3.0),
            "ch2-slot": _call("set_preset_slot", channel=2, slot=3),
            "ch2-mix": _call("set_fx_mix", channel=2, value=ch2_mix),
            "ch2-eq": _call(
                "set_eq_band", channel=2, band=0, shape="peaking",
                freq_hz=240.0, gain_db=-4.0, q=1.2),
            "ch2-send": _call(
                "set_send_db", source="line/ch2", bus="mixb", gain_db=-9.0),
            "owner": _call(
                "set_processing_channel", channel=1, source_input=owner),
            "voicefx": _call(
                "set_fx", model="delay", on=True, time_s=fx_time,
                feedback=0.42, mix=0.6),
            "global": _call("set_bus_master", bus="main", gain_db=-6.0),
        },
    }


class _Device:
    def __init__(self, snapshot):
        self.calls = []
        self.fail_on = None
        self.fail_once = False
        self.state = {}
        self.current = snapshot

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, snapshot):
        self._current = copy.deepcopy(snapshot)
        calls = self._current["calls"].values()
        slots = {call["kwargs"]["channel"]: call["kwargs"]["slot"]
                 for call in calls if call["fn"] == "set_preset_slot"}
        enabled = {call["kwargs"]["channel"]:
                   float(call["kwargs"]["value"]) != 0.0
                   for call in calls if call["fn"] == "set_fx_mix"}
        owner = next((call["kwargs"]["source_input"] for call in calls
                      if call["fn"] == "set_processing_channel"), 1)
        flags = sum(1 << (4 + ch) for ch in (1, 2)
                    if not enabled.get(ch, True))
        self.params = {
            "input1Gain": self._current["live"]["input1Gain"],
            "input2Gain": self._current["live"]["input2Gain"],
            "input1PhantomPower": self._current["live"]["input1PhantomPower"],
            "input2PhantomPower": self._current["live"]["input2PhantomPower"],
            "input1SlotIndex": slots.get(1, 0),
            "input2SlotIndex": slots.get(2, 2),
            "input1ProcessingChannel": owner - 1,
            "input2ProcessingChannel": 1 if owner == 1 else 0,
            "flags": flags,
        }
        self.state = {
            "eq": {call["kwargs"]["channel"]: copy.deepcopy(call["kwargs"])
                   for call in calls if call["fn"] == "set_eq_band"},
            "send": {call["kwargs"]["source"]: copy.deepcopy(call["kwargs"])
                     for call in calls if call["fn"] == "set_send_db"},
            "fx": next((copy.deepcopy(call["kwargs"]) for call in calls
                        if call["fn"] == "set_fx"), None),
        }

    def snapshot(self):
        return copy.deepcopy(self.current)

    def read_params(self):
        return copy.deepcopy(self.params)

    def _record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        if self.fail_on == name:
            if self.fail_once:
                self.fail_on = None
            raise RuntimeError("injected %s failure" % name)

    def set_gain(self, channel, db):
        self._record("set_gain", channel, db)
        self.params["input%dGain" % channel] = db
        self._current["live"]["input%dGain" % channel] = db

    def set_phantom(self, channel, on):
        self._record("set_phantom", channel, on)

        self.params["input%dPhantomPower" % channel] = bool(on)
        self._current["live"]["input%dPhantomPower" % channel] = bool(on)

    def set_preset_slot(self, channel, slot):
        self._record("set_preset_slot", channel=channel, slot=slot)
        self.params["input%dSlotIndex" % channel] = slot

    def set_preset_enabled(self, channel, on):
        self._record("set_preset_enabled", channel=channel, on=on)
        bit = 4 + channel
        if on:
            self.params["flags"] &= ~(1 << bit)
        else:
            self.params["flags"] |= 1 << bit

    def set_fx_mix(self, channel, value):
        self._record("set_fx_mix", channel=channel, value=value)
        bit = 4 + channel
        if float(value) != 0.0:
            self.params["flags"] &= ~(1 << bit)
        else:
            self.params["flags"] |= 1 << bit

    def set_processing_channel(self, channel, source_input):
        self._record("set_processing_channel", channel=channel,
                     source_input=source_input)
        self.params["input1ProcessingChannel"] = source_input - 1
        self.params["input2ProcessingChannel"] = 1 if source_input == 1 else 0

    def set_eq_band(self, **kwargs):
        self._record("set_eq_band", **kwargs)
        self.state["eq"][kwargs["channel"]] = copy.deepcopy(kwargs)

    def set_send_db(self, **kwargs):
        self._record("set_send_db", **kwargs)
        self.state["send"][kwargs["source"]] = copy.deepcopy(kwargs)

    def set_fx(self, **kwargs):
        self._record("set_fx", **kwargs)
        self.state["fx"] = copy.deepcopy(kwargs)

    def __getattr__(self, name):
        if name.startswith("set_") or name in {
                "gate_off", "compressor_off", "output_delay_off"}:
            return lambda *args, **kwargs: self._record(name, *args, **kwargs)
        raise AttributeError(name)


class HostHotKeyAvailabilityTests(unittest.TestCase):
    def test_source_bound_host_hotkey_session_is_available(self):
        self.assertTrue(
            hasattr(io24, "HostHotKeySession"),
            "source-bound HostHotKeySession is not implemented")


@unittest.skipUnless(hasattr(io24, "HostHotKeySession"),
                     "HostHotKeySession is the missing production feature")
class HostHotKeyTests(unittest.TestCase):
    def test_press_release_filters_one_channel_orders_and_is_idempotent(self):
        target = _full_snapshot(ch1_gain=8.0, ch2_gain=18.0, owner=2)
        normal = _full_snapshot(ch1_gain=1.5, ch2_gain=27.0, owner=2)
        dev = _Device(target)
        session = io24.HostHotKeySession()

        captured = session.capture(dev, 1)
        dev.current = normal
        pressed = session.press(dev, 1)
        first_press_calls = list(dev.calls)
        repeated = session.press(dev, 1)

        self.assertEqual(captured["channel"], 1)
        self.assertEqual(set(captured["live"]),
                         {"input1Gain", "input1PhantomPower"})
        self.assertEqual(
            [call[0] for call in first_press_calls],
            ["set_preset_slot", "set_gain", "set_phantom", "set_fx_mix",
             "set_eq_band", "set_send_db"])
        self.assertTrue(all(
            (not args or args[0] != 2) and
            kwargs.get("channel") != 2 and
            kwargs.get("source") != "line/ch2"
            for _name, args, kwargs in first_press_calls))
        self.assertEqual(pressed["status"], "ACTIVE")
        self.assertEqual(repeated["status"], "ALREADY_ACTIVE")
        self.assertEqual(dev.calls, first_press_calls)

        released = session.release(dev, 1)
        release_calls = dev.calls[len(first_press_calls):]
        repeated_release = session.release(dev, 1)

        self.assertEqual(released["status"], "INACTIVE")
        self.assertEqual(repeated_release["status"], "ALREADY_INACTIVE")
        self.assertEqual(release_calls[1], ("set_gain", (1, 1.5), {}))
        self.assertEqual(len(dev.calls), len(first_press_calls) * 2)

    def test_voicefx_is_replayed_only_for_its_selected_physical_owner(self):
        target = _full_snapshot(owner=2)
        dev = _Device(target)
        session = io24.HostHotKeySession()

        ch1 = session.capture(dev, 1)
        ch2 = session.capture(dev, 2)
        self.assertNotIn("set_fx", {c["fn"] for c in ch1["calls"].values()})
        self.assertIn("set_fx", {c["fn"] for c in ch2["calls"].values()})

        dev.current = _full_snapshot(ch2_gain=7.0, owner=2)
        session.press(dev, 2)

        names = [call[0] for call in dev.calls]
        self.assertLess(names.index("set_processing_channel"),
                        names.index("set_fx"))
        self.assertFalse(any(
            ((args and args[0] == 1) or kwargs.get("channel") == 1 or
             kwargs.get("source") == "line/ch1") and
            name not in {"set_processing_channel"}
            for name, args, kwargs in dev.calls))

    def test_invalid_assigned_snapshots_fail_before_any_device_setter(self):
        valid = io24.HostHotKeySession().capture(
            _Device(_full_snapshot(owner=1)), 1)
        cases = {}

        incomplete = copy.deepcopy(valid)
        del incomplete["live"]["input1Gain"]
        cases["incomplete"] = incomplete

        malformed = copy.deepcopy(valid)
        eq_key = next(key for key, call in malformed["calls"].items()
                      if call["fn"] == "set_eq_band")
        malformed["calls"][eq_key]["kwargs"] = []
        cases["malformed"] = malformed

        cross_channel = copy.deepcopy(valid)
        cross_channel["calls"]["foreign"] = _call(
            "set_preset_slot", channel=2, slot=2)
        cases["cross-channel"] = cross_channel

        cross_live = copy.deepcopy(valid)
        cross_live["live"]["input2Gain"] = 12.0
        cases["cross-channel readable"] = cross_live

        unknown = copy.deepcopy(valid)
        unknown["calls"]["unknown"] = _call(
            "set_preset_hotkey", channel=1, on=True)
        cases["unknown setter"] = unknown

        alternate = copy.deepcopy(valid)
        alternate["calls"]["alternate"] = _call(
            "set_eq_band", channel=1, band=0, model="passive",
            shape="peaking", freq_hz=120.0, gain_db=1.0, q=0.7)
        cases["alternate EQ"] = alternate

        raw_alternate = copy.deepcopy(valid)
        raw_alternate["eq"] = {"__classid": "Passive"}
        cases["raw alternate EQ"] = raw_alternate

        for label, snapshot in cases.items():
            with self.subTest(label=label):
                dev = _Device(_full_snapshot(owner=1))
                session = io24.HostHotKeySession()
                with self.assertRaises((ValueError, io24.HostActionError)):
                    session.assign(1, snapshot)
                self.assertEqual(dev.calls, [])

    def test_failed_press_rolls_back_every_partial_mutation(self):
        target = _full_snapshot(ch1_gain=19.0, owner=1, fx_time=0.11)
        normal = _full_snapshot(ch1_gain=3.0, owner=2, fx_time=0.77)
        dev = _Device(target)
        session = io24.HostHotKeySession()
        session.capture(dev, 1)
        dev.current = normal
        baseline_params = copy.deepcopy(dev.params)
        baseline_state = copy.deepcopy(dev.state)
        dev.fail_on = "set_send_db"
        dev.fail_once = True

        with self.assertRaisesRegex(RuntimeError, "injected set_send_db failure") \
                as caught:
            session.press(dev, 1)

        self.assertEqual(caught.exception.hotkey_rollback, "RESTORED")
        self.assertEqual(dev.params, baseline_params)
        self.assertEqual(dev.state, baseline_state)
        self.assertEqual(dev.state["fx"]["time_s"], 0.77)
        self.assertFalse(session.is_active(1))

    def test_normal_capture_overlays_readable_slot_enable_and_owner(self):
        target = _full_snapshot(owner=1)
        stale_normal = _full_snapshot(owner=2)
        dev = _Device(target)
        session = io24.HostHotKeySession()
        session.capture(dev, 1)
        dev.current = stale_normal
        dev.params["input1SlotIndex"] = 0
        dev.params["flags"] |= 1 << 5

        session.press(dev, 1)
        session.release(dev, 1)

        self.assertEqual(dev.params["input1SlotIndex"], 0)
        self.assertTrue(dev.params["flags"] >> 5 & 1)
        self.assertEqual(dev.params["input1ProcessingChannel"], 1)
        self.assertEqual(dev.params["input2ProcessingChannel"], 0)

    def test_capture_preserves_exact_positive_processing_mix(self):
        dev = _Device(_full_snapshot(owner=1, ch1_mix=0.35))

        captured = io24.HostHotKeySession().capture(dev, 1)

        mixes = [call for call in captured["calls"].values()
                 if call["fn"] == "set_fx_mix"]
        self.assertEqual(mixes, [
            _call("set_fx_mix", channel=1, value=0.35)])

    def test_capture_refuses_enabled_channel_without_exact_mix(self):
        snapshot = _full_snapshot(owner=1)
        del snapshot["calls"]["ch1-mix"]
        dev = _Device(snapshot)
        dev.params["flags"] &= ~(1 << 5)

        with self.assertRaisesRegex(
                io24.HostActionError, "exact processing mix is unknown"):
            io24.HostHotKeySession().capture(dev, 1)

    def test_release_restores_prior_voicefx_owner_in_both_directions(self):
        for channel, held_owner, normal_owner in ((1, 1, 2), (2, 2, 1)):
            with self.subTest(channel=channel):
                dev = _Device(_full_snapshot(owner=held_owner, fx_time=0.11))
                session = io24.HostHotKeySession()
                session.capture(dev, channel)
                dev.current = _full_snapshot(owner=normal_owner, fx_time=0.77)

                session.press(dev, channel)
                session.release(dev, channel)

                owners = [kwargs["source_input"]
                          for name, _args, kwargs in dev.calls
                          if name == "set_processing_channel"]
                self.assertEqual(owners, [held_owner, normal_owner])
                fx_times = [kwargs["time_s"]
                            for name, _args, kwargs in dev.calls
                            if name == "set_fx"]
                self.assertEqual(fx_times, [0.11, 0.77])
                self.assertEqual(dev.state["fx"]["time_s"], 0.77)
                self.assertEqual(dev.params["input1ProcessingChannel"],
                                 normal_owner - 1)

    def test_ownership_change_refuses_unknown_or_incoherent_prior_fx(self):
        target = _full_snapshot(owner=1, fx_time=0.11)
        for case in ("missing", "owner-drift"):
            with self.subTest(case=case):
                dev = _Device(target)
                session = io24.HostHotKeySession()
                session.capture(dev, 1)
                normal = _full_snapshot(owner=2, fx_time=0.77)
                if case == "missing":
                    del normal["calls"]["voicefx"]
                    dev.current = normal
                else:
                    dev.current = _full_snapshot(owner=1, fx_time=0.77)
                    dev.params["input1ProcessingChannel"] = 1
                    dev.params["input2ProcessingChannel"] = 0
                dev.calls.clear()

                with self.assertRaisesRegex(
                        io24.HostActionError,
                        "complete known prior-owner VoiceFX state"):
                    session.press(dev, 1)

                self.assertEqual(dev.calls, [])
                self.assertFalse(session.is_active(1))

    def test_matrix_rows_trace_the_host_hotkey_session_api(self):
        matrix = json.loads((Path(__file__).parents[1] / "runs" /
            "20260906T165749-0700-host-live-routing-repair" /
            "PARAMETER-VERIFICATION-MATRIX.json").read_text())
        rows = {row["id"]: row for row in matrix["rows"]}

        self.assertEqual(rows["state.hotkey_ch1"]["api"], [
            "HostHotKeySession.assign", "HostHotKeySession.capture",
            "HostHotKeySession.press"])
        self.assertEqual(rows["state.hotkey_ch2"]["api"], [
            "HostHotKeySession.assign", "HostHotKeySession.capture",
            "HostHotKeySession.press"])
        self.assertEqual(rows["state.hotkey_release"]["api"], [
            "HostHotKeySession.release"])

    def test_programmatic_gtk_synchronization_cannot_capture_or_toggle(self):
        queued = []
        host = SimpleNamespace(
            _hotkey_sync=True,
            ctl=SimpleNamespace(submit=queued.append),
            hotkeys=io24.HostHotKeySession(),
            say=lambda _message: None,
        )

        io24gtk.Win._hotkey_capture(host, None, 1)
        io24gtk.Win._hotkey_pressed(host, None, 1, 0.0, 0.0, 1)
        io24gtk.Win._hotkey_released(host, None, 1, 0.0, 0.0, 1)

        self.assertEqual(queued, [])


if __name__ == "__main__":
    unittest.main()
