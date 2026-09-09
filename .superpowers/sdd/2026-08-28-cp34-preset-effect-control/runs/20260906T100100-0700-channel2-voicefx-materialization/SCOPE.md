# CP34 final stock Channel-2 VoiceFX discriminator

Timestamp: 2026-09-06T14:54:07-07:00

Status: terminal stock-firmware negative; corrected Channel-2 maximum-wet
effect was not audibly present after the user power-cycled the interface

## Objective

Prepare one final stock-firmware Channel-2 slot-3 trial that corrects the exact
omission in the previous run: materialize the saved VoiceFX model and state in
UC order before transmitting a factory-derived Reverb record with Wet/Dry
raised from 29.5% to 100% for an unmistakable result.

## Current execution boundary

- The retained `LIVE-ATTEMPT-2.json` sent the model/state and one slot-3 record,
  but its preset calls operated physical Channel 1. It is classified
  `INVALID_PHYSICAL_CHANNEL_CONTROL_MAPPING` and is not a Channel-2 result.
- Channel 1's selector has been restored to 0 while bypassed; neither of its
  preset bodies was written.
- The corrected runner ran once on serial `AB7C22200355` at 45 percent battery.
  It sent four model-before-state messages and one maximum-wet slot-3 record,
  then read back Channel 1 unchanged at selector 0/bypassed and Channel 2 at
  selector 3/enabled with VoiceFX still assigned to Input 2. Exact evidence is
  `LIVE-ATTEMPT-3-CORRECTED-MAX-WET.json`.
- No readable record-write reply exists. Physical commit, persistence, recall,
  and internal activation remain unresolved.
- The user completed the disconnected power-cycle check and reported no
  noticed change. `STANDALONE-LISTENING-RESULT.md` seals that human observation
  as the terminal stock-firmware outcome.
- Do not access USB, audio, or the io24.
- Do not start or inspect Wine.
- Do not use the network.
- Do not repeat the completed live stage without a new exact authorization.
- Do not build, stage, patch, or flash firmware.
- Custom firmware is deferred until after the initial GitHub publication.

## Acceptance boundary

The previous transport/listening result did not complete CP34 because recall
targeted the wrong physical channel. The corrected trial did target physical
Channel 2 and used the deliberately maximum-wet record. The user observed no
change after unplugging and reconnecting the interface, so the identifiable
saved VoiceFX/private-reverb pass condition was not met. That negative closes
the stock-firmware investigation without attributing the failure to a specific
internal stage.
