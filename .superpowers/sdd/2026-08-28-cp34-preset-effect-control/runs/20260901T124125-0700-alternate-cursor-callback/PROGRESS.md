# CP34 alternate-path constructed cursor callback boundary — progress

Opened: 2026-09-01T12:41:25-07:00
Status: active, offline-only static analysis.

## Starting boundary

The sealed paired-handoff stage source-binds the second call's alternate gate
at `0x5338e`, but initially leaves its first `r4` virtual callback unresolved.
The direct caller constructs that same stack receiver immediately before both
handoffs.

## Planned bounded action

Verify the constructor literal/vtable route, the first virtual callback target,
and the returned pair's direct capture only. Do not give the returned `+0x1c`
word parser or component semantics.

## 2026-09-01T12:50:19-07:00 — constructed cursor callback boundary sealed

- The direct caller constructs the stack receiver at `sp+0xc` through
  `0x42236 -> 0x2ccf4`. The constructor loads literal `0x600869e4`, stores
  vtable address `0x600869ec` in the receiver, and the direct post-construction
  cursor routine writes only receiver `+0x1c` in its own bounded function body.
- If the alternate gate is reached and normal AAPCS callee-saved `r4` flow is
  preserved, alternate target `0x5338e` loads that receiver's vtable first word
  and calls pinned raw target `0x2cb58`. That callback loads receiver `+0x1c`,
  sign-extends it into `r1`, returns, and the caller captures low/high parts in
  `r6`/`r7` at `0x5339e`/`0x533a6`.
- This is an exact constructed receiver/callback/result route, not a meaning
  for the returned word. Parser state, record order, `r7` semantics, Voice FX
  slot one, component 201, top-level apply `r1` provenance, `godv` linkage,
  executable placement, and a firmware implementation all remain unresolved.
- TDD RED was the missing `alternate_cursor_callback_boundary` report key. The
  focused hardware-free contract passed 1/1 in 14.936 seconds; the
  firmware-static module passed 28/28 in 15.527 seconds. The complete
  hardware-free suite passed 173 tests with one expected local-artifact skip
  in 290.082 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. A separate exact static scope may bind only the same
receiver's immediate `+0x4` vtable call at `0x533c6`, including its direct
stack argument shape. It may not infer cursor semantics, parser behavior,
component identity, or an image implementation.
