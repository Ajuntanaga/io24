# CP34 structured-state dispatcher boundary — progress

Opened: 2026-09-01T11:25:02-07:00
Status: sealed, offline-only static analysis.

## Starting boundary

The sealed primary-slot inventory found no local straight-line generic virtual
dispatch that source-binds the Voice FX embedded owner, top-level apply target,
or independent `r1` record. The model-state dynamic dispatch remains excluded.

## Planned bounded action

Inventory only application-local `Stat` literal/tag evidence and its direct
control flow. Record a top-level apply caller only if a pinned dispatcher slice
directly reaches `0x5545c` and materially binds `r1`; otherwise preserve the
no-dispatcher/no-route boundary.

## 2026-09-01T11:35:56-07:00 — structured-state dispatcher boundary sealed

- `Stat` is represented in the pinned application as little-endian literal
  bytes `tatS` (`0x53746174` as a conventional big-endian FourCC). Exactly
  seven such literals occur at raw `0x2f278`, `0x30a10`, `0x30a60`, `0x30bdc`,
  `0x30c30`, `0x41ea0`, and `0x423d4`.
- The new source-bound contract verifies each literal's Thumb PC-relative
  load, tagged-record `+0x8` load, and compare instruction. That establishes
  application-code tag comparisons, rather than a host JSON/string match.
- A full-image linear immediate-edge inventory finds exactly one branch to
  top-level apply `0x5545c`: the previously established secondary-interface
  adjustor tail branch `0x555bc -> 0x5545c`. No validated `Stat` literal-load,
  record-tag-load, or compare instruction is that edge's source.
- This is deliberately not a complete control-flow graph. It does not rule out
  dynamic or interprocedural routing, and it does not bind a direct top-level
  caller or the independently supplied `r1` record. The sealed result is
  `STRUCTURED_STATE_TAG_SITES_SOURCE_BOUND_DIRECT_APPLY_ROUTE_UNRESOLVED`.
- TDD RED was the missing `structured_state_dispatcher_boundary` report key;
  its focused hardware-free contract passed 1/1 after the minimal verifier.
  The full hardware-free suite passed 167 tests with one expected
  local-artifact skip in 231.293 seconds. The only warning was the pre-existing
  temporary-WAV `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This bounded stage is sealed. Any later static investigation must name an
exact dispatcher-to-apply transfer boundary and preserve the distinction
between verified tag comparisons, dynamic routing, parser/default semantics,
and executable placement. It must not follow the excluded model-state indirect
call, infer optional-field behavior, invent a code cave, or emit an image.
