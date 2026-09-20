#!/usr/bin/env python3
"""Open the effects path, silence the reverb, and toggle block 201 out loud.

The rig is an instrument cable in Input 1 with a finger on the far end: the
finger is the source. Nothing is played -- playback goes out Main and never
enters Channel 1, so beeps cannot reach the FX.

Two things made earlier attempts useless, both worth not repeating:

1. The send and return are established BY THE HOST. With the Host closed
   nothing has opened them, so arming a model is arming it into a return that
   is routed nowhere. This script performs that transaction itself.
2. Block 201 and block 202 share one return. With the reverb armed fully wet,
   its tail masks the delay's repeats -- the user heard "reverb is on" and
   could not tell whether the delay was doing anything. So the reverb is held
   off for the whole block-201 test, and then turned on at the end as an
   audible proof that the return really was carrying sound.

    Input 1 -> channel 1 DSP -> FX send ('Para' wire 4)
            -> block 201 -> fxreturn/ch1 -> Main -> headphones

The dry signal also reaches Main through `line/ch1 -> main`, so taps stay
audible throughout; only the effect should come and go.

Writes the channel processing scalar, the `fxreturn/ch1 -> Main` level and
assignment, block 201 and block 202. All are Host-known in the shadow and are
resent exactly at the end.

    python3 re/io24_fx_listen_ab.py
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
PHASES = 3
PHASE_S = 9.0
CONTROL_S = 9.0
# Long, repeated and fully wet: the most obvious thing block 201 can do.
DELAY = {"time_s": 0.45, "feedback": 0.55, "mix": 1.0}
DEFAULT_RETURN_DB = 6.0
DEFAULT_CHANNEL_MIX = 1.0


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
    if not prior.get("fx"):
        raise SystemExit("the Host shadow holds no complete Voice FX call; "
                         "open the Host, touch the FX page, and re-run")
    model = prior["fx"]["model"]
    kwargs = dict(prior["fx"]["kwargs"])
    kwargs.update(DELAY)
    reverb = dict(prior.get("reverb") or {})

    return_db, return_known = shadow_value(
        shadow, "set_send_db", {"source": "fxreturn/ch1", "bus": "main"},
        "gain_db", DEFAULT_RETURN_DB)
    channel_mix, mix_known = shadow_value(
        shadow, "set_fx_mix", {"channel": 1}, "value", DEFAULT_CHANNEL_MIX)

    print("effects path: channel 1 scalar %.3f, fxreturn/ch1 -> Main %+.2f dB"
          % (channel_mix, return_db), flush=True)
    print("reverb held OFF for the whole block-201 test, so anything you hear"
          " in the return is block 201", flush=True)
    print("block 201 %s — %.0f ms, feedback %.2f, 100%% wet"
          % (model, DELAY["time_s"] * 1000, DELAY["feedback"]), flush=True)
    print("", flush=True)
    print("Keep tapping or rubbing the far end of the cable for the next "
          "%d seconds." % int(PHASES * 2 * PHASE_S + CONTROL_S), flush=True)

    device = foundation._open_checked()
    try:
        device.establish_effects_return(
            bus="main", return_db=float(return_db),
            channel_mix=float(channel_mix))
        device.reverb_off()
        print("  reverb OFF", flush=True)
        for _phase in range(PHASES):
            device.set_fx(model, **dict(kwargs, on=True))
            print("  FX ON  — taps should echo, about %.0f ms apart"
                  % (DELAY["time_s"] * 1000), flush=True)
            time.sleep(PHASE_S)
            device.set_fx(model, **dict(kwargs, on=False))
            print("  FX OFF — taps should be dry", flush=True)
            time.sleep(PHASE_S)
        # Whatever the answer above, prove the return was carrying sound.
        if reverb:
            device.set_reverb(**dict(reverb, on=True))
            print("  CONTROL: reverb ON — if you hear this, the return was "
                  "live the whole time", flush=True)
            time.sleep(CONTROL_S)
    finally:
        notes = shared.restore(device, prior)
        if return_known:
            device.set_send_db("fxreturn/ch1", "main", return_db)
            notes.append("Host-known fxreturn/ch1 -> Main %+.2f dB resent"
                         % return_db)
        if mix_known:
            device.set_fx_mix(1, channel_mix)
            notes.append("Host-known channel 1 processing scalar %.3f resent"
                         % channel_mix)
        state = shared.readable_state(device.read_params())
        device.close()
        print("restored: %s" % "; ".join(notes), flush=True)
        print("main %.3f  headphones %.3f  ch1 gain %.1f dB"
              % (state["main_volume"], state["headphone_volume"],
                 state["input1_gain_db"]), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
