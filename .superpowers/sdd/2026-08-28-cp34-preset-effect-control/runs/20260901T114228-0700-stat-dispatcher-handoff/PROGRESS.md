# CP34 `Stat` dispatcher first-handoff boundary — progress

Opened: 2026-09-01T11:42:28-07:00
Status: sealed, offline-only static analysis.

## Starting boundary

The sealed predecessor proves seven application-code `Stat` tag comparisons
but only inventories direct immediate edges into `0x5545c`. Its sole such edge
is the known secondary-interface adjustor tail branch, so the outer dispatcher's
first vtable handoff and the relation of its argument registers to top-level
apply remain unbound.

## Planned bounded action

Verify only the `0x420bc` `Stat` branch into `0x42200`, its `+0x38` vtable
call, the pinned `0x531e0` target, and the captured `r1`/`r2` ABI at that
callee's entry. Do not traverse its component-selection loop or any later
state/model dispatch.

## 2026-09-01T11:49:43-07:00 — first-handoff ABI sealed

- Pinned live-device vtable word `0x10cb40` targets dispatcher `0x420bc`; its
  `+0x38` slot at `0x10cb78` targets structured-state method `0x531e0`.
- The dispatcher copies its outer `r1` into `r4` at `0x420c4`, compares the
  `Stat` FourCC at `r1+0x8`, and conditionally branches at `0x420ea` to
  `0x42200`. This binds the outer `Stat` branch rather than merely a literal.
- At the first `+0x38` virtual call, the code captures the receiver in `r5`,
  sets `r2` to local stack address `sp+0xc`, moves `r6` into `r1`, loads the
  vtable target at `0x42262`, and calls it at `0x42266`. `0x531e0` immediately
  captures incoming `r1` into `r6` and incoming `r2` into `r4`.
- This proves the first handoff ABI only. It does not traverse `0x531e0`'s
  component-selection loop, identify a component state-interface call, or bind
  the later top-level apply `0x5545c` `r1`. The sealed result is
  `STAT_DISPATCHER_FIRST_VTABLE_HANDOFF_SOURCE_BOUND_TOP_LEVEL_R1_UNRESOLVED`.
- TDD RED was the missing `stat_dispatcher_first_handoff_boundary` report key;
  its focused hardware-free contract passed 1/1 after the minimal verifier.
  The complete hardware-free suite passed 168 tests with one expected
  local-artifact skip in 219.485 seconds. The only warning was the pre-existing
  temporary-WAV `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This bounded stage is sealed. Any later static investigation must name one
exact component-selection-to-state-interface transfer inside `0x531e0` and
must independently track its argument registers. It must not follow the
excluded model-state indirect call, infer parser/default behavior, invent a
code cave, or emit an image.
