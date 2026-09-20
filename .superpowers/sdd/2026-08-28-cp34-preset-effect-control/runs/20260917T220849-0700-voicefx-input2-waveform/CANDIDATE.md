# Candidate: Input-2 VoiceFX waveform proof

State: `synthesized`, staged only, not promoted.

## Done

- Built an Input-2-specific gated waveform probe with exact shadow-backed
  restoration and anti-feedback ordering.
- Ran attempt 1 through reverb control and two Delay cycles.
- Added an exact PipeWire sink mute guard after diagnosing the invalid run.
- Ran attempt 2 with the authorized temporary sink unmute.
- Added ordered, readable Input 2 gain staging and exact restoration locally.
- Ran attempt 3 with the authorized 60 dB Input-2 gain stage.
- Generalized the audited probe to physical Input 1 or 2 without adding any
  `processingChannel` write.

## Verified

- Seven hardware-free contracts pass.
- Attempt 1 restoration is exact for all readable fields and all five changed
  write-only routes.
- The io24 PipeWire sink was `MUTED`; Input 2 was digital silence, so the run
  correctly blocked before making a VoiceFX inference.
- Attempt 2 proved Main L -> Input 2 and stable gating, but measured only
  -116.872 dBFS; sink mute and all device state restored exactly.
- Nine hardware-free contracts pass, including channel-specific route, gain,
  mute, shadow-restoration and dry-plan checks for Input 1.
- Attempt 3 is a valid Input-2-lane null: source -20.604 dBFS, reverb control
  +23.305 dB, stable off states, and no Delay taps in either cycle.
- Sink mute, Input 2 gain, all readable state, VoiceFX/reverb state, and five
  write-only routes restored exactly.

## Unverified

- Corrected Delay is objectively absent on the tested Input-2 lane.
- The corresponding physical Input-1 waveform result remains unmeasured.

## Decisions

- Do not classify attempt 1 as a VoiceFX null.
- Preserve the sink's 0.40 volume; change only its mute bit.
- Re-mute the sink before restoring any device route that can feed the cable.
- Restore Input 2 gain to 0 dB before reopening either Main feedback route.
- Do not generalize the Input-2 null to Input 1; prior live model-0 evidence is
  Input-1-specific and simultaneous two-lane processing was never proved.

## Evidence

- `attempt-1/live-report.json`
- SHA-256: `fbfe60db79f98d5dbc2ac547dba61ef5c6d99c375791a40adf3782779c147f4d`
- `attempt-2/live-report.json`
- SHA-256: `bc3c6565425d364a900b185393f0b511f4ec66895e5960f93e5966161c5fb256`
- `attempt-3/live-report.json`
- SHA-256: `cc1266fef8df88106641ca0f8d1d32b7b312b40e2462ed929fcd00123b2df504`
- `tests/test_io24_voicefx_waveform_probe.py`: 9/9 passed.

## Next

Prepare the same guarded waveform probe for physical Input 1. Ask the user to
move Main Out L from Input 2 to Input 1, then obtain/confirm exact live scope,
run once, restore exactly, and promote nothing without the resulting evidence.
