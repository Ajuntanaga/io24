#!/usr/bin/env python3
"""Behavioral contracts for the channel-2-only CP34 slot trial."""

import importlib.util
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest

from io24_native_stat import (
    CHANNEL_COMPONENT_SIZES,
    NativeChunk,
    NativeStatRecord,
    encode_chunk_group,
    encode_native_stat_record,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "cp34_channel2_slot_trial.py")


def _load_trial_module():
    if not os.path.exists(SCRIPT):
        return None
    spec = importlib.util.spec_from_file_location("cp34_channel2_slot_trial", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TRIAL = _load_trial_module()


def _int_as_float(value):
    return struct.unpack("<f", struct.pack("<i", value))[0]


def _jast_reply(slot1=0, slot2=2, flags=0):
    payload = bytearray(0x1C + 51 * 4)
    struct.pack_into("<I", payload, 0, 0x52706C79)  # Rply
    for slot, value in ((40, _int_as_float(slot1)),
                        (41, _int_as_float(slot2)),
                        (42, _int_as_float(flags))):
        struct.pack_into("<f", payload, 0x1C + slot * 4, value)
    return (struct.pack("<H", len(payload) + 8) +
            b"\x01\x01\x00\x00\x00\x00" + payload)


def _empty_ack():
    return struct.pack("<H", 8) + b"\x01\x01\x00\x00\x00\x00"


class USBTimeoutError(Exception):
    """Match PyUSB's timeout type name without requiring physical USB in tests."""


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
        event = self.replies.pop(0)
        if isinstance(event, BaseException):
            raise event
        return event


class _Configuration:
    def __init__(self, interface):
        self.interface = interface

    def __getitem__(self, key):
        if key != (5, 1):
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


class Channel2SlotTrialTests(unittest.TestCase):
    @staticmethod
    def _record():
        channel = encode_chunk_group([
            (key, bytes([index + 1]) * size)
            for index, (key, size) in enumerate(CHANNEL_COMPONENT_SIZES.items())
        ])
        return encode_native_stat_record(
            NativeStatRecord(2, (NativeChunk(b"opt ", channel),)))

    def _trial(self):
        self.assertIsNotNone(TRIAL, "channel-2 trial production module is missing")
        return TRIAL

    def _fixture(self):
        trial = self._trial()
        input_endpoint = _Endpoint(
            trial.EP_IN,
            [_jast_reply(slot1=0, slot2=2), _empty_ack(), _empty_ack(),
             _jast_reply(slot1=0, slot2=3)])
        output_endpoint = _Endpoint(trial.EP_OUT)
        device = _Device("AB7C22200355", input_endpoint, output_endpoint)
        return _Core(device), _Util(), device, input_endpoint, output_endpoint

    def test_channel1_slot_is_rejected_before_usb_enumeration(self):
        trial = self._trial()
        core, util, _, _, _ = self._fixture()

        result = trial.run_trial(core, util, 89, "AB7C22200355", 1,
                                 self._record(), sleep_fn=lambda _seconds: None)

        self.assertEqual(result["status"], "BLOCKED_TARGET")
        self.assertEqual(core.find_calls, [])
        self.assertEqual(util.claims, [])

    def test_slot3_trial_writes_only_stat3_then_channel2_selector(self):
        trial = self._trial()
        core, util, device, input_endpoint, output_endpoint = self._fixture()

        result = trial.run_trial(core, util, 89, "AB7C22200355", 3,
                                 self._record(), sleep_fn=lambda _seconds: None)

        self.assertEqual(result["status"], "WRITE_SENT_AND_SELECTED")
        self.assertEqual(result["baseline"]["input1_slot_index"], 0)
        self.assertEqual(result["post_state"]["input1_slot_index"], 0)
        self.assertEqual(result["post_state"]["input2_slot_index"], 3)
        self.assertEqual(result.get("setp_replies_received"), 0)
        self.assertEqual(result.get("setp_empty_acks_received"), 2)
        self.assertEqual(device.altsettings, [(trial.IFACE, trial.ALTSETTING)])
        self.assertEqual(len(util.claims), 1)
        self.assertEqual(len(util.releases), 1)
        self.assertEqual(len(input_endpoint.replies), 0)
        self.assertEqual(len(output_endpoint.writes), 4)

        frames = [frame for frame, _timeout in output_endpoint.writes]
        self.assertEqual(struct.unpack_from("<III", frames[0], 8),
                         (trial.GETP, trial.APPL, 0))
        self.assertEqual(struct.unpack_from("<III", frames[1], 8),
                         (trial.SETP, trial.APPL, 0))
        self.assertEqual(struct.unpack_from("<I", frames[1], 20)[0], trial.MEMP)
        self.assertEqual(struct.unpack_from("<I", frames[1], 28)[0], trial.STAT)
        self.assertEqual(struct.unpack_from("<I", frames[1], 32)[0], 3)
        self.assertEqual(struct.unpack_from("<III", frames[2], 8),
                         (trial.SETP, trial.APPL, 0))
        self.assertEqual(struct.unpack_from("<I", frames[2], 20)[0], trial.PARI)
        self.assertEqual(struct.unpack_from("<I", frames[2], 28)[0], 1)
        self.assertEqual(struct.unpack_from("<I", frames[2], 32)[0], 16)
        self.assertEqual(struct.unpack_from("<i", frames[2], 36)[0], 3)
        self.assertEqual(struct.unpack_from("<III", frames[3], 8),
                         (trial.GETP, trial.APPL, 0))

    def test_active_channel2_target_is_blocked_before_stat_write(self):
        trial = self._trial()
        core, util, _, input_endpoint, output_endpoint = self._fixture()

        result = trial.run_trial(core, util, 89, "AB7C22200355", 2,
                                 self._record(), sleep_fn=lambda _seconds: None)

        self.assertEqual(result["status"], "BLOCKED_ACTIVE_TARGET")
        self.assertEqual(result["baseline"]["input2_slot_index"], 2)
        self.assertEqual(len(output_endpoint.writes), 1)
        self.assertEqual(len(input_endpoint.replies), 3)
        self.assertEqual(len(util.claims), 1)
        self.assertEqual(len(util.releases), 1)

    def test_cli_dry_run_imports_the_project_protocol_module(self):
        with tempfile.TemporaryDirectory() as directory:
            record_path = os.path.join(directory, "channel2-record.stat")
            with open(record_path, "wb") as handle:
                handle.write(self._record())
            completed = subprocess.run(
                [sys.executable, SCRIPT, "--serial", "AB7C22200355", "--slot", "3",
                 "--record", record_path],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["target_slot"], 3)
        self.assertGreater(result["record_bytes"], 0)

    def test_cli_rejects_a_tagged_json_archive_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            record_path = os.path.join(directory, "obsolete-record.json")
            with open(record_path, "w", encoding="utf-8") as handle:
                json.dump({"preset_name": "Slap Echo"}, handle)
            completed = subprocess.run(
                [sys.executable, SCRIPT, "--serial", "AB7C22200355", "--slot", "3",
                 "--record", record_path],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )

        self.assertEqual(completed.returncode, 3, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "BLOCKED_TARGET")
        self.assertIn("version", result["target_error"])


if __name__ == "__main__":
    unittest.main()
