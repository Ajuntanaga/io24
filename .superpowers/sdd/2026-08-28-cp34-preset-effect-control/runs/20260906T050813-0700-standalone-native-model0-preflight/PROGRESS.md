# Standalone native model-0 preflight progress

Timestamp: 2026-09-06T06:20:48-07:00
Status: **SLOT-0 PLAN CANCELLED; NO STOCK CHANNEL-2 TARGET ELIGIBLE**

## User target correction

The user prohibited slot 0 because it belongs to Channel 1 and requested a
second-channel slot. No live write occurred. Slots 2/3 are the actual Channel-2
pair, but their exact firmware-native records contain only the Fat Channel and
do not own component 201/Voice FX. They cannot carry the prepared model-0
private-reverb state.

The staging runner now blocks both Channel-1 owning slots before device open
under the current user requirement. Focused verification of that new gate and
the native format passes 21/21. `CHANNEL2-CONSTRAINT.md` records the two valid
next choices.

## Completed offline

- Recovered and validated all four firmware-native version-2 slot defaults.
- Separated slots 0/1, which own component 201, from strip-only slots 2/3 and
  from the sixteen tagged library records.
- Built pinned slot-0 and slot-1 model-0 candidates while preserving each
  native Fat Channel chunk byte-for-byte.
- Built byte-exact firmware-default restoration records for both owning slots.
- Added a bounded live runner that validates candidate hash and slot ownership
  before opening hardware and distinguishes transport/readback from standalone
  persistence and audibility.
- Corrected `read_params()` processing-channel normalization: its values are
  zero-based 0/1, while the public control and operator input names are 1/2.
- Selected slot 0 and physical Input 1 for the first acceptance attempt. This
  avoids depending on host-selected routing or a second-block selection after
  the standalone cold boot.
- Passed the final complete hardware-free suite: 261 tests, one expected skip,
  no failures, exit 0.

## Current boundary

There is no authorized or eligible live action. Do not execute the cancelled
`LIVE-PLAN.md`. Continue only after the user chooses either owning slot 1 routed
to physical Input 2, or an actual Channel-2 slot/button requirement deferred to
the private custom-firmware lane.

After a standalone audible pass, CP34 stops. Linux-host cleanup and public
GitHub packaging follow. Custom-firmware work stays private and begins only
after the host package, unless the user changes that order.
