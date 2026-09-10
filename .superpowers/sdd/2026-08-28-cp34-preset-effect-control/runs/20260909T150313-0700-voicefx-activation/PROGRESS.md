# Voice FX activation progress

Status: `DELAY_NEGATIVE_DETUNER_DEFAULT_CORRECTED_LISTENING_PENDING`

At 96 percent battery, the Host was closed and serial `AB7C22200355` read back
with Channel 1 already owning Voice FX, both channel processing scalars nonzero,
slots 0 and 2 selected, and flags 385. The bounded transition disabled shared
reverb for isolation, reasserted Channel-1 ownership, set Channel 1 processing
mix to 100 percent, and then sent a 240 ms, 75-percent-feedback, 100-percent-wet
Delay as the final operation. Two block-201 messages completed. Readable flags,
slots, and processing ownership were unchanged afterward.

The user reported that only reverb was audible. The Delay transition is therefore
a live negative, and the candidate processing-mix ordering change was removed:
that control belongs to the shared reverb path, not the Voice FX insert.

Inspection of Detuner found a separate concrete Host defect. Its Tune default was
index 8, which is zero semitones and therefore audibly dry. UC's Detuned Vocal
record uses index 1, 80-percent wet, and `on=1`; the Host now uses those audible
defaults. At 95 percent battery those exact values were sent to Channel 1 in
three writes, and the patched Host was reopened. Human confirmation of the pitch
drop remains pending. The stale section description was also removed. The
affected suite passes 164/164 with `ResourceWarning` elevated to error.

A passive 14-second six-channel capture confirmed strong Input-1 signal at
-10.09 dBFS. The captured physical-source mapping carried no Mix A/B output in
channels 3-6, so it cannot independently establish the effect. The raw capture
is retained temporarily at `/tmp/io24-voicefx-delay-20260909-alsa.wav`; its
hash and bounded analysis are in `CAPTURE-ANALYSIS.json`. The user's direct
listening report, not this capture, establishes the Delay negative.
