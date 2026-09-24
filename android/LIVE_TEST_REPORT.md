# Android physical test record

The current 0.3.4 controller has not yet sent its expanded control surface or
native preset-block writer to a
physical io24. The physical results below are the proven foundation from the
earlier transport builds.

## Setup

- Phone: BLU 1660V
- Device: PreSonus Revelator io24 (`194f:0422`)
- Signal: patch-cable signal into io24 Input 2

## Control and audio coexistence

The 0.1.0 app claimed vendor interface 5 without forced driver detachment and
reported protocol 1, 2048-byte command and response limits, a complete
2048-byte `GetP / Appl / JaSt` reply, and 503 state slots.

While the app retained interface 5, a separate Android recorder captured five
seconds from io24 Input 2. The patch-cable signal was loud and clear, and
playback returned through the io24 output. Returning to the controller still
showed it connected. Disconnect then released the control interface.

This proves that direct native vendor control can coexist with Android USB
audio input and output on this phone.

## Manual launch and power observation

The 0.2.1 build removed automatic USB-attach launch. After a phone system
update and a transient USB power incident, the user manually opened the app
and completed a fresh connection. The io24 then remained powered and reported
Input 2 mute Off. The timing does not establish that the APK caused or fixed
the earlier phone-side power cycling.

## Input 2 mute and short reply

The user tapped **Mute input 2** in 0.2.1. The app reported that the following
state reply was too short and released control. A fresh connection then read
Input 2 mute On. This proves that `Pari` parameter 7, channel index 1 applied,
and that the old verifier had consumed the firmware's short `SetP` reply as if
it were the next `JaSt` response.

The user did not hear attenuation on the observed path. That run did not
isolate whether monitoring was before the mute point or routed independently,
so audible mute is not claimed.

The matching Unmute attempt produced the same old verifier error. Its final
physical state was not read back in that run.

## 0.3.4 boundary

Version 0.3.4 drains and validates each optional short write reply before any
fresh state request. It also adds the full typed mixer, Fat Channel, Voice FX,
native reverb, scene, settings, and exact front-panel block architecture. The
native block body is byte-matched to the Linux encoder, but neither that send
nor its recall has been attempted from this APK. Exact byte vectors, state
handling, failure recovery, and emulator workflows pass offline, but those
expanded writes still require a new physical acceptance run before they are
described as device-confirmed, audible, or power-cycle persistent.
