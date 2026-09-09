#!/usr/bin/env python3
"""Normalize a supported-host io24 capture export into strict JSONL.

Input is a tab-separated, headerless export with exactly six columns:

    frame.time_epoch  usb.bus_id  usb.device_address
    usb.interface_number  usb.endpoint_address  usb.capdata

The required target bus/device, interface 5, and io24 control endpoints
0x01/0x81 are enforced. Each payload must be one complete paesdk frame; damaged
or partial evidence is an error, never a row to silently discard.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

try:
    from io24_capture_format import validate_bulk_frame
except ModuleNotFoundError:  # imported as tests.normalize_io24_capture
    from tests.io24_capture_format import validate_bulk_frame


INTERFACE = 5
ENDPOINTS = {0x01: ("OUT", "S"), 0x81: ("IN", "C")}


def _integer(value, label, line_number):
    try:
        return int(value, 0)
    except (TypeError, ValueError) as error:
        raise ValueError("line %d: invalid %s %r"
                         % (line_number, label, value)) from error


def _payload(value, direction, transfer_type, line_number):
    compact = "".join(value.replace(":", " ").split())
    try:
        payload = bytes.fromhex(compact)
    except ValueError as error:
        raise ValueError("line %d: payload is not hexadecimal"
                         % line_number) from error
    try:
        validate_bulk_frame(payload, direction, transfer_type, 1)
    except (TypeError, ValueError) as error:
        raise ValueError("line %d: %s" % (line_number, error)) from error
    return payload


def _expected_device(value):
    try:
        bus_text, device_text = value.split(":", 1)
        bus = int(bus_text, 0)
        device = int(device_text, 0)
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("device must be BUS:ADDRESS, for example 1:7") from error
    if bus < 0 or not 0 <= device <= 127:
        raise ValueError("device BUS:ADDRESS is outside the USB address range")
    return bus, device


def normalize(input_path, output_path, action, expected_device):
    """Filter and validate one TSV export, returning the written row count."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not isinstance(action, str) or not action.strip():
        raise ValueError("action must be a non-empty capture identifier")
    expected_bus, expected_address = _expected_device(expected_device)

    records = []
    with input_path.open(errors="strict") as source:
        for line_number, raw in enumerate(source, 1):
            if not raw.strip():
                continue
            columns = raw.rstrip("\r\n").split("\t")
            if len(columns) != 6:
                raise ValueError("line %d: expected six tab-separated columns"
                                 % line_number)
            timestamp, bus_text, device_text, interface_text, endpoint_text, data = columns
            if not timestamp:
                raise ValueError("line %d: timestamp is empty" % line_number)
            bus = _integer(bus_text, "bus", line_number)
            device = _integer(device_text, "device address", line_number)
            if (bus, device) != (expected_bus, expected_address):
                continue
            interface = _integer(interface_text, "interface", line_number)
            endpoint = _integer(endpoint_text, "endpoint", line_number)
            if interface != INTERFACE or endpoint not in ENDPOINTS:
                continue
            direction, transfer_type = ENDPOINTS[endpoint]
            payload = _payload(data, direction, transfer_type, line_number)
            records.append({
                "ts": timestamp,
                "action": action,
                "bus": bus,
                "device": device,
                "dir": direction,
                "ep": endpoint & 0x0F,
                "type": transfer_type,
                "data": payload.hex(),
            })

    if not records:
        raise ValueError("capture contains no complete interface-5 control payloads")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=".%s." % output_path.name, suffix=".tmp",
        dir=output_path.parent, text=True)
    try:
        with os.fdopen(fd, "w") as target:
            for record in records:
                target.write(json.dumps(record, separators=(",", ":")) + "\n")
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, output_path)
        directory_fd = os.open(
            output_path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return len(records)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True,
                        help="capture matrix identifier, for example C02")
    parser.add_argument("--device", required=True,
                        help="authorized USB target as BUS:ADDRESS")
    parser.add_argument("input", help="headerless six-column TSV export")
    parser.add_argument("output", help="normalized JSONL destination")
    args = parser.parse_args(argv)
    count = normalize(args.input, args.output, args.action, args.device)
    print("wrote %d complete io24 control payloads to %s"
          % (count, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
