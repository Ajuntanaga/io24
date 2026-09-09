# CP34 alternate-path cursor-adjust callback boundary — progress

Opened: 2026-09-01T12:52:48-07:00
Status: active, offline-only static analysis.

## Starting boundary

The sealed alternate-cursor stage binds the constructed receiver and its first
vtable callback. The adjacent `+0x4` callback is the same direct cursor routine
whose local stores are already bounded to receiver `+0x1c`.

## Planned bounded action

Verify the call's `r2`/stack argument shape, its exact `+0x4` vtable target,
the zero-argument branch, and local signed handling only. Do not interpret the
word as a parser field or component identity.

## 2026-09-01T13:00:40-07:00 — alternate cursor-adjust boundary sealed

- The entry clears `r1` and retains zero in callee-saved `r5`. If alternate
  flow reaches `0x533c6` under ordinary ABI preservation, it passes that zero
  as the `+0x4` cursor callback's stack argument, with `r2:r3` sourced from the
  prior low/high callback return in `r6:r7`.
- The constructed receiver's `+0x4` vtable word resolves to raw `0x2cb60`.
  Its zero-argument branch loads receiver `+0x1c`, adds it to incoming `r2`,
  then applies only local signed/limit handling: it can keep the sum, zero it,
  or store the receiver's `+0x20` limit. No semantic name for the cursor is
  established.
- This source-binds a conditional local cursor adjustment, not parser state,
  record order, `r7` semantics, Voice FX slot one, component 201, top-level
  apply `r1` provenance, `godv` linkage, executable placement, or a firmware
  implementation.
- TDD RED was the missing `alternate_cursor_adjust_boundary` report key. The
  focused hardware-free contract passed 1/1 in 14.997 seconds; the
  firmware-static module passed 29/29 in 15.771 seconds. The complete
  hardware-free suite passed 174 tests with one expected local-artifact skip
  in 285.589 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. A separate exact static scope may inspect the immediate
four-byte reader/comparison following this cursor callback at
`0x5341c..0x53436`, without inferring parser semantics, component identity, or
firmware implementation.
