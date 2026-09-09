# CP34 slot-two local construction-route boundary — progress

Opened: 2026-09-01T23:14:54-07:00
Status: active, offline-only static analysis.

## Starting boundary

The sealed base-initializer boundary proves that its direct call initializes
outer-receiver vtables only. The component-table constructor still stores
`device +0x5090` in slot two at `0x5e064`; its direct local construction route
has not been checked.

## Planned bounded action

Verify the exact straight-line instruction tail from the object-address store
through the constructor return. Do not enter any callee or infer what slot two
does when later dispatched.

## 2026-09-01T23:21:17-07:00 — local construction-route boundary sealed

- The component-table constructor forms `device + 0x5090` in `r2` at
  `0x5e04a` and retains it only by storing it into table slot two at `0x5e064`.
- Its complete fall-through tail through return at `0x5e08a` contains no direct
  call. `r0` is first overwritten with `0x5da0` and later restored to the outer
  device receiver before the constructor returns.
- This is an exact named-function result:
  `NO_LOCAL_DIRECT_SLOT_TWO_SUBCONSTRUCTOR_CALL`. It does not rule out an
  embedded-object construction route elsewhere and does not identify a vtable,
  dynamic target, parser behavior, or semantics.
- TDD RED was the missing `slot_two_local_construction_route_boundary` report
  key. The focused hardware-free contract passed 1/1 in 10.996 seconds; the
  firmware-static module passed 33/33 in 13.936 seconds. The complete
  hardware-free suite passed 178 tests with one expected local-artifact skip
  in 227.406 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. A separate exact static scope may inspect one
source-bound construction callsite outside this wrapper only after identifying
the caller and receiver address. It may not follow a virtual target, infer
semantics, parser behavior, component identity, executable placement, or a
firmware implementation.
