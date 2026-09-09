# CP34 paired direct `Stat` handoff entry-gate boundary — progress

Opened: 2026-09-01T12:31:48-07:00
Status: active, offline-only static analysis.

## Starting boundary

The corrected first-handoff result says only that `r3 = 1` enables the selector
gate if prior helpers reach it. The adjacent code returns from that call and
immediately makes a second `+0x38` handoff with different direct arguments.

## Planned bounded action

Verify caller-side `r6 == 0` gating, both exact `r1`/`r3` setups, the common
pinned vtable target, and the callee's `r1` alternate-gate / `r3` selector-gate
instructions. Do not interpret the meanings of either argument or follow
dynamic work.

## 2026-09-01T12:38:32-07:00 — paired entry-gate boundary sealed

- The caller loads byte `r6`, exits on nonzero, and continues only through its
  zero branch. On that normal continuation and standard callee-saved `r6`
  convention, the first virtual handoff supplies `(r1, r3) = (0, 1)` and the
  adjacent second handoff supplies `(r1, r3) = (1, 0)` to the same pinned
  `+0x38` vtable target `0x531e0`.
- The common callee captures `r1` first. If its prior helpers reach the entry
  gate, the first call's zero `r1` permits the later `r3` selector gate, where
  `r3 = 1` enables fallthrough. The second call's nonzero `r1` takes alternate
  branch `0x5338e` before the `r3` selector gate.
- This source-binds paired entry-gate configuration only. It does not prove
  helper/parser completion, record order, `r7`, Voice FX slot one, component
  201, top-level apply `r1` provenance, parser/default semantics, `godv`
  linkage, executable placement, or a firmware implementation.
- TDD RED was the missing `paired_stat_handoff_entry_gates_boundary` report
  key. The focused hardware-free contract passed 1/1 in 7.304 seconds; the
  firmware-static module passed 27/27 in 7.645 seconds. The complete
  hardware-free suite passed 172 tests with one expected local-artifact skip
  in 244.176 seconds. The only warning was the pre-existing temporary-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This stage is sealed. A separate exact static scope may inspect only the first
post-branch setup at `0x5338e` for the second handoff's alternate path. It may
not follow dynamic helpers, infer parser semantics or component identity, or
emit an image.
