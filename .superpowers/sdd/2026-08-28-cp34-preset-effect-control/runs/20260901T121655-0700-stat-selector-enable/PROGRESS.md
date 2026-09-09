# CP34 direct `Stat` selector-enable argument boundary — progress

Opened: 2026-09-01T12:16:55-07:00
Status: active, offline-only static analysis.

## Starting boundary

The sealed component-key comparison record proves how the selector matches two
locals but does not establish whether prior helper work reaches the selector
gate. The call at `0x42266` is already source-bound to `0x531e0` via the
dispatcher `+0x38` vtable slot.

## Planned bounded action

Verify the caller's `r3` setup, the callee's immediate capture, and its zero
gate only. Record whether the call enables that gate if reached; do not infer
the later component index or follow a parser/helper.

## 2026-09-01T12:22:38-07:00 — direct selector-enable boundary sealed

- The pinned direct `Stat` handoff loads its vtable receiver at `0x4225a`,
  explicitly writes `r3 = 1` at `0x4225c`, prepares `r2`/`r1`, loads the
  `+0x38` vtable target, and calls it at `0x42266`. The pinned slot still
  resolves to structured-state method `0x531e0`.
- That callee copies fourth argument `r3` to `r7` at `0x531f4`, then—if its
  earlier helpers have not returned—compares it with zero at `0x53232`. Its
  zero branch targets `0x534ba`; `r3 = 1` enables the fallthrough at `0x53238`
  if that gate is reached.
- This proves only the enabled selector-gate value for this direct handoff, not
  unconditional selector-path entry or the dynamic later `r7` component index.
  Voice FX slot one, component 201, top-level apply `r1` provenance,
  parser/default semantics, `godv` linkage, executable placement, and a
  firmware implementation all remain unresolved.
- TDD RED was the missing `stat_selector_enable_boundary` report key. The
  focused hardware-free contract passed 1/1 in 7.434 seconds; the
  firmware-static module passed 26/26 in 7.873 seconds. The complete
  hardware-free suite passed 171 tests with one expected local-artifact skip
  in 223.228 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. A separate exact static scope may compare the paired
second `+0x38` handoff at `0x42280` with this one, including only the direct
`r1`/`r3` entry-gate values. It may not infer a selected component, parser
semantics, or a firmware image.

## 2026-09-01T12:29:56-07:00 — wording correction revalidated

- A follow-on control-flow audit found two bounded helper calls before the
  `0x53222`/`0x53232` gates. They can return before either gate executes.
  The result has therefore been corrected from unconditional selector-path
  entry to `r3 = 1` enabling the selector gate **if reached** after those
  helpers. No firmware or hardware fact changed.
- The narrowed contract first failed under its updated expected result, then
  passed focused 1/1. The firmware-static module passed 26/26 in 7.555 seconds
  and the complete hardware-free suite passed 171 tests with one expected
  local-artifact skip in 223.650 seconds. The only warning was again the
  pre-existing temporary-WAV `ResourceWarning` at
  `re/cp34_current_slot_survey.py:260`.
