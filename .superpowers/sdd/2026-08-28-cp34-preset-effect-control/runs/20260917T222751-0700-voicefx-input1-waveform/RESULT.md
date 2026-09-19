# Attempt 1 result

Status: `BLOCKED_PHYSICAL_INPUT1_STIMULUS_UNUSABLE`.

The authorized Input-1 capture completed and restored exactly, but the gated
Main-L waveform did not reach physical Input 1. Channel 1 remained a steady
-60.9 dBFS preamp-noise floor: 0.029 dB active/quiet contrast and only 0.047
normalized correlation with the exact stimulus. This is an invalid rig result,
not a VoiceFX Delay result.

An all-channel offline check found one correlated trace on capture channel 2,
but it was only -116.845 dBFS. That is far below the preregistered -75 dBFS
usability floor. For calibration, the same analysis on the valid Input-2
attempt measured -20.604 dBFS and 0.987 correlation on channel 2. Channels 3-6
in this attempt carried only the same steady Input-1 noise into Mix A/Mix B.

Because the physical Input-1 source failed, the apparent reverb and Delay
differences are noise-floor changes and cannot be interpreted. No VoiceFX
conclusion was drawn.

Restoration passed completely:

- battery: 51% before, 50% after;
- the exact io24 PipeWire sink returned to muted at the same channel volumes;
- Input 1 returned from 60 to 0 dB;
- every readable device field matched its prestate;
- the exact Host-known VoiceFX, reverb, and five write-only routes were resent.

Evidence:

- `attempt-1/live-report.json`, SHA-256
  `b2169d4bc3e2bf42f652677ec2cb373ad2036425950040e252efd542d0fe3c04`;
- `attempt-1/cross-channel-stimulus-analysis.json`.

The extracted UC component model exposes both io24 inputs as the same
`MicLineInputChannel` type. Its input controls are gain, phantom, high-pass,
mute and DSP state; it contains no hidden mic/line or Hi-Z source selector to
correct in Host. The next useful action is therefore physical: reseat Main Out
L in the Input-1 combo jack, then rerun the guarded Input-1 measurement. A new
live run still requires explicit authorization.

## Attempt 2 result

Status: `VOICEFX_DELAY_PROCESSING_DETECTED` in a valid Input-1 run.

After the cable was reseated, the separately authorized rerun produced a
strong physical Input-1 source: -22.350 dBFS bursts and 20.410 dB gate
contrast. The shared-reverb positive control passed with a +12.576 dB gap
rise. The five VoiceFX-off source stages agreed within 0.003 dB, and the three
off-state Mix-A gaps agreed within 0.064 dB.

Corrected UC 4.7.2 Delay processing then appeared twice at the programmed
250 ms spacing:

- cycle 1: +10.484 dB at 250 ms, +3.931 dB at 500 ms, and +12.971 dB at
  750 ms;
- cycle 2: +10.514 dB at 250 ms, +3.959 dB at 500 ms, and +12.985 dB at
  750 ms.

The live report's initial classifier returned `INVALID_INPUT1_SOURCE_DRIFTED`
because it compared the Input-1 USB reference during Delay-on stages. Those
two captures both changed by about 3.11 dB while every VoiceFX-off reference
remained stable. UC declares that USB send as post-DSP; a working insert is
therefore expected to change it. The validator now measures physical-source
stability only in VoiceFX-off stages. Reanalysis of the immutable WAV files
returns `run_valid: true` and `VOICEFX_DELAY_PROCESSING_DETECTED`.

Restoration passed completely: the PipeWire sink returned to muted at its
original volumes, Input 1 returned from the guarded 60 dB to the exact 11 dB
prestate, every readable device field matched, and Host-known VoiceFX, reverb,
and all five changed write-only routes were resent. Battery was 42% before and
41% after.

Evidence:

- `attempt-2/live-report.json`, immutable raw report, SHA-256
  `979c420f72df209f5df7716e81bdca4e4ca1902ffcdb07c515c9b089dedbdca5`;
- `attempt-2/corrected-verdict.json`;
- corrected-verdict SHA-256
  `f186a6dd4b141f0f29e800f35d074b29790db0e62b95aa8064d9dfa3c3aea84d`;
- seven immutable stage WAV files plus the exact stimulus;
- `tests/test_io24_voicefx_waveform_probe.py`, 9/9 passed with the post-DSP
  regression contract;
- the focused VoiceFX regression set, 115/115 passed.
