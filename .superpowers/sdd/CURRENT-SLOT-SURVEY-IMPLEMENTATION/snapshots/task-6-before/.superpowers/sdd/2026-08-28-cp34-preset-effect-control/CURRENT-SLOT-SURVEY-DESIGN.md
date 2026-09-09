# CP34 current-slot Voice FX survey design v2

Date: 2026-08-29
Status: approved revision 2; offline only; no live authority
Evidence protocol: `cp34-current-slot-evidence-v2`

Revision 2 supersedes the revision-1 plan/result schemas and root input-manifest
layout. It makes each attempted candidate independently immutable before its
verifier runs, then creates one terminal run-wide seal. The user selected the
recommended correction path after the revision-1 final review; this amendment
does not authorize a live run.

## Objective

Determine whether either currently selected front-panel preset produces a
repeatable audible 150 ms delay signature when its preset processing is enabled,
without identifying the preset by title and without changing slot selection,
mixer routing, gain, monitor level, reverb, Voice FX parameters, or any other
mapped device value.

The survey is positive-only. A positive can establish an audible delay-type
preset effect controlled by the front-panel enable/bypass action. A null result
is inconclusive because this no-write survey has no same-run device-DSP positive
control. It cannot identify `Slap Echo`, prove a model identity, prove custom
device-resident storage, or close CP34 by itself.

## Fixed scope

- Target device: serial `AB7C22200355` only.
- Candidate order:
  1. channel 1, currently selected numeric slot 0 (`ch1-slot1`);
  2. channel 2, currently selected numeric slot 2 (`ch2-slot1`), only if the
     first candidate is inconclusive.
- Stop after the first restored `SIGNATURE_PRESENT` result.
- Never short-press a Preset button or otherwise change the selected slot.
- The only permitted device-state mutation is one front-panel long press to
  enter the opposite enable/bypass state and one long press to restore the
  initial state.
- Interface-5 activity is limited to bounded JaSt reads before the first
  transition, after the first transition, and after the restoring transition.
  Every claim is released before audio work resumes.
- Wine, `/home/ajuntanaga/.wine-io24`, network access, firmware operations,
  reset, DFU, installation, staging, USB detach, mapped writes, guessed packets,
  io24 playback, and io24 live monitoring remain prohibited.
- Stop at or below 10 percent battery.

This document is a design. A future authorization must name the serial, run
directory, physical source/cable/input, ALSA capture, manual long presses,
bounded interface-5 reads, evidence creation, and the exact inverse action.

## Physical signal path

Use a separate line-level playback device, never an io24 output, to feed one
declared io24 input at a time. Before a live run, record:

- playback-device identity and power source;
- exact local stimulus file and SHA-256;
- cable and adapter chain;
- target io24 input;
- external playback-volume setting;
- initial physical connection and the restoration action.

Phantom power must read off. The io24 monitor path is not used. No io24 gain or
level is adjusted. The mapping capture must place the raw-input peak between
-36 and -12 dBFS and every captured channel below -3 dBFS. If the level is
outside that window, stop before a preset toggle. A later authorization may
permit adjustment of the external source only; it does not permit an io24
setting change.

Audible attestation occurs only after `P2`, `S4`, and physical-connection
restoration. Replay each of the four preserved mono derivatives, one at a time,
through a separate non-io24 playback and monitoring path. The operator must
attest both active derivatives heard and both dry derivatives not heard; a
single stimulus replay through the controlled io24 path cannot earn that
attestation. Nothing is monitored live through the io24.

## Audio capture and channel freeze

Capture the io24 with `hw:CARD=R24,DEV=0`, six-channel S32_LE at 48 kHz. Preserve
each raw interleaved WAV unchanged. Create analysis derivatives only after the
raw file is closed and hashed.

Historical source-bound evidence maps analog inputs to USB capture channels
1-2 and Mix A to channels 3-4. The live mapping row verifies that relationship
without changing device state:

1. The declared raw-input channel must contain five isolated impulses with the
   pinned stimulus cadence.
2. Only Mix A channels 3 and 4 are candidates for effect observation.
3. Score channels 3 and 4 against the simultaneous raw-input channel using
   normalized cross-correlation over lags from 0 to 250 ms.
4. A candidate is usable only if it contains the same five-impulse cadence and
   its best absolute normalized correlation is at least 0.80.
5. Freeze the higher-scoring usable Mix A channel before any preset action. If
   the scores are equal to six decimal places, freeze the lower-numbered
   channel. Record both scores and the selection rule.
6. If neither Mix A channel is usable, label the candidate `UNAVAILABLE` and do
   not press a Preset button. Do not scan channels 1, 2, 5, or 6 for a more
   favorable result.

The frozen Mix A channel is used for every dry and active derivative for that
candidate. It cannot be reselected after an effect result is visible.

## Adaptive two-toggle sequence

All ALSA streams must be stopped before an interface-5 read. Interface 5 must be
released before the next ALSA capture. Control reads and audio streaming never
overlap.

For each candidate:

1. `P0`: read and hash JaSt. Confirm the expected numeric slot is still selected,
   record initial enable/bypass state, processing-channel mapping, phantom,
   gains, and monitor values. A slot mismatch makes the candidate unavailable;
   do not select it.
2. `M0`: with state unchanged, acquire and hash the six-channel mapping capture.
   Freeze one Mix A analysis channel using the rule above.
3. `S1`: acquire the first capture in the initial state.
4. `T1`: after all streams close, perform exactly one long press on that
   channel's Preset button. Do not repeat a press that produces no clear state
   transition.
5. `P1`: perform a bounded JaSt read. The selected numeric slot must be unchanged
   and the enable flag must equal the logical inverse of `P0`. Otherwise enter
   restoration handling immediately.
6. `S2` and `S3`: acquire two captures in the opposite state.
7. `T2`: after all streams close, perform exactly one restoring long press.
8. `P2`: perform a bounded JaSt read. The selected slot and enable flag must
   equal `P0`. The declared stable restoration fields must also match `P0`.
9. `S4`: acquire the second capture in the restored initial state. This is
   evidence that the signal observation and readable state both survived the
   restoration boundary.

If `P0` is enabled, `S1` and `S4` are active while `S2` and `S3` are dry. If
`P0` is bypassed, `S1` and `S4` are dry while `S2` and `S3` are active. The
analyzer always receives exactly two dry and two active derivatives; filenames
do not determine their role.

## Restoration contract

The pre-run plan is valid only when it declares:

- schema `cp34-current-slot-survey-plan-v2` and evidence protocol
  `cp34-current-slot-evidence-v2`;
- run ID and exact device serial;
- exactly the two fixed candidates in the required order, with the second
  conditionally executable only after a restored inconclusive first result;
- `stop_on_first_positive: true`;
- external line-level source provenance;
- the fixed ALSA format and six-channel capture;
- the three bounded JaSt checkpoints;
- exactly two `manual_preset_toggle` actions per attempted candidate;
- no slot-selection or mapped-write action;
- the initial physical connection and inverse restoration text;
- the evidence directory; and
- the battery floor.

An executable validator must reject missing fields, a different serial, reversed
candidate order, any candidate other than the two current slots, a device-output
source, a non-48-kHz or non-six-channel format, continuous interface claims,
fewer or more than two toggles, mapped writes, slot selection, missing physical
inverse text, or a battery floor below 10 percent.

Post-run restoration passes only when:

- `P2` has the same selected numeric slot and enable flag as `P0`;
- processing-channel mapping, phantom state, input gains, headphone/main volume,
  and monitor blend match the declared stable `P0` fields;
- the action log contains exactly the authorized two long presses and no short
  press or mapped write;
- `S4` is present, valid, and uses the frozen Mix A channel;
- the physical connection is restored and operator-attested; and
- all plan, snapshot, action-log, raw-WAV, derivative, analysis, and attestation
  files are hashed.

Write-only state is never claimed restored because the survey does not change
it. JaSt cannot prove every internal DSP byte; the report must retain that
limitation.

If a failure occurs after `T1`, the only allowed recovery is the predeclared
inverse `T2`, and only when `P1` or unambiguous front-panel observation shows the
opposite state. If neither can establish state, do not blind-toggle. Record
`RESTORATION_FAILED` and stop for user direction.

## Evidence layout

Create one immutable directory under the active CP34 task:

`runs/<timestamp>-current-slot-survey/`

It contains:

- `PLAN.json` and its validation report;
- one directory per attempted candidate, named `ch1-slot1/` or `ch2-slot1/`,
  containing `P0.json`, `P1.json`, and `P2.json` JaSt summaries plus the
  untouched raw JaSt snapshots they reference;
- each candidate's `ACTION-LOG.jsonl` with monotonic timestamps;
- each candidate's `MAP.raw.wav` and `S1.raw.wav` through `S4.raw.wav`;
- each candidate's frozen-channel mono derivatives, channel-map result, A/B
  analysis, and post-restoration audible-attestation JSON;
- each attempted candidate's own `EVIDENCE-SHA256SUMS`, covering every input
  consumed by that candidate's restoration verifier;
- each attempted candidate's own `RESTORATION.json` using schema
  `cp34-current-slot-restoration-v2`;
- a human-readable `REPORT.md`; and
- `SHA256SUMS` covering every retained file except itself.

Never overwrite an existing run directory or evidence file.

For channel 1, `ch1-slot1/EVIDENCE-SHA256SUMS` covers `PLAN.json` plus every
channel-1 verifier input and excludes only its own manifest and later output
files. It is sealed with NUL-safe, `pipefail`, no-clobber semantics before the
channel-1 verifier runs. Save the result without replacement as
`ch1-slot1/RESTORATION.json`.

Only a restored inconclusive channel-1 result permits collection of channel 2.
Before channel-2 verification, `ch2-slot1/EVIDENCE-SHA256SUMS` covers
`PLAN.json`, every channel-2 verifier input, and the immutable channel-1 input
manifest and restoration result. It uses the same NUL-safe, `pipefail`,
no-clobber publication rule. The channel-2 verifier must independently verify
and recompute the complete channel-1 predecessor evidence; the saved result is
not proof by itself.

There is no root `EVIDENCE-SHA256SUMS` or root `RESTORATION.json` in evidence
protocol v2. After the first restored positive or the terminal attempted
candidate, write root `REPORT.md` and create root `SHA256SUMS` over every
retained file except itself. Verification of that terminal manifest is the
last offline seal step.

## Outcomes

`SIGNATURE_PRESENT` requires all of the following:

- both active derivatives have a repeatable 150 ms peak at least 6 dB above the
  worst dry derivative;
- both dry derivatives remain below the existing dry-repeat threshold;
- stimulus cadence matches across all four captures;
- the operator hears the repeat in both active derivatives and not in either dry
  derivative during post-restoration replay;
- the frozen Mix A channel was selected before toggling;
- `P2` and the restoration contract pass; and
- all evidence hashes verify.

The claim is: the current preset enable/bypass action caused a restored,
repeatable audible 150 ms effect signature on the controlled io24 path. Model
identity and title remain unresolved.

`INCONCLUSIVE` covers no distinctive signature, a non-specific late tail, or
failure of audible attestation after successful restoration. Proceed from
channel 1 to channel 2 only for `INCONCLUSIVE`.

`UNAVAILABLE` covers pre-mutation identity, level, map, capture, or battery
failure. `RESTORATION_FAILED` covers any unresolved post-mutation state or
physical restoration mismatch. Neither permits another candidate.

## Offline implementation and review gates

Before any live authorization request:

1. Add a hardware-free plan validator and post-run restoration verifier.
2. Add deterministic six-channel mapping fixtures, including channel 3, channel
   4, equal-score, absent-Mix-A, wrong-cadence, and clipping cases.
3. Add adaptive enabled-first and bypassed-first run fixtures.
4. Prove malformed action logs, extra toggles, short presses, mapped writes,
   slot drift, missing `S4`, incomplete hashes, and failed physical restoration
   are rejected.
5. Keep all file analysis independent of `io24.py`; the tools must not open USB
   or ALSA.
6. Reproduce the complete hardware-free suite, update the CP34 evidence ledger,
   refresh `RESUME.md`, and verify `LINUX-OFFLINE-SHA256SUMS`.
7. Obtain an independent review of the written procedure and executable gates.

Passing these offline gates makes an exact live authorization request possible.
It does not itself authorize the run.
