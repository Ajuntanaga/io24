# Host v2 selector replay: zero-output Ring Mod is still inert

Status: `NO_CORRECTED_RINGMOD_ZERO_OUTPUT_EFFECT_DETECTED`

Authorized live run. Unit `AB7C22200355`, firmware `0128`, 96 kHz / 512,
Host closed, battery 67 -> 66 percent.

## Result

Positive control first, as always:

| window | Main/Input-1 | MAD |
|---|---|---|
| gate_off_before | -0.154 dB | 0.341 |
| **gate_on** | **-19.751 dB** | 1.361 |
| gate_off_after | -0.245 dB | 0.302 |

`DIRECT_GATE_EFFECT_DETECTED`, delta **-19.551 dB** against an 8.167 dB
threshold, drift -0.091 dB. The rig is sound.

Ring Mod, fully wet with `vol = 0`, so the firmware's own arithmetic predicts
active dry 0.0 and wet 0.0 -- an installed model would silence the channel:

| window | Main/Input-1 | MAD |
|---|---|---|
| ringmod_off_before | -0.125 dB | 0.213 |
| ringmod_on | -0.361 dB | 0.287 |
| ringmod_off_after | -0.263 dB | 0.269 |

Delta **-0.167 dB** against a 1.722 dB threshold, drift -0.138 dB.

## What this eliminates

Host sequencing v2 -- `VoFx`, wait 60 ms for the bypass fade, replay `VoFx` to
install, then state once -- does **not** install the model. v1 was already a
negative; v2 now joins it.

## The sharpest constraint we have

On the **same channel, at the same moment, through the same meter**, the Fat
Channel gate moved the signal -19.55 dB while block 201 moved it -0.17 dB. So
the channel chain is live and processing, the scheduler is running, the meter
is sensitive, and the routing reaches Main. Whatever stops block 201 is
specific to block 201, not to the channel, the rate branch being idle, the
buffer handoff, or the measurement.

## A boundary worth checking

The scheduler trace gives the root call gate as `device+0x5e71 != 0`, defined
at setup as `device+0x5dc0 <= 96000.0`. This run was at exactly 96 kHz, which
sits precisely on that boundary. If the comparison is strict rather than
inclusive, 96 kHz would be excluded and every block-201 measurement so far --
all of which were at 96 kHz -- would have been made on the wrong branch.

That is cheap to settle empirically without resolving the instruction: repeat
this exact run at 48 kHz. Four interpretations of block 201 have now been
wrong in turn, so a boundary-sense error is worth ruling out by experiment
rather than by reading.

## Restoration

`MEASURED_AND_RESTORED`, no errors. Every readable field matched before and
after except `flags` 385 -> 897, bit 9, which the 2026-09-14 power-cycle
evidence already classifies as session/stream state rather than preset state.
Voice FX and the Channel-1 gate were resent as Host-known write-only intents;
input gain, main volume and headphone volume restored; routing, preset slots,
DSP Amount and processingChannel untouched.

Evidence: `live-report.json`.
