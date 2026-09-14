"""Does Input-1-owned Doubler reverb process Input 2?  (Codex INBOX task 2.)

Runs only on the user's explicit go ("Proceed with all three", 2026-09-11).
The user feeds Input 2 by hand (static and pops from a patch cable) and
listens to Channel 2 on Main; this script only moves Channel 1 between its
own two blocks: block 2 = MAIN + Doubler private reverb, block 1 = MAIN dry.

  probe      read-only; the first probe records before.json for the restore
  block N    recall Channel 1 block N (1 or 2), then verify

Every invocation opens Io24(shadow=False), checks battery, unit identity,
link off, Input 2 phantom off and Voice FX owned by Input 1, and stops at the
first failed check.  No audio is played or captured.
"""
import json
import os
import sys
import time

PROJECT = "/home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont"
sys.path.insert(0, PROJECT)
import io24  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BEFORE = os.path.join(HERE, "before.json")
SERIAL, FIRMWARE = "AB7C22200355", "0128"


def battery():
    for name in sorted(os.listdir("/sys/class/power_supply")):
        path = os.path.join("/sys/class/power_supply", name, "capacity")
        if name.startswith("BAT") and os.path.exists(path):
            return int(open(path).read().strip())
    return None


def state(dev):
    params = dev.read_params()
    if params is None:
        raise SystemExit("STOPPED: JaSt read failed")
    flags = int(params["flags"])
    return {
        "ch1_slot": int(params["input1SlotIndex"]),
        "ch2_slot": int(params["input2SlotIndex"]),
        "ch1_bypassed": bool(flags >> 5 & 1),
        "ch2_bypassed": bool(flags >> 6 & 1),
        "link": bool(flags >> 12 & 1),
        "mute": [bool(flags >> 3 & 1), bool(flags >> 4 & 1)],
        "phantom": [bool(params["input1PhantomPower"]),
                    bool(params["input2PhantomPower"])],
        "gain": [round(params["input1Gain"], 3), round(params["input2Gain"], 3)],
        "hp_volume": round(params["hpVolume"], 3),
        "main_volume": round(params["mainVolume"], 3),
        "owner": dev.processing_channel(1),
    }


def stop(message):
    print("STOPPED:", message)
    return 1


def main(argv):
    if not argv or argv[0] not in ("probe", "block") or \
            (argv[0] == "block" and argv[1:] not in (["1"], ["2"])):
        return stop("usage: probe | block 1 | block 2")
    level = battery()
    print("battery:", level)
    if level is not None and level <= 10:
        return stop("battery at %d%%" % level)
    dev = io24.Io24(shadow=False)
    try:
        identity = dev._device_slot_identity()
        if identity["serial"] != SERIAL or identity["bcd_device"] != FIRMWARE:
            return stop("unexpected unit %s" % identity)
        pair = dev.device_slot_pair(1)
        now = state(dev)
        print("state:", json.dumps(now), "ch1 pair:", list(pair))
        if not os.path.exists(BEFORE):
            with open(BEFORE, "w") as fh:
                json.dump(now, fh, indent=1)
            print("recorded before.json")
        if now["link"]:
            return stop("stereo link is on")
        if now["phantom"][1]:
            return stop("phantom power is on for Input 2 (patch cable)")
        if now["owner"] != 1:
            return stop("Voice FX is owned by input %s, not 1" % now["owner"])
        if now["ch1_slot"] not in pair:
            return stop("Channel 1 is on slot %d, outside its pair" % now["ch1_slot"])
        if argv[0] == "probe":
            print("RESULT: OK (read-only)")
            return 0

        block = int(argv[1])
        target = pair[block - 1]
        if now["ch1_slot"] == target:
            print("Channel 1 is already on block %d; nothing sent" % block)
            print("RESULT: OK")
            return 0
        report = dev.recall_device_slot(1, target)
        print("recall Channel 1 block %d:" % block, json.dumps(report))
        time.sleep(0.35)
        after = state(dev)
        print("after:", json.dumps(after))
        problems = []
        if after["ch1_slot"] != target:
            problems.append("Channel 1 is not on block %d" % block)
        if after["ch1_bypassed"]:
            problems.append("Channel 1 is bypassed")
        for key in now:
            if key in ("ch1_slot", "ch1_bypassed"):
                continue
            if after[key] != now[key]:
                problems.append("%s changed: %s -> %s" % (key, now[key], after[key]))
        print("RESULT:", "OK" if not problems else "; ".join(problems))
        return 0 if not problems else 1
    finally:
        dev.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
