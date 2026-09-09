import copy
import hashlib
import unittest

import io24
import io24_dsp


class _LinkedRecallDevice:
    """Stateful device boundary fake; it never opens hardware."""

    def __init__(self, *, linked=False, channel1_slot=0, fail_on_slot3=False,
                 input2_level=0.001, fail_gate_off=False,
                 fail_gate_on_call=None):
        self.params = {
            "input1Gain": 37.0,
            "input1SlotIndex": channel1_slot,
            "input1ProcessingChannel": 0,
            "input2Gain": 0.0,
            "input2SlotIndex": 3,
            "input2ProcessingChannel": 1,
            "input1Level": 0.0,
            "input2Level": input2_level,
            "flags": 0x1A1 | ((1 << 12) if linked else 0),
        }
        self.fail_on_slot3 = fail_on_slot3
        self.fail_gate_off = fail_gate_off
        self.fail_gate_on_call = fail_gate_on_call
        self.gate_on_calls = 0
        self.calls = []

    def read_params(self):
        self.calls.append(("read_params",))
        return copy.deepcopy(self.params)

    def set_preset_slot(self, channel, slot):
        self.calls.append(("set_preset_slot", channel, slot))
        if slot == 3 and self.fail_on_slot3:
            raise RuntimeError("injected slot-3 failure")
        self.params["input%dSlotIndex" % channel] = slot

    def set_channel_link(self, on):
        self.calls.append(("set_channel_link", bool(on)))
        if on:
            self.params["flags"] |= 1 << 12
        else:
            self.params["flags"] &= ~(1 << 12)

    def set_gate(self, channel, *, on, threshold_db, range_db, attack_s,
                 release_s, keyfilter_hz, expander, keylisten, instance, fs):
        kwargs = {
            "threshold_db": threshold_db,
            "range_db": range_db,
            "attack_s": attack_s,
            "release_s": release_s,
            "keyfilter_hz": keyfilter_hz,
            "expander": expander,
            "keylisten": keylisten,
            "instance": instance,
            "fs": fs,
        }
        indexes = (0, 1) if instance is None else (instance,)
        hashes = tuple(hashlib.sha256(io24_dsp.gate_blob(
            index, on=on, threshold_db=threshold_db, range_db=range_db,
            attack_s=attack_s, release_s=release_s,
            keyfilter_hz=keyfilter_hz, expander=expander,
            keylisten=keylisten, fs=fs)).hexdigest() for index in indexes)
        self.calls.append(("set_gate", channel, bool(on), kwargs, hashes))
        if on:
            self.gate_on_calls += 1
            if self.gate_on_calls == self.fail_gate_on_call:
                raise RuntimeError("injected gate restore failure")
        elif self.fail_gate_off:
            raise RuntimeError("injected gate-off failure")


class LinkedRecallActionTests(unittest.TestCase):
    def _action(self):
        action = getattr(io24, "recall_channel2_slot3_while_linked", None)
        self.assertIsNotNone(action, "bounded linked-recall action is missing")
        return action

    def _probe(self):
        action = getattr(io24, "probe_channel2_slot3_with_gate_transition", None)
        self.assertIsNotNone(action, "bounded gate-transition action is missing")
        return action

    def test_cycles_channel2_under_link_and_finishes_unlinked(self):
        """Catches an unlinked slot-3 recall or failure to restore link off."""
        device = _LinkedRecallDevice()
        waits = []
        events = []

        result = self._action()(
            device, sleep_fn=waits.append, event_fn=events.append)

        self.assertEqual("LINKED_CHANNEL2_SLOT3_RECALL_COMPLETED", result["status"])
        self.assertFalse(result["final_state"]["channel_linked"])
        self.assertEqual(3, result["final_state"]["input2_slot_index"])
        self.assertTrue(result["channel1_unchanged"])
        self.assertEqual(
            [
                ("read_params",),
                ("set_preset_slot", 2, 2),
                ("read_params",),
                ("set_channel_link", True),
                ("read_params",),
                ("set_preset_slot", 2, 3),
                ("read_params",),
                ("set_channel_link", False),
                ("read_params",),
            ],
            device.calls,
        )
        self.assertEqual(
            [
                "baseline_confirmed",
                "channel2_slot2_confirmed",
                "link_on_confirmed",
                "channel2_slot3_confirmed",
                "link_off_confirmed",
            ],
            events,
        )
        self.assertEqual([0.5, 3.0, 0.5, 0.5, 5.0, 0.5], waits)

    def test_link_is_cleared_when_linked_slot3_recall_raises(self):
        """Catches an exception path that strands the device stereo-linked."""
        device = _LinkedRecallDevice(fail_on_slot3=True)

        with self.assertRaisesRegex(RuntimeError, "injected slot-3 failure"):
            self._action()(device, sleep_fn=lambda _seconds: None)

        self.assertEqual(("set_channel_link", False), device.calls[-2])
        self.assertEqual(("read_params",), device.calls[-1])
        self.assertFalse(device.params["flags"] >> 12 & 1)

    def test_wrong_baseline_refuses_before_any_write(self):
        """Catches a trial that runs against an already-linked baseline."""
        device = _LinkedRecallDevice(linked=True)

        with self.assertRaisesRegex(io24.HostActionError, "must start unlinked"):
            self._action()(device, sleep_fn=lambda _seconds: None)

        self.assertEqual([("read_params",)], device.calls)

    def test_gate_transition_uses_exact_factory_blobs_and_restores_link(self):
        """Catches wrong gate bytes, wrong channel, or unsafe cleanup order."""
        device = _LinkedRecallDevice()
        waits = []
        events = []

        result = self._probe()(
            device, sleep_fn=waits.append, event_fn=events.append)

        gate_calls = [call for call in device.calls if call[0] == "set_gate"]
        self.assertEqual([True, False, True], [call[2] for call in gate_calls])
        self.assertTrue(all(call[1] == 2 for call in gate_calls))
        expected_kwargs = {
            "threshold_db": -47.5,
            "range_db": -60.0,
            "attack_s": 0.025,
            "release_s": 0.7,
            "keyfilter_hz": 730.000244,
            "expander": True,
            "keylisten": False,
            "instance": None,
            "fs": 48000.0,
        }
        self.assertTrue(all(call[3] == expected_kwargs for call in gate_calls))
        self.assertEqual(
            [
                (
                    "e6efb8cf74415621a6160091ff06b1e0ef07a465eb03c2dc2863b053b83f73ee",
                    "ed052c4ac25cc0edb837d0a0c68c245869980e66a9a6a347888afc674f67c31a",
                ),
                (
                    "4c4231f9a63267d6b42a7723099b538f53bdcb786ca72de2e9034705b1d2200c",
                    "028d515d874947adebc745078ea6f83b7b03764dc1013da588952ffe98bcdbac",
                ),
                (
                    "e6efb8cf74415621a6160091ff06b1e0ef07a465eb03c2dc2863b053b83f73ee",
                    "ed052c4ac25cc0edb837d0a0c68c245869980e66a9a6a347888afc674f67c31a",
                ),
            ],
            [call[4] for call in gate_calls],
        )
        self.assertEqual(
            [
                "baseline_confirmed",
                "channel2_slot2_confirmed",
                "link_on_confirmed",
                "channel2_slot3_confirmed",
                "factory_gate_on_sent",
                "factory_gate_off_sent",
                "factory_gate_restored",
                "link_off_confirmed",
            ],
            events,
        )
        self.assertEqual([0.5, 1.0, 0.5, 0.5, 1.5, 3.0, 1.0, 0.5], waits)
        self.assertEqual("LINKED_CHANNEL2_GATE_TRANSITION_COMPLETED",
                         result["status"])
        self.assertEqual("WRITE_SENT_NOT_READABLE", result["gate_restoration"])
        self.assertFalse(result["final_state"]["channel_linked"])
        self.assertTrue(result["channel1_unchanged"])
        self.assertEqual(("set_channel_link", False), device.calls[-2])

    def test_input_above_probe_ceiling_blocks_before_any_gate_write(self):
        """Catches a gate opening while a listening-level source is present."""
        device = _LinkedRecallDevice(input2_level=0.02)

        with self.assertRaisesRegex(io24.HostActionError, "probe ceiling"):
            self._probe()(device, sleep_fn=lambda _seconds: None)

        self.assertFalse(any(call[0] == "set_gate" for call in device.calls))
        self.assertEqual(("set_channel_link", False), device.calls[-2])
        self.assertFalse(device.params["flags"] >> 12 & 1)

    def test_gate_off_failure_still_restores_factory_gate_then_unlinks(self):
        """Catches loss of either cleanup write after a gate-off exception."""
        device = _LinkedRecallDevice(fail_gate_off=True)

        with self.assertRaisesRegex(RuntimeError, "injected gate-off failure"):
            self._probe()(device, sleep_fn=lambda _seconds: None)

        gate_states = [call[2] for call in device.calls if call[0] == "set_gate"]
        self.assertEqual([True, False, True], gate_states)
        self.assertEqual(("set_channel_link", False), device.calls[-2])
        self.assertFalse(device.params["flags"] >> 12 & 1)

    def test_gate_restore_failure_still_unlinks_and_reports_cleanup_failure(self):
        """Catches a masked gate restoration failure or stranded stereo link."""
        device = _LinkedRecallDevice(fail_gate_on_call=2)

        with self.assertRaisesRegex(io24.HostActionError,
                                    "factory gate restoration failed"):
            self._probe()(device, sleep_fn=lambda _seconds: None)

        self.assertEqual(("set_channel_link", False), device.calls[-2])
        self.assertEqual(("read_params",), device.calls[-1])
        self.assertFalse(device.params["flags"] >> 12 & 1)


if __name__ == "__main__":
    unittest.main()
