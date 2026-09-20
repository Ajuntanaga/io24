#!/usr/bin/env python3
"""Print a bounded JSONL timeline of outgoing UC SetP submissions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


LINE = re.compile(
    r"^(\S+)\s+(\d+)\s+([SCE])\s+([Bb][oi]):(\d+):(\d+):(\d+)\s+"
    r"(-?\d+|\S+)\s+(\d+)(?:\s+[=<>]\s*(.*))?$"
)


def fourcc(value: int) -> str:
    raw = struct.pack("<I", value)[::-1]
    if all(32 <= byte < 127 for byte in raw):
        return raw.decode("ascii")
    return f"#{value}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int)
    args = parser.parse_args()

    for line_number, raw in enumerate(args.capture.open(errors="replace"), 1):
        if line_number < args.start:
            continue
        if args.end is not None and line_number > args.end:
            break
        match = LINE.match(raw.strip())
        if not match:
            continue
        _, timestamp, event, pipe, bus, device, endpoint, _, _, data = match.groups()
        if event != "S" or pipe != "Bo" or int(endpoint) != 1 or not data:
            continue
        try:
            payload = bytes.fromhex("".join(data.split()))
        except ValueError:
            continue
        if len(payload) < 28:
            continue
        command, block, block_index = struct.unpack_from("<III", payload, 8)
        if command != 0x53657450:
            continue
        tag, declared = struct.unpack_from("<II", payload, 20)
        record = {
            "line": line_number,
            "timestamp_us": int(timestamp),
            "bus": int(bus),
            "device": int(device),
            "block": fourcc(block),
            "block_index": block_index,
            "tag": fourcc(tag),
            "declared": declared,
            "payload_length": len(payload),
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
        }
        if declared >= 12 and len(payload) >= 32:
            record["component_index"] = struct.unpack_from("<I", payload, 28)[0]
        if tag == 0x50617261 and declared == 20 and len(payload) >= 40:
            record["param_id"] = struct.unpack_from("<I", payload, 32)[0]
            record["value"] = struct.unpack_from("<f", payload, 36)[0]
        elif tag == 0x50617269 and declared == 20 and len(payload) >= 40:
            record["param_id"] = struct.unpack_from("<I", payload, 32)[0]
            record["value"] = struct.unpack_from("<i", payload, 36)[0]
        elif tag == 0x566F4678 and declared == 16 and len(payload) >= 36:
            record["model"] = struct.unpack_from("<I", payload, 32)[0]
        print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
