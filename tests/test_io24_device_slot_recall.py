#!/usr/bin/env python3
"""Hardware-free contracts for physical device-slot recall.

Storing a slot body is not recalling it. Recall selects the requested physical
Fat Channel state; the current framing evidence does not establish block-201
FX activation, so these contracts make no such claim.

Nothing here opens USB.
"""

import unittest
from unittest import mock

import io24
import io24gtk
from io24_preset_record import DEVICE_SLOT_PAIRS


CH1_BYPASS_BIT = 1 << 5
CH2_BYPASS_BIT = 1 << 6


class _RecallDevice(io24.Io24):
    """Only the two wire primitives are faked; the recall logic above them
    is the real code, including the JaSt flag decode."""

    def __init__(self, *, ch1_processing=True, ch2_processing=True,
                 readable=True):
        flags = 0
        if not ch1_processing:
            flags |= CH1_BYPASS_BIT
        if not ch2_processing:
            flags |= CH2_BYPASS_BIT
        self._flags = flags
        self._readable = readable
        self.writes = []

    def read_params(self):
        if not self._readable:
            return None
        return {"flags": self._flags}

    def set_param(self, param_id, value, index=0, as_int=False):
        self.writes.append((param_id, value, index, as_int))


class DeviceSlotRecallTests(unittest.TestCase):
    def test_device_slot_pair_matches_the_registry_pairing(self):
        device = _RecallDevice()
        for channel, pair in DEVICE_SLOT_PAIRS.items():
            self.assertEqual(device.device_slot_pair(channel), pair)
        with self.assertRaises(ValueError):
            device.device_slot_pair(3)

    def test_recall_selects_then_enables_a_bypassed_channel(self):
        device = _RecallDevice(ch1_processing=False)
        report = device.recall_device_slot(1, 0)
        # Slot first, enable second: the other order would briefly run the
        # previously selected slot through a channel asked to be processing.
        self.assertEqual([write[0] for write in device.writes], [16, 4])
        self.assertEqual(device.writes[0], (16, 0, 0, True))
        self.assertEqual(device.writes[1][:3], (4, 1.0, 0))
        self.assertTrue(report["enable_asserted"])
        self.assertFalse(report["was_processing"])
        self.assertEqual(report["relative_slot"], 0)
        self.assertNotIn("voicefx_gate", report)
        self.assertEqual(report["audibility"], "UNPROVED")

    def test_recall_leaves_an_already_processing_channel_mix_alone(self):
        # Wire id 4 is a float whose nonzero value is write-only, so
        # re-asserting it would silently force a partial mix to full.
        device = _RecallDevice(ch2_processing=True)
        report = device.recall_device_slot(2, 3)
        self.assertEqual(device.writes, [(16, 3, 1, True)])
        self.assertFalse(report["enable_asserted"])
        self.assertTrue(report["was_processing"])
        self.assertEqual(report["relative_slot"], 1)

    def test_recall_refuses_a_cross_channel_slot_before_any_write(self):
        device = _RecallDevice()
        for channel, slot in ((1, 2), (1, 3), (2, 0), (2, 1)):
            with self.assertRaises(io24.HostActionError):
                device.recall_device_slot(channel, slot)
        self.assertEqual(device.writes, [])

    def test_recall_rejects_a_non_integer_slot_before_any_write(self):
        device = _RecallDevice()
        for slot in (True, 0.0, "0", None):
            with self.assertRaises((ValueError, io24.HostActionError)):
                device.recall_device_slot(1, slot)
        self.assertEqual(device.writes, [])

    def test_recall_fails_closed_when_processing_state_is_unreadable(self):
        device = _RecallDevice(readable=False)
        with self.assertRaises(io24.HostActionError):
            device.recall_device_slot(1, 0)
        self.assertEqual(device.writes, [])


class _Value:
    def __init__(self, value):
        self.value = value

    def get_selected(self):
        return int(self.value)


class _Row:
    def __init__(self):
        self.subtitle = None

    def set_subtitle(self, text):
        self.subtitle = text


class _Label:
    def __init__(self):
        self.text = None

    def set_text(self, text):
        self.text = text


class _Blocks:
    def __init__(self):
        self.selected = None

    def set_selected(self, index):
        self.selected = index


def _window(entries=()):
    window = io24gtk.Win.__new__(io24gtk.Win)
    window._observed_preset_slot = {}
    window._host_slot_entries = list(entries)
    window.preset_rows = {1: (_Row(), _Blocks()), 2: (_Row(), _Blocks())}
    window.messages = []
    window.say = window.messages.append
    window.PR = None
    window.host_preset_group = None
    window._host_preset_rows = []
    window.device_slot_registry = _Registry(entries)
    return window


class _Registry:
    """Stands in for the identity-bound on-disk registry."""

    def __init__(self, entries=()):
        self._entries = list(entries)

    def entries(self):
        return list(self._entries)

    def add(self, entry):
        self._entries.append(entry)


def _entry(slot, channel, name, fx_on):
    return {
        "slot": slot,
        "physical_channel": channel,
        "record": {"preset_name": name, "voicefx": {"on": 1 if fx_on else 0}},
        "device_identity": {"serial": "AB7C22200355"},
    }


class PresetRecallPresentationTests(unittest.TestCase):
    def test_unknown_slots_are_named_within_their_own_channel_pair(self):
        # Global index 2 is Channel 2's FIRST block, not "Slot 3".
        window = _window()
        self.assertEqual(window._slot_voicefx_intent(0)["name"], "Block 1")
        self.assertEqual(window._slot_voicefx_intent(1)["name"], "Block 2")
        self.assertEqual(window._slot_voicefx_intent(2)["name"], "Block 1")
        self.assertEqual(window._slot_voicefx_intent(3)["name"], "Block 2")

    def test_an_unnamed_recall_does_not_repeat_the_channel_twice(self):
        class Device:
            def recall_device_slot(self, channel, slot):
                return {"relative_slot": 0, "enable_asserted": False}

        class Ctl:
            dev = Device()

            def submit(self, fn):
                fn(self.dev)

        window = _window()
        window.ctl = Ctl()
        with mock.patch.object(io24gtk.GLib, "idle_add",
                               side_effect=lambda fn, *args: fn(*args)):
            window._slot_changed(2, 2)
        self.assertEqual(window.messages, ["Recalled Block 1 on Channel 2"])

class HostRecallWiringTests(unittest.TestCase):
    def test_selecting_a_block_recalls_rather_than_only_selecting(self):
        calls = []

        class Device:
            def recall_device_slot(self, channel, slot):
                calls.append((channel, slot))
                return {"relative_slot": slot, "enable_asserted": False}

        class Ctl:
            dev = Device()

            def submit(self, fn):
                fn(self.dev)

        window = _window(entries=[_entry(0, 1, "MAIN", True)])
        window.ctl = Ctl()
        with mock.patch.object(io24gtk.GLib, "idle_add",
                               side_effect=lambda fn, *args: fn(*args)):
            window._slot_changed(1, 0)

        self.assertEqual(calls, [(1, 0)])
        self.assertEqual(window.preset_rows[1][1].selected, 0)

    def test_known_recalled_record_sends_its_global_fx_state_once(self):
        window = _window(entries=[_entry(0, 1, "MAIN", True)])
        sent = []
        window._adopt_recalled_slot = lambda channel, slot: True
        window._follow_recall_processing = lambda channel, report: None
        window._push_fx = lambda: sent.append("fx")

        window._slot_recalled(
            1, 0, {"relative_slot": 0, "enable_asserted": False})

        self.assertEqual(sent, ["fx"])

    def test_recalling_a_host_preset_uses_its_own_slot_and_channel(self):
        calls = []

        class Device:
            def recall_device_slot(self, channel, slot):
                calls.append((channel, slot))
                return {"relative_slot": 1, "enable_asserted": True}

        class Ctl:
            dev = Device()

            def submit(self, fn):
                fn(self.dev)

        entry = _entry(1, 1, "B A S E", False)
        window = _window(entries=[entry])
        window.ctl = Ctl()
        with mock.patch.object(io24gtk.GLib, "idle_add",
                               side_effect=lambda fn, *args: fn(*args)):
            window._recall_host_preset(None, entry)

        self.assertEqual(calls, [(1, 1)])
        self.assertTrue(any("B A S E" in message for message in window.messages))
        # A bypassed channel that had to be enabled must say so.
        self.assertTrue(any("bypassed" in message for message in window.messages))

    def test_a_failed_recall_reports_the_failure(self):
        class Device:
            def recall_device_slot(self, channel, slot):
                raise io24.HostActionError("injected refusal")

        class Ctl:
            dev = Device()

            def submit(self, fn):
                fn(self.dev)

        window = _window()
        window.ctl = Ctl()
        with mock.patch.object(io24gtk.GLib, "idle_add",
                               side_effect=lambda fn, *args: fn(*args)):
            window._slot_changed(1, 0)

        self.assertTrue(any("injected refusal" in m for m in window.messages))

    def test_front_panel_slot_changes_are_observed_without_fx_claims(self):
        window = _window(entries=[_entry(0, 1, "MAIN", True),
                                  _entry(1, 1, "B A S E", False)])
        # First sighting is the resting index, not a load.
        self.assertEqual(window._observe_device_slot_recalls([0, 2]), [])
        # Someone presses the unit's Preset button.
        self.assertEqual(window._observe_device_slot_recalls([1, 2]), [1])
        # And back to the first record.
        self.assertEqual(window._observe_device_slot_recalls([0, 2]), [1])

    def test_repeated_identical_slot_reports_are_not_treated_as_recalls(self):
        window = _window(entries=[_entry(0, 1, "MAIN", True)])
        window._observe_device_slot_recalls([0, 2])
        for _ in range(5):
            self.assertEqual(window._observe_device_slot_recalls([0, 2]), [])

    def test_unit_presets_load_by_recall_on_their_own_channel(self):
        import inspect
        source = inspect.getsource(io24gtk.Win._load_device_entry)
        self.assertIn("_recall_host_preset", source)


if __name__ == "__main__":
    unittest.main()


class PresetSavingTests(unittest.TestCase):
    def test_saving_requires_a_name(self):
        window = io24gtk.Win.__new__(io24gtk.Win)
        window.slot_name_row = _Label()
        window.slot_name_row.get_text = lambda: "   "
        with self.assertRaises(io24.HostActionError) as caught:
            window._current_slot_name()
        self.assertIn("name this preset", str(caught.exception))

    def test_saving_rejects_a_name_too_long_for_the_record(self):
        window = io24gtk.Win.__new__(io24gtk.Win)
        window.slot_name_row = _Label()
        window.slot_name_row.get_text = lambda: "x" * 128
        with self.assertRaises(io24.HostActionError) as caught:
            window._current_slot_name()
        self.assertIn("too long", str(caught.exception))

    def test_a_named_preset_is_accepted_and_stripped(self):
        window = io24gtk.Win.__new__(io24gtk.Win)
        window.slot_name_row = _Label()
        window.slot_name_row.get_text = lambda: "  MY VOCAL  "
        self.assertEqual(window._current_slot_name(), "MY VOCAL")

    def _plan(self, activate):
        return {
            "name": "MY VOCAL",
            "target": 1,
            "relative_slot": 1,
            "slot": 1,
            "record": {"preset_name": "MY VOCAL",
                       "voicefx": {"on": 1}},
            "source": "current:channel1;base:Broadcast",
            "activate": activate,
        }

    def _run(self, activate, recall_fails=False):
        saved, recalled = [], []

        class Device:
            def save_known_device_slot(self, slot, record, registry, source):
                saved.append((slot, source))
                return {"transport": {"fragments_sent": 1,
                                      "replies_received": 1},
                        "registry": {"status": "WRITE_SENT_UNVERIFIED"}}

            def recall_device_slot(self, channel, slot):
                if recall_fails:
                    raise io24.HostActionError("injected recall failure")
                recalled.append((channel, slot))
                return {"relative_slot": 1, "enable_asserted": False}

        class Ctl:
            dev = Device()

            def submit(self, fn):
                fn(self.dev)

        window = _window(entries=[_entry(1, 1, "MY VOCAL", True)])
        window.ctl = Ctl()
        with mock.patch.object(io24gtk.GLib, "idle_add",
                               side_effect=lambda fn, *args: fn(*args)):
            window._queue_factory_slot_store(self._plan(activate))
        return window, saved, recalled

    def test_save_only_writes_the_body_and_does_not_recall(self):
        window, saved, recalled = self._run(activate=False)
        self.assertEqual(saved, [(1, "current:channel1;base:Broadcast")])
        self.assertEqual(recalled, [])
        self.assertTrue(any("Not loaded" in m for m in window.messages))

    def test_save_and_activate_writes_then_recalls(self):
        window, saved, recalled = self._run(activate=True)
        self.assertEqual(saved, [(1, "current:channel1;base:Broadcast")])
        self.assertEqual(recalled, [(1, 1)])

    def test_a_failed_recall_is_not_reported_as_a_failed_save(self):
        window, saved, recalled = self._run(activate=True, recall_fails=True)
        self.assertEqual(saved, [(1, "current:channel1;base:Broadcast")])
        self.assertEqual(recalled, [])
        joined = " ".join(window.messages)
        self.assertIn("Saved MY VOCAL", joined)
        self.assertIn("the recall failed", joined)

    def test_a_saved_preset_is_listed_without_restarting_the_host(self):
        window = _window()
        self.assertEqual(window._host_slot_entries, [])
        window.device_slot_registry.add(_entry(0, 1, "MAIN", True))
        window._refresh_host_slot_entries()
        self.assertEqual([e["record"]["preset_name"]
                          for e in window._host_slot_entries], ["MAIN"])
        self.assertEqual(window._slot_names_by_channel[1], ["MAIN"])


class RecalledBodyDisplayTests(unittest.TestCase):
    """A recall replaces the whole chain, so the controls must follow it —
    or say plainly that they cannot."""

    class _PR:
        def __init__(self, supported, reason):
            self._supported, self._reason = supported, reason
            self.adopted = []

        def direct_apply_support(self, record):
            return self._supported, self._reason

        def alternate_eq_view(self, record):
            return None

        def to_bands(self, record):
            raise AssertionError("must not be reached for an unsupported body")

    def test_an_unsupported_body_is_not_shown_and_says_why(self):
        # A body whose non-EQ sections the Host cannot model is not put on
        # the controls at all. (A Passive/Vintage EQ alone no longer blocks
        # this: the rest is shown and the EQ is listed read-only -- see
        # test_io24_vintage_eq_view.)
        window = _window(entries=[_entry(1, 1, "ODD", False)])
        window.PR = self._PR(
            False, "Compressor model is missing an unambiguous class id")
        self.assertFalse(window._adopt_recalled_slot(1, 1))
        joined = " ".join(window.messages)
        self.assertIn("missing an unambiguous class id", joined)
        self.assertIn("still show the previous sound", joined)

    def test_a_body_the_host_never_wrote_is_not_shown(self):
        window = _window()
        window.PR = self._PR(True, "exact direct-live mapping")
        self.assertFalse(window._adopt_recalled_slot(1, 0))
        self.assertEqual(window.messages, [])

    def test_a_supported_body_is_adopted_onto_the_controls(self):
        window = _window(entries=[_entry(0, 1, "MAIN", True)])
        window.PR = self._PR(True, "exact direct-live mapping")
        seen = []
        window._adopt_preset_record = \
            lambda record, chans, fx_channel=None: seen.append(
                (record["preset_name"], chans, fx_channel))
        self.assertTrue(window._adopt_recalled_slot(1, 0))
        self.assertEqual(seen, [("MAIN", (1,), 1)])
