# CP34 primary state-apply caller provenance — progress

Opened: 2026-09-01T11:13:27-07:00
Status: sealed, offline-only static analysis.

## Starting boundary

The sealed predecessor source-binds the embedded-owner `r0` route through the
secondary interface to `0x5545c`, but leaves all direct static caller and `r1`
record provenance unresolved. The model-state dynamic dispatch at `0x54730`
remains excluded.

## Planned bounded action

Inspect only primary-vtable `+0x28` virtual calls whose receiver may originate
at embedded-owner `+0x11e0`. Record a caller only if its receiver vtable is
proven to be `0x10c6bc`; otherwise preserve the no-candidate/unresolved
boundary without following later model-state calls.

## 2026-09-01T11:22:55-07:00 — primary caller provenance sealed

- The required Voice FX primary table remains `0x10c6bc`; its `+0x28` slot is
  raw `0x10c6e4` and points to top-level apply `0x5545c`.
- A reproducible local straight-line scan found ten generic `+0x28` virtual
  dispatches at raw calls `0x27458`, `0x27c9a`, `0x281f0`, `0x2dfb2`,
  `0x3041e`, `0x30572`, `0x30ce2`, `0x30d44`, `0x30d8c`, and `0x53450`.
  Every candidate has the vtable-load/slot-load/`blx` form, but none locally
  constructs embedded-owner `+0x11e0` or preserves that owner as `r0` at the
  call boundary.
- Therefore these are syntactic slot matches only: none source-binds vtable
  `0x10c6bc`, target `0x5545c`, or a caller-supplied `r1` record. The sealed
  result is `NO_LOCAL_STRAIGHT_LINE_EMBEDDED_OWNER_PRIMARY_APPLY_CALLER`.
- TDD RED was the missing
  `primary_apply_embedded_owner_caller_boundary` report key; its focused
  hardware-free contract passed 1/1 after the minimal verifier. The complete
  hardware-free suite passed 166 tests with one expected local-artifact skip
  in 222.125 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This bounded stage is sealed. Any future caller investigation must start with
a separate exact scope and checkpoint naming a concrete dispatcher or object-
transfer boundary into one generic call. It must not promote a slot match to a
Voice FX receiver/target proof, follow a model-state indirect call, invent a
parser hook/code cave, or emit an image.
