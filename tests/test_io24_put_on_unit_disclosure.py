#!/usr/bin/env python3
"""The Presets menu exposes the repaired firmware-native slot writer."""

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import io24
import io24gtk
from io24_preset_record import DeviceSlotRegistry

ROOT = Path(__file__).resolve().parents[1]


class PutOnUnitDisclosureTests(unittest.TestCase):
    def test_the_menu_does_not_disable_put_on_unit(self):
        self.assertIsNone(io24gtk.PUT_ON_UNIT_UNAVAILABLE)

    def test_known_slot_write_sends_native_bytes_then_commits_the_receipt(self):
        scene = NativeScene.standard()
        sent = []
        device = object.__new__(io24.Io24)
        device.dev = SimpleNamespace(
            serial_number="TEST-IO24-001", idVendor=0x194f,
            idProduct=0x0422, bcdDevice=0x0128)
        device.save_device_slot = lambda slot, body: (
            sent.append((slot, body)) or {
                "slot": slot, "fragments_sent": 1, "replies_received": 1,
            })
        with tempfile.TemporaryDirectory() as directory:
            registry = DeviceSlotRegistry(Path(directory) / "slots.json")

            result = device.save_known_device_slot(
                1, scene, registry, "user:Test",
                sample_rate_hz=96000.0)

            saved = registry.get(1, device_identity=device._device_slot_identity())
        self.assertEqual(sent[0][0], 1)
        self.assertEqual(sent[0][1][:4], b"\x02\x00\x00\x00")
        self.assertEqual(result["registry"], saved)
        self.assertEqual(saved["body_format"], "firmware-native-v2")
        self.assertEqual(saved["native_sha256"], result["native_sha256"])


class NativeScene:
    @staticmethod
    def standard():
        from tests.test_io24_native_stat import NativeStatTests
        return NativeStatTests._standard_scene()
