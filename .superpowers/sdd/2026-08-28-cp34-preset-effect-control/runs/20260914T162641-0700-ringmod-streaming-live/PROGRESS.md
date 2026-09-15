# Block 201 with the device genuinely streaming, and on both channels

Status: `INERT_WHILE_STREAMING_AND_ON_EITHER_CHANNEL`

Unit `AB7C22200355`, firmware `0128`, Host closed, battery 59 percent.

## A provenance correction first

`re/io24_corrected_ringmod_probe.py` hardcodes `RATE_HZ = 96000.0` and
`QUANTUM_FRAMES = 512`, and reports them as `host_configured_sample_rate_hz`
and `host_configured_quantum_frames`. They are constants, not measurements.

PipeWire on this machine was actually at `clock.rate 48000`,
`clock.force-rate 0`, `clock.quantum 1024`, and **both io24 PCM substreams were
`closed`**. So no block-201 measurement we have ever made was at 96 kHz, and
the earlier suggestion that we were sitting exactly on the `<= 96000.0` root
gate boundary is withdrawn -- we were never near it.

The crossfade arithmetic survives either way: `round(rate*40/quantum/1000)`
gives 42.667 ms at 96k/512, 96k/1024 and 48k/512 alike, so the 60 ms settle is
adequate regardless of which figure was real.

## Test 1: with the device genuinely streaming

Every prior block-201 measurement ran with `playback: NONE` and both substreams
closed. The Fat Channel gate processes regardless because it sits in the analog
monitor path, so a positive control could not have revealed this. An insert FX
plausibly only runs when the audio engine is actually clocking.

Opened silent playback and capture streams; both substreams came up at
48000 Hz, period 512, six channels. Re-ran the identical probe:

| window | Main/Input-1 | MAD |
|---|---|---|
| gate_off_before | -0.332 dB | 0.254 |
| **gate_on** | **-19.840 dB** | 1.898 |
| gate_off_after | -0.189 dB | 0.202 |

Control valid: delta **-19.580 dB** against an 11.385 dB threshold.

| window | Main/Input-1 | MAD |
|---|---|---|
| ringmod_off_before | -0.143 dB | 0.307 |
| ringmod_on | -0.209 dB | 0.338 |
| ringmod_off_after | -0.284 dB | 0.340 |

Delta **+0.005 dB** against a 2.038 dB threshold. Still inert.

## Test 2: the blind spot a positive control cannot cover

A control validates the meter, not the channel assignment. Every measurement so
far has targeted Channel 1 on the driver's reading that the chain whose
`processingChannel` is 0 owns the singleton. If that reading were inverted we
would have been arming one channel and measuring the other, and the gate control
would still have passed, because the gate is per-channel and works on whichever
channel is tested.

So Channel 2 was made to dominate Main -- Input-2 raised to 60 dB, Channel 2's
gate opened -- and the same fully wet `vol = 0` Ring Mod was armed. Measured
inline; raw values recorded here rather than in a separate report:

| window | Main/Input-2 | MAD |
|---|---|---|
| ch2_off_before | +4.770 dB | 0.342 |
| ch2_armed | +4.781 dB | 0.299 |
| ch2_off_after | +4.721 dB | 0.155 |

Delta **+0.035 dB** against a 2.054 dB threshold, drift -0.049 dB.

Block 201 is inert on **both** channels.

## Cumulative elimination

Ruled out by direct measurement or by source, each with a valid control where
a control applies:

- the three gate flags (satisfied at construction)
- signal path and routing (the gate control reaches Main)
- delegate not installed (installed by the lazy installer at `0x5f170`)
- scheduler not running (the gate proves the chain is live)
- Host sequencing v1 and v2
- device not clocking / no active stream (this run)
- the `<= 96000.0` root-gate boundary (never applied; we were not at 96 kHz)
- wrong channel (both channels tested)

Block 201 accepts writes, answers normally, and does nothing, on either
channel, streaming or idle, with the chain demonstrably processing.

## Restoration

Both probe runs returned `MEASURED_AND_RESTORED` with no errors. The inline
Channel-2 test restored Input-2 gain to 24.287769317626953 dB and main volume
to 0.75. Final readable state matches: ch1 slot 0 gain 30.00 enabled, ch2 slot 2
gain 24.29 enabled, main 0.750000, headphones 0.510000, link off. The streams
opened for Test 1 were stopped and both substreams read `closed` afterwards.
Routing, preset slots, DSP Amount and processingChannel untouched throughout.

Evidence: `live-report.json` for Test 1; Test 2 values are above.
