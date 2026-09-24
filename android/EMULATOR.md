# Android emulator workflow

The local AVD is `io24_blu_api35`. It runs Android 15 / API 35 x86_64 at
720x1600 and 320 dpi, matching the BLU phone viewport used for the physical
transport trial.

The helper always targets `emulator-5556`. It never selects a physical phone or
an unqualified ADB device.

## Normal loop

Start the emulator in one terminal:

```sh
./emulator.sh start
```

Build while the emulator is stopped, then restart it and install:

```sh
./verify.sh
./emulator.sh start
./emulator.sh install
```

This workstation has a bounded task scope. Stop the emulator before Gradle
unit tests so the JVM has enough process and thread slots.

Launch a deterministic session:

```sh
./emulator.sh simulate verified
./emulator.sh simulate failure
./emulator.sh simulate delay96
```

- `verified` supplies the normal in-memory io24.
- `failure` injects a fresh-state readback failure after a readback-class
  command. The controller must release control, show the exact error, and leave
  only Connect available.
- `delay96` supplies semantic Delay intent at 96 kHz. The Effects page must
  show **Unavailable safely**, with the native Delay rack disabled.

Launch the ordinary physical-USB activity or stop the AVD:

```sh
./emulator.sh plain
./emulator.sh stop
```

Simulation requires a debuggable APK and an explicit intent extra. An ordinary
launch always uses the physical USB implementation.

## What the emulator proves

It covers navigation, narrow layout, insets, fine scrolling, graph updates,
scene persistence, connection lifecycle, high-rate placement, and error states.
It does not emulate io24 USB timing, Android USB audio coexistence, native DSP,
device persistence, or audible output.
