---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: local-checkpoint-review-pending
workflow: offline-static-analysis
updated: 2026-09-03T21:32:42-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260903T213242-0700-model-zero-decoder-linear-edge-inventory
checkpoint_manifest: CHECKPOINT.sha256
tags:
  - project/io24
  - topic/firmware
  - practice/recovery
  - status/offline-only
  - status/review-pending
---

# PreSonus Revelator io24 - CP34 custom-firmware recovery

## Resume first

1. Read task-local `RESUME.md`, this run's `SCOPE.md`, and `PROGRESS.md`.
2. Run `sha256sum -c CHECKPOINT.sha256` from the project root before trusting
   this saved state.
3. Treat this dashboard as an index only; it does not authorize a firmware
   image, hardware action, or a claim about device-native preset behavior.

## Current locally verified state

- The recovered source/test addition inventories only immediate edges into
  model-0 decoder `0x5e0ec` through a full-image linear decode.
- The only observed edge is known adjustor tail branch `0x5e26c -> 0x5e0ec`.
  No immediate `BL` candidate was observed by that inventory.
- Result:
  `MODEL_ZERO_DECODER_LINEAR_IMMEDIATE_EDGE_INVENTORY_SOURCE_BOUND_DYNAMIC_CALLER_UNRESOLVED`.
- This is not proof that the executable has no other direct, dynamic, or
  interprocedural caller. Record/parser semantics, safe placement, and image
  emission remain unresolved or blocked.

## Verification and gates

- Focused contract: 1/1 passed in 17.99 seconds.
- Firmware-static module: 41/41 passed in 17.84 seconds.
- Complete hardware-free suite: 185 passed, one expected local-artifact skip,
  and 47 subtests in 215.55 seconds.
- Independent review remains open. This local checkpoint does not close a
  platform, approval, or hardware gate.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Only a new bounded static scope may examine one named decoder caller after
source-binding the call instruction, receiver adjustment, and input arguments.
Do not infer field names, defaults, a parser hook, code cave, or image-ready
placement from this inventory.
