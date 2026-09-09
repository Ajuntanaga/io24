#!/usr/bin/env python3
"""Bounded CP34 preflight for one explicitly authorized read-only USB scope.

This client deliberately does not reuse ``io24.Io24``: that general-purpose
class clears endpoint halts and queries extra vendor properties during setup.
The preflight below claims the authorized interface, selects its authorized
alternate setting, sends exactly two ``GetP | Appl(0) | JaSt`` requests, and
releases the claim.  It has no ``SetP`` or recovery-write path.
"""

import argparse
import hashlib
import json
import struct
import sys


VID = 0x194F
PID = 0x0422
IFACE = 5
ALTSETTING = 1
EP_OUT = 0x01
EP_IN = 0x81
GETP = 0x47657450
SETP = 0x53657450
RPLY = 0x52706C79
APPL = 0x4170706C
JAST = 0x4A615374
STATE_BLOB_SIZE = 0x7EC
DATA_START = 0x1C
READ_COUNT = 2


class PreflightError(RuntimeError):
    """The limited preflight could not produce a safe read-only result."""


def _battery_result(battery_percent):
    if isinstance(battery_percent, bool) or not isinstance(battery_percent, int):
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if not 0 <= battery_percent <= 100:
        return {"status": "BLOCKED_BATTERY_UNAVAILABLE"}
    if battery_percent <= 10:
        return {"status": "BLOCKED_BATTERY", "battery_percent": battery_percent}
    return None


def _jast_frame(uid):
    blob = struct.pack("<IIII", JAST, STATE_BLOB_SIZE, 0, 0)
    blob += b"\0" * (STATE_BLOB_SIZE - len(blob))
    payload = struct.pack("<III", GETP, APPL, 0) + blob
    return (struct.pack("<H", len(payload) + 8) +
            bytes((0x01, 0x01, uid, 0, 0, 0)) + payload)


def _read_reply(input_endpoint):
    raw = bytes(input_endpoint.read(2048, timeout=2000))
    if len(raw) < 12:
        raise PreflightError("short read")
    total, = struct.unpack_from("<H", raw, 0)
    if total != len(raw):
        raise PreflightError("incomplete or trailing response")
    payload = raw[8:]
    tag, = struct.unpack_from("<I", payload, 0)
    if tag != RPLY:
        raise PreflightError("response is not Rply")
    if len(payload) < DATA_START + 51 * 4:
        raise PreflightError("JaSt response is too short")
    return payload


def _float_at(payload, slot):
    return struct.unpack_from("<f", payload, DATA_START + slot * 4)[0]


def _int_at(payload, slot):
    return struct.unpack("<i", struct.pack("<f", _float_at(payload, slot)))[0]


def _readable_state(payload):
    flags = _int_at(payload, 42)
    return {
        "flags_word": flags,
        "channel_linked": bool(flags >> 12 & 1),
        "input1_slot_index": _int_at(payload, 40),
        "input2_slot_index": _int_at(payload, 41),
        "input1_preset_enabled": not bool(flags >> 5 & 1),
        "input2_preset_enabled": not bool(flags >> 6 & 1),
    }


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


def run_preflight(usb_core, usb_util, battery_percent, expected_serial):
    """Perform exactly the authorized identity/claim/two-JaSt-read sequence.

    ``usb_core`` and ``usb_util`` are injected so the command order is covered
    by hardware-free tests.  No operation after the identity check runs unless
    the battery is above the 10-percent floor and the serial matches exactly.
    """
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
            raise PreflightError("authorized interface endpoints unavailable")

        payloads = []
        for uid in range(1, READ_COUNT + 1):
            output_endpoint.write(_jast_frame(uid), timeout=2000)
            payloads.append(_read_reply(input_endpoint))
    except Exception as error:
        return {"status": "READ_FAILED", "battery_percent": battery_percent,
                "device": identity,
                "read_error": "%s: %s" % (type(error).__name__, error)}
    finally:
        if claimed:
            try:
                usb_util.release_interface(device, IFACE)
            except Exception:
                pass

    hashes = [hashlib.sha256(payload).hexdigest() for payload in payloads]
    result = {
        "schema": "cp34-readonly-preflight-v1",
        "status": "PASS" if len(set(hashes)) == 1 else "STATE_CHANGED_DURING_PREFLIGHT",
        "battery_percent": battery_percent,
        "device": identity,
        "interface": {"number": IFACE, "alternate_setting": ALTSETTING},
        "jast_reads": [{"reply_bytes": len(payload), "sha256": digest}
                       for payload, digest in zip(payloads, hashes)],
    }
    if result["status"] == "PASS":
        result.update(_readable_state(payloads[0]))
    return result


def _read_battery(path):
    try:
        with open(path, encoding="ascii") as handle:
            return int(handle.read().strip())
    except (OSError, ValueError) as error:
        raise PreflightError("battery unavailable: %s" % error) from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True,
                        help="exact authorized io24 serial")
    parser.add_argument("--battery-path", default="/sys/class/power_supply/BAT0/capacity",
                        help="host battery percentage path")
    arguments = parser.parse_args(argv)
    try:
        battery_percent = _read_battery(arguments.battery_path)
    except PreflightError as error:
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

    result = run_preflight(usb.core, usb.util, battery_percent, arguments.serial)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 3


if __name__ == "__main__":
    sys.exit(main())
