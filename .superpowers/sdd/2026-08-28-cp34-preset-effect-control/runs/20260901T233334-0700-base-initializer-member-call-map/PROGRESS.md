# CP34 base-initializer member-call map — progress

Opened: 2026-09-01T23:33:34-07:00
Status: active, offline-only static analysis.

## Starting boundary

The direct base initializer at `0x5d990` receives the unadjusted outer device
and writes its own base tables. The local component-table wrapper and all exact
`0x5090` immediate materializations contain no direct slot-two subconstructor.

## Planned bounded action

Build only a reachable static control-flow map for the direct base initializer,
recognize its return correctly, and inventory locally formed outer-member `r0`
receivers at direct callsites. Do not enter those targets.

## 2026-09-01T23:42:40-07:00 — base-initializer prologue map sealed

- The reachable static CFG from direct entry `0x5d990` contains 510 decoded
  instructions and 43 direct calls, no dynamic program-counter transfer, and
  one normal return: `pop.w {r4, r5, r6, r7, r8, sb, sl, fp, pc}` at `0x5df6a`.
- The exact entry prologue has four direct member-construction calls only:
  outer offsets `+0xc38`, `+0xc5c`, `+0x11e0`, and `+0x3a70`, at calls
  `0x5d9ec`, `0x5d9f6`, `0x5da12`, and `0x5da1e` respectively.
- Slot-two `device +0x5090` is absent from that prologue member-call map. This
  does not inspect later initializer calls or any target, so it does not rule
  out later/nonlocal construction or identify a vtable, virtual target, parser
  behavior, or semantics.
- TDD RED was the missing `base_initializer_member_call_map_boundary` report
  key. The focused hardware-free contract passed 1/1 in 19.961 seconds; the
  firmware-static module passed 35/35 in 20.176 seconds. The complete
  hardware-free suite passed 180 tests with one expected local-artifact skip
  in 254.657 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. A separate exact static scope may inspect one named later
base-initializer callsite only if its `r0` receiver can be source-bound before
the call. It may not enter a target, follow a virtual target, infer semantics,
parser behavior, component identity, executable placement, or a firmware
implementation.
