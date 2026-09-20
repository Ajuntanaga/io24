#!/usr/bin/env python3
"""Print outgoing UC mixer ``mprm`` batches from one usbmon text capture."""

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
        _, timestamp, event, pipe, _bus, _device, endpoint, _, _, data = match.groups()
        if event != "S" or pipe != "Bo" or int(endpoint) != 1 or not data:
            continue
        try:
            payload = bytes.fromhex("".join(data.split()))
        except ValueError:
            continue
        if len(payload) < 20 + 0x1F0:
            continue
        command, block, block_index = struct.unpack_from("<III", payload, 8)
        tag, declared, component_index = struct.unpack_from("<III", payload, 20)
        if (command, block, tag, declared) != (
                0x53657450, 100, 0x6D70726D, 0x1F0):
            continue
        count = struct.unpack_from("<I", payload, 20 + 0x1EC)[0]
        entries = [
            {"param_id": param_id, "gain_db": gain_db}
            for param_id, gain_db in (
                struct.unpack_from("<If", payload, 20 + 0x0C + 8 * i)
                for i in range(count)
            )
        ]
        print(json.dumps({
            "line": line_number,
            "timestamp_us": int(timestamp),
            "block_index": block_index,
            "component_index": component_index,
            "entries": entries,
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
