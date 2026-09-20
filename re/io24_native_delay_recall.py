#!/usr/bin/env python3
"""Store a native Delay in a slot, recall it, and listen. Guitar on Input 1.

Live host control of block 201 is closed: on 2026-09-15 all six models were
swept fully wet against an audible reverb control on the same return and
nothing was heard. The other install path is the firmware's own preset
deserializer -- the slot's model pointer at `slot+0x14` is what `0x60070af8`
checks, and a stored record containing component 201 is the one thing besides
the live selector that can populate it.

The body written here is the firmware's OWN Channel-1 default slot record,
which already ships a Delay (component 201, selected_model 5), with only the
delay's four state words changed. Everything else in it is PreSonus's bytes.

Writes: one slot body, then a recall. Both are restored -- the prior slot body
from the Host's device-slot registry when it knows it, and the previously
selected slot re-selected at the end.

    python3 re/io24_native_delay_recall.py --slot 1 --execute
"""

import argparse
import json
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _directory in (ROOT, ROOT / "re"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import io24_fw_disasm as fwimg  # noqa: E402
import io24_native_stat as ns  # noqa: E402
import io24_loopback_foundation as foundation  # noqa: E402

FW_CHANNEL1_DEFAULT = 0x68070
FW_CHANNEL1_DEFAULT_BYTES = 1088
BATTERY_FLOOR = 12
LISTEN_S = 12.0


def native_delay_body(slot_index, time_s, feedback, mix):
    """The firmware's own Channel-1 default, with its Delay armed."""
    image = fwimg.firmware()
    base = bytes(image[FW_CHANNEL1_DEFAULT:
                       FW_CHANNEL1_DEFAULT + FW_CHANNEL1_DEFAULT_BYTES])
    ns.validate_native_stat_record(base)
    return ns.build_native_delay_stat_record(
        base, slot_index, enabled=True, time_s=time_s, feedback=feedback,
        mix=mix)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--slot", type=int, default=1,
                        help="global slot 0..3; channel 1 owns 0 and 1")
    parser.add_argument("--time", type=float, default=0.25)
    parser.add_argument("--feedback", type=float, default=0.6)
    parser.add_argument("--mix", type=float, default=1.0)
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    args = parser.parse_args(argv)

    body = native_delay_body(args.slot, args.time, args.feedback, args.mix)
    summary = ns.native_stat_summary(body, slot_index=args.slot)
    print("native body: %d bytes, voicefx=%s"
          % (len(body), json.dumps(summary["voicefx"])), flush=True)
    on, mix, half, time_s = struct.unpack(
        "<Ifff", bytes.fromhex(summary["voicefx"]["state_hex"]))
    print("  delay on=%d  mix=%.2f  feedback=%.2f  time=%.0f ms"
          % (on, mix, half * 2, time_s * 1000), flush=True)
    if not args.execute:
        print("\n(offline only — pass --execute to write and recall)")
        return 0

    battery = foundation._battery(args.battery_path)
    print("battery %d%%" % battery, flush=True)
    if battery <= BATTERY_FLOOR:
        raise SystemExit("battery %d%% is at or below the %d%% floor"
                         % (battery, BATTERY_FLOOR))

    device = foundation._open_checked()
    selected_before = None
    try:
        params = device.read_params()
        selected_before = (int(params["input1SlotIndex"]),
                           int(params["input2SlotIndex"]))
        print("selected slots before: %s" % (selected_before,), flush=True)
        if args.slot == selected_before[0]:
            raise SystemExit(
                "slot %d is the one Channel 1 is using; choose the other"
                % args.slot)

        print("writing the native body to global slot %d ..." % args.slot,
              flush=True)
        transport = device.save_device_slot(args.slot, body)
        print("  sent %d frame(s), %d repl(ies)"
              % (transport["fragments_sent"], transport["replies_received"]),
              flush=True)

        print("recalling slot %d on Channel 1 — PLAY THE GUITAR NOW"
              % args.slot, flush=True)
        report = device.recall_device_slot(1, args.slot)
        print("  recall: %s" % json.dumps(report), flush=True)
        print("  listening window: %.0f s" % LISTEN_S, flush=True)
        time.sleep(LISTEN_S)
    finally:
        if selected_before is not None:
            try:
                device.recall_device_slot(1, selected_before[0])
                print("re-selected Channel 1 slot %d" % selected_before[0],
                      flush=True)
            except Exception as error:
                print("could not re-select the prior slot: %s" % error,
                      flush=True)
        try:
            device.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
