---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: local-checkpoint-sealed-review-pending
workflow: offline-static-analysis
updated: 2026-09-05T18:16:19-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260905T172026-0700-structured-state-record-prefix-gate
checkpoint_manifest: CHECKPOINT.sha256
tags:
  - project/io24
  - topic/firmware
  - topic/presets
  - practice/recovery
  - status/offline-only
  - status/review-pending
---

# PreSonus Revelator io24 - CP34 structured-state prefix gate

## Resume first

1. Read task-local `RESUME.md`, this run's `SCOPE.md`, and `PROGRESS.md`.
2. Run `sha256sum -c CHECKPOINT.sha256` from the project root before trusting
   this saved state.
3. Treat this dashboard as an index only. It does not authorize a firmware
   image, hardware action, or device-native preset/effect conclusion.

## Current locally verified state

- The stack wrapper at `0x531e0` reads exactly four bytes from its incoming
  record stream and does not reverse them in this path.
- `0x53212` requires native integer `2`; only equality reaches the component
  selection gates at `0x53222` and beyond.
- The retained factory Slap Echo archive and the existing pure `MemP/Stat`
  encoder both begin `7b690b70`, native word `0x700b697b`, so that raw archive
  is not directly eligible when presented unchanged from byte zero.
- Result:
  `STRUCTURED_STATE_PREFIX_GATE_SOURCE_BOUND_RAW_FACTORY_ARCHIVE_NOT_DIRECTLY_ELIGIBLE`.

## Boundary and verification

No source-bound edge in this scope shows how storage or recall transforms the
raw archive before `0x531e0`. Physical record storage, stored-record equality,
selected component index, Voice FX activation, and audible processing remain
unresolved.

- Focused contract: 1/1 passed in 16.853s after the intended RED.
- Firmware-static module: 45/45 passed in 18.537s.
- Complete hardware-free suite: 224 passed, one expected skip, 233.126s,
  exit 0. Its only diagnostic was the pre-existing unclosed-WAV warning.
- Resume seal repair reproduced 1/1 focused, 45/45 firmware-static, and 224
  complete hardware-free tests with one expected skip; the rebuilt checkpoint
  then verified 6/6.
- Independent review remains open.
- No image, USB/device, ALSA, preset/effect, Wine, network, reset, DFU, install,
  or REAPER action was performed.

## Next safe action

Use a new bounded offline/static scope to trace the actual first word supplied
by the incoming record stream at the `0x42266` handoff. Do not infer a framing
transformation, physical commit, component selection, parser semantics, safe
code placement, or image readiness until each is separately source-bound.
