#!/usr/bin/env python3
"""Reassemble UC MemP records and print their VoiceFX state."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from io24_preset_record import decode_preset_record


LINE = re.compile(
    r"^(\S+)\s+(\d+)\s+([SCE])\s+([Bb][oi]):(\d+):(\d+):(\d+)\s+"
    r"(-?\d+|\S+)\s+(\d+)(?:\s+[=<>]\s*(.*))?$"
)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} USBTAP_LOG", file=sys.stderr)
        return 2

    pending: dict[tuple[int, int], dict[str, object]] = {}
    for line_number, raw in enumerate(Path(sys.argv[1]).open(errors="replace"), 1):
        match = LINE.match(raw.strip())
        if not match:
            continue
        _, timestamp, event, pipe, _, _, endpoint, _, _, data = match.groups()
        if event != "S" or pipe != "Bo" or int(endpoint) != 1 or not data:
            continue
        try:
            payload = bytes.fromhex("".join(data.split()))
        except ValueError:
            continue
        if len(payload) < 49:
            continue
        command, block, block_index, tag, declared, record_tag, record_index = \
            struct.unpack_from("<IIIIIII", payload, 8)
        if (command, block, block_index, tag, declared) != (
                0x53657450, 0x4170706C, 0, 0x4D656D50, 0x7EC):
            continue
        fragment_offset = struct.unpack_from("<I", payload, 38)[0]
        more = payload[42]
        fragment_length = struct.unpack_from("<H", payload, 43)[0]
        total_length = struct.unpack_from("<I", payload, 45)[0]
        fragment = payload[49:49 + fragment_length]
        if len(fragment) != fragment_length:
            continue

        key = (record_tag, record_index)
        if fragment_offset == 0:
            pending[key] = {
                "buffer": bytearray(total_length),
                "filled": bytearray(total_length),
                "line_start": line_number,
                "timestamp_us": int(timestamp),
            }
        state = pending.get(key)
        if state is None or fragment_offset + fragment_length > total_length:
            continue
        buffer = state["buffer"]
        filled = state["filled"]
        assert isinstance(buffer, bytearray) and isinstance(filled, bytearray)
        buffer[fragment_offset:fragment_offset + fragment_length] = fragment
        filled[fragment_offset:fragment_offset + fragment_length] = b"\x01" * fragment_length
        if more or not all(filled):
            continue

        encoded = bytes(buffer)
        record = {
            "line_start": state["line_start"],
            "line_end": line_number,
            "timestamp_us": state["timestamp_us"],
            "record_tag": struct.pack("<I", record_tag)[::-1].decode("ascii", "replace"),
            "record_index": record_index,
            "encoded_length": len(encoded),
            "encoded_sha256": hashlib.sha256(encoded).hexdigest(),
        }
        try:
            decoded = decode_preset_record(encoded)
        except (TypeError, ValueError) as error:
            record["decode_error"] = str(error)
        else:
            record["preset_name"] = decoded.get("preset_name")
            record["voicefx"] = decoded.get("voicefx")
            record["processingChannel"] = decoded.get("processingChannel")
        print(json.dumps(record, sort_keys=True))
        del pending[key]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
