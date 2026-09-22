# io24 Android Controller

This directory contains the standalone Android companion app for the PreSonus
Revelator io24.

The intended runtime connection is direct:

```text
Android phone -> USB-C -> Revelator io24
```

The Linux Host remains a separate application. The current Android milestone is
an intentionally read-only USB control probe. It verifies the device identity,
opens only vendor interface 5, reads the paesdk capabilities and `JaSt` state,
then holds that interface until **Disconnect control** is tapped. It does not
change mixer, effect, preset, firmware, or sample-rate state.

## Project status

- Protocol and safety contracts: implemented and host-tested.
- Native Android source: implemented without AndroidX or Compose.
- APK compilation: verified with the ignored project-local toolchain pinned in
  `toolchain.lock.json` and detected automatically by `verify.sh`.
- Physical phone/io24 coexistence: verified on a BLU 1660V. Android recorded
  io24 input 2 and played audio through the io24 output while the app retained
  control interface 5.

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
[BUILD_REPORT.md](BUILD_REPORT.md). The authorized hardware result is in
[LIVE_TEST_REPORT.md](LIVE_TEST_REPORT.md).
