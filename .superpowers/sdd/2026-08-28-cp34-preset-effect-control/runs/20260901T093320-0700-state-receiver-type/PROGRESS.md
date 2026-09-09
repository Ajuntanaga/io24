# CP34 state-apply receiver-type recovery — progress

Opened: 2026-09-01T09:33:20-07:00
Status: sealed, offline-only static analysis.

## Starting boundary

The predecessor checkpoint is verified. It proves that model-0 state apply
forwards a caller-supplied receiver to the `+8` vtable slot at raw `0x54730`,
with `model+0x340` as the output argument. Its target remains
`CALLER_SUPPLIED_RECEIVER_VTABLE_TARGET_UNRESOLVED`.

## Planned bounded action

Inspect only the receiver provenance and its possible construction/vtable
assignment paths in the pinned artifact. Stop if those paths cannot establish a
single concrete receiver type. Do not follow another indirect call or produce
any firmware image.

## 2026-09-01T09:41:33-07:00 — receiver-type boundary sealed

- The top-level state-apply entry `0x5545c` occurs in exactly two static
  application literals: raw `0x10c520` and `0x10c6e4`. These are entry
  references, not evidence of the input receiver's concrete type.
- The input receiver is captured unchanged from `r1` to `r4` at `0x55462`.
  The top-level flow then dispatches its dynamic vtable slots `+0` and `+4`
  at `0x554d4` and `0x554fa`, before forwarding the same object to model 0.
  Model 0 dispatches that receiver's slot `+8` at `0x54730`.
- No concrete receiver vtable or target is materialized in this validated
  top-level receiver flow. The honest result is
  `NO_CONCRETE_RECEIVER_TYPE_IN_VALIDATED_TOP_LEVEL_FLOW`, with
  `TOP_LEVEL_APPLY_ENTRY_LITERALS_DO_NOT_BIND_THE_CALLER_SUPPLIED_RECEIVER_TYPE`
  retained as the boundary.
- TDD RED was the missing `state_apply_receiver_type_boundary` report key.
  The focused hardware-free contract then passed 1/1.
- Broad hardware-free regression: 163 tests passed, one expected
  local-artifact skip, 219.202 seconds. The only warning was the pre-existing
  temporary-WAV `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.
  No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This bounded static pass is sealed. Preserve the receiver-type boundary; do not
assign parser semantics, trace a second indirect call, invent a parser hook or
code cave, or emit an image. Any later attempt to inspect caller construction
must begin as a separate bounded scope and checkpoint.
