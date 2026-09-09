# CP34 slot-two immediate-materialization inventory — progress

Opened: 2026-09-01T23:23:34-07:00
Status: active, offline-only static analysis.

## Starting boundary

The sealed wrapper-tail stage finds no direct slot-two subconstructor in
`0x5e04a..0x5e08a`. That does not rule out a construction callsite elsewhere.

## Planned bounded action

Search only direct immediate `0x5090` materializations, validate local Thumb
contexts, and retain any non-source-bound hit as a candidate rather than a
route. Do not traverse targets or infer object behavior.

## 2026-09-01T23:30:38-07:00 — immediate-materialization inventory sealed

- The full pinned application was decoded at each halfword-aligned raw offset
  for an exact immediate operand `0x5090`. It produced one raw candidate only:
  `0x5e03e`, `45f29002`, `movw r2, #0x5090`.
- Exact local Thumb evidence independently binds that candidate to the existing
  component-table path: it adds the outer device at `0x5e04a` and stores the
  resulting address at table slot two `0x5e88` at `0x5e064`.
- No additional direct immediate-materialization route is source-bound. This
  does not exclude split, non-immediate, or dynamic construction elsewhere; it
  does not identify a vtable, virtual target, parser behavior, or semantics.
- TDD RED was the missing
  `slot_two_immediate_materialization_inventory_boundary` report key. The
  focused hardware-free contract passed 1/1 in 17.923 seconds; the
  firmware-static module passed 34/34 in 22.805 seconds. The complete
  hardware-free suite passed 179 tests with one expected local-artifact skip
  in 244.182 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. Before another static continuation, inspect the existing
task-local evidence index for a different source-bound seam. Do not repeat the
immediate scan as a substitute for a new construction route, and do not follow
a virtual target, infer semantics, parser behavior, component identity,
executable placement, or a firmware implementation.
