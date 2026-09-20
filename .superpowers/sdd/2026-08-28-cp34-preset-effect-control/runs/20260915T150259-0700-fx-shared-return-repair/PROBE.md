# The block-201 shared-return probe, and why it is shaped this way

`re/io24_fx_shared_return_probe.py`, schema `io24-fx-shared-return-probe-v2`.
Offline only so far: 26 hardware-free tests pass and no device action has run.

## What it measures, and where

The return, not the direct path. Every CP34 block-201 measurement ratioed the
JaSt `main`/`mixa`/`mixb` meters against Input 1 without opening the channel FX
send or assigning `fxreturn/ch1` into the bus it measured — the one path the
2026-07-28 hardware result says the block does not reach. This probe assigns
`fxreturn/ch1` into Mix A and captures Mix A natively.

## Why the stimulus is gated

The user's suggestion, and it is the right one. The probe plays its own gated
stimulus — five cycles of a 0.5 s burst (800 Hz + 1234 Hz plus a noise bed at
−12 dB, total −30 dBFS) and 1.0 s of silence — instead of relying on the
feedback loop's continuous signal. A silent gap is the strongest evidence
available: nothing but an effect's own tail can put energy into it.

| model | evidence |
|---|---|
| delay | energy at burst end + k × 250 ms, k = 1,2,3, each landing in silence |
| reverb | a decaying tail in the gap — the in-run positive control |
| ring mod | sidebands at \|f ± carrier\| inside the bursts, for two unrelated carriers |
| de-tuner | a partner partial at f × 2^(−8/12) |
| transformer | broadband level only; reported, never votes |

A broadband level ratio is blind to four of the six models, and a continuous
tone defeats the autocorrelation test outright — a tone is already self-similar
at every lag that is a whole number of its periods, which is why the delay test
reports `inconclusive` rather than a null when it meets one.

## Two defects found while building it

**Autocorrelation normalised by the wrong energy.** Dividing by the whole
signal's energy rather than the overlapping segments' scaled every value by the
overlap fraction, so a perfectly self-similar tone read ~0.58 instead of ~1.0
and the tonality gate could never fire.

**An effect with a tail moved its own measurement windows.** Envelope
thresholding absorbed the delay's repeats into one long "burst" and pushed the
tap windows into the next cycle, so the delay could not be detected at all —
and, in the same way, the second ring-mod carrier failed. Windows now come from
`align_bursts()`, which matches the known gate pattern by correlation and
derives every window from one offset. The armed and unarmed captures therefore
use the same windows. Locked in by
`test_a_tail_in_the_gaps_does_not_move_the_burst_windows`.

After the fix, a synthetic ring modulator reads +37 to +40 dB in its sidebands
with the guard bands *falling* 3 to 10 dB, against a gate contrast of 93 dB.

## Validity before verdict

A run reports on block 201 only if the reverb control put a tail in the gap
(≥ 4 dB), the gate is really present (burst − gap ≥ 6 dB), and the two off
states held within 2 dB. Otherwise the status is `INVALID_…` or `BLOCKED_…` and
the FX readings are not evidence. That is the exact failure this probe exists to
stop repeating.

## Safety, by construction

- The only SetP frames permitted are block 100 at the Mix A bus index, block 202
  and block 201. An `'Appl'` frame — gain, volume, the per-channel processing
  scalar, slot, phantom, link — or any mixer frame at the Main bus index fails
  the run. `validate_transport_log()` checks that from the log afterwards, so
  the loop gain the user set is the loop gain throughout.
- The probe refuses to run on a bypassed Channel 1 rather than un-bypassing it:
  that would change what reaches Main, and so the loop.
- Control writes never overlap a stream. Concurrent streaming plus control
  writes is the known cause of this unit dropping to its bootloader, so
  `capture_stage()` closes both `arecord` and `aplay` before returning.
- The FX return goes to Mix A only — a USB capture bus, which cannot feed the
  loop — so a fully wet delay cannot run away through the monitors.
- Restoration runs in `finally`, so a Ctrl+C part way through still puts the
  return and the models back; it is skipped only when the transport log proves
  nothing was written.
- Mixer sends are write-only here. The prior Mix A return level cannot be read
  back: the Host shadow is consulted for an exact value and, absent one, the off
  sentinel is written and the report says so.

## Not done

No USB, device, audio, Host, Wine, network, install, or publication. The live
run needs separate authorization and is one command; battery 73 % on AC.
