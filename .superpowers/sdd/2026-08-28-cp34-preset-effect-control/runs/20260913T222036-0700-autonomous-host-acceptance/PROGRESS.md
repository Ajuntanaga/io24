# Autonomous Host acceptance progress

Status: `DSP_AMOUNT_FUNCTIONALLY_CLASSIFIED_AND_RESTORED`

## Starting evidence

- DSP Amount is not yet proved to be a simple dry/wet law. Firmware and live
  evidence establish only that wire 4 is a per-input 0–1 scalar, exact zero
  bypasses the complete Fat Channel, one restores full processing, and device
  readback exposes only zero versus nonzero. The matrix's 0.25/0.75 stimuli
  remain pending.
- Voice FX model `mix` is a separate control with a source-bound final dry/wet
  blend. It must not be used as proof of DSP Amount semantics.
- The connected Linux Host is near its stopping point: core UC controls are
  implemented and the latest hardware-free suite passed 668 tests with one
  skip. Remaining closure is objective live acceptance, not another broad
  feature-design pass.
- Device-slot save/recall and standalone FX remain unproved on the repaired
  Host. Passive/Vintage EQ is preserved/read-only rather than editable.
- Custom firmware is technically plausible but not flash-ready: no emitted
  patch, no safe executable home, no completed parser/reset lifecycle, no
  reproduced vendor updater transaction, DFU upload unsupported, and no proven
  unconditional recovery path. `io24_firmware.py flash` intentionally refuses.

## 2026-09-13T22:20:36-07:00 live preflight

Battery was 100% and Full. A host-scope `lsusb`, `aplay -l`, `arecord -l` and
`wpctl status` check found no `194f:0422` io24, no io24 ALSA card, and no
reachable PipeWire session. Only laptop HDMI/ALC257 devices were enumerated.
Therefore no io24 write, capture, playback, preset operation or Host launch was
attempted. The user was asked only to plug the io24 in; no listening or other
interaction will be required.

## Active preparation

Build an objective, fail-closed capture workflow before the device appears.
The DSP Amount classifier must use recorded audio and report evidence rather
than asking the user to listen. It must distinguish at least dry/wet-like,
level/send-like, bypass-only and inconclusive behavior; reject insufficient or
clipped stimulus; randomize or interleave levels where practical; and retain
raw captures, pre/post state, commands, hashes and restoration status. The
cold-boot persistence item remains not runnable unless independent physical
power control exists; USB reset/detach will not be mislabeled as cold boot.

## 2026-09-13T22:37:15-07:00 objective runner result

The hardware-free acquisition and analysis path is now implemented in
`re/io24_dsp_amount_capture.py` and `re/io24_dsp_amount_audio.py`, with 14
focused tests. The live runner pins six-channel S32_LE capture to 96 kHz and a
512-frame ALSA period, measures 0/100/25/75/50 percent, aligns each processed
Mix A waveform to the raw Input 2 reference, compensates small reference-gain
drift, and distinguishes linear endpoint interpolation, zero/nonzero gate,
zero-anchored output-level scaling, nonlinear endpoint blend, and
inconclusive behavior. It rejects a
missing state, wrong rate/format, clipping, weak alignment, and acoustically
indistinguishable endpoints.

The corrected acquisition path refuses every positive write-only prestate,
even if the Host shadow is also positive, and permits only exact-zero device
readback. It requires stereo link off and a fresh calibrated loopback
foundation that proves the feedback-safe parked route and freezes the
correlated Mix A channel. It temporarily opens only the foundation's
proven-off playback-return cell, then restores that cell, the readable Main
level and Input 2 gain, and the zero scalar in `finally`. The complete
hardware-free discovery run passed **681 tests,
1 skipped** in 180.348 seconds. After making the absent-device outcome
explicit, the 14 new focused tests passed in 6.480 seconds.

Two actual live-run invocations stopped before USB or audio. Attempt 1 exposed
an overly generic `LIVE_FAILED` label; the regression test went RED, then the
runner was corrected. Attempt 2 is the controlling artifact:
`dsp-amount-live-attempt-2/live-report.json`, SHA-256
`8e066cdde33d0adce1125101021294f0c4cc2ade879cd37c9e69913a3bb4576e`.
It records battery 98% before/after, the pinned 96 kHz stimulus SHA-256
`e0338750f5d2cd5769d863d57995ed7684ee00093c63813bfc070ffecad864e6`,
`BLOCKED_DEVICE_ABSENT`, and `write_only_mixer_routes=UNTOUCHED`.

Therefore DSP Amount semantics, global FX audibility, device-slot runtime
recall/persistence, Solo, Auto gain, Multiband, and Mix A/B remain **not run on
the device**. The offline work does not prove that DSP Amount is dry/wet. A
disconnected cold boot also remains unavailable without a physical power
cycle; software reset will not substitute for it. Resume by enumerating the
io24 and running the controlling attempt only when `194f:0422` and its audio
endpoints exist.

## Independent subagent evaluation and bounded correction

The requested fresh read-only reviewer found four material problems in the
initial future-live design: unknown anti-feedback routing and stereo-link
state, an uncalibrated hardcoded Mix A channel, stale-shadow restoration of a
positive scalar, and an overstrong dry/wet label for endpoint interpolation.
It also requested clearer timing on the two PipeWire preflights and the
post-full-suite status fix. The review is saved as `SUBAGENT-REVIEW.md`.

All actionable offline findings were corrected once. The 19 focused tests pass
in 5.837 seconds. A first full corrected run caught one time-dependent test
fixture: its hardcoded mock proof aged beyond the deliberately enforced
ten-minute window while the suite ran. That fixture went RED, was changed to
use the current time, and its focused retest passed. The final complete suite
then passed **687 tests, 1 skipped** in 178.624 seconds; `git diff --check` is
clean. This does not upgrade any hardware result: the device remains absent,
the old attempt-2 artifact is only proof of fail-closed absence, the corrected
runner has not reached hardware, and no requested live behavior is accepted.

## 2026-09-13T23:20:21-07:00 device-present no-cable preflight

The device subsequently enumerated as USB `194f:0422`, serial
`AB7C22200355`, ALSA card 2. Battery was 97 percent and not charging. The
active PipeWire clock was forced to 96 kHz with a 512-frame quantum, which
confirms the requested current Host clock settings in the live session.

The user corrected the physical assumption: Main L is **not** connected to
Input 2. No playback, Main-output route, loopback-foundation mutation, DSP
Amount write, preset/effect write, detach, reset, or firmware action followed.
Instead, a read-only ALSA probe verified the native capture format as six
channels of S32_LE at 96 kHz. A five-second passive capture is retained at
`no-cable-passive-preflight/native-6ch-passive.wav`, SHA-256
`4745cb53424f3fa42ba48bea6a1339e379271a854e65ccd053b71d0211efce94`.
It contains only Input-2 self-noise (RMS -94.25 dBFS, peak -80.80 dBFS);
Mix A channels 3/4 are correlated copies at -97.25 dBFS RMS. This proves the
existing passive Input-2-to-Mix-A observation path, but it is not adequate by
itself to classify DSP Amount.

Three prior PipeWire file attempts are retained as zero-byte diagnostics. Two
failed before stream creation because this build's libsndfile path rejected
the requested three-channel WAV, and the raw attempt opened but produced no
frames because the selected PipeWire node remained suspended. They made no
device change.

The live GTK Host, PID 160463, still exclusively owns vendor interface 5 via
`usbfs`. A direct read-only JaSt query therefore fails with `USBError: [Errno
16] Resource busy`. The Host appears in AT-SPI but exposes only its top-level
frame, so its DSP slider cannot be read or operated through accessibility.
The user has been asked to close the Host window. No process was killed and no
USB interface was detached. Once the Host exits, resume with a read-only exact
zero/link/permutation preflight; do not run the amount sequence unless that
prestate is safely restorable.

## 2026-09-14T00:07:04-07:00 live DSP Amount conclusion

After the user closed Host, a direct JaSt preflight passed every write gate on
serial `AB7C22200355`: Channel 2 DSP Amount was exact zero, stereo link and
both phantom supplies were off, processing-channel order was 0/1, Input 2 gain
was 24.287769 dB, and Main was 0.7599996.

Three no-playback PCM attempts then established a useful boundary. Plain
self-noise, a temporary 1 kHz high-pass coefficient set, and a temporary
+15 dB/1 kHz peaking EQ all produced indistinguishable Input-2-to-USB-capture
transfer functions (endpoint deltas 0.016%, 0.090%, and 0.017%). Therefore the
six-channel USB capture pair used here is upstream of the controlled Fat
Channel blocks and cannot answer DSP Amount audibility. Each attempt restored
DSP Amount zero, Main, and the controlled block's identity coefficients; input
gains and mixer routes were untouched. The three retained PCM directories are
88 MiB each.

The final no-cable probe used the device's simultaneous JaSt Input-2 and Main
meter slots, where the controlled processor is observable. With one stable
+15 dB/1 kHz high-shelf on Channel 2, 240 frames per amount produced normalized
endpoint positions of **0.000, 0.2473, 0.4917, 0.7552, 1.000** for DSP Amount
0/25/50/75/100%. The maximum error from a linear law was 0.0083. The Main to
Input-2 meter ratio rose from 0.70797 to 3.86581, so zero retained the dry
signal rather than muting or scaling the output from zero. Classification is
`LINEAR_METER_ENDPOINT_INTERPOLATION`, interpreted as
`CONSISTENT_WITH_LINEAR_DRY_WET_NOT_ARCHITECTURE_PROOF`.

This is strong functional evidence that DSP Amount is one linear blend across
the complete Channel Fat Channel: zero is dry/bypass, one is the fully
processed chain, and intermediate values interpolate. It is not a per-module
mix, a send level, or a channel/output fader. The measurement cannot prove
whether firmware implements literal parallel paths or an equivalent internal
law.

The controlling artifact is
`dsp-amount-meter-live-attempt-1/live-report.json`, SHA-256
`7a98ebff0c782037adf58c1bd06e0e7ca6ec9e8cd3b2eaf679d6eeadd4b24c71`.
It records battery 95% before/after and exact readable restoration: flags 449,
DSP Amount zero, Main 0.7599996, gains unchanged, link/phantom off, processing
order 0/1, EQ band 0 identity sent, and no restoration errors. There was no
playback, mixer-route write, firmware, reset, detach, Wine, network, commit, or
push action.

The final focused DSP Amount gate passed **29/29 tests in 8.654 seconds**.
`git diff --check` is clean. A broad discovery run was interrupted after more
than ten minutes of sustained CPU with no failure output; it emitted only the
pre-existing unclosed-WAV `ResourceWarning` and is not reported as a pass. The
last completed broad result remains 687 tests with one skip before these ten
new meter/passive tests were added.

## 2026-09-14T00:34:45-07:00 Voice FX internal-meter result

The new no-cable runner `re/io24_voicefx_meter_probe.py` uses Input 1 preamp
self-noise, simultaneous JaSt input/bus meters, safe Main/headphone attenuation,
and complete Host-shadow restoration for the write-only Voice FX and Channel 1
gate controls. It never changes routing, slots, DSP Amount, or
`processingChannel`. Six focused tests cover classification, restoration after
success/failure, float-quantized safety readback, and shadow validation.

Attempt 1 stopped on the original exact-decimal 0.01 safety comparison and
restored cleanly. Attempt 2 completed but its gain control was invalid because
the user's active Channel 1 gate suppressed the amplified self-noise; it is not
a Voice FX negative. The controlling attempt 3 bypassed that ordinary gate and
restored its complete Host-known state afterward.

Attempt 3 passed its measurement control: Input 1 moved 26.986 dB and Main,
Mix A, and Mix B each moved 26.248 dB. Transformer on produced a -4.024 dB
normalized bus change with 0.045 dB off drift and is classified
`DIRECT_BLOCK201_METER_EFFECT_DETECTED`. This proves direct Transformer
processing in the current armed state. De-Tuner, Vocoder, Ring Modulator,
Filters, and Delay did not produce a resolved level change, but a scalar meter
cannot prove those algorithms inaudible and the run did not independently prove
each selector transition.

Controlling report SHA-256:
`0436e1da0a3fa9e3c83a7988f0d7b90507aaeae998403e8e7d36c0ac4578002e`.
Restoration read back flags 449, both gains, Main, headphones, phantom/link, and
the 0/1 processing permutation exactly. Transformer-off and the original gate
state were resent; routes, slots, DSP Amount, and `processingChannel` were
untouched. Battery was 100 percent before and after.

## 2026-09-14T00:44:21-07:00 inactive-slot save/recall result

The new runner `re/io24_slot_recall_meter_probe.py` and its five focused tests
exercise an inactive slot without relying on subjective listening. Slot 1 was
eligible because the registry contained its complete original `B A S E` body.
The A/B/A sequence wrote and selected flat, +15 dB/1 kHz high shelf, then flat
again while comparing simultaneous Input-1 and bus meters.

The slot selector reached 1 on every recall, but the boosted body moved the
normalized bus response only +0.143 dB, with -0.085 dB flat drift. Result:
`NO_SAVED_BODY_RECALL_EFFECT_DETECTED`. This is a clean negative for the
current tagged `MemP`/`Stat` writer/framing, not proof that native device preset
storage is absent.

The complete original slot-1 body was resent and Input 1 was returned to slot
0. The write again received no reply, matching its pre-existing
`WRITE_SENT_UNVERIFIED` registry status. Registry data was never modified.
Every readable control restored exactly; routes, DSP Amount, and
`processingChannel` were untouched; battery was 100 percent. The combined
Voice FX and slot-probe focused gate passed 11/11 tests. Controlling report
SHA-256:
`8db972783d0ce15d799c1fc8b1f6ff7422faee4f13c8fefdac8b962822363299`.

## 2026-09-14T00:57:56-07:00 Host feature smoke

Preflight reproduced a live Multiband selector bug without starting the
processor: because real `pw-cli` global-id lines begin with a tab, the node
parser treated the listing as one block and returned the laptop's first ALSA
sink after encountering a later io24 marker. A real-format test failed, the
parser was corrected to split stripped id lines, and the live resolver then
returned the exact Revelator capture and playback nodes. The focused Solo,
Auto Gain, Multiband, Mix-source, parameter, and clock suite passes 168 tests
plus 55 subtests.

The controlling bounded live run then passed at forced 96 kHz / 512. Auto Gain
made a 30→24 dB clip correction and the preamp read it back. Both passive Mix
A/B sources reached ready. The Input-1 Multiband process published all required
nodes, accepted a live ratio move, stopped, and left no temporary nodes. The
device mixer was not rerouted. Main/headphones were attenuated first; all
readable state restored exactly; routes, slots, DSP Amount, and
`processingChannel` were untouched; battery was 100 percent.

Solo remains hardware-free only because a live toggle would rewrite mixer
cells with unreadable, unrecorded prestates. Report SHA-256:
`7713875f492c3125078fc2bd1ae607c57e5d3977e5da2be24d1055f00d57e8fd`.
