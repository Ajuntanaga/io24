# Corrected VoiceFX objective meter result

Status: measured and restored; strict acceptance inconclusive

The authorized no-listening test completed on serial `AB7C22200355`, firmware
`0128`. Battery was 76% before and after. The quiet-input preflight and the
27.503 dB gate/path positive control both passed.

The live transport matched the corrected UC 4.7.2 lifecycle exactly:

```text
VoFx, Bqdf, Bqdf, MBdf, MBdf, godv
godv-only off/on/off updates
VoFx, vech restoration to the Host-known Delay state
```

Two Transformer cycles produced same-sign Main/Input-1 changes:

| cycle | Transformer-on delta | off-baseline drift | max window MAD |
|---|---:|---:|---:|
| 1 | -3.765 dB | -0.074 dB | 0.743 dB |
| 2 | -3.086 dB | +0.015 dB | 0.740 dB |

The preregistered detector requires the absolute active delta to reach six
times the largest window MAD. Those thresholds were 4.456 dB and 4.437 dB, so
neither cycle passed even though both changes were large, same-sign, and had
stable off baselines. Preserve the runner's result:
`NO_DIRECT_BLOCK201_METER_EFFECT_DETECTED`, repeatability invalid. This is not
proof of no effect, and the observed deltas must not be promoted into a pass by
changing the threshold after seeing them.

Restoration completed without errors. Flags, both gains, Main, headphones,
phantom/link state, and processing permutation 0/1 read back exactly. The
Host-known Delay-on VoiceFX state and complete Channel 1 gate state were
resent. Mixer routes, preset slots, DSP Amount, and `processingChannel` were
untouched. No playback or ALSA capture was opened.

Evidence:

- `attempt-1/live-report.json`
- SHA-256: `cf507c3483f50bc1ac3a91cae062542de3eaf5d43e551ac61a94cd54c0271219`
- focused regression: 18 passed
- `git diff --check`: clean

The next objective discriminator needs a fresh authorization. The strongest
choices are a deterministic post-FX waveform capture through a physical output
loopback, or a meter rerun that removes Channel 2 from the measurement with an
exact supplied DSP Amount restore value. Human listening is not required for
either route.
