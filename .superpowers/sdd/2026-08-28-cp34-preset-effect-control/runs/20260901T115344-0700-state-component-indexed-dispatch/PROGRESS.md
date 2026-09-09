# CP34 structured-state indexed component-dispatch boundary — progress

Opened: 2026-09-01T11:53:44-07:00
Status: sealed, offline-only static analysis.

## Starting boundary

The sealed first-handoff stage reaches `0x531e0` with separate `r1` and `r2`
arguments but intentionally stops before its component-selection loop. The
later top-level apply `0x5545c` `r1` remains unresolved.

## Planned bounded action

Verify only the `r7`-indexed object-table call at `0x53374..0x5337c`, the
table base created by the device constructor, and the entry that stores the
Voice FX state-interface address. Record whether the selected index is pinned
or dynamic; do not trace index production or parser semantics.

## 2026-09-01T12:00:36-07:00 — indexed component-dispatch boundary sealed

- Structured-state method `0x531e0` saves its device receiver, builds table
  base `device+0x5e78`, and dispatches the object at
  `[table_base + r7 * 8]` through that object's vtable `+0x4` slot at
  `0x53374..0x5337c`. The same call passes its retained record-side value in
  `r1`.
- `r7` is initialized to `-1`, derived from incrementing loop counter `r6`,
  and captured only after a data-dependent comparison. The bounded instructions
  do not fix its selected value, so it remains `DYNAMIC_UNRESOLVED`.
- Device construction stores `device+0x11e4` at table slot one
  (`device+0x5e80`). That Voice FX state-interface vtable's `+0x4` slot is
  adjustor `0x555b8`, which subtracts four from `r0` and branches to top-level
  apply `0x5545c`.
- This establishes the indexed dispatch and the valid slot-one route, not that
  a given structured-state record selected slot one/component 201, nor the
  later top-level apply `r1`. The sealed result is
  `INDEXED_COMPONENT_DISPATCH_SOURCE_BOUND_VOICEFX_SLOT_ONE_ROUTE_SELECTED_INDEX_UNRESOLVED`.
- TDD RED was the missing `indexed_component_dispatch_boundary` report key;
  its focused hardware-free contract passed 1/1 after the minimal verifier.
  The complete hardware-free suite passed 169 tests with one expected
  local-artifact skip in 225.742 seconds. The only warning was the pre-existing
  temporary-WAV `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This bounded stage is sealed. Continue with a separate exact scope for the
data-dependent comparison that supplies `r7`, beginning with the two local
values compared at `0x53326`. Do not follow an unbounded parsing helper, infer
component 201 from a route alone, follow model-state call `0x54730`, invent a
code cave, or emit an image.
