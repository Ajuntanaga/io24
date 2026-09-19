# Remaining VoiceFX model waveform run

User authorization: `you have authorization for live if you need it`

Date: 2026-09-17

Rig: Main Out L -> physical Input 1, as left connected after the valid Delay
run. The probe raises only Input 1 from its readable prestate while both Main
feedback legs are off and restores it in `finally`.

## Allowed live operations

- read battery, exact io24 identity, and readable device state;
- temporarily mute the exact io24 PipeWire sink;
- establish the already-proven protected Mix-A observation path;
- select Transformer, Detuner, Vocoder, Ring Modulator, and Filters;
- materialize each model off and operate its own On control twice;
- play the deterministic -30 dBFS gated stimulus and capture six-channel USB
  audio;
- restore the exact Host-shadow FX, reverb, and write-only routes plus every
  readable value changed by the probe.

## Explicitly excluded

- DSP Amount or `processingChannel` writes;
- device-resident slots, preset recall/save/assign, firmware, reset, or DFU;
- phantom, stereo link, output-volume, Input 2 gain, or `.wine-io24` access;
- promoting a candidate or changing a protocol builder without valid model-
  specific evidence.

## Validity contract

Reverb must create a tail on the same return, the gated physical source must
be usable and stable across VoiceFX-off stages, and off-state return levels
must remain stable. Each model is toggled on/off twice. Detuner must produce
the -8-semitone partner and Ring Modulator the programmed 313.7 Hz sidebands;
the other models must produce a repeatable gain-normalized spectral change
(Filters may additionally qualify by its resonant tail).
