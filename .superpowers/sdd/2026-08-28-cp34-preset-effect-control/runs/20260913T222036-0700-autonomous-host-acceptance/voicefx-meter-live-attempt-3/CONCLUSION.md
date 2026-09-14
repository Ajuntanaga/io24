# Voice FX internal-meter conclusion

Controlling report: `live-report.json`

SHA-256: `0436e1da0a3fa9e3c83a7988f0d7b90507aaeae998403e8e7d36c0ac4578002e`

At 96 kHz, with no playback and no physical loopback, Input 1 preamp
self-noise supplied the broadband stimulus. Main and headphone output controls
were held at 0.01. The Channel 1 noise gate was temporarily bypassed because
the first complete sweep proved its configured threshold suppressed the
stimulus; its full Host-known 96 kHz state was restored afterward.

The gain control was decisive: raising Input 1 from 30 to 60 dB moved its meter
by 26.986 dB and Main, Mix A, and Mix B by 26.248 dB. On that valid path,
Transformer on changed the Main/Input-1 ratio by **-4.024 dB** relative to its
two off baselines. Off-state drift was 0.045 dB and the largest window MAD was
0.478 dB. Classification:
`DIRECT_BLOCK201_METER_EFFECT_DETECTED`.

| Model | On delta vs off midpoint | Off drift | Meter effect |
|---|---:|---:|---|
| Transformer | -4.024 dB | +0.045 dB | detected |
| De-Tuner | -0.015 dB | +0.025 dB | not detected |
| Vocoder | +0.009 dB | -0.008 dB | not detected |
| Ring Modulator | -0.186 dB | -0.044 dB | not detected |
| Filters | -0.032 dB | -0.034 dB | not detected |
| Delay | -0.008 dB | +0.019 dB | not detected |

This proves that direct block-201 Transformer on/off and parameter writes can
produce a real audio-path change in the device's current armed state. It does
not identify which earlier state transition armed the internal Voice FX gate,
prove cold-start activation, prove both structural lanes, or prove audible
operation of models 1 through 5. A scalar level meter is intrinsically weak for
energy-preserving pitch and delay effects, so those five results remain
unproved rather than disproved.

Restoration completed without errors. Flags 449, both gains, Main, headphones,
phantom/link state, and processing permutation 0/1 read back exactly. The
complete Host-known Transformer-off and Channel 1 gate states were resent.
Mixer routes, preset slots, DSP Amount, and `processingChannel` were untouched.
Battery was 100 percent before and after.

Attempts 1 and 2 are diagnostics, not controlling results. Attempt 1 stopped
on an exact-decimal safety comparison and restored cleanly. Attempt 2 completed
with the configured Channel 1 gate still active; its gain control failed and
its effect classification is inconclusive.
