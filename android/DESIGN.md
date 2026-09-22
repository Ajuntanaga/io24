# io24 Android Controller Design

## Goal

Build a standalone Android controller that can hold the Revelator io24 vendor
control interface while Android continues to use the device for audio. Add
controls one proven native record at a time, with device-state readback after
every write.

The phone connects directly to the io24. A laptop is not part of the runtime
path.

## Verified foundation

The first APK will:

1. Recognize only USB device `194f:0422`.
2. Wait for an explicit **Inspect io24** action.
3. Request Android USB permission.
4. Select vendor interface 5, alternate setting 1, without force-detaching a
   driver.
5. Verify bulk OUT `0x01` and bulk IN `0x81`.
6. Run the three read-only paesdk capability queries.
7. Send one synchronous `GetP / Appl / JaSt` state-read request.
8. Validate the matching `Rply`, decode the Input 2 mute flag, and retain the
   interface until the user taps **Disconnect**.

The 0.1.0 APK completed this flow on the BLU 1660V while another application
recorded and played audio through the io24.

## First bounded write

Version 0.2.0 adds only Input 2 mute:

1. The action remains disabled until a valid full-state reply is available.
2. A tap sends one fixed `SetP / Appl / Pari` record with channel index 1,
   parameter ID 7, and integer value 0 or 1.
3. The transport waits 350 ms. `SetP` is fire-and-forget, so silence is never
   treated as an acknowledgment.
4. The app sends a new `GetP / Appl / JaSt` request with a fresh UID.
5. Success requires bit 4 of state flags slot 42 to match the requested mute
   value. A timeout, malformed reply, or mismatch is reported as unverified and
   the control interface is released.

The application exposes no generic parameter writer. It does not touch
interface 6, reset the USB device, claim an audio or MIDI interface, poll
meters, or run host-side audio effects.

## Architecture

- `PaeFrame` owns endian-safe paesdk request construction and response
  validation. It has no Android dependencies.
- `Io24UsbProbe` owns Android USB discovery, permission-independent connection
  work, interface selection, capability reads, serialized transfers, and
  write-then-readback verification.
- `MainActivity` owns permission flow and a restrained status screen. It never
  performs USB work on the main thread.
- A protocol-vector fixture, pure-Java tests, and host-side safety tests keep
  the Android framing aligned with `io24.py` and limit the write surface to the
  fixed Input 2 mute record.

## Data and lifecycle

The activity discovers the matching device, asks for permission after a button
press, and starts one background probe. A successful probe reports protocol
version, command/response limits, response length, the number of readable state
slots, and the current Input 2 mute state. USB work runs on a single background
executor. The connection remains open while the activity is backgrounded so
the user can switch to a recorder or camera application. **Disconnect**, device
detach, activity destruction, or an unverified write releases only interface 5
and closes the USB connection.

## Errors

Every failure becomes a short user-facing status: device absent, permission
denied, interface unavailable, endpoint mismatch, capability-query failure,
short transfer, timeout, malformed reply, readback mismatch, or detach.
Failures close the control connection. The app never retries a USB command
automatically.

## Build constraints

- Java source and Android platform APIs only; no AndroidX or Compose.
- Minimum Android API 23.
- No Internet permission, analytics, account, storage, or network dependency at
  runtime.
- Each new write-capable APK remains offline until its physical USB run is
  separately authorized.

## Verification boundary

Host tests can prove project structure, exact frame bytes, reply parsing,
bounded source surface, and successful APK assembly. The completed 0.1.0 phone
test proves simultaneous vendor control and Android audio capture. Only a new,
separately authorized phone test can prove that the 0.2.0 mute write is accepted
and confirmed by the physical io24.
