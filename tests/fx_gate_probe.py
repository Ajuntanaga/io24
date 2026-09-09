#!/usr/bin/env python3
"""Retired direct Voice FX probe retained as historical analysis.

The active procedure is CP34's supported-host `CAPTURE-MANIFEST.md`. Running
this file performs no device action; the old implementation remains below for
provenance only.

The standing blocker (PROTOCOL §13c-§13m): block 201's handler does nothing
unless three flags on its object are set, and those flags are written by the
firmware's signal-chain BUILDER, which no host message was known to invoke.
Every FX blob this driver sends is accepted, stored, and silent.

What changed 2026-08-10: preset recall works from Linux (`presetMode` wire 17,
§13r) and the firmware's factory preset table carries `voicefx` sections. If a
recall runs the chain builder, it might set the gate flags as a side effect.
This test asks that question and gets an answer either way.

NO LOOPBACK AND NO SIGNAL SOURCE. A cable left plugged into an input and
unterminated is an antenna: at high preamp gain it delivers mains hum, which
is all this needs. Mix A loops back to USB capture 3-4, so the whole path is
inside the box.

The design that matters is the POSITIVE CONTROL. A null result is worthless
unless the same rig can detect a working block, so every run measures the
REVERB (block 202, known good) through the identical send/return/capture path
before judging the voice FX (block 201). If the reverb does not arrive, the
run reports itself inconclusive instead of claiming a negative.

Read the steps as one variable each:

    1  every Mix A source hard-off        -> must be digital silence
    2  + FX return into Mix A             -> proves the return bus carries
    3  + FX send open, mix fully wet      -> dry falls away, wet is whatever
                                             the DSP block produces
    4  + reverb on          [block 202]   -> POSITIVE CONTROL
    5  + voice FX on        [block 201]   -> the subject
    6  preset recall, then 5 again        -> does a recall open the gate?

    python3 tests/fx_gate_probe.py
"""

import math
import os
import struct
import subprocess
import sys
import tempfile
import time
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import io24  # noqa: E402

CARD = "R24"
RATE = 48000
CAPTURE_CH = 6
MIXA_CH = 2               # USB capture 3, zero-based — verified by A/B, not
                          # assumed: muting the Mix A send drops it to -280 dB
                          # while every other capture channel sits unchanged
GAIN_DB = 55.0            # the cable's own pickup, well clear of the floor
PROBE_HZ = (60.0, 220.0, 440.0, 880.0)
DETECT_DB = 3.0           # a block "produces output" if it moves the wet path
                          # by more than this


def capture(seconds=2):
    tmp = tempfile.mktemp(suffix=".wav")
    r = subprocess.run(
        ["arecord", "-D", "plughw:CARD=%s" % CARD, "-f", "S32_LE",
         "-c", str(CAPTURE_CH), "-r", str(RATE), "-d", str(seconds), tmp],
        capture_output=True)
    if r.returncode != 0 or not os.path.exists(tmp):
        return []
    w = wave.open(tmp); n = w.getnframes(); raw = w.readframes(n); w.close()
    os.unlink(tmp)
    if n < RATE // 2:
        return []
    v = struct.unpack("<%di" % (n * CAPTURE_CH), raw)
    ch = [x / 2147483648.0 for x in v[MIXA_CH::CAPTURE_CH]]
    return ch[len(ch) // 6: -len(ch) // 6]


def goertzel(s, f):
    """Energy at one exact frequency — sharper than an FFT bin when the
    question is 'is there something precisely here?'."""
    k = 2.0 * math.cos(2.0 * math.pi * f / RATE)
    s1 = s2 = 0.0
    for x in s:
        s0 = x + k * s1 - s2
        s2, s1 = s1, s0
    return math.sqrt(max(0.0, s1 * s1 + s2 * s2 - k * s1 * s2)) / len(s)


def db(x):
    return 20 * math.log10(x) if x > 1e-14 else -280.0


def step(tag):
    s = capture()
    if not s:
        print("  %-38s NO CAPTURE" % tag)
        return None
    rms = db(math.sqrt(sum(x * x for x in s) / len(s)))
    tones = "  ".join("%.0fHz %6.1f" % (f, db(goertzel(s, f))) for f in PROBE_HZ)
    print("  %-38s rms %7.1f   %s" % (tag, rms, tones))
    return rms


def arm_voicefx(d):
    d.set_fx("vocoder", carrier_type=1, carrier_freq=220.0, vol=1.0, mix=1.0)


def _legacy_probe():
    d = io24.Io24()
    print("Leave a cable in input 1. No loopback, no signal source needed.\n")
    d.set_gain(1, GAIN_DB)
    for src in d.MIXER_SOURCES:
        d.set_send_db(src, "mixa", None)      # None is the off sentinel; a
                                              # very low dB value is not
    d.set_fx_mix(1, 0.0); d.set_fx_mix(2, 0.0)
    d.set_reverb(on=False)
    time.sleep(0.8)

    print("Mix A sources all hard-off, one variable at a time:\n")
    floor = step("1. nothing at all (true floor)")
    if floor is None:
        print("\n  capture failed — is another program holding the card?")
        d.close(); return 1
    if floor > -100:
        print("\n  !! the floor is not silent — something else feeds Mix A.")
        d.close(); return 1

    d.set_send_db("fxreturn/ch1", "mixa", 0.0); time.sleep(0.8)
    ret = step("2. + FX return into Mix A")

    d.set_fx_mix(1, 1.0); time.sleep(0.8)
    wet = step("3. + FX send open, fully wet, no effect")

    d.set_reverb(on=True, size=0.9, mix=1.0, hp_freq=0.0, predelay=0.05)
    time.sleep(1.2)
    rev = step("4. + REVERB on          [block 202]")

    d.set_reverb(on=False); time.sleep(0.5)
    arm_voicefx(d); time.sleep(1.2)
    vfx = step("5. reverb off, VOICE FX [block 201]")

    print("\n6. recall a device preset, then re-arm the voice FX")
    cur = d.read_params()["input1SlotIndex"]
    d.set_preset_slot(1, 1 if cur == 0 else 0); time.sleep(2.0)
    print("   channel 1 slot %d -> %d"
          % (cur, d.read_params()["input1SlotIndex"]))
    arm_voicefx(d); time.sleep(1.2)
    vfx2 = step("   voice FX after recall  [block 201]")

    print("\n" + "=" * 78)
    print("  FX return carries signal   : %+.1f dB over floor" % (ret - floor))
    print("  blending fully wet         : %+.1f dB" % (wet - ret))
    print("  REVERB   (202) contributes : %+.1f dB   <- positive control"
          % (rev - wet))
    print("  VOICE FX (201) contributes : %+.1f dB" % (vfx - wet))
    print("  VOICE FX after a recall    : %+.1f dB" % (vfx2 - wet))
    print("=" * 78)

    if rev - wet < DETECT_DB:
        print("INCONCLUSIVE: the reverb did not arrive either, so this rig")
        print("  cannot presently tell a working block from a dead one.")
        rc = 1
    elif vfx2 - wet > DETECT_DB and vfx - wet <= DETECT_DB:
        print("THE RECALL OPENED THE GATE. Voice FX produces output only")
        print("  after a preset recall — §13m has a way in.")
        rc = 0
    elif vfx - wet > DETECT_DB:
        print("VOICE FX IS ALREADY RUNNING — the gate is not closed the way")
        print("  §13c-§13m concluded.")
        rc = 0
    else:
        print("STILL GATED, and this is a real negative, not a rig failure:")
        print("  the reverb reached Mix A through the very same send, return")
        print("  and capture path in the same run. Block 201 contributes")
        print("  nothing, before or after a preset recall.")
        rc = 0
    print("=" * 78)

    d.set_fx_mix(1, 0.0); d.set_fx_mix(2, 0.0); d.set_reverb(on=False)
    d.set_send_db("line/ch1", "mixa", 0.0)
    d.set_gain(1, 5.0)
    d.close()
    return rc


def main():
    print("Direct probe retired; use CP34 CAPTURE-MANIFEST.md C00-C07.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
