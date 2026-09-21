#!/usr/bin/env python3
"""
Closed-loop SetP write test, using the WIRE paramId space recovered from the
io24's embedded firmware.

  SetP / block 'Appl' / blockIndex 0 / blob 'Para' / index 0 / paramId 3
    -> input1Gain (ch1 preamp gain), firmware-clamped to 0..60 dB
    -> observable in JaSt slot 46

Safety:
  * paramId 3 is inside the 'Para' handler's accepted range (1..14), verified by
    disassembly of 0x6004e360; the firmware clamps the value to the parameter's
    declared min/max, so it cannot be driven out of 0..60 dB
  * a FULL stable-state diff is taken before and after, so any unintended change
    is visible, not just the one we aimed at
  * the original value is restored and the restore is verified
  * SetP is fire-and-forget (no reply), so we do not sit waiting on the IN pipe
  * 'FRst' is never sent
"""
import struct
import sys
import time

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))   # driver modules live one level up
from io24 import Io24, DATA_START, SETP, APPL, PARA

TARGET_SLOT = 46      # JaSt slot: ch1 preamp gain, dB
WIRE_PARAM = 3        # 'Para' wire id 3 -> input1Gain/input2Gain
CHAN_INDEX = 0        # blob index: 0 = ch1, 1 = ch2
GAIN_MIN, GAIN_MAX = 0.0, 60.0


def set_gain(dev, value, index=CHAN_INDEX):
    """SetP 'Para' paramId 3 — ch1/ch2 preamp gain in dB."""
    blob = struct.pack("<IIII", PARA, 0x14, index, WIRE_PARAM)
    blob += struct.pack("<f", float(value))
    payload = struct.pack("<III", SETP, APPL, 0) + blob
    # fire-and-forget: short wait, we do not expect a reply
    dev._exec(payload, wait=0.25)


def stable_snapshot(dev, n=4):
    runs = []
    for _ in range(n):
        r = dev.read_state()
        if r is not None:
            runs.append(dev.floats(r))
        time.sleep(0.12)
    if not runs:
        return {}
    m = min(len(x) for x in runs)
    return {i: [x[i] for x in runs][0]
            for i in range(m) if len({x[i] for x in runs}) == 1}


def diff(a, b):
    return [(i, a[i], b[i]) for i in sorted(set(a) & set(b)) if a[i] != b[i]]


def report(changes):
    for i, va, vb in changes:
        raw = struct.pack("<f", vb)
        iv, = struct.unpack("<i", raw)
        extra = "  (int %d)" % iv if 0 < abs(vb) < 1e-30 else ""
        mark = "   <<< TARGET (ch1 gain)" if i == TARGET_SLOT else ""
        print("     slot[%3d] off=0x%03x : %-12.6g -> %-12.6g%s%s"
              % (i, DATA_START + i * 4, va, vb, extra, mark))


def main():
    dev = Io24()
    try:
        print("io24 connected: proto=%d maxCmd=%d\n" % (dev.proto, dev.max_cmd))
        before = stable_snapshot(dev)
        if TARGET_SLOT not in before:
            print("could not read a stable ch1 gain — aborting"); return
        orig = before[TARGET_SLOT]
        print("baseline ch1 gain (slot %d) = %.3g dB   [%d stable slots]"
              % (TARGET_SLOT, orig, len(before)))

        # pick a clearly different, in-range target
        target = 15.0 if orig > 30.0 else 45.0
        print("\n--- SetP 'Para' paramId=%d index=%d value=%.1f dB ---"
              % (WIRE_PARAM, CHAN_INDEX, target))
        set_gain(dev, target)
        time.sleep(0.4)

        after = stable_snapshot(dev)
        changes = diff(before, after)
        if not changes:
            print("   no stable slot changed — write did not take effect")
        else:
            report(changes)
        got = after.get(TARGET_SLOT)
        ok = got is not None and abs(got - target) < 0.6
        print("\n   ch1 gain now = %s dB  -> %s"
              % (got, "*** WRITE CONFIRMED ***" if ok else "not the value we wrote"))

        # restore
        print("\n--- restoring to %.3g dB ---" % orig)
        set_gain(dev, orig)
        time.sleep(0.4)
        final = stable_snapshot(dev)
        print("   ch1 gain restored = %s dB" % final.get(TARGET_SLOT))
        resid = [c for c in diff(before, final) if c[0] != TARGET_SLOT]
        print("   residual unintended changes vs baseline: %s"
              % (resid if resid else "none"))
    finally:
        dev.close()


if __name__ == "__main__":
    main()
