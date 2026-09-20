# Candidate: corrected VoiceFX objective acceptance

Status: staged, not promoted

## Done

- Ran the user-authorized no-listening Transformer A/B/A test twice.
- Used the corrected UC 4.7.2 block-201 transaction.
- Restored all changed readable controls and Host-known write-only intents.

## Verified

- Target identity: serial `AB7C22200355`, firmware `0128`.
- Correct live frame order and state-only edits.
- Quiet preflight and gate/path positive control passed.
- Two stable, same-sign Transformer-on deltas: -3.765 and -3.086 dB.
- Exact readable restoration; no restoration errors; battery 76% before/after.
- Mixer routes, slots, DSP Amount, and `processingChannel` were untouched.

## Unverified

- The preregistered six-MAD effect threshold was not reached.
- Corrected Host VoiceFX therefore does not yet have objective audible
  acceptance under the existing classifier.
- Models 1 through 5 were outside this bounded run.

## Decisions

- Do not weaken or reinterpret the detector after observing the data.
- Do not label the same-sign deltas either a pass or proof of no effect.
- Do not rerun or expand live scope without a new exact authorization.
- Do not promote this candidate silently.

## Evidence

- `RESULT.md`
- `attempt-1/live-report.json`
- report SHA-256
  `cf507c3483f50bc1ac3a91cae062542de3eaf5d43e551ac61a94cd54c0271219`

## Next

Use deterministic waveform capture through a physical loopback, or authorize
the existing Channel-2-zero meter discriminator with an exact positive DSP
Amount restore value. Neither needs human listening.
