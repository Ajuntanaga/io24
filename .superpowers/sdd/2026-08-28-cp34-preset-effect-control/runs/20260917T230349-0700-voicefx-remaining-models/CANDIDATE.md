# Candidate: complete Linux Host VoiceFX repair

State: `promoted`

Promoted locally on 2026-09-17 by the user's explicit `Proceed` instruction,
given immediately after the candidate was reported as staged and unpromoted.
The user then explicitly authorized the focused local integration commit. No
push, upload, release, or external publication is included.

## Done

- retained the exact UC XML rack and one independent `On` control per model;
- retained the exact XML-field -> packet-builder routes for all six models;
- applied the captured UC 4.7.2 lifecycle: select/materialize on model change,
  model-state-only On/Off and parameter edits, no reverb-return mutation;
- objectively exercised both On and Off twice for each of the five models not
  covered by the earlier Delay run;
- corrected the Detuner evidence classifier without changing device packets.

## Verified

- Delay: exact 250/500/750 ms repeats in two cycles in the preceding run;
- Transformer, Detuner, Vocoder, Ring Modulator, and Filters: repeatable
  processing in two cycles each in this run;
- Detuner -8-semitone targets and Ring Modulator 313.7 Hz sidebands are
  frequency-specific, not broadband level guesses;
- reverb positive control, physical source, off states, PipeWire sink, and
  exact device restoration all passed;
- focused VoiceFX regression suite passes.

## Unverified

- simultaneous processing of both physical input lanes;
- standalone VoiceFX audibility from device-resident preset recall;
- an ear-based character judgment for each algorithm (not needed for the
  objective processing result).

## Decisions

- do not change working builders in response to the original Detuner partial;
- treat the raw live report as immutable and publish the corrected verdict
  beside it;
- keep `processingChannel`, DSP Amount, slots, and reverb routing out of
  ordinary VoiceFX edits.

## Evidence

- `SCOPE.md`;
- `RESULT.md`;
- `attempt-1/live-report.json`;
- `attempt-1/corrected-verdict.json`;
- all stage WAV captures and the deterministic stimulus.

## Next

No further repair is required for Host-driven VoiceFX on Input 1. Push,
publication, two-lane testing, or standalone device-preset work requires its
own decision and scope.
