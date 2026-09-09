import copy
import hashlib
import json
from pathlib import Path
import unittest

import io24
from io24_preset_record import encode_preset_record


DELAY_GUID = "{98A527BA-2D6E-4B35-BB26-251EC081A067}"
FACTORY_SLAP_ECHO_SHA256 = (
    "a6c3294b62cfb3a46122a82c93514ea2aeb836280fb5d1e458707a78634f87eb"
)


def _factory_slap_echo_record():
    """The recovered complete factory record, excluding extraction metadata."""
    records = json.loads(
        (Path(__file__).parents[1] / "re" / "uc_factory_presets.json").read_text())
    record = dict(records[4])
    record.pop("_offset")
    return record


class _FactorySlapActionDevice:
    """Stateful USB boundary fake; it never opens a real device."""

    def __init__(self, *, channel2_slot=3, channel2_enabled=True):
        flags = 1 << 5  # Keep Channel 1 disabled as a preservation sentinel.
        if not channel2_enabled:
            flags |= 1 << 6
        self.params = {
            "input1Gain": 37.0,
            "input1SlotIndex": 0,
            "input1ProcessingChannel": 0,
            "input2Gain": 0.0,
            "input2SlotIndex": channel2_slot,
            "input2ProcessingChannel": 1,
            "flags": flags,
        }
        self.calls = []

    def read_params(self):
        self.calls.append(("read_params",))
        return copy.deepcopy(self.params)

    def save_device_slot(self, slot, record):
        self.calls.append(("save_device_slot", slot, copy.deepcopy(record)))
        return {"slot": slot, "fragments_sent": 1, "replies_received": 1}

    def set_preset_slot(self, channel, slot):
        self.calls.append(("set_preset_slot", channel, slot))
        self.params["input%dSlotIndex" % channel] = slot


class FactorySlapEchoActionTests(unittest.TestCase):
    def test_superseded_action_is_refused_before_device_access(self):
        """The old action cannot repeat a trial missing channel assignment."""
        device = _FactorySlapActionDevice()
        waits = []
        action = getattr(io24, "load_channel2_factory_slap_echo", None)
        self.assertIsNotNone(action, "factory Slap Echo diagnostic action is missing")

        record = _factory_slap_echo_record()
        encoded = encode_preset_record(record)
        self.assertEqual("Slap Echo", record["preset_name"])
        self.assertEqual({
            "__classid": DELAY_GUID,
            "on": 1,
            "time": 0.15,
            "feedback": 0.25,
            "mix": 0.5,
        }, {field: record["voicefx"][field] for field in (
            "__classid", "on", "time", "feedback", "mix")})
        self.assertEqual(850, len(encoded))
        self.assertEqual(FACTORY_SLAP_ECHO_SHA256,
                         hashlib.sha256(encoded).hexdigest())

        with self.assertRaisesRegex(
                io24.HostActionError, "omits Assign Voice FX"):
            action(device, record, sleep_fn=waits.append)

        self.assertEqual([], device.calls)
        self.assertEqual([], waits)

    def test_rejects_a_near_match_before_any_device_write(self):
        """Catches a diagnostic that overwrites slot 3 with an altered record."""
        device = _FactorySlapActionDevice()
        record = _factory_slap_echo_record()
        record["voicefx"]["time"] = 0.173
        action = getattr(io24, "load_channel2_factory_slap_echo", None)
        self.assertIsNotNone(action, "factory Slap Echo diagnostic action is missing")

        with self.assertRaisesRegex(ValueError, "canonical Slap Echo"):
            action(device, record, sleep_fn=lambda _seconds: None)

        self.assertEqual([], device.calls)


if __name__ == "__main__":
    unittest.main()
