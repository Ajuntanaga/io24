# CP34 unlinked Channel-2 Stat routing scope

Timestamp: 2026-09-04T01:59:15-07:00
Status: active checkpoint; hardware mutation stopped at the retained Channel-1
preservation boundary.

## Objective

Explain the repeated dry result from the complete custom Delay and factory Slap
Echo records written to Channel-2 global slot 3. Determine whether the current
device state can dispatch their Voice FX component, and bind the alternate
slot-two target before choosing another live test.

## Live operation performed in this continuation

The user directed continuation of the device-dependent objective. The live
operation was deliberately bounded to the existing dedicated read-only client:

- read the host battery;
- match io24 serial `AB7C22200355` and descriptor version;
- claim interface 5 and select alternate setting 1;
- send exactly two `GetP | Appl(0) | JaSt` requests;
- release the interface.

It sent no `SetP`, preset/effect command, audio stream, link change, Channel-1
write, reset, DFU, firmware command, install, Wine access, or network request.

## Offline analysis and edit scope

- Decode only the pinned UC 4.7.2 io24 application image with SHA-256
  `65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.
- Extend the existing read-only preflight report with the raw flags word and
  decoded stereo-link bit.
- Add exact instruction contracts for unlinked slot-pair routing, slot-two
  object identity/state apply, and linked positive-slot dual dispatch.
- Update current documentation and preserve earlier sections as historical,
  superseded evidence.
- Run hardware-free tests only after the one bounded live read.

## Excluded actions

- No further USB/device access without a new exact live scope.
- Channel 1 remains untouched; do not enable stereo link or apply a Channel-1
  slot while that boundary stands.
- No output/headphone/routing change, ALSA playback/capture, stimulus, or
  physical patch change.
- No firmware image emission, packaging, staging, flash, reset, DFU, restore,
  install, Wine, or network action.
- Stop any later live operation at or below 10% host battery.

## Authoritative predecessor

`../20260903T232428-0700-channel2-slot3-173ms/` retains the complete write,
selection, recall-edge, factory Slap Echo, passive-audio, and operator-audibility
evidence. Those files are immutable predecessors and were not edited here.

