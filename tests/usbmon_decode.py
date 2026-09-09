#!/usr/bin/env python3
"""Decode a usbmon capture of the io24's control interface into readable messages.

This is a file-only decoder. It does not open the device, start Universal
Control, or depend on Wine. Captures made on a supported native host can be
normalized to the JSONL form below and analyzed here after the live session.

This script is the reader. Point it at a usbmon text capture or a normalized
JSONL export and it prints the paesdk framing and the FourCC TLVs inside,
marking anything this project has never sent.

    sudo modprobe usbmon
    sudo cat /sys/kernel/debug/usb/usbmon/1u > uc.txt     # bus 1
    python3 tests/usbmon_decode.py uc.txt

Normalized JSONL is capture-tool independent and contains one bulk payload per
line:

    {"dir":"OUT","ep":1,"type":"S","data":"1000010101000000..."}

Run it against a capture of THIS driver first to confirm the pipeline, then
against a capture of UC, then diff. The interesting output is the tags and
blocks that appear only in UC's.

usbmon text format, the fields that matter:

    <urb-id> <ts> <type> <pipe> <status> <len> <data-tag> <hex bytes...>

    type:  S submission, C callback
    pipe:  Bo:1:004:2  = Bulk out, bus 1, device 4, endpoint 2
    data:  '=' followed by hex, space-separated in 4-byte groups
"""

import json
import re
import sys
from collections import Counter

try:
    from io24_capture_format import validate_bulk_frame
except ModuleNotFoundError:  # imported as tests.usbmon_decode
    from tests.io24_capture_format import validate_bulk_frame

# what this project already sends — anything else is the point of the exercise
KNOWN_CMD = {"SetP", "GetP", "Rply"}
KNOWN_BLOCK = {"Appl"}
KNOWN_BLOB = {"VoFx", "godv", "may4", "bota", "botb", "botc", "vech", "inia",
              "Bqdf", "vrvb", "FRst", "MemP", "Pari", "Para", "JaSt"}

LINE = re.compile(
    r"^(\S+)\s+(\d+)\s+([SCE])\s+([BbCcIi][oi]?):(\d+):(\d+):(\d+)\s+"
    r"(-?\d+|\S+)\s+(\d+)(?:\s+[=<>]\s*(.*))?$")


def fourcc(b):
    s = bytes(b[::-1])
    try:
        t = s.decode("ascii")
        return t if all(32 <= ord(c) < 127 for c in t) else None
    except Exception:
        return None


def parse(path):
    urbs = []
    capture_format = None
    with open(path, errors="replace") as capture:
        for line_number, raw in enumerate(capture, 1):
            line = raw.strip()
            if not line:
                continue
            if capture_format is None:
                capture_format = "jsonl" if line.startswith("{") else "usbmon"

            if capture_format == "jsonl":
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise TypeError("row is not an object")
                    direction = record["dir"]
                    typ = record["type"]
                    endpoint = record["ep"]
                    data = record["data"]
                    if not isinstance(direction, str):
                        raise TypeError("dir must be a string")
                    if not isinstance(typ, str):
                        raise TypeError("type must be a string")
                    direction = direction.upper()
                    typ = typ.upper()
                    if isinstance(endpoint, bool) or \
                            not isinstance(endpoint, int) or not 0 <= endpoint <= 15:
                        raise ValueError("ep must be an integer from 0 through 15")
                    if not isinstance(data, str):
                        raise TypeError("data must be a hexadecimal string")
                    payload = bytes.fromhex("".join(data.split()))
                    validate_bulk_frame(payload, direction, typ, endpoint)
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError("invalid normalized JSONL at line %d: %s"
                                     % (line_number, error)) from error
                urbs.append({"dir": direction, "ep": endpoint,
                             "type": typ, "data": payload})
                continue

            m = LINE.match(line)
            if not m:
                continue
            _, _, typ, pipe, bus, dev, ep, status, ln, data = m.groups()
            if not data or not pipe.lower().startswith("b"):
                continue
            hexs = "".join(data.split())
            try:
                payload = bytes.fromhex(hexs)
            except ValueError:
                continue
            if payload:
                urbs.append({"dir": "OUT" if pipe.lower().startswith("bo") else "IN",
                             "ep": int(ep), "type": typ, "data": payload})
    return urbs


def decode_msg(p):
    """paesdk frame -> list of (cmd, block, index, blobtag, bloblen)."""
    out = []
    if len(p) < 8:
        return out
    # [u16 totalLen][0x01][0x01 req / 0x81 resp][u8 uid][u8 status][u16 rsvd]
    body = p[8:]
    if len(body) < 12:
        return out
    cmd = fourcc(body[0:4])
    blk = body[4:8]
    blkname = fourcc(blk) or ("#%d" % int.from_bytes(blk, "little"))
    idx = int.from_bytes(body[8:12], "little")
    blob = body[12:]
    btag = blen = None
    if len(blob) >= 8:
        btag = fourcc(blob[0:4])
        blen = int.from_bytes(blob[4:8], "little")
    out.append((cmd, blkname, idx, btag, blen, len(blob)))
    return out


def decode_preset_metadata(p):
    """Decode bounded MemP metadata without inferring save/recall semantics."""
    if len(p) < 36:
        return None
    body = p[8:]
    command = fourcc(body[0:4])
    block = fourcc(body[4:8])
    block_index = int.from_bytes(body[8:12], "little")
    blob = body[12:]
    if block != "Appl" or block_index != 0 or len(blob) < 16 or \
            fourcc(blob[0:4]) != "MemP":
        return None

    declared = int.from_bytes(blob[4:8], "little")
    if declared != len(blob):
        raise ValueError("MemP length does not match the captured envelope")
    record = fourcc(blob[8:12])
    index = int.from_bytes(blob[12:16], "little")
    if record == "PrsM":
        if not 16 <= index <= 27:
            raise ValueError("PrsM index must be in the range 16..27")
        meaning = ("cache-refresh-envelope" if command == "SetP" else
                   "bounded-preset-metadata")
    elif record == "Stat":
        if not 0 <= index <= 3:
            raise ValueError("Stat index must be in the range 0..3")
        meaning = "enumeration-metadata"
    else:
        return None
    return {"record": record, "index": index, "meaning": meaning,
            "operation": None}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    urbs = parse(sys.argv[1])
    if not urbs:
        print("No bulk URBs with data found in %s." % sys.argv[1])
        print("Check the bus number and that the capture ran while UC was")
        print("actually talking to the device.")
        return 1

    print("%d bulk transfers with payload\n" % len(urbs))
    seen_cmd, seen_blk, seen_blob = Counter(), Counter(), Counter()
    novel = []
    for u in urbs:
        for cmd, blk, idx, btag, blen, n in decode_msg(u["data"]):
            if cmd:
                seen_cmd[cmd] += 1
            seen_blk[blk] += 1
            if btag:
                seen_blob[btag] += 1
            flag = ""
            if (cmd and cmd not in KNOWN_CMD) or \
               (btag and btag not in KNOWN_BLOB) or \
               (blk not in KNOWN_BLOCK and not blk.startswith("#")):
                flag = "   ** NOT IN OUR SET **"
                novel.append((cmd, blk, btag))
            print("  %-3s ep%-2d %-5s %-8s idx %-3d blob %-6s len %-5s%s"
                  % (u["dir"], u["ep"], cmd or "?", blk, idx,
                     btag or "-", blen if blen is not None else "-", flag))
            try:
                metadata = decode_preset_metadata(u["data"])
            except ValueError as error:
                print("      preset metadata INVALID: %s" % error)
            else:
                if metadata:
                    print("      %s index %d: %s; no inferred operation" %
                          (metadata["record"], metadata["index"],
                           metadata["meaning"]))

    print("\n" + "=" * 66)
    print("commands : %s" % dict(seen_cmd))
    print("blocks   : %s" % dict(seen_blk.most_common(12)))
    print("blob tags: %s" % dict(seen_blob.most_common(20)))
    if novel:
        print("\nNEVER SENT BY THIS PROJECT:")
        for c, b, t in sorted(set(novel)):
            print("   cmd %-5s block %-8s blob %s" % (c or "?", b, t or "-"))
    else:
        print("\nEverything here is already in this project's vocabulary.")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
