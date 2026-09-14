"""User go (2026-09-11): the four unit blocks.

"Can you put both of those presets on both chanels and both blocks", layout
answer "MAIN 1, B A S E 2", then "Piano Accomany should be on Channel 2
Block" / "block 2". Result:

    Channel 1: block 1 MAIN (slot 0)   block 2 B A S E (slot 1)
    Channel 2: block 1 MAIN (slot 2)   block 2 Piano Accomany (slot 3)

Slot 0 already holds MAIN (registry f74cd983...) and Channel 1 is playing it,
so it is not rewritten. MAIN and B A S E come from the slot registry; Piano
Accomany is built from `Piano Accomany.scene` line/ch2 (the scene's piano
channel, preamp 0 dB) by the same seven-section rule that reproduces B A S E.
All three are hash-verified before USB opens.

Device actions, in order: write B A S E to slot 1 (Channel 1 stays on block
1); write Piano Accomany to slot 3 (Channel 2 is on slot 2); recall Channel 2
block 2 (slot 3) so slot 2 is not playing; write MAIN to slot 2; recall
Channel 2 block 1 (slot 2). Does not load or save the driver shadow cache.
Updates the slot registry.
"""
import copy
import json
import os
import struct
import sys

PROJECT = "/home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont"
sys.path.insert(0, PROJECT)
import io24  # noqa: E402
from io24_preset_record import (  # noqa: E402
    DeviceSlotRegistry, _canonical_record_sha256, complete_device_slot_record)

MAIN_SHA = "f74cd9837af8fb093ae1260381bf98b21b4549d40cc58cbf531d209910efd222"
BASE_SHA = "135a93f1e6b0b63cd8102cf1309eb2ffb6e627cd21490fecd4481ef884fb2384"
PIANO_SHA = "d58136ce09a602d5b291233ba2f2f742023a4bb56459edd771eea20e335bbd8f"
MAIN_SOURCE = "restored-user:MAIN (Main.scene line/ch1)"
BASE_SOURCE = "restored-user:B A S E (B A S E.scene line/ch1)"
PIANO_SOURCE = "restored-user:Piano Accomany (Piano Accomany.scene line/ch2)"
PIANO_SCENE = os.path.expanduser("~/.cache/io24/re/scenes/Piano Accomany.scene")
SECTIONS = ("opt", "filter", "gate", "comp", "eq", "limit", "voicefx")
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


def piano_record():
    channel = json.load(open(PIANO_SCENE))["line"]["ch2"]
    record = {name: channel[name] for name in SECTIONS if name in channel}
    record["preset_name"] = "Piano Accomany"
    return complete_device_slot_record(record)


def stop(message):
    print("STOPPED:", message)
    return 1


def main():
    slots = json.load(open(REGISTRY))["slots"]
    main_record = copy.deepcopy(slots["0"]["record"])
    base_record = copy.deepcopy(slots["2"]["record"])
    piano = piano_record()
    if _canonical_record_sha256(main_record) != MAIN_SHA:
        return stop("registry slot 0 is not the pinned MAIN")
    if _canonical_record_sha256(base_record) != BASE_SHA:
        return stop("registry slot 2 is not the pinned B A S E")
    if _canonical_record_sha256(piano) != PIANO_SHA:
        return stop("Piano Accomany record does not match its pinned hash")
    level = battery()
    print("battery:", level)
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
        if before["slot"] not in ((0, 2), (1, 2)):
            return stop("expected Channel 1 on slot 0 or 1 and Channel 2 on slot 2")
        if before["link"]:
            return stop("stereo link is on")
        if before["slot"][0] == 1:
            # Left there by the user's front-panel block test; slot 1 is the
            # B A S E target, so Channel 1 returns to MAIN on block 1 first.
            print("0. recall Channel 1 block 1:", dev.recall_device_slot(1, 0))
            moved = state(dev)
            if moved["slot"] != (0, 2):
                return stop("Channel 1 did not return to block 1: %s" % (moved,))

        result = dev.save_known_device_slot(1, base_record, registry, BASE_SOURCE)
        print("A. write B A S E to slot 1:", result["transport"],
              result["registry"]["status"])
        result = dev.save_known_device_slot(3, piano, registry, PIANO_SOURCE)
        print("B. write Piano Accomany to slot 3:", result["transport"],
              result["registry"]["status"])

        print("C. recall Channel 2 block 2:", dev.recall_device_slot(2, 3))
        moved = state(dev)
        if moved["slot"] != (0, 3):
            return stop("Channel 2 did not move cleanly: %s" % (moved,))
        result = dev.save_known_device_slot(2, main_record, registry, MAIN_SOURCE)
        print("D. write MAIN to slot 2:", result["transport"],
              result["registry"]["status"])
        print("E. recall Channel 2 block 1:", dev.recall_device_slot(2, 2))

        after = state(dev)
        print("after:", after)
        problems = []
        if after["slot"] != (0, 2):
            problems.append("slots are %s" % (after["slot"],))
        for key in ("bypassed", "gain", "link", "owner"):
            if after[key] != before[key]:
                problems.append("%s changed: %s -> %s" % (key, before[key], after[key]))
        slots = json.load(open(REGISTRY))["slots"]
        for index, expected in (("0", MAIN_SHA), ("1", BASE_SHA),
                                ("2", MAIN_SHA), ("3", PIANO_SHA)):
            entry = slots.get(index)
            if entry is None:
                problems.append("registry slot %s is empty" % index)
                continue
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
