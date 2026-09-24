# Android controller design

## Goal

Run the useful io24 control surface directly on an Android phone while Android
keeps using the same interface for recording and playback. The runtime path is
phone to USB-C to io24. There is no browser client or laptop relay.

## Layers

`Io24State` is one immutable snapshot for connection state, decoded hardware
state, write-only shadows, mixer routing, Fat Channel, effects, and scene data.

`Io24Command` is the validated command catalog. It owns ranges, legal targets,
proof classes, and rate restrictions. Views never name a raw parameter ID.

`NativeDsp` and `Io24Protocol` turn a semantic command into an ordered set of
native scalar or block writes. `PaeFrame` owns endian-safe paesdk framing and
reply validation.

`Io24UsbProbe` owns one physical connection to vendor interface 5, alternate
setting 1, with bulk OUT `0x01` and bulk IN `0x81`. `SimulatedIo24Control`
implements the same session contract for the emulator.

`Io24Controller` is the only scheduler. It serializes commands on one worker,
publishes immutable UI snapshots, batches scene restores, and fails closed if
request/reply ordering is uncertain. A session epoch discards queued work and
late callbacks after Disconnect. Physical release runs on the worker, not the
UI thread. A failed scene reports its confirmed progress and partial-device
uncertainty before requiring a reconnect.

`MainActivity` renders Mixer, Fat Channel, Effects, Presets, and Device with
plain Android platform views. Each long page is one native `ScrollView`; there
is no synthetic paging or focus-driven scroll offset.

## Native transaction rules

- Match only USB `194f:0422`.
- Claim only interface 5 without forcing a kernel-driver detach.
- Keep exactly one command in flight.
- Use UIDs 1 through 255 and wrap back to 1.
- Drain and validate each optional short `SetP` reply before another request.
- Treat a USB reply as transport acceptance, not an audio-frame fence.
- Read fresh `JaSt` state for fields with known readback.
- Label write-only fields **Sent** and local-only values **Stored on this
  phone**.
- Close the session after a malformed reply, mismatch, or timeout. Never retry
  a write automatically.
- Never claim interface 6, reset USB, enter DFU, or write firmware.

## Native DSP surface

The Android builders use the same established block families and coefficient
math as the Linux Host:

- Voice FX selector plus model-specific materialization for Transformer,
  De-Tuner, Vocoder, Ring Modulator, Filters, and Delay;
- shared reverb block 202;
- variable HPF, gate/expander, Standard compressor, limiter, Standard EQ, and
  processing order;
- mixer block 100 routing with source mute, solo, assignment, bus mute, and bus
  master folded into effective sends.

Changing the Voice FX input writes the processing-source scalar first, then
replays and materializes the active model. This is the channel 2 path. Each
Voice FX model has a separate XML On value, but the reducer normalizes the rack
to one active model. Turning one model on clears every other model's On value
without clearing its parameters. Only the selected model is materialized on
the device.

The shared device reverb is native block 202.

Alternative UC compressor and EQ models are deliberately not synthesized on
Android. Their exact design depends on retained Universal Control desktop code.

## Rate safety

Delay model 5 is forbidden on the device above 48 kHz. On entry to 88.2 or 96
kHz, an active Delay intent is replaced by an off Transformer at the old rate. The
transaction then waits two old-rate audio quanta. The semantic Delay state is
kept locally, but rate confirmation itself never arms model 5. At 44.1 or 48
kHz the user must explicitly turn Delay on after confirming the rate.

The controller cannot observe Android's USB audio clock. Every connection
therefore starts unconfirmed, and Delay remains absent from hardware until the
user confirms the rate currently negotiated by the audio app. A scene can
remember a rate as context, but decoding or applying it never confirms the
clock and never sends a rate command. Android's audio stack remains responsible
for the hardware clock. An external rate change can bypass this controller, so
Delay must be off before that change and the new rate confirmed afterward.

## Persistence

Phone scenes are whole-setup, schema-versioned semantic records in app-private storage.
They include both inputs, all buses and sends, Fat Channel, every model-local
Voice FX state, reverb, and device settings. Import and export use Android's
Storage Access Framework, so broad storage permission is unnecessary.

Scene restore runs through the same typed validation and serialized controller
as manual edits. Placement is recalculated from the current confirmed rate.
Scenes do not change that rate or select a front-panel block. Front-panel blocks
remain separate. Version 0.3.4 can select either of the two blocks per input or
replace an inactive one with a complete firmware-native `MemP/Stat` body. The
block selector changes the front-panel choice; firmware does not reapply the
stored body on selection. The builder is byte-matched to the Linux encoder.
Transport completion is still `WRITE_SENT_UNVERIFIED` because the body cannot
be read back.

An active Delay is never embedded in a device-resident block, regardless of
rate. It belongs in a phone scene or full Host setup so the execution placement
can be chosen safely when it loads.

## UI rules

- One green accent, dark neutral surfaces, a 4/8 dp spacing rhythm, and 48 dp
  touch targets.
- Stable five-button bottom navigation kept above the system navigation bar.
- Each Voice FX rack follows the established control order and has its own On
  switch.
- Every editable effect parameter feeds the associated graph. Vocoder Voiced
  is a read-only detector and is displayed as such.
- Connection failures show the exact reason in the persistent header and
  disable writes until reconnect.
- The debug simulator requires an explicit intent extra and cannot be opened
  from the release UI.

## Privacy and platform boundary

The app uses Java 17 and Android platform APIs, with API 23 minimum and API 35
target. It requests no permissions, has no Internet path, analytics, account,
ads, telemetry, automatic USB-attach launch, or broad storage access. The APK
must not contain workstation paths or development hostnames.

Host tests prove bytes, validation, state reduction, and source safety.
Emulator tests prove UI and local workflow. Only a physical phone/io24 run can
prove the expanded native writes, timing, and audible result.
