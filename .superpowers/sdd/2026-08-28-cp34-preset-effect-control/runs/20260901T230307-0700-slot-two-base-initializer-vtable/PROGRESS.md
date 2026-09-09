# CP34 slot-two base-initializer vtable boundary — progress

Opened: 2026-09-01T23:03:07-07:00
Status: active, offline-only static analysis.

## Starting boundary

The sealed alternate equal-branch stage proves that table slot two stores and
dispatches `device + 0x5090` through its vtable `+0x4` entry. It explicitly
leaves that object's vtable and dynamic target unresolved.

## Planned bounded action

Inspect only the direct base-initializer call immediately before the slot-two
address store, then record a concrete vtable installation only if the exact
callee body contains it. Do not trace virtual targets or semantics.

## 2026-09-01T23:12:18-07:00 — outer-base vtable boundary sealed

- The component-table constructor captures the outer device in `r4` at
  `0x5e016` and immediately calls `0x5d990` with unadjusted `r0` at `0x5e018`.
- That callee captures the same receiver at `0x5d9a0`, loads static primary
  table raw `0x6d3a8`, derives its `+0x48` secondary table raw `0x6d3f0`, and
  stores them directly at outer-receiver offsets `+0` and `+4` at `0x5d9b6`.
- The existing slot-two address (`device + 0x5090`) is materialized only later
  in the caller at `0x5e03e..0x5e04a`. The direct base call therefore does not
  bind a slot-two vtable. The slot-two virtual target and semantics remain
  unresolved; no indirect target was followed.
- TDD RED was the missing `slot_two_base_initializer_vtable_boundary` report
  key. The focused hardware-free contract passed 1/1 in 9.739 seconds; the
  firmware-static module passed 32/32 in 9.948 seconds. The complete
  hardware-free suite passed 177 tests with one expected local-artifact skip
  in 211.171 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. A separate exact static scope may establish the direct
construction route for the embedded object at `device + 0x5090` only if it can
be source-bound without following a virtual target. It may not infer semantics,
parser behavior, component identity, executable placement, or a firmware
implementation.
