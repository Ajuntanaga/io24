# Corrected VoiceFX objective meter acceptance

Status: executed and restored; strict effect-detection gate not passed

## Authorization

The user authorized this exact no-listening test on 2026-09-17:

- target io24 serial `AB7C22200355`;
- use Input 1 preamp self-noise as the stimulus;
- run two Transformer off/on/off meter cycles through the corrected Linux Host
  block-201 transaction;
- temporarily set Input 1 gain to 60 dB, bypass the Channel 1 gate, and hold
  Main/headphone output controls at 0.01;
- record internal Input 1 and Main meter evidence;
- restore the complete Host-known VoiceFX and gate intents plus every readable
  control changed by the probe.

Excluded: playback, ALSA capture, mixer-route changes, reverb, preset or slot
operations, DSP Amount, `processingChannel`, firmware, reset, DFU, Wine, and
network access.

Stop before writes if identity, battery, phantom/link, processing permutation,
DSP-enabled, Host-shadow, or quiet-input preflight fails. Stop at or below 10%
battery. A failed measurement must still execute restoration.

## Preflight

- battery: 78%
- USB ID: `194f:0422`
- ALSA card: `R24`, playback and capture available
- Host/QEMU owner: none
- Host shadow: complete Delay-on and Channel 1 gate states
- focused offline regression: 18 passed

The first invocation stopped before opening the device because this scope file
made the runner's required-empty output directory nonempty. The actual live
attempt is isolated in `attempt-1/`.
