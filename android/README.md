# io24 Controller for Android

This is a direct, offline Android controller for the PreSonus Revelator io24.
The phone talks to the interface over USB-C. It does not need the Linux laptop,
a browser, a web server, or an Internet connection.

```text
Android phone -> USB-C -> Revelator io24
```

Version 0.3.4 is the current controller build. The earlier 0.1 and 0.2 builds
proved that Android can hold the io24 vendor-control interface while another
app records and plays USB audio. This version keeps that transport and adds the
five-screen control surface.

## What is in the app

- **Mixer:** both preamps, phantom power, fixed 80 Hz filters, input mute,
  processing mix, input link, Main and headphone levels, monitor blend, and
  Main/Mix A/Mix B routing for both inputs, all three playback pairs, and the
  FX return. Bus mute, solo, assignment, trim, and one-shot **Copy Main** are
  included.
- **Fat Channel:** variable HPF, gate/expander, Standard compressor, limiter,
  four-band Standard EQ, processing order, and live response graphs for both
  inputs.
- **Effects:** the native Transformer, De-Tuner, Vocoder, Ring Modulator,
  Filters, and Delay racks in the established control order. Every model keeps
  its own parameter settings, while turning one model On turns the other five
  off, matching UC's single active rack. Every editable parameter, including
  Wet/Dry, changes its graph. The shared native reverb is a separate rack.
- **Presets & setups:** private whole-setup phone scenes with save, rename,
  delete, load, JSON import, and JSON export. Each input's two front-panel
  blocks can be recalled or replaced through an explicit Input 1/2 and Block
  1/2 choice.
- **Device:** session-rate safety, output alignment delay, headphone source,
  mute-sync behavior, front-panel Main-mute readback, and exact connection
  diagnostics.

The USB command layer is an allowlist of typed operations. UI code cannot send
an arbitrary parameter ID or raw firmware record. Disconnect updates the UI
immediately and releases the USB interface on the serial worker. If a scene
stops partway through, the app closes the uncertain session and reports how
many controls were confirmed plus the possibility of a partially changed
device.

## What has been proved

The current build has three different kinds of evidence:

| Area | Current evidence |
| --- | --- |
| Android USB control plus USB audio | Physically proved on the BLU 1660V with the earlier transport build |
| Input 2 mute native write | Physically applied; the original short-reply bug was isolated |
| Ordered ACK drain and fresh state read | Unit and emulator tested in 0.3.4; needs a new physical run |
| Mixer, Fat Channel, Voice FX, native reverb, channel 2, and native preset-block builders | Exact offline vectors and protocol tests pass; not yet sent by this APK to the physical io24 |
| Five-screen UI, scenes, error recovery, and high-rate guard | Exercised on the 720x1600 Android 15 emulator |
| Audible Android-hosted DSP | Not implemented and not claimed |

The native DSP byte tests compare the Android builders with the established
Linux builders for all six Voice FX models, shared reverb, variable HPF, gate,
Standard compressor, limiter, Standard EQ, and complete firmware-native
`MemP/Stat` block bodies.

## What the save names mean

- A **phone scene** is the whole setup this app knows: mixer, both inputs, Fat
  Channel, effects, and device settings.
- A **front-panel preset block** is one input sound recalled by the io24 Preset
  button. Each input has Block 1 and Block 2.
- The Linux app's **full Host setup** is broader than a UC scene because it can
  also contain Linux-only Multiband and the safe high-rate Delay insert.
- **Automatic recovery** is the Linux Host's unnamed last session. Android
  phone scenes are named files in the app's private storage instead.

Saving a front-panel block writes the Fat Channel currently shown on the
phone. If Voice FX is assigned to that input, the decoded native block body can
also carry Transformer. Active Delay is deliberately kept in a phone scene or
Linux Host setup instead of a device block, even at a lower rate, so loading it
can choose a safe execution path for the rate that is actually in use. The
currently playing block cannot be overwritten. Because the io24 cannot return
a stored body, completion is reported as `WRITE_SENT_UNVERIFIED`, not readback
or power-cycle proof.

The block button selects which block the front panel uses. It does not make the
firmware reapply that block's stored body. Whole-setup scene loading likewise
does not move the front-panel selection or change the audio rate.

## High-rate Delay rule

Firmware Voice FX model 5, Delay, is never selected on the io24 above 48 kHz.
Selecting it at 96 kHz reset the tested firmware; 88.2 kHz has the same growing
private histories and no physical Delay acceptance, so the app uses the same
conservative boundary. The app cannot observe Android's USB audio clock, so
every new connection begins with the rate unconfirmed and hardware Delay
safely off. If a recording or video app may open or change the io24 to 88.2 or
96 kHz, first choose another Voice FX model or turn Delay off. Then make the
clock change and use **Confirm current audio rate** on the Device page.
Confirming either high rate keeps an off Transformer on the device and retains
the Delay settings locally. Confirming 44.1 or 48 kHz also keeps device Delay
off; it unlocks the rack so an explicit **On** action can place model 5 only
after that confirmation.

That selector records your observation; it does not force or detect the clock.
A saved scene remembers its old value for context but cannot confirm it on a
later connection and never applies a sample-rate command. If another audio app
changes rates, turn Delay off before that change and confirm the new current
rate afterward. Until then, the Delay rack stays disabled with an explicit
safety message.

## Honest limits

- Tube and FET compressors, plus Passive and Vintage EQ, depend on Universal
  Control's retained desktop designer. The Android app exposes only the exact
  native Standard models instead of approximating those alternatives.
- Mono-source pan, stereo width, writable names, persistent Mirror Main, and a
  writable front-panel Main-mute latch still have no proved io24 command. Pan
  may exist in imported scene data, but this app does not present it as a
  hardware control.
- A successful front-panel block send is not stored-body readback. Cold-boot
  custom-preset persistence remains firmware behavior, not an Android promise.
- Android does not expose the current USB audio clock to this controller. Rate
  confirmation is manual and must be repeated after reconnecting or after an
  audio app changes its session rate.
- De-Tuner, Vocoder, Ring Modulator, and Filters do not yet have decoded native
  front-panel block bodies. The app refuses to silently omit an active one.
- Multiband compression, auto-leveling, and audible high-rate Delay would require a
  phone-side audio engine. That engine is not in 0.3.4. The Android **Device
  reverb** rack controls the io24's native block 202.

## Build and verify

From this directory:

```sh
./verify.sh
```

The script runs the host safety contracts, all Java tests, Android lint, and a
clean offline debug build. It prints the APK SHA-256 when everything passes.
Use `./verify.sh --host-only` for the fast source-contract check.

The installable artifact is:

```text
app/build/outputs/apk/debug/app-debug.apk
```

This is a debug-signed APK for direct testing, not a Play Store package. The
project pins Temurin 17, Gradle 8.11.1, Android Gradle Plugin 8.9.2, Android
Platform 35 revision 2, and Build Tools 35.0.0 in `toolchain.lock.json`.

See [EMULATOR.md](EMULATOR.md) for the local development loop,
[BUILD_REPORT.md](BUILD_REPORT.md) for the exact artifact record, and
[LIVE_TEST_REPORT.md](LIVE_TEST_REPORT.md) for the physical observations.
The underlying protocol work builds on
[Oddbear's Revelator.io24.Api](https://github.com/oddbear/Revelator.io24.Api),
with the broader credit and protocol history in the repository root README.
