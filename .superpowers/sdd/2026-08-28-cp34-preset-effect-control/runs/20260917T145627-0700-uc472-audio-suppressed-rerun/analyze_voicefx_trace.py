#!/usr/bin/env python3
"""Print exact UC block-201 selector and Transformer state submissions."""

from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path


LINE = re.compile(
    r"^(\S+)\s+(\d+)\s+([SCE])\s+([Bb][oi]):(\d+):(\d+):(\d+)\s+"
    r"(-?\d+|\S+)\s+(\d+)(?:\s+[=<>]\s*(.*))?$"
)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} USBTAP_LOG", file=sys.stderr)
        return 2

    for line_number, raw in enumerate(Path(sys.argv[1]).open(errors="replace"), 1):
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
        if len(payload) < 32:
            continue
        command, block, block_index = struct.unpack_from("<III", payload, 8)
        tag, declared, component_index = struct.unpack_from("<III", payload, 20)
        if command != 0x53657450 or block != 201 or block_index != 0:
            continue

        record = {
            "line": line_number,
            "timestamp_us": int(timestamp),
            "bus": int(bus),
            "device": int(device),
            "component_index": component_index,
            "raw_hex": payload.hex(),
        }
        if tag == 0x566F4678 and declared == 16 and len(payload) >= 36:
            record.update(kind="selector", model=struct.unpack_from("<I", payload, 32)[0])
        elif tag == 0x676F6476 and declared == 32 and len(payload) >= 52:
            on, lows, width, lows_mirror, mix = struct.unpack_from("<Iffff", payload, 32)
            record.update(
                kind="godv",
                on=on,
                lows=lows,
                width=width,
                lows_mirror=lows_mirror,
                mix=mix,
            )
        elif tag == 0x76656368 and declared == 28 and len(payload) >= 48:
            on, mix, feedback_half, time_s = struct.unpack_from("<Ifff", payload, 32)
            record.update(
                kind="vech",
                on=on,
                mix=mix,
                feedback_half=feedback_half,
                feedback=feedback_half * 2.0,
                time_s=time_s,
            )
        else:
            continue
        print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
