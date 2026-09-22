# io24 Android Controller

This directory contains the standalone Android companion app for the PreSonus
Revelator io24.

The intended runtime connection is direct:

```text
Android phone -> USB-C -> Revelator io24
```

The Linux Host remains a separate application. The Android controller verifies
the device identity, opens only vendor interface 5, reads the paesdk
capabilities and `JaSt` state, then holds that interface until **Disconnect
control** is tapped.

Version 0.2.0 adds one deliberately narrow control: **Mute input 2**. The app
sends the fixed native mute record, waits 350 ms, and reads the full device
state again. It reports success only when the Input 2 mute bit matches the
requested value. It exposes no generic parameter writer and does not change
effects, presets, firmware, or sample rate.

## Project status

- Protocol and safety contracts: implemented and host-tested.
- Native Android source: implemented without AndroidX or Compose.
- APK compilation: verified with the ignored project-local toolchain pinned in
  `toolchain.lock.json` and detected automatically by `verify.sh`.
- Physical phone/io24 coexistence: verified on a BLU 1660V. Android recorded
  io24 input 2 and played audio through the io24 output while the app retained
  control interface 5.
- Input 2 mute frame and readback logic: implemented and verified offline.
- Input 2 mute on physical hardware: not yet run; it requires separate exact
  authorization.

## Verify

From this directory:

```sh
./verify.sh --host-only
```

Once the Android build toolchain is installed locally, run:

```sh
./verify.sh
```

The full command uses Gradle's offline mode, runs the Java unit tests and lint,
builds the debug APK, and prints its SHA-256. The project currently pins JDK
17.0.20.1+1, Gradle 8.11.1, Android Gradle Plugin 8.9.2, Platform 35 revision 2,
and Build Tools 35.0.0.

See [DESIGN.md](DESIGN.md) for the safety boundary and
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the staged build plan.
The latest offline result and APK checksum are in
[BUILD_REPORT.md](BUILD_REPORT.md). The authorized hardware result for the
read-only 0.1.0 build is in [LIVE_TEST_REPORT.md](LIVE_TEST_REPORT.md).
