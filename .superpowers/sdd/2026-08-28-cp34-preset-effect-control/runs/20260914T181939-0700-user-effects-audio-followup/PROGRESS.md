# CP34 user effects audio follow-up

Status: `PRESET_LOAD_DECOUPLED; INPUT1_ASSIGNMENT_REASSERTION_ELIMINATED; CHANNEL2_DSP_ZERO_ELIMINATED; FRESH_ENUMERATION_RETEST_INCONCLUSIVE_ACTIVE_SOURCE`

## 2026-09-14T22:06-07:00 fresh-enumeration retest

The io24 re-enumerated and the already-authorized reordered run completed with
Transformer before the configured-gate control. It cannot be classified. Input
1 was carrying a large changing signal rather than stable preamp self-noise:
the two Transformer-off baselines drifted **-5.112 dB**, their maximum MAD was
**3.194 dB**, and Input 1 itself changed **-12.973 dB** across the later gate
control. The computed Transformer midpoint delta was **-2.965 dB**, but no FX
inference is valid under those source/baseline failures. Classification:
`INCONCLUSIVE_METER_ROUTE_CONTROL_FAILED`.

Restoration succeeded with no errors. Every readable prestate matched: flags
385, Input-1 gain 46 dB, Main 0.4500003, headphones 0.6800003, link/phantom,
and processing permutation 0/1. The supplied Channel-2 amount 1.0 was resent
and its zero/nonzero readback returned to nonzero; Host-known Detuner-off and
gate intent were resent. Battery was 42 -> 41%. Presets, routes, firmware,
Wine, and power state were untouched. Report:
`voicefx-channel2-zero-live-attempt-3/live-report.json`.

This does not refute the initial-model-0 hypothesis. A further meter run must
first prove Input 1 is at a stable self-noise floor before any state write; it
must abort read-only if the source is active.

That pre-write guard is now implemented and unit-tested. It records two full
JaSt windows, requires both Input-1 medians at or below 0.01 and their drift at
or below 1 dB, and returns `BLOCKED_INPUT1_NOT_QUIET` without a state write if
either condition fails. A valid follow-up should repeat Transformer on/off and
require both off returns, rather than treating a one-time persistent step as an
effect.

The follow-up mode is now executable as `--transformer-repeatability`. It
leaves Channel-2 DSP Amount untouched, runs two complete Transformer A/B/A
cycles only after the read-only quiet gate passes, requires stable off returns
and same-sign detected on deltas, and keeps the direct-gate positive control
last. Twelve probe tests and its dry run pass. Live execution requires fresh
exact authorization.

## 2026-09-14T19:12-07:00 latest controlling result

The authorized Channel-2-zero discriminator recreated the lone positive's
flags 449 without recreating its effect. With Channel-2 DSP Amount temporarily
changed from the explicitly authorized 1.0 to zero, Transformer measured
**-0.097 dB** with **0.016 dB** off drift. The same-run direct Channel-1 gate
control moved the selected bus **26.614 dB** with **0.502 dB** Input-1 source
drift. Classification remained
`NO_DIRECT_BLOCK201_METER_EFFECT_DETECTED`.

Restoration was error-free: the supplied Channel-2 DSP Amount 1.0 was resent,
flags returned 449 -> 385 (zero -> nonzero), the Host-known Detuner-off and
Channel-1 gate intent were resent, and every readable field matched the
prestate. The exact positive DSP scalar is not readable. Presets, routes,
`processingChannel`, firmware, Wine, and power state were untouched. Report:
`voicefx-channel2-zero-live-attempt-1/live-report.json`.

Independent review found that this is not a one-variable comparison. The
positive began with the write-only state known as Transformer-off; the null
began Detuner-off. It also used gate-off before a 30 -> 60 dB gain step and
roughly five seconds of pre-FX dwell, versus gain-before-gate-off and roughly
0.5 seconds. Its three bus ratios were mutually equal; the null's Main/Mix-A
and Mix-B ratios were split by about 4.6 dB. `UNTOUCHED` only describes writes
inside a run and does not prove equal cross-run routing/state.

The probe is now ordered FX A/B/A first, direct-gate control second. This avoids
one perturbation but does not isolate it from the other differences. The first
authorized reordered run stopped before device open because `194f:0422` was
absent and made no writes:
`voicefx-channel2-zero-live-attempt-2/live-report.json`. A second `lsusb` check
at 19:12 still found no device. Resume the already-authorized reordered run
when the unit re-enumerates, treating a fresh construction's initial model-0
delegate as the important discriminator rather than claiming exact state
equivalence.

## 2026-09-14T18:55-07:00 controlling live result

The one-time Input-1 assignment reassertion is not the missing activation. On
serial `AB7C22200355`, attempt 3 ran all six models after the guarded same-value
`0/1` assignment. A direct Channel-1 gate control moved the observed bus by
27.041 dB with only -0.131 dB Input-1 source drift, so the meter demonstrably
saw Channel-1 DSP. Every FX model remained within -0.153 to +0.033 dB with
stable off baselines. Classification:
`NO_DIRECT_BLOCK201_METER_EFFECT_DETECTED`.

Restoration was exact: flags 385, Input-1 gain 56 dB, Main 0.8600001,
headphones 0.5100005, phantom/link, and processing order 0/1 all matched the
prestate; Host-known Detuner-off and Channel-1 gate intent were resent. Battery
was 63/64%. Preset slots, routes, DSP Amount, firmware, Wine, and power state
were untouched. Attempt 1 stopped before device writes because Host owned USB;
attempt 2 restored exactly but was inconclusive because the old gain control
had only 56 -> 60 dB available. Both are retained, not promoted.

Comparison with the retained measured Transformer positive exposes one exact
state discriminator. The positive had flags 449: Channel 1 processed and
Channel 2 DSP Amount was exactly zero. Today's valid null had flags 385: both
channels processed. The positive immediately followed the DSP Amount experiment,
whose preflight and exact restoration both pinned Channel 2 to zero. The later
slot test returned Channel 2 to nonzero processing before the subsequent FX
negatives. This is a state difference, not a loading-time theory.

On firmware 0128 the apparent Channel-2 enable is the same wire-4 DSP Amount
scalar, not a separate switch. The device reports only zero versus nonzero, and
the current Host shadow has an exact Channel-1 amount of 1.0 but no Channel-2
amount. Therefore a zero/nonzero discriminator cannot promise exact restoration
unless the user explicitly authorizes restoring Channel 2 to a chosen positive
value. The offline runner now supports a one-model Transformer discriminator
with an exact supplied restore value; its restoration test is green.

## Preset-without-FX acceptance

Named Host preset saving is file-only and performs no device or FX write. A new
explicit regression saves a complete `voicefx.on=0` record, reloads it, and
replays the Fat Channel with `with_fx=False`; it verifies that neither the FX
activation prelude nor `set_fx` is called. Separately, the GUI applies the Fat
Channel first and reports any opted-in FX failure without cancelling or
misreporting the strip load.

## Controlling correction

The user correctly rejected frame loading time as the cause. The positive
Transformer probe inherited an already-armed device after an older Host had
run. That Host reasserted `set_voicefx_channel(1)` before its first model write;
`99c8e7b` removed the prelude, and the later negative tests did not reproduce
it. Timing is no longer claimed as the activation mechanism.

The Host now restores the old prelude on startup, preset FX load, and the first
FX edit. It is guarded to an unchanged live `0/1` routing permutation, so it
cannot silently swap Input 1 and Input 2. Preset replay is now two-stage: the
Fat Channel loads first with FX omitted, and an FX failure is reported
separately without cancelling the preset. The six-model meter runner now
performs the same guarded prelude before its A/B/A sweep.

Everything in this correction is offline. No Host/device/USB operation was
performed.

## User evidence

- The current Host's six Effects-page Voice FX models are all inaudible.
- Shared reverb does not sound like the expected UC reverb.
- A displayed `100 %` reverb setting does not sound wet-only.

This is user auditory evidence, not an instrumented capture. `effects` is scoped
to the six block-201 models, not the separately measured Fat Channel. The user
later clarified that reverb may simply have needed its return above 0 dB, as in
their UC use, and that they approve the new character/movement additions.

## Superseded static diagnosis

- Block 201 has a retained positive: autonomous acceptance attempt 3 measured
  Transformer at -4.024 dB with 0.045 dB drift and a valid 26.248 dB control.
- That positive used selector -> state frames with 20 ms between every frame.
- `f39f1a8` replaced it with selector -> 60 ms -> selector replay -> state, and
  its live Host-v2 run was negative. The current listening failure is therefore
  a plausible Host regression, not proof that the unit cannot run FX.
- Shared block-202 reverb is a parallel FX return. Its internal mix at 100%
  does not mute the channel's direct Main route.
- The Host's named reverb characters are locally authored combinations of the
  one device algorithm's size, high-pass, and pre-delay. Spring/Hall/Cathedral
  may also enable Host-driven room-size modulation. None is a recovered UC
  algorithm or captured UC preset.

## Superseded timing correction and retained UI corrections

- Restored `Io24.send_fx` to the exact measured-positive builder order and
  removed the extra selector replay.

- `Wet mix` -> `Reverb return blend`, with direct-Main semantics explicit.
- `Character` -> `Host approximation`, explicitly not separate device
  algorithms.
- Movement says it is Host-driven and not a device mode.
- The FX group states that the last measured-working order is restored and all
  six models still need a live recheck.

No USB access, device state, Wine state, firmware, preset, or network operation
occurred. The Host send ordering changed offline and is regression-tested.

## Fat Channel observation

The user heard only minimal possible Channel-1 compression before starting the
Host, then clearly heard the Fat Channel once the Host was running. This matches
the Host's `_resume_session` behavior: write-only HPF/EQ/dynamics state is
reapplied on attach. It is useful positive context for the general DSP control
path but not a scalar measurement.

## Next evidence

Run the current Host and recheck Transformer first, then the other five models.
That live device interaction requires fresh exact authorization. The stored-FX
cold-boot experiment is no longer the cheapest first move: restore and test the
known-positive direct sequence before changing any slot or cycling power.
