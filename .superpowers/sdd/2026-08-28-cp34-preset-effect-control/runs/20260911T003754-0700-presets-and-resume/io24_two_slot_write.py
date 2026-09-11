"""User go (2026-09-11): B A S E on Channel 2 block 1; MAIN + Reverb on Channel 1 block 2.

Device actions: write MAIN + factory Reverb to global slot 1 (Channel 1 is left
on block 1); recall Channel 2 block 2 so its target is not playing; write
B A S E to global slot 2; recall Channel 2 block 1. Reads state before/after.
Does not load or save the driver shadow cache. Updates the slot registry.
"""
import json
import os
import struct
import sys

PROJECT = "/home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont"
sys.path.insert(0, PROJECT)
import io24  # noqa: E402
from io24_preset_record import (  # noqa: E402
    DeviceSlotRegistry, _canonical_record_sha256, with_doubler_private_reverb)

MAIN = "/home/ajuntanaga/.claude/jobs/dfb44a5b/tmp/main-record.json"
MAIN_SHA = "f74cd9837af8fb093ae1260381bf98b21b4549d40cc58cbf531d209910efd222"
BASE_SHA = "135a93f1e6b0b63cd8102cf1309eb2ffb6e627cd21490fecd4481ef884fb2384"
REGISTRY = os.path.join(
    os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")),
    "io24", "device-slots.json")


def battery():
    for name in sorted(os.listdir("/sys/class/power_supply")):
        path = os.path.join("/sys/class/power_supply", name, "capacity")
        if name.startswith("BAT") and os.path.exists(path):
            return int(open(path).read().strip())
    return None


def state(dev):
    f = dev.floats(dev.read_state(0x7EC))

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
    main_record = json.load(open(MAIN))
    if _canonical_record_sha256(main_record) != MAIN_SHA:
        return stop("MAIN record hash mismatch")
    # The user asked for the reverb maxed out: Wet/Dry 100 %; lows and width
    # stay at UC's factory Reverb values.
    main_reverb = with_doubler_private_reverb(
        main_record, preset_name="MAIN + Reverb", mix=1.0)
    base_record = json.load(open(REGISTRY))["slots"]["1"]["record"]
    if _canonical_record_sha256(base_record) != BASE_SHA:
        return stop("B A S E record in the registry does not match its hash")
    print("MAIN + Reverb canonical:", _canonical_record_sha256(main_reverb))
    level = battery()
    if level is not None and level <= 10:
        return stop("battery at %d%%" % level)
    dev = io24.Io24(shadow=False)
    try:
        identity = dev._device_slot_identity()
        if identity["serial"] != "AB7C22200355" or identity["bcd_device"] != "0128":
            return stop("unexpected unit %s" % identity)
        registry = DeviceSlotRegistry(REGISTRY)
        before = state(dev)
        print("before:", before)
        if before["slot"][0] == 1:
            return stop("Channel 1 is playing block 2, the MAIN + Reverb target")

        result = dev.save_known_device_slot(
            1, main_reverb, registry, "restored-user:MAIN + factory Reverb")
        print("A. write MAIN + Reverb to slot 1:", result["transport"],
              result["registry"]["status"])

        if before["slot"][1] == 2:
            print("B1. recall Channel 2 block 2:", dev.recall_device_slot(2, 3))
            moved = state(dev)
            if moved["slot"][1] != 3 or moved["slot"][0] != before["slot"][0]:
                return stop("Channel 2 did not move cleanly: %s" % (moved,))
        result = dev.save_known_device_slot(
            2, base_record, registry, "restored-user:B A S E (B A S E.scene line/ch1)")
        print("B2. write B A S E to slot 2:", result["transport"],
              result["registry"]["status"])
        print("B3. recall Channel 2 block 1:", dev.recall_device_slot(2, 2))

        after = state(dev)
        print("after:", after)
        problems = []
        if after["slot"] != (before["slot"][0], 2):
            problems.append("slots are %s" % (after["slot"],))
        for key in ("bypassed", "gain", "link", "owner"):
            if after[key] != before[key]:
                problems.append("%s changed: %s -> %s" % (key, before[key], after[key]))
        slots = json.load(open(REGISTRY))["slots"]
        for index, expected in (("1", _canonical_record_sha256(main_reverb)),
                                ("2", BASE_SHA)):
            entry = slots[index]
            print("registry slot %s: %s | %s | %s | %s" % (
                index, entry["record"]["preset_name"], entry["source"],
                entry["canonical_sha256"][:16], entry["status"]))
            if entry["canonical_sha256"] != expected:
                problems.append("registry slot %s hash mismatch" % index)
        print("RESULT:", "OK" if not problems else "; ".join(problems))
        return 0 if not problems else 1
    finally:
        dev.close()


if __name__ == "__main__":
    sys.exit(main())
