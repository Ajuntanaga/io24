# HPF physical-display finding

## Result

The physical Channel screen's `80Hz` field is the fixed preamp high-pass
filter, not a numeric presentation of the adjustable Fat Channel HPF.

Primary-source evidence:

- The official Revelator io24 Reference Manual, section 2.2, identifies the
  Channel-screen field as `High-pass filter 80Hz` and says rotating the encoder
  turns it on or off.
- The official Reference Manual, section 7.3, separately defines the Fat
  Channel HPF as adjustable from 24 Hz through 1 kHz, with 24 Hz/off at the
  lowest point.

The bounded live observation agrees: after the Host sent a Channel-1 digital
Fat Channel cutoff of 40 Hz, the user reported that the physical Channel screen
still displayed `80Hz`. The exact 24 Hz bypass cleanup was sent afterward.
Therefore the remaining 80/160/55 writes were not run; they would perturb the
write-only DSP state without adding useful evidence.

## State note

Channel 1 remained selected on slot 0 with its preset enabled, and Channel 2's
guarded readable state was unchanged. Channel-1 gain changed from 30 dB to
33 dB during the observation window. The probe contains no gain command. The
user subsequently confirmed that they made this gain change intentionally.
The resulting 33 dB setting is therefore retained and is not a Host/probe
defect or an unresolved state change.
