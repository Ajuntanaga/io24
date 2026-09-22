# Android USB Control and Audio Coexistence

Authorized live test completed on 2026-09-22.

This report applies only to version 0.1.0. The later 0.2.0 Input 2 mute path has
not been installed or exercised on hardware.

## Test setup

- Phone: BLU 1660V
- Device: PreSonus Revelator io24 (`194f:0422`)
- App: io24 Controller 0.1.0 debug build from commit `ddab3df`
- APK SHA-256: `f415bc4af06e18eda3691ba4a0a21cbebb9e56c840d1291f403166062336ef17`
- Audio stimulus: patch-cable signal into io24 input 2

## Native control result

Android granted the app access to the io24. The read-only probe claimed vendor
interface 5 without forced driver detachment and reported:

- Protocol: 1
- Command limit: 2048 bytes
- Response limit: 2048 bytes
- `GetP / Appl / JaSt` reply: 2048 bytes
- State slots: 503

The app continued to show **Connected read-only** after switching to a separate
recording application. **Disconnect Control** then released interface 5 and the
app reported **Control interface released**.

## Audio coexistence result

While the controller retained interface 5, a separate Android application
recorded five seconds from io24 input 2. The captured patch-cable signal was
loud and clear. Playback also ran through the io24 output.

This verifies simultaneous native vendor control, Android USB audio input, and
Android USB audio output on the direct phone-to-io24 connection.

## Boundary

This APK contains only capability reads and one state read. It does not yet
write mixer, Fat Channel, Voice FX, reverb, preset, scene, sample-rate, reset,
or firmware state. The result validates the Android transport architecture; it
does not claim that the full controller UI or write path is implemented.

The temporary HTTPS transfer tunnel and local APK origin were stopped after
installation, and their temporary APK copy was removed.
