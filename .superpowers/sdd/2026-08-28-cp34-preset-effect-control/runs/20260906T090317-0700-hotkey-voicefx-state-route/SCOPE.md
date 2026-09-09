# CP34 UC 4.7.2 Hot Key and VoiceFX state route

Timestamp: 2026-09-06T09:03:17-07:00

## Objective

Determine whether the previously unexamined `presetHotKey` state supplies the
missing VoiceFX save/apply behavior, and identify the exact source of the active
VoiceFX algorithm when Universal Control serializes a preset.

## Scope

- Read only the retained, hash-pinned Universal Control 4.7.2 binaries and XML.
- Add a deterministic source analyzer and hardware-free regression test.
- Record implications for the Linux host and the later custom-firmware design.
- Do not access Wine, USB, audio, or the connected interface.
- Do not build, patch, stage, or flash firmware.
- Do not use the network.

## Evidence boundary

The result is source-bound evidence for the UC host state route. It does not
prove runtime event propagation, device-resident storage, standalone recall,
VoiceFX activation, simultaneous two-channel routing, or audibility.
