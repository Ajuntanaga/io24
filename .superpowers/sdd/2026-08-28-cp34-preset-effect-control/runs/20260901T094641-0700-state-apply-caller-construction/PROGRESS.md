# CP34 top-level state-apply caller-construction recovery — progress

Opened: 2026-09-01T09:46:41-07:00
Status: sealed, offline-only static analysis.

## Starting boundary

The verified predecessor proves that `0x5545c` has two static entry literals,
but captures an independent receiver from `r1`, forwards it unchanged to
model 0, and dispatches it dynamically at `0x54730`. The receiver type and
target remain unresolved.

## Planned bounded action

Inspect the owner/vtable and construction context of only the two top-level
entry literals. Record whether either context provides direct evidence about
the separate incoming receiver; stop without following any new state-apply
indirect call.

## 2026-09-01T09:54:06-07:00 — owner-construction boundary sealed

- The shared top-level state-apply entry `0x5545c` occurs at `+0x38` in the
  primary table at raw `0x10c4e8` and at `+0x28` in the distinct primary table
  at raw `0x10c6bc`.
- The first table is installed twice from literal locations `0x3d708` and
  `0x3d868`, each written to a live owner at `r8+0x22c`. Its owner identity is
  unresolved; no semantic identity has been inferred from the adjacent table.
- The second table is installed from `0x418fc` into `r4+0x11e0`; this is the
  source-bound Voice FX owner entry. It shares the apply implementation but
  does not construct or type the input receiver.
- The top-level method independently captures the input from `r1` at
  `0x55462`, before forwarding it to the pre-existing dynamic `+8` dispatch at
  `0x54730`. Neither validated owner installation materializes that separate
  receiver. The sealed result is
  `OWNER_INSTALLATIONS_DO_NOT_BIND_INPUT_RECEIVER_TYPE`.
- TDD RED was the missing `state_apply_owner_construction_boundary` report
  key; the focused hardware-free contract passed 1/1. The broad hardware-free
  suite passed 164 tests with one expected local-artifact skip in 205.779
  seconds. The only warning was the pre-existing temporary-WAV `ResourceWarning`
  at `re/cp34_current_slot_survey.py:260`.
- No image, device, USB, audio, Wine, network, or other live action occurred.

## Next safe action

This bounded stage is sealed. A future caller-construction investigation must
start with a separate scope and checkpoint that identifies an exact caller
boundary. It must not infer an input receiver type from either owner table,
follow another model-state indirect call, invent a parser hook/code cave, or
emit an image.
