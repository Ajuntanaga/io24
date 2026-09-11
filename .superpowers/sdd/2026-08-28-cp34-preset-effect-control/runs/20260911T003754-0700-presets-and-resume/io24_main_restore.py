"""Restore the user's MAIN to Channel 1 block 1 (global slot 0).

Runs only on the user's explicit go. Stops at the first failed check.
Device actions, in order: (1) if Channel 1 is on slot 0, recall slot 1 so the
target is not the block being played; (2) write the MAIN record to slot 0;
(3) recall slot 0. Reads state before and after. Does not load or save the
driver shadow cache (shadow=False); does update the slot registry, which is
the intended record of this write.
"""
import json
import os
import struct
import sys

PROJECT = "/home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont"
sys.path.insert(0, PROJECT)
import io24  # noqa: E402
from io24_preset_record import (  # noqa: E402
    DeviceSlotRegistry, _canonical_record_sha256)

RECORD = "/home/ajuntanaga/.claude/jobs/dfb44a5b/tmp/main-record.json"
EXPECTED = "f74cd9837af8fb093ae1260381bf98b21b4549d40cc58cbf531d209910efd222"
SERIAL, FIRMWARE = "AB7C22200355", "0128"
REGISTRY = os.path.join(
    os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")),
    "io24", "device-slots.json")
SOURCE = "restored-user:MAIN (Main.scene line/ch1)"


def battery():
    for name in sorted(os.listdir("/sys/class/power_supply")):
        path = os.path.join("/sys/class/power_supply", name, "capacity")
        if name.startswith("BAT") and os.path.exists(path):
            return int(open(path).read().strip())
    return None


def state(dev):
    rsp = dev.read_state(0x7EC)
    f = dev.floats(rsp)

    def as_int(slot):
        return struct.unpack("<i", struct.pack("<f", f[slot]))[0]

    flags = as_int(42)
    params = dev.read_params() or {}
    return {
        "slot": (as_int(40), as_int(41)),
        "bypassed": (bool(flags >> 5 & 1), bool(flags >> 6 & 1)),
        "link": bool(flags >> 12 & 1),
        "gain": (round(params.get("input1Gain", -1), 3),
                 round(params.get("input2Gain", -1), 3)),
        "owner": dev.processing_channel(1),
    }


def stop(message):
    print("STOPPED:", message)
    return 1


def main():
    record = json.load(open(RECORD))
    if _canonical_record_sha256(record) != EXPECTED:
        return stop("MAIN record hash does not match the pinned value")
    level = battery()
    if level is not None and level <= 10:
        return stop("battery at %d%%" % level)
    dev = io24.Io24(shadow=False)
    try:
        identity = dev._device_slot_identity()
        if identity["serial"] != SERIAL or identity["bcd_device"] != FIRMWARE:
            return stop("unexpected unit %s" % identity)
        before = state(dev)
        print("before:", before)
        if before["slot"][0] == 0:
            report = dev.recall_device_slot(1, 1)
            print("step 1, recall Channel 1 block 2:", report)
            moved = state(dev)
            if moved["slot"][0] != 1:
                return stop("Channel 1 did not move to block 2: %s" % (moved,))
            if moved["slot"][1] != before["slot"][1] or moved["gain"] != before["gain"]:
                return stop("Channel 2 or gains changed: %s" % (moved,))
        registry = DeviceSlotRegistry(REGISTRY)
        result = dev.save_known_device_slot(0, record, registry, SOURCE)
        print("step 2, write MAIN to slot 0:", result["transport"],
              result["registry"]["status"])
        report = dev.recall_device_slot(1, 0)
        print("step 3, recall Channel 1 block 1:", report)
        after = state(dev)
        print("after:", after)
        problems = []
        if after["slot"][0] != 0:
            problems.append("Channel 1 is not on block 1")
        if after["bypassed"][0]:
            problems.append("Channel 1 is bypassed")
        for key in ("gain", "link", "owner"):
            if after[key] != before[key]:
                problems.append("%s changed: %s -> %s" % (key, before[key], after[key]))
        if after["slot"][1] != before["slot"][1] or \
                after["bypassed"][1] != before["bypassed"][1]:
            problems.append("Channel 2 changed")
        entry = json.load(open(REGISTRY))["slots"]["0"]
        if entry.get("canonical_sha256") != EXPECTED:
            problems.append("registry slot 0 does not carry MAIN's hash")
        print("registry slot 0:", entry["record"]["preset_name"], entry["source"],
              entry["canonical_sha256"][:16], entry["status"])
        print("RESULT:", "OK" if not problems else "; ".join(problems))
        return 0 if not problems else 1
    finally:
        dev.close()


if __name__ == "__main__":
    sys.exit(main())
