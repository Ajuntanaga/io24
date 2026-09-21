#!/usr/bin/env python3
"""
First write to the per-channel DSP chain: enable the limiter on channel 1,
instance 0 only, then read gain-reduction metering back.

The asymmetry is the point — writing only instance 0 should make 'Redu' return
[<1.0, 1.0], which in one reply proves the message framing, the block FourCC,
the blob layout, the blob-index semantics and the metering count.

Block   'lim ' (0x6c696d20), blockIndex 0 (channel 1)
Blob    'lim ' size 0x18:  +0x08 index | +0x0c enable u32
                           +0x10 inverse-threshold f32 | +0x14 release coef f32
Read    GetP 'lim '/'Redu', size field MUST be >= 0x4c;
        reply = N linear gains at blob+0x08, N at blob+0x48

Safety: the blob index is NOT bounds-checked by the firmware, so it is clamped
to 0..1 here. Restore uses the exact power-on values from firmware initialiser
0x60076c6c. 'IFac' is never sent. Worst case this attenuates a channel.
"""
import struct
import sys
import time

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))   # driver modules live one level up
from io24 import Io24, GETP, SETP

def fourcc(s):
    """C constant 'A'<<24|'B'<<16|'C'<<8|'D' — reverse the ASCII, read LE."""
    return struct.unpack("<I", s.encode("ascii")[::-1])[0]


LIM = fourcc("lim ")      # 0x6c696d20 — block and blob tag share the FourCC
REDU = fourcc("Redu")     # 0x52656475

# firmware power-on state, from initialiser 0x60076c6c
OFF_ENABLE, OFF_THRESH, OFF_RELEASE = 0, 0x3FAAB0D5, 0x00000000
RELEASE_48K = 0x3F7FEA8F                        # release coefficient for fs=48000


def inv_threshold(db):
    """Wire encoding: inverse of the linear threshold, i.e. 10**(-db/20)."""
    return 10.0 ** (-db / 20.0)


def lim_blob(index, enable, inv_thresh_bits, release_bits):
    index = max(0, min(1, index))               # firmware does NOT clamp this
    return (struct.pack("<II", LIM, 0x18)
            + struct.pack("<II", index, enable)
            + struct.pack("<I", inv_thresh_bits)
            + struct.pack("<I", release_bits))


def set_limiter(dev, index, enable, thresh_db=None, release_bits=RELEASE_48K):
    if enable:
        bits, = struct.unpack("<I", struct.pack("<f", inv_threshold(thresh_db)))
    else:
        bits, release_bits = OFF_THRESH, OFF_RELEASE
    payload = struct.pack("<III", SETP, LIM, 0) + lim_blob(index, enable, bits, release_bits)
    dev._exec(payload, wait=0.25)


def read_redu(dev, block=LIM):
    blob = struct.pack("<IIII", REDU, 0x4C, 0, 0) + b"\x00" * (0x4C - 16)
    rsp = dev._exec(struct.pack("<III", GETP, block, 0) + blob, wait=0.8)
    if not rsp or len(rsp) < 12 + 0x4C:
        return None, []
    body = rsp[12:]
    count, = struct.unpack_from("<I", body, 0x48)
    vals = list(struct.unpack_from("<%df" % max(0, min(count, 16)), body, 0x08))
    return count, vals


def show(tag, count, vals):
    def db(v):
        return "-inf" if v <= 1e-9 else "%+.2f dB" % (20 * __import__("math").log10(v))
    print("   %-10s count=%s  %s" % (tag, count, "  ".join(
        "[%d]=%.6f (%s)" % (i, v, db(v)) for i, v in enumerate(vals))))


def main():
    dev = Io24()
    try:
        # sanity: confirm the encoding matches the analysis' worked example
        chk, = struct.unpack("<I", struct.pack("<f", inv_threshold(-28.0)))
        print("encoding check: invThreshold(-28 dB) = 0x%08x (analysis says 0x41c8f36f)  %s\n"
              % (chk, "OK" if chk == 0x41C8F36F else "MISMATCH"))

        print("baseline:")
        c0, v0 = read_redu(dev)
        show("lim Redu", c0, v0)

        for thresh in (-28.0, -60.0, -90.0):
            print("\n--- limiter ON: ch1, instance 0 only, threshold %.0f dBFS ---" % thresh)
            set_limiter(dev, 0, 1, thresh)
            time.sleep(0.5)
            c1, v1 = read_redu(dev)
            show("lim Redu", c1, v1)
            if v1 and len(v1) >= 2 and v1[0] < 0.999 and v1[1] > 0.999:
                print("   *** ASYMMETRIC REDUCTION — instance 0 limiting, instance 1 untouched ***")
                break
            if v1 and any(v < 0.999 for v in v1):
                print("   (reduction present)")
                break
        else:
            print("\n   no reduction seen — input signal is below every threshold tried")

        print("\n--- restoring power-on state (both instances) ---")
        for idx in (0, 1):
            set_limiter(dev, idx, 0)
            time.sleep(0.25)
        c2, v2 = read_redu(dev)
        show("lim Redu", c2, v2)
        print("   restored" if all(v > 0.999 for v in v2) else "   CHECK: reduction still present")
    finally:
        dev.close()


if __name__ == "__main__":
    main()
