# Autonomous Host acceptance results

As of 2026-09-13T22:37:15-07:00, the objective test machinery is verified but
the io24 was absent for every live preflight and invocation. No device state,
audio route, preset block, firmware, Wine prefix, or external system changed.

| Target | Result | Evidence |
|---|---|---|
| DSP Amount 0/25/50/75/100 | `LINEAR_METER_ENDPOINT_INTERPOLATION` | `dsp-amount-meter-live-attempt-1/live-report.json` |
| Objective endpoint-law classifier | `VERIFIED_OFFLINE` | 19 focused tests cover five classifications, alignment/gain drift, format, clipping, restoration, route proof, and absence |
| Global FX on/off and model audibility | `TRANSFORMER_POSITIVE; MODELS_1_TO_5_UNRESOLVED` | `voicefx-meter-live-attempt-3/live-report.json` |
| Known-preset inactive-block recall | `NO_SAVED_BODY_RECALL_EFFECT_DETECTED` | `inactive-slot-recall-live-attempt-1/live-report.json` |
| Disconnected cold-boot persistence | `NOT_RUN_NO_PHYSICAL_POWER_CONTROL` | USB reset is explicitly excluded |
| Solo / Auto gain / Multiband / Mix A/B at 96k/512 | `RUNTIME_SMOKE_PASS; SOLO_HARDWARE_FREE_ONLY` | `host-feature-smoke-live-attempt-1/live-report.json`; 168 tests + 55 subtests |
| Complete corrected hardware-free suite | `PASS` | 687 tests, one expected skip, 178.624 s |
| Post-review acquisition/analyzer suite | `PASS` | 19 focused tests, 5.837 s; timestamp-fixture retest also passed |

The table is the cumulative current result; the initial absent-device evidence
is retained below as chronology. DSP Amount is now functionally classified,
Transformer is positively detected, and the current device-slot writer has a
clean negative. Cold-boot persistence still has no physical power-control path.

## Independent review and correction

The requested fresh subagent review found that the first runner revision must
not be used live: it trusted a stale positive Host shadow as exact scalar
prestate, hardcoded one member of the Mix A pair, did not guard stereo link or
prove anti-feedback routing, and called endpoint interpolation dry/wet. Those
findings do not change the controlling absent-device artifact because that run
stopped before opening the device or audio path.

The bounded correction now refuses all positive DSP Amount prestates, requires
exact-zero device readback, rejects stereo link, requires a calibrated
foundation no more than ten minutes old that started and finished at zero and
left the exact feedback-safe parked route, adopts the foundation's measured
Mix A channel 3 or 4, and opens/restores only the proven-off playback-return
cell. Relative capture paths are also fixed. The classifier reports
`LINEAR_ENDPOINT_INTERPOLATION`, with
`CONSISTENT_WITH_DRY_WET_NOT_ARCHITECTURE_PROOF` as interpretation. It cannot
claim internal parallel topology from waveforms alone.

The corrected runner has not executed against hardware. The earlier attempt-2
artifact predates these corrections but remains valid evidence of absence
because it stopped at device discovery before any USB/audio/control write.

## Device-present update at 2026-09-13T23:20:21-07:00

The io24 is now present and the live session is confirmed at forced 96 kHz / a
512-frame quantum. Main L is not connected to Input 2, so the cable-dependent
foundation was not run. A read-only six-channel ALSA capture succeeded without
playback or control writes. Input 2 contains only self-noise at -94.25 dBFS
RMS; Mix A channels 3/4 carry a 3 dB lower, near-perfectly correlated copy.
Evidence: `no-cable-passive-preflight/native-6ch-passive.wav`, SHA-256
`4745cb53424f3fa42ba48bea6a1339e379271a854e65ccd053b71d0211efce94`.

This does **not** classify DSP Amount. The running GTK Host owns vendor
interface 5 and prevents even a direct read-only JaSt preflight (`EBUSY`). Its
child controls are not exposed through AT-SPI. The next action is gated only
on closing that Host; no Host process, USB driver, route, or device state was
stopped or changed automatically.

## DSP Amount live result

Host was closed and the authorized no-listening test completed on serial
`AB7C22200355` at 96 kHz / 512 frames. The decisive internal-meter artifact is
`dsp-amount-meter-live-attempt-1/live-report.json`, SHA-256
`7a98ebff0c782037adf58c1bd06e0e7ca6ec9e8cd3b2eaf679d6eeadd4b24c71`.

| Amount | Main/Input-2 median ratio | Normalized endpoint position |
|---:|---:|---:|
| 0% | 0.70797 | 0.0000 |
| 25% | 1.48875 | 0.2473 |
| 50% | 2.26080 | 0.4917 |
| 75% | 3.09274 | 0.7552 |
| 100% | 3.86581 | 1.0000 |

The controlled processor was a stable +15 dB/1 kHz high-shelf on Channel 2.
The result is `LINEAR_METER_ENDPOINT_INTERPOLATION`; maximum position error is
0.0083. Functionally, DSP Amount behaves as one linear dry-to-processed blend
for the complete Fat Channel. It is not an output/send level because exact
zero retained the dry signal. This does not prove a literal parallel internal
topology, and it does not make the control per-module.

Restoration passed with no errors: DSP Amount exact zero, EQ identity sent,
Main restored to 0.7599996, flags restored to 449, gains unchanged, link and
phantom off, processing order 0/1, mixer routes untouched, battery 95% before
and after. Final focused gate: 29 tests passed in 8.654 seconds. The attempted
broad discovery run was interrupted after exceeding ten minutes of sustained
CPU and is not a pass; its only emitted diagnostic was the pre-existing
`cp34_current_slot_survey.py` unclosed-WAV `ResourceWarning`.

## UX decision following the live result

Intermediate whole-chain DSP Amount values are not recommended for HPF,
corrective EQ, gate, or limiter use: dry blending restores rejected frequencies,
leaks around a gate, and lets peaks bypass the limiter ceiling. The primary
workflow should be Bypass plus 100% processing. Intermediate Amount remains a
deliberate advanced parallel-processing control, chiefly useful for compression
or creative coloration; Voice FX and Reverb retain their own mix controls.

## Voice FX live result

The controlling no-cable result is
`voicefx-meter-live-attempt-3/live-report.json`, SHA-256
`0436e1da0a3fa9e3c83a7988f0d7b90507aaeae998403e8e7d36c0ac4578002e`.
With the ordinary Channel 1 gate temporarily bypassed, the Input 1 gain control
moved its meter 26.986 dB and every bus 26.248 dB. Transformer on changed the
normalized bus level by -4.024 dB with 0.045 dB off-state drift. Direct
block-201 Transformer processing is therefore present in the current armed
device state.

The remaining models produced no resolved scalar-level response: De-Tuner
-0.015 dB, Vocoder +0.009 dB, Ring Modulator -0.186 dB, Filters -0.032 dB,
and Delay -0.008 dB. This meter cannot establish their inaudibility, especially
for pitch/delay algorithms that can preserve broadband energy, and it did not
independently prove every model-selector transition. They remain unresolved.

Restoration had no errors. Flags 449, gains, Main, headphones, phantom/link,
and processing order 0/1 read back exactly; the complete Host-known
Transformer-off and gate states were resent. Routes, slots, DSP Amount, and
`processingChannel` were untouched. Battery was 100 percent before/after.

## 96 kHz / 512 Host feature smoke

The controlling result is
`host-feature-smoke-live-attempt-1/live-report.json`, SHA-256
`7713875f492c3125078fc2bd1ae607c57e5d3977e5da2be24d1055f00d57e8fd`.
Auto Gain's actual clip decision moved Input 1 from 30 to 24 dB and read back
exactly. Both passive Mix A/B sources reached ready. Multiband published all
three required nodes against the exact Revelator capture/playback pair,
accepted a live control move, and stopped cleanly. Clock remained forced to
96000/512 throughout, every temporary node disappeared, and readable device
state restored exactly.

The preflight exposed one real defect: the PipeWire node parser did not split
tab-indented `pw-cli` id lines and could select the laptop ALSA sink. A
real-format regression reproduced it; `io24_mbc.py` now returns the exact
Revelator input/output pair. The focused Host smoke gate passes 168 tests plus
55 subtests.

Solo is accepted only at the hardware-free contract level. A live toggle was
not safe because Solo rewrites every source in a bus and the current shadow
does not hold an exact prestate for every write-only mixer cell. Multiband's
process/control lifecycle was live, but its write-only device-mixer reroute was
likewise excluded. These are explicit acceptance limits, not silent passes.

## Inactive device-slot save/recall result

The controlling no-cable A/B/A result is
`inactive-slot-recall-live-attempt-1/live-report.json`, SHA-256
`8db972783d0ce15d799c1fc8b1f6ff7422faee4f13c8fefdac8b962822363299`.
Inactive Input-1 slot 1 was safely testable because its complete original
`B A S E` body was Host-known. The runner wrote and selected a flat body, the
same body with a +15 dB/1 kHz high shelf, and the flat body again. The readable
slot selector reached slot 1 every time, but the boosted body changed the
normalized Main/Input-1 response by only +0.143 dB; flat-state drift was
-0.085 dB. Classification: `NO_SAVED_BODY_RECALL_EFFECT_DETECTED`.

This isolates a failure in the current tagged `MemP`/`Stat` save/framing path:
selection works, but the saved processing body did not become active. It does
not establish that the device lacks native preset storage. The original body
was resent, although the device gave zero replies just as it had for the
registry's original `WRITE_SENT_UNVERIFIED` write. Readable state restored
exactly, the registry remained read-only, and routes, DSP Amount, and
`processingChannel` were untouched. Battery was 100 percent before/after.
