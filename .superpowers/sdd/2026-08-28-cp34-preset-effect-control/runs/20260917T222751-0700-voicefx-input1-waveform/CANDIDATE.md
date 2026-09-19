# Candidate: Input-1 VoiceFX waveform proof

State: `synthesized`, staged only, not promoted.

## Done

- Ran the authorized guarded Input-1 waveform sequence once.
- Compared all six capture channels with the exact played stimulus.
- Compared the same correlation metric with the valid Input-2 attempt.
- Checked the UC component model for an Input-1 source/mode control.
- Ran the separately authorized Input-1 sequence after the cable was reseated.
- Corrected the classifier's post-DSP reference assumption and reclassified
  the immutable attempt-2 WAV files.

## Verified

- Physical Input 1 did not receive a usable waveform: -60.873 dBFS active,
  0.029 dB gate contrast, and 0.047 normalized stimulus correlation.
- Capture channel 2 contained only a -116.845 dBFS correlated trace, below the
  -75 dBFS validity floor.
- The valid Input-2 calibration measured -20.604 dBFS and 0.987 correlation.
- UC models both hardware inputs as identical `MicLineInputChannel` components
  and exposes no mic/line/Hi-Z source-selection parameter.
- Sink mute, Input-1 gain, all readable state, VoiceFX/reverb state, and all
  changed write-only routes restored exactly.
- Attempt 2 had a strong, stable Input-1 waveform and a +12.576 dB reverb
  positive control.
- Corrected Host Delay produced programmed 250/500/750 ms repeat energy in
  both cycles, with +12.971 dB and +12.985 dB maximum rises.
- All VoiceFX-off source stages held within 0.003 dB and all off-state Mix-A
  gaps within 0.064 dB.
- Attempt-2 restoration returned Input-1 gain exactly to 11 dB and matched
  every readable field; sink mute and write-only state also restored.

## Unverified

- The other four model-specific audio signatures have not been waveform-tested
  in this run. Transformer has separate live evidence; Delay now has direct
  repeat-timing proof.
- Simultaneous processing of both structural lanes remains unproved.

## Decisions

- Do not interpret any reverb or Delay delta from attempt 1's invalid source.
- Do not add a speculative Host input-mode control; UC exposes none.
- Do not generalize the valid Input-2 Delay null to Input 1.
- Keep the candidate staged until the user explicitly authorizes promotion.
- Treat Delay-on changes in the post-DSP Input-1 USB send as effect evidence;
  source stability is evaluated only while VoiceFX is off.
- The corrected Linux Host VoiceFX Delay path is working on physical Input 1.

## Evidence

- `attempt-1/live-report.json`
- SHA-256: `b2169d4bc3e2bf42f652677ec2cb373ad2036425950040e252efd542d0fe3c04`
- `attempt-1/cross-channel-stimulus-analysis.json`
- `attempt-2/live-report.json`
- SHA-256: `979c420f72df209f5df7716e81bdca4e4ca1902ffcdb07c515c9b089dedbdca5`
- `attempt-2/corrected-verdict.json`
- SHA-256: `f186a6dd4b141f0f29e800f35d074b29790db0e62b95aa8064d9dfa3c3aea84d`
- `tests/test_io24_voicefx_waveform_probe.py`: 9/9 passed after the classifier
  correction.
- Focused VoiceFX regression set: 115/115 passed.

## Next

No further live action is required for the proven Input-1 Delay path. Keep the
candidate unpromoted pending user direction. Separate model-by-model waveform
coverage is optional follow-up and would require fresh live authorization.
