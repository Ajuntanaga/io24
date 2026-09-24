# Android controller build report

Clean offline build completed on 2026-09-24.

## Artifact

- APK: `app/build/outputs/apk/debug/app-debug.apk`
- SHA-256: `822b10fcf7f7a29ed81b031ef8814fa3a98501b23552cc0a32f97424b1a7c01e`
- Size: 129,443 bytes
- Package: `dev.ajuntanaga.io24`
- Version: `0.3.4` (`versionCode` 9)
- Android: API 23 minimum, API 35 target
- Signing: Android debug certificate; v1 and v2 signatures verified

## Automated verification

- Host protocol and safety contracts: 17 passed
- Java unit tests: 67 passed, 0 failed, 0 skipped
- Android lint: no issues found
- Clean debug APK assembly: passed
- Manifest: USB host feature only; no requested permissions
- USB entry: launcher only; no automatic `USB_DEVICE_ATTACHED` activity
- APK privacy scan: no home paths, workstation hostname, old transfer URL,
  Wine path, or repository path found

The native byte suite covers scalar state/write framing, ACK parsing, mixer
blocks, both Voice FX input assignments, all six Voice FX models, reverb,
variable HPF, gate, Standard compressor, limiter, Standard EQ, UID wrap, scene
validation, mutual Voice FX exclusion, exact two-block addressing, complete
native `MemP/Stat` record generation, per-connection rate confirmation, and the
88.2/96 kHz device-Delay safe-off/settle sequence. A rate confirmation at any
rate leaves a selected Delay explicitly off until the user enables it again.
Scenes cannot confirm a remembered rate or move a front-panel block, and active
Delay is refused in every device-resident block. The flat and fully edited
Standard native records match the Linux builder byte for byte.

The controller tests also prove that Disconnect publishes immediately while
USB release drains on the serial worker, queued writes are discarded after a
disconnect, and an interrupted scene reports its confirmed progress plus the
possibility of a partially changed device.

## Emulator acceptance

The final APK was inspected at 720x1600 and 320 dpi on Android 15. Verified:

- Mixer, Fat Channel, Effects, Presets, and Device navigation and layout;
- system-bar insets and unobstructed bottom navigation;
- small, fine-grained Effects scrolling and access to shared device reverb;
- parameter-driven Voice FX graphs and disabled unknown/high-rate Delay controls;
- phone-scene save/load across process restart;
- exact Input 1/2 and Block 1/2 save controls with confirmation and honest
  `WRITE_SENT_UNVERIFIED` labeling;
- serialized scene apply;
- injected readback failure releases control, preserves the last confirmed
  state, displays the exact error, and leaves only Connect enabled.

## Proof boundary

No physical phone installation, USB transfer, io24 command, firmware action,
or audible test occurred during this 0.3.4 build. Earlier physical trials prove
the direct Android transport and USB-audio coexistence, plus application of the
Input 2 mute write. The expanded mixer, Fat Channel, Voice FX, reverb, scene,
and high-rate paths are ready for, but not promoted beyond, the next physical
acceptance run.
