# io24 Android Read-Only Probe Design

## Goal

Build the smallest standalone Android application that can prove the phone may
hold the Revelator io24 control interface while Android continues to use the
device as an audio interface.

The phone connects directly to the io24. A laptop is not part of the runtime
path.

## First milestone

The first APK will:

1. Recognize only USB device `194f:0422`.
2. Wait for an explicit **Inspect io24** action.
3. Request Android USB permission.
4. Select vendor interface 5, alternate setting 1, without force-detaching a
   driver.
5. Verify bulk OUT `0x01` and bulk IN `0x81`.
6. Run the three read-only paesdk capability queries.
7. Send one synchronous `GetP / Appl / JaSt` state-read request.
8. Validate the matching `Rply` and retain the interface until the user taps
   **Disconnect**.

The application will not send `SetP`, touch interface 6, reset the USB device,
claim an audio or MIDI interface, poll meters, or run host-side audio effects.

## Architecture

- `PaeFrame` owns endian-safe paesdk request construction and response
  validation. It has no Android dependencies.
- `Io24UsbProbe` owns Android USB discovery, permission-independent connection
  work, interface selection, capability reads, and one synchronous state read.
- `MainActivity` owns permission flow and a restrained status screen. It never
  performs USB work on the main thread.
- A protocol-vector fixture and host-side safety tests keep the Android framing
  aligned with `io24.py` and prevent write-capable tags or permissions from
  entering the first milestone.

## Data and lifecycle

The activity discovers the matching device, asks for permission after a button
press, and starts one background probe. A successful probe reports protocol
version, command/response limits, response length, and the number of readable
state slots. The connection remains open while the activity is backgrounded so
the user can switch to a recorder or camera application. **Disconnect**, device
detach, or activity destruction releases only interface 5 and closes the USB
connection.

## Errors

Every failure becomes a short user-facing status: device absent, permission
denied, interface unavailable, endpoint mismatch, capability-query failure,
short transfer, timeout, malformed reply, or detach. Failures close the control
connection. The app never retries a USB command automatically.

## Build constraints

- Java source and Android platform APIs only; no AndroidX or Compose.
- Minimum Android API 23.
- No Internet permission, analytics, account, storage, or network dependency at
  runtime.
- The initial APK is a diagnostic build. A physical USB run remains separately
  authorized and is not part of offline compilation.

## Verification boundary

Host tests can prove project structure, read-only framing, parser behavior once
a JDK is available, and successful APK assembly once an Android SDK is
available. Only a separately authorized phone test can prove simultaneous
vendor control and Android audio capture.
