#!/usr/bin/env python3
"""Behavioral contracts for the CP34 exact read-only USB preflight."""

import importlib.util
import os
import struct
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "cp34_readonly_preflight.py")
SPEC = importlib.util.spec_from_file_location("cp34_readonly_preflight", SCRIPT)
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


def _int_as_float(value):
    return struct.unpack("<f", struct.pack("<i", value))[0]


def _jast_reply(slot1=0, slot2=2, flags=0):
    payload = bytearray(PREFLIGHT.DATA_START + 51 * 4)
    struct.pack_into("<I", payload, 0, PREFLIGHT.RPLY)
    for slot, value in ((40, _int_as_float(slot1)),
                        (41, _int_as_float(slot2)),
                        (42, _int_as_float(flags))):
        struct.pack_into("<f", payload, PREFLIGHT.DATA_START + slot * 4, value)
    frame = struct.pack("<H", len(payload) + 8) + b"\x01\x01\x00\x00\x00\x00"
    return frame + payload


class _Endpoint:
    def __init__(self, address, replies=()):
        self.bEndpointAddress = address
        self.replies = list(replies)
        self.writes = []

    def write(self, frame, timeout):
        self.writes.append((bytes(frame), timeout))
        return len(frame)

    def read(self, size, timeout):
        if not self.replies:
            raise AssertionError("read without a prepared reply")
        return self.replies.pop(0)


class _Configuration:
    def __init__(self, interface):
        self.interface = interface

    def __getitem__(self, key):
        if key != (PREFLIGHT.IFACE, PREFLIGHT.ALTSETTING):
            raise AssertionError("wrong interface lookup: %r" % (key,))
        return self.interface


class _Device:
    def __init__(self, serial, input_endpoint, output_endpoint):
        self.serial_number = serial
        self.bcdDevice = 0x0128
        self._configuration = _Configuration((input_endpoint, output_endpoint))
        self.altsettings = []

    def set_interface_altsetting(self, interface, alternate_setting):
        self.altsettings.append((interface, alternate_setting))

    def get_active_configuration(self):
        return self._configuration


class _Core:
    def __init__(self, device):
        self.device = device
        self.find_calls = []

    def find(self, **kwargs):
        self.find_calls.append(kwargs)
        return self.device


class _Util:
    def __init__(self):
        self.claims = []
        self.releases = []

    def claim_interface(self, device, interface):
        self.claims.append((device, interface))

    def release_interface(self, device, interface):
        self.releases.append((device, interface))

    @staticmethod
    def find_descriptor(interface, custom_match):
        matches = [endpoint for endpoint in interface if custom_match(endpoint)]
        return matches[0] if matches else None


class ReadOnlyPreflightTests(unittest.TestCase):
    def _fixture(self, serial="AB7C22200355"):
        input_endpoint = _Endpoint(
            PREFLIGHT.EP_IN,
            [_jast_reply(flags=1 << 5), _jast_reply(flags=1 << 5)])
        output_endpoint = _Endpoint(PREFLIGHT.EP_OUT)
        device = _Device(serial, input_endpoint, output_endpoint)
        return _Core(device), _Util(), device, input_endpoint, output_endpoint

    def test_battery_floor_blocks_before_usb_enumeration(self):
        core, util, _, _, _ = self._fixture()

        result = PREFLIGHT.run_preflight(core, util, 10, "AB7C22200355")

        self.assertEqual(result["status"], "BLOCKED_BATTERY")
        self.assertEqual(core.find_calls, [])
        self.assertEqual(util.claims, [])

    def test_wrong_serial_blocks_before_interface_claim(self):
        core, util, _, _, _ = self._fixture(serial="WRONG")

        result = PREFLIGHT.run_preflight(core, util, 76, "AB7C22200355")

        self.assertEqual(result["status"], "IDENTITY_MISMATCH")
        self.assertEqual(util.claims, [])
        self.assertEqual(util.releases, [])

    def test_safe_preflight_uses_only_two_getp_jast_reads_and_releases_claim(self):
        core, util, device, input_endpoint, output_endpoint = self._fixture()

        result = PREFLIGHT.run_preflight(core, util, 76, "AB7C22200355")

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["battery_percent"], 76)
        self.assertEqual(result["device"]["serial"], "AB7C22200355")
        self.assertEqual(device.altsettings, [(PREFLIGHT.IFACE, PREFLIGHT.ALTSETTING)])
        self.assertEqual(len(util.claims), 1)
        self.assertEqual(len(util.releases), 1)
        self.assertEqual(len(input_endpoint.replies), 0)
        self.assertEqual(len(output_endpoint.writes), 2)
        self.assertEqual(len(result["jast_reads"]), 2)
        self.assertEqual(result["flags_word"], 1 << 5)
        self.assertFalse(result["channel_linked"])
        self.assertFalse(result["input1_preset_enabled"])
        self.assertTrue(result["input2_preset_enabled"])
        self.assertEqual(result["input1_slot_index"], 0)
        self.assertEqual(result["input2_slot_index"], 2)
        for sequence, (frame, timeout) in enumerate(output_endpoint.writes, 1):
            self.assertEqual(timeout, 2000)
            self.assertEqual(frame[2:4], b"\x01\x01")
            self.assertEqual(frame[4], sequence)
            self.assertEqual(struct.unpack_from("<III", frame, 8),
                             (PREFLIGHT.GETP, PREFLIGHT.APPL, 0))
            self.assertEqual(struct.unpack_from("<I", frame, 20)[0],
                             PREFLIGHT.JAST)
            self.assertNotEqual(struct.unpack_from("<I", frame, 8)[0],
                                PREFLIGHT.SETP)

    def test_readonly_state_reports_the_link_bit_used_by_stat_dispatch(self):
        input_endpoint = _Endpoint(
            PREFLIGHT.EP_IN,
            [_jast_reply(flags=1 << 12), _jast_reply(flags=1 << 12)])
        output_endpoint = _Endpoint(PREFLIGHT.EP_OUT)
        device = _Device("AB7C22200355", input_endpoint, output_endpoint)

        result = PREFLIGHT.run_preflight(
            _Core(device), _Util(), 76, "AB7C22200355")

        self.assertEqual(result["flags_word"], 1 << 12)
        self.assertTrue(result["channel_linked"])
