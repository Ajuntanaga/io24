# CP34 model-0 decoder input-iteration boundary — progress

Status: sealed, offline-only static analysis.

## Starting boundary

The sealed first-helper result established only local descriptor mechanics.
The decoder's incoming-pointer consumption remained unbound, and the parser
gate remained `OPTIONAL_FIELD_LOOKUP_UNRESOLVED`.

## 2026-09-02T00:26:06-07:00 — input-iteration boundary sealed

- Decoder `0x5e0ec` retains incoming pointer `r1` in `r6`, derives endpoint
  `r7 = r1 + (r2 << 2)` at `0x5e0fe`, and iterates with
  `vldmia r6!, {s15}` at `0x5e110`. This source-binds a four-byte word stride
  and FP-register treatment, not a serialized field type or schema.
- It compares that FP register against zero, transfers flags to APSR, and on
  the corresponding branch reaches the input endpoint check. The normal input
  endpoint branch returns to the same `0x5e110` load.
- The non-branch path loads a model-local candidate count from `sl +0x1cc` and
  candidate base from `sl +0x1c8`; each candidate reads `s14` at `+4`, advances
  by `0x58`, compares with `s15`, and its mismatch branch returns to the
  candidate-loop check at `0x5e12e`.
- TDD RED was the absent `doubler_decoder_input_iteration_boundary` report key.
  The focused contract passed 1/1 in 22.325 seconds; the firmware-static module
  passed 39/39 in 23.389 seconds. The complete hardware-free suite passed 184
  tests with one expected local-artifact skip in 223.686 seconds. The only
  warning was the pre-existing temporary-WAV `ResourceWarning` at
  `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Result and retained boundary

`DOUBLER_DECODER_FP_REGISTER_WORD_ITERATION_AND_MODEL_CANDIDATE_SCAN_SOURCE_BOUND_OPTIONAL_FIELD_LOOKUP_UNRESOLVED`.

Word iteration and FP comparison do not recover serialized field names, record
layout, optional fields/defaults, parser behavior, safe executable placement,
or an image implementation.

## Next safe action

Any continuation needs a separate exact static scope. It may inspect one named
post-match decoder block only after its entry condition and incoming registers
are source-bound. It may not follow a call, label a record field, or weaken any
image or hardware gate.
