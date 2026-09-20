#!/usr/bin/env python3
"""Sweep all six block-201 models by ear, with the reverb silenced.

Established by ear on 2026-09-15: the shared reverb (block 202) IS audible
through `fxreturn/ch1 -> Main` once the Host's send/return transaction is
performed, and block 201's Delay on that identical path, with the reverb off,
is NOT. That is one model. This sweeps the other five, because on 2026-07-28
Delay, De-Tuner and Transformer were all ear-verified on this unit and this
firmware, so a per-model difference is worth ruling out before concluding that
block 201 is inert.

Rig: an instrument cable in Input 1 with a finger on the far end. Nothing is
played -- playback goes out Main and never enters Channel 1.

    Input 1 -> channel 1 DSP -> FX send ('Para' wire 4)
            -> block 201 -> fxreturn/ch1 -> Main -> headphones

The reverb is held off for the whole sweep and turned on at the end, so a
silent sweep is still a run whose path was proven live.

Writes the channel processing scalar, the `fxreturn/ch1 -> Main` level and
assignment, block 201 and block 202. All are Host-known and resent exactly.

    python3 re/io24_fx_listen_sweep.py
"""

import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
for _directory in (ROOT, ROOT / "re"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import io24_loopback_foundation as foundation  # noqa: E402
import io24_fx_shared_return_probe as shared  # noqa: E402

SHADOW = os.path.expanduser("~/.cache/io24/shadow.json")
RATE = 48000.0
ON_S = 8.0
OFF_S = 3.0
CONTROL_S = 8.0
DEFAULT_RETURN_DB = 6.0
DEFAULT_CHANNEL_MIX = 1.0

# Each model at its most obvious setting, fully wet, using the exact kwargs its
# own builder takes.
MODELS = (
    ("delay", {"time_s": 0.45, "feedback": 0.55, "mix": 1.0},
     "a repeat about 450 ms after each tap"),
    ("transformer", {"lows": 1.0, "width": 1.0, "mix": 1.0, "fs": RATE},
     "much heavier low end, wider"),
    ("detuner", {"detune": 0, "mix": 1.0, "fs": RATE},
     "a second voice pitched eight semitones down"),
    ("ringmod", {"carrier_hz": 60.0, "dist": 1.0, "vol": 1.0,
                 "carrier2": False, "carrier2_hz": 50.0, "mix": 1.0},
     "a hard 60 Hz buzz/tremolo on everything"),
    ("vocoder", {"carrier_type": 1, "carrier_freq": 110.0, "vol": 1.0,
                 "mix": 1.0, "fs": RATE},
     "a robotic sawtooth taking over the sound"),
    ("filters", {"pitch": 0.5, "regeneration": 1.0, "damping": 0.0,
                 "distortion": 0.5, "volume": 1.0, "mix": 1.0},
     "a ringing comb/resonator pitch"),
)


def shadow_value(shadow, function, match, field, default):
    """One exact value the Host last wrote, or a stated default."""
    for entry in shadow.values():
        if not isinstance(entry, dict) or entry.get("fn") != function:
            continue
        kwargs = entry.get("kwargs") or {}
        if all(kwargs.get(key) == value for key, value in match.items()):
            value = kwargs.get(field)
            if value is not None:
                return value, True
    return default, False


def main():
    with open(SHADOW, encoding="utf-8") as handle:
        shadow = json.load(handle)
    prior = shared.known_prior_state(SHADOW)
    reverb = dict(prior.get("reverb") or {})
    return_db, _known = shadow_value(
        shadow, "set_send_db", {"source": "fxreturn/ch1", "bus": "main"},
        "gain_db", DEFAULT_RETURN_DB)
    channel_mix, _mix_known = shadow_value(
        shadow, "set_fx_mix", {"channel": 1}, "value", DEFAULT_CHANNEL_MIX)

    total = len(MODELS) * (ON_S + OFF_S) + CONTROL_S
    print("effects path: channel 1 scalar %.3f, fxreturn/ch1 -> Main %+.2f dB"
          % (channel_mix, return_db), flush=True)
    print("reverb held OFF for the whole sweep — anything you hear is block 201",
          flush=True)
    print("", flush=True)
    print("Keep tapping the cable end for about %d seconds. Say the moment you"
          " hear ANY change." % int(total), flush=True)
    print("", flush=True)

    device = foundation._open_checked()
    try:
        device.establish_effects_return(
            bus="main", return_db=float(return_db),
            channel_mix=float(channel_mix))
        device.reverb_off()
        for index, (model, kwargs, expect) in enumerate(MODELS, start=1):
            device.set_fx(model, **dict(kwargs, on=True))
            print("  %d/%d  %-11s ON  — expect %s"
                  % (index, len(MODELS), model, expect), flush=True)
            time.sleep(ON_S)
            device.set_fx(model, **dict(kwargs, on=False))
            print("       %-11s off" % model, flush=True)
            time.sleep(OFF_S)
        if reverb:
            device.set_reverb(**dict(reverb, on=True))
            print("  CONTROL  reverb ON — proves the return carried sound",
                  flush=True)
            time.sleep(CONTROL_S)
    finally:
        notes = shared.restore(device, prior)
        device.set_send_db("fxreturn/ch1", "main", return_db)
        device.set_fx_mix(1, channel_mix)
        notes.append("fxreturn/ch1 -> Main %+.2f dB and channel scalar %.3f "
                     "resent" % (return_db, channel_mix))
        state = shared.readable_state(device.read_params())
        device.close()
        print("restored: %s" % "; ".join(notes), flush=True)
        print("main %.3f  headphones %.3f  ch1 gain %.1f dB"
              % (state["main_volume"], state["headphone_volume"],
                 state["input1_gain_db"]), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
