#!/usr/bin/env python3
"""Restore only the two readable input-mute bits after an aborted CP34 batch.

The default invocation is a no-I/O dry run.  The live path uses the same
minimal serial-pinned interface sequence as cp34_readonly_preflight: no endpoint
halt clear, no general Host cache, and no device-property queries beyond serial
and bcdDevice.  Channel 2 is restored and read back before Channel 1.
"""

import argparse
import json
from pathlib import Path
import struct
import sys
import time

import usb.core
import usb.util

import cp34_readonly_preflight as readonly


PARI = 0x50617269
MUTE_WIRE_ID = 7
EXPECTED_BCD_DEVICE = 0x0128
SETTLE_SECONDS = 0.35


def _set_mute_frame(uid, channel, on):
    index = channel - 1
    blob = struct.pack("<IIIIi", PARI, 0x14, index, MUTE_WIRE_ID,
                       1 if on else 0)
    payload = struct.pack("<III", readonly.SETP, readonly.APPL, 0) + blob
    return (struct.pack("<H", len(payload) + 8) +
            bytes((0x01, 0x01, uid, 0, 0, 0)) + payload)


def _read_state(output_endpoint, input_endpoint, uid):
    frame = readonly._jast_frame(uid)
    written = output_endpoint.write(frame, timeout=2000)
    if written != len(frame):
        raise readonly.PreflightError("short JaSt request write")
    payload = _read_complete_reply(input_endpoint)
    state = readonly._readable_state(payload)
    state["input1_muted"] = bool(state["flags_word"] >> 3 & 1)
    state["input2_muted"] = bool(state["flags_word"] >> 4 & 1)
    return state


def _read_complete_reply(input_endpoint):
    """Assemble a JaSt response that libusb may deliver in several reads."""
    raw = b""
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        try:
            chunk = bytes(input_endpoint.read(2048, timeout=400))
        except usb.core.USBTimeoutError:
            if raw:
                break
            continue
        raw += chunk
        if len(raw) >= 2:
            total, = struct.unpack_from("<H", raw, 0)
            if total <= len(raw):
                break
    if len(raw) < 12:
        raise readonly.PreflightError("short read")
    total, = struct.unpack_from("<H", raw, 0)
    if total != len(raw):
        raise readonly.PreflightError("incomplete or trailing response")
    payload = raw[8:]
    tag, = struct.unpack_from("<I", payload, 0)
    if tag != readonly.RPLY:
        raise readonly.PreflightError("response is not Rply")
    if len(payload) < readonly.DATA_START + 51 * 4:
        raise readonly.PreflightError("JaSt response is too short")
    return payload


def run_restore(battery_percent, expected_serial, sleep_fn=time.sleep,
                usb_core=usb.core, usb_util=usb.util):
    blocked = readonly._battery_result(battery_percent)
    if blocked is not None:
        return blocked
    device = usb_core.find(idVendor=readonly.VID, idProduct=readonly.PID)
    if device is None:
        return {"status": "DEVICE_NOT_FOUND"}
    identity, failure = readonly._identity(device, expected_serial)
    if failure is not None:
        return failure
    if int(getattr(device, "bcdDevice", 0)) != EXPECTED_BCD_DEVICE:
        return {"status": "FIRMWARE_MISMATCH", "device": identity}

    claimed = False
    events = []
    try:
        usb_util.claim_interface(device, readonly.IFACE)
        claimed = True
        device.set_interface_altsetting(interface=readonly.IFACE,
                                        alternate_setting=readonly.ALTSETTING)
        interface = device.get_active_configuration()[
            (readonly.IFACE, readonly.ALTSETTING)]
        input_endpoint = usb_util.find_descriptor(
            interface, custom_match=lambda ep: ep.bEndpointAddress == readonly.EP_IN)
        output_endpoint = usb_util.find_descriptor(
            interface, custom_match=lambda ep: ep.bEndpointAddress == readonly.EP_OUT)
        if input_endpoint is None or output_endpoint is None:
            raise readonly.PreflightError("authorized interface endpoints unavailable")

        uid = 1
        initial = _read_state(output_endpoint, input_endpoint, uid)
        current = initial
        for channel in (2, 1):
            key = "input%d_muted" % channel
            if not current[key]:
                events.append({"channel": channel, "action": "NO_WRITE_ALREADY_OFF",
                               "state": current})
                continue
            uid += 1
            frame = _set_mute_frame(uid, channel, False)
            written = output_endpoint.write(frame, timeout=2000)
            if written != len(frame):
                raise readonly.PreflightError("short mute restore write")
            events.append({"channel": channel, "action": "MUTE_OFF_SENT",
                           "frame_bytes": len(frame)})
            sleep_fn(SETTLE_SECONDS)
            uid += 1
            current = _read_state(output_endpoint, input_endpoint, uid)
            events.append({"channel": channel, "action": "READBACK",
                           "state": current})
            if current[key]:
                raise readonly.PreflightError(
                    "Channel %d mute remained on after write" % channel)

        protected_mask = ~((1 << 3) | (1 << 4))
        protected_equal = ((initial["flags_word"] & protected_mask) ==
                           (current["flags_word"] & protected_mask))
        slots_equal = all(initial[key] == current[key] for key in
                          ("input1_slot_index", "input2_slot_index"))
        restored = (not current["input1_muted"] and
                    not current["input2_muted"] and protected_equal and slots_equal)
        return {
            "schema": "cp34-input-mute-restoration-v1",
            "status": "RESTORED" if restored else "RESTORATION_FAILED",
            "battery_percent": battery_percent,
            "device": identity,
            "initial": initial,
            "events": events,
            "final": current,
            "protected_flags_equal": protected_equal,
            "slot_indices_equal": slots_equal,
        }
    except BaseException as error:
        return {
            "schema": "cp34-input-mute-restoration-v1",
            "status": "RESTORATION_TRANSPORT_FAILED",
            "battery_percent": battery_percent,
            "device": identity,
            "events": events,
            "error": {"type": type(error).__name__, "message": str(error)},
        }
    finally:
        if claimed:
            try:
                usb_util.release_interface(device, readonly.IFACE)
            except BaseException:
                pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--serial", default="AB7C22200355")
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({
            "schema": "cp34-input-mute-restoration-v1",
            "status": "DRY_RUN_ONLY",
            "order": ["read", "Channel 2 mute off", "readback",
                      "Channel 1 mute off", "readback"],
        }, indent=2, sort_keys=True))
        return 0
    try:
        battery = int(Path(args.battery_path).read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        battery = None
    result = run_restore(battery, args.serial)
    if args.report:
        report = Path(args.report)
        if report.exists() or not report.parent.is_dir():
            parser.error("report path must be new and have an existing parent")
        with report.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "RESTORED" else 3


if __name__ == "__main__":
    sys.exit(main())
