#!/usr/bin/env python3
"""Execute one auditable CP34 ``Stat`` trial restricted to channel-2 slots.

The caller supplies a firmware-native version-2 record and chooses either
global slot 2 or 3.  The client verifies the exact serial and host battery,
reads a ``JaSt`` baseline, writes only that ``MemP/Stat`` record, selects that
same channel-2 slot, and reads a post-state.  It neither accepts tagged preset
archives, changes channel 1, nor claims that a transport write proves
persistent storage or audible effect.
"""

import argparse
import hashlib
import json
import os
import struct
import sys
import time

# Running this file directly places ``re/`` first on ``sys.path``.  Put the
# project root ahead of it so the same local io24 protocol module used by the
# test suite is imported by an operator invocation.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import io24
from io24_native_stat import validate_native_stat_record


VID = 0x194F
PID = 0x0422
IFACE = 5
ALTSETTING = 1
EP_OUT = 0x01
EP_IN = 0x81
GETP = io24.GETP
SETP = io24.SETP
RPLY = io24.RPLY
APPL = io24.APPL
JAST = io24.JAST
MEMP = io24.MEMP
STAT = io24.STAT
PARI = io24.PARI
STATE_BLOB_SIZE = io24.STATE_BLOB_SIZE
DATA_START = io24.DATA_START
CHANNEL2_SLOTS = frozenset((2, 3))
EMPTY_ACK = object()


class TrialError(RuntimeError):
    """The bounded channel-2 trial could not establish its observation."""


def _battery_result(battery_percent):
    if isinstance(battery_percent, bool) or not isinstance(battery_percent, int):
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if not 0 <= battery_percent <= 100:
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if battery_percent <= 10:
        return {"status": "BLOCKED_BATTERY", "battery_percent": battery_percent}
    return None


def _identity(device, expected_serial):
    try:
        serial = device.serial_number
    except Exception as error:
        return None, {"status": "IDENTITY_UNAVAILABLE",
                      "identity_error": "%s: %s" % (type(error).__name__, error)}
    if serial != expected_serial:
        return None, {"status": "IDENTITY_MISMATCH", "expected_serial": expected_serial,
                      "observed_serial": serial}
    return {"serial": serial,
            "bcd_device": "%04x" % int(getattr(device, "bcdDevice", 0))}, None


def _transport_frame(uid, payload):
    return (struct.pack("<H", len(payload) + 8) +
            bytes((0x01, 0x01, uid, 0, 0, 0)) + payload)


def _jast_payload():
    blob = struct.pack("<IIII", JAST, STATE_BLOB_SIZE, 0, 0)
    blob += b"\0" * (STATE_BLOB_SIZE - len(blob))
    return struct.pack("<III", GETP, APPL, 0) + blob


def _reply_payload(raw):
    if len(raw) < 12:
        raise TrialError("short read")
    total, = struct.unpack_from("<H", raw, 0)
    if total != len(raw):
        raise TrialError("incomplete or trailing response")
    payload = raw[8:]
    tag, = struct.unpack_from("<I", payload, 0)
    if tag != RPLY:
        raise TrialError("response is not Rply")
    return payload


def _read_reply(input_endpoint):
    payload = _reply_payload(bytes(input_endpoint.read(2048, timeout=2000)))
    if len(payload) < DATA_START + 51 * 4:
        raise TrialError("JaSt response is too short")
    return payload


def _read_optional_setp_reply(input_endpoint):
    """Drain a synchronous SetP response when the device emits one.

    Native requests are strictly serialized.  SetP commonly yields no payload,
    but an endpoint response must be consumed before the next command rather
    than leaving the transport in an ambiguous request/response state.
    """
    try:
        raw = bytes(input_endpoint.read(2048, timeout=2000))
    except Exception as error:
        if type(error).__name__ == "USBTimeoutError":
            return None
        raise
    if len(raw) == 8:
        total, = struct.unpack_from("<H", raw, 0)
        if total != 8:
            raise TrialError("malformed empty SetP acknowledgement")
        return EMPTY_ACK
    return _reply_payload(raw)


def _float_at(payload, slot):
    return struct.unpack_from("<f", payload, DATA_START + slot * 4)[0]


def _int_at(payload, slot):
    return struct.unpack("<i", struct.pack("<f", _float_at(payload, slot)))[0]


def _readable_state(payload):
    flags = _int_at(payload, 42)
    return {
        "input1_processing_channel": _int_at(payload, 38) - 3,
        "input2_processing_channel": _int_at(payload, 39) - 3,
        "input1_slot_index": _int_at(payload, 40),
        "input2_slot_index": _int_at(payload, 41),
        "input1_preset_enabled": not bool(flags >> 5 & 1),
        "input2_preset_enabled": not bool(flags >> 6 & 1),
        "input1_gain_db": _float_at(payload, 46),
        "input2_gain_db": _float_at(payload, 47),
    }


def _send(output_endpoint, uid, payload):
    frame = _transport_frame(uid, payload)
    written = output_endpoint.write(frame, timeout=2000)
    if written != len(frame):
        raise TrialError("short bulk write")
    return frame


def _channel2_selector_payload(slot_index):
    """Build the source-bound ``Pari`` selector for input/channel 2 only."""
    blob = struct.pack("<IIIIi", PARI, 0x14, 1, 16, slot_index)
    return struct.pack("<III", SETP, APPL, 0) + blob


def build_trial(slot_index, native_record):
    """Prepare the exact channel-2-only payload sequence without USB access."""
    if isinstance(slot_index, bool) or slot_index not in CHANNEL2_SLOTS:
        raise ValueError("channel-2 trial target must be slot 2 or 3")
    record = validate_native_stat_record(native_record, slot_index=slot_index)
    stat_payloads = tuple(io24._build_native_slot_memp_frames(slot_index, record))
    return {
        "target_slot": slot_index,
        "record_wire_sha256": hashlib.sha256(record).hexdigest(),
        "record_bytes": len(record),
        "stat_payloads": stat_payloads,
        "selector_payload": _channel2_selector_payload(slot_index),
    }


def run_trial(usb_core, usb_util, battery_percent, expected_serial, slot_index,
              native_record, sleep_fn=time.sleep):
    """Run the one-write, channel-2-only trial with injected USB dependencies."""
    try:
        trial = build_trial(slot_index, native_record)
    except (TypeError, ValueError) as error:
        return {"status": "BLOCKED_TARGET", "target_slot": slot_index,
                "target_error": str(error)}

    blocked = _battery_result(battery_percent)
    if blocked is not None:
        return blocked

    device = usb_core.find(idVendor=VID, idProduct=PID)
    if device is None:
        return {"status": "DEVICE_NOT_FOUND", "expected_serial": expected_serial}
    identity, failure = _identity(device, expected_serial)
    if failure is not None:
        return failure

    claimed = False
    stage = "claim_interface"
    baseline = None
    frame_hashes = []
    setp_replies_received = 0
    setp_empty_acks_received = 0
    try:
        usb_util.claim_interface(device, IFACE)
        claimed = True
        device.set_interface_altsetting(interface=IFACE, alternate_setting=ALTSETTING)
        interface = device.get_active_configuration()[(IFACE, ALTSETTING)]
        input_endpoint = usb_util.find_descriptor(
            interface, custom_match=lambda endpoint: endpoint.bEndpointAddress == EP_IN)
        output_endpoint = usb_util.find_descriptor(
            interface, custom_match=lambda endpoint: endpoint.bEndpointAddress == EP_OUT)
        if input_endpoint is None or output_endpoint is None:
            raise TrialError("authorized interface endpoints unavailable")

        uid = 1
        stage = "baseline_jast_write"
        _send(output_endpoint, uid, _jast_payload())
        stage = "baseline_jast_read"
        baseline_payload = _read_reply(input_endpoint)
        baseline = _readable_state(baseline_payload)
        if baseline["input2_slot_index"] == slot_index:
            return {
                "schema": "cp34-channel2-slot-trial-v1",
                "status": "BLOCKED_ACTIVE_TARGET",
                "battery_percent": battery_percent,
                "device": identity,
                "target_slot": slot_index,
                "baseline": baseline,
            }
        uid += 1

        for sequence, payload in enumerate(trial["stat_payloads"], 1):
            stage = "stat_write_%d" % sequence
            frame_hashes.append(hashlib.sha256(_send(output_endpoint, uid, payload)).hexdigest())
            uid += 1
            stage = "stat_reply_%d" % sequence
            reply = _read_optional_setp_reply(input_endpoint)
            if reply is EMPTY_ACK:
                setp_empty_acks_received += 1
            elif reply is not None:
                setp_replies_received += 1
        # UC's slot-save scheduler waits for settled edits before it builds the
        # record.  The submitted record is already complete; this bounded wait
        # simply gives the device writer a turn before the subsequent selector.
        sleep_fn(0.6)
        stage = "selector_write"
        frame_hashes.append(hashlib.sha256(
            _send(output_endpoint, uid, trial["selector_payload"])).hexdigest())
        uid += 1
        stage = "selector_reply"
        reply = _read_optional_setp_reply(input_endpoint)
        if reply is EMPTY_ACK:
            setp_empty_acks_received += 1
        elif reply is not None:
            setp_replies_received += 1
        sleep_fn(0.1)

        stage = "post_jast_write"
        _send(output_endpoint, uid, _jast_payload())
        stage = "post_jast_read"
        post_payload = _read_reply(input_endpoint)
        post_state = _readable_state(post_payload)
    except Exception as error:
        return {"status": "TRIAL_FAILED", "battery_percent": battery_percent,
                "device": identity,
                "trial_stage": stage,
                "baseline": baseline,
                "write_frame_sha256": frame_hashes,
                "setp_replies_received": setp_replies_received,
                "setp_empty_acks_received": setp_empty_acks_received,
                "trial_error": "%s: %s" % (type(error).__name__, error)}
    finally:
        if claimed:
            try:
                usb_util.release_interface(device, IFACE)
            except Exception:
                pass

    channel1_keys = ("input1_processing_channel", "input1_slot_index",
                     "input1_preset_enabled", "input1_gain_db")
    channel1_unchanged = all(baseline[key] == post_state[key]
                             for key in channel1_keys)
    if not channel1_unchanged:
        status = "CHANNEL1_GUARD_FAILED"
    elif post_state["input2_slot_index"] != slot_index:
        status = "TARGET_SELECTION_UNCONFIRMED"
    else:
        status = "WRITE_SENT_AND_SELECTED"
    return {
        "schema": "cp34-channel2-slot-trial-v1",
        "status": status,
        "battery_percent": battery_percent,
        "device": identity,
        "interface": {"number": IFACE, "alternate_setting": ALTSETTING},
        "target_slot": slot_index,
        "record_wire_sha256": trial["record_wire_sha256"],
        "record_bytes": trial["record_bytes"],
        "stat_fragments_sent": len(trial["stat_payloads"]),
        "write_frame_sha256": frame_hashes,
        "setp_replies_received": setp_replies_received,
        "setp_empty_acks_received": setp_empty_acks_received,
        "baseline": baseline,
        "post_state": post_state,
        "channel1_unchanged": channel1_unchanged,
        "physical_commit": "UNPROVED",
        "front_panel_recall": "UNPROVED",
        "audibility": "UNPROVED",
    }


def _read_battery(path):
    try:
        with open(path, encoding="ascii") as handle:
            return int(handle.read().strip())
    except (OSError, ValueError) as error:
        raise TrialError("battery unavailable: %s" % error) from error


def _load_record(path):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError as error:
        raise TrialError("record unavailable: %s" % error) from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="exact authorized io24 serial")
    parser.add_argument("--slot", required=True, type=int, choices=(2, 3),
                        help="authorized channel-2 global slot")
    parser.add_argument(
        "--record", required=True,
        help="local firmware-native version-2 Stat record (binary)")
    parser.add_argument("--execute", action="store_true",
                        help="perform the bounded write/select trial")
    parser.add_argument("--battery-path", default="/sys/class/power_supply/BAT0/capacity",
                        help="host battery percentage path")
    arguments = parser.parse_args(argv)

    try:
        record = _load_record(arguments.record)
        trial = build_trial(arguments.slot, record)
    except (TrialError, TypeError, ValueError) as error:
        print(json.dumps({"status": "BLOCKED_TARGET", "target_error": str(error)},
                         sort_keys=True))
        return 3
    if not arguments.execute:
        print(json.dumps({key: value for key, value in trial.items()
                          if key not in ("stat_payloads", "selector_payload")},
                         indent=2, sort_keys=True))
        return 0

    try:
        battery_percent = _read_battery(arguments.battery_path)
    except TrialError as error:
        print(json.dumps({"status": "BLOCKED_BATTERY_UNAVAILABLE",
                          "battery_error": str(error)}, sort_keys=True))
        return 3
    try:
        import usb.core
        import usb.util
    except ImportError as error:
        print(json.dumps({"status": "USB_LIBRARY_UNAVAILABLE",
                          "usb_error": str(error)}, sort_keys=True))
        return 3

    result = run_trial(usb.core, usb.util, battery_percent, arguments.serial,
                       arguments.slot, record)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "WRITE_SENT_AND_SELECTED" else 3


if __name__ == "__main__":
    sys.exit(main())
