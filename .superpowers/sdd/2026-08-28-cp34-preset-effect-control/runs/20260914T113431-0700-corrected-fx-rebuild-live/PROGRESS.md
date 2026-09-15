# Corrected block-201 rebuild live validation

Status: `INCONCLUSIVE_EXPECTED_LEVEL_SIGNATURE_BELOW_THRESHOLD; RESTORED`

The user authorized one corrected Delay or Ring-Mod objective measurement with
a same-session positive control and exact restoration. One process was the sole
device writer. Host and ALSA streams were closed; no Wine, firmware, reset,
DFU, routing, preset-slot, DSP Amount, or `processingChannel` action occurred.

## Result

Serial `AB7C22200355`, firmware `0128`, Host-configured 96 kHz / 512 frames.

| measurement | effect delta | threshold | off drift | result |
|---|---:|---:|---:|---|
| Channel-1 direct gate | -18.313 dB | 12.014 dB | -0.049 dB | detected |
| corrected fully-wet Delay | -0.148 dB | 1.990 dB | -0.040 dB | not detected |

Delay used 0.25 s, feedback 1.0, mix 1.0 and the corrected sequence: selector,
60 ms wait, first state as rebuild trigger, 60 ms wait, state replay. The API
maps feedback 1.0 to coefficient 0.5, so uncorrelated stationary noise should
gain only 1.249 dB, below this run's 1.990 dB threshold. The gate control proves
gross Main/Input-1 sensitivity but does not turn this underpowered scalar test
into a Delay null. Corrected Delay audibility and the pacing hypothesis remain
unresolved.

## Restoration

Readable before/after state matches exactly: flags 897, Input-1 gain 30.0 dB,
Input-2 gain 24.287769317626953 dB, slots 0/2, processing permutation 0/1,
Main 0.7699995636940002, headphones 0.510000467300415, link and phantom off.
The complete Host-known Transformer-off and `MAIN` Channel-1 gate writes were
resent. Battery remained 82 percent.

## Offline follow-on and next

The model-5 trace is complete: construction, `vech` state application, process
dispatch, and the one-input/two-output in-place descriptor are source-bound.
That rules out a missing Delay model or lane, but does not make this scalar
measurement sensitive enough. The next objective discriminator is corrected
fully-wet Ring Mod with the same gate control and exact restoration. Any
additional device mutation requires a new exact authorization.

Controlling artifact: `live-report.json`, SHA-256
`672083ccb336e08727abe0509dd6567f85511eee6dad177b465a8f0214f9652f`.
Focused offline guard before live execution: 14 tests passed. After the
model-5 extension and deterministic matrix refresh, the repair/focused run
passed 23/23.
