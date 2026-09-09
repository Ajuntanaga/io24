---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-02T00:38:36-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260902T003836-0700-model-zero-decoder-entry-routes
checkpoint_manifest: CHECKPOINT.sha256
vault_mirror: Projects/PreSonus Revelator io24 — CP34 custom-firmware recovery.md
tags:
  - project/io24
  - topic/firmware
  - practice/recovery
  - status/offline-only
---

# PreSonus Revelator io24 — CP34 custom-firmware recovery

## Resume first

1. Read task-local `RESUME.md`, this run's `SCOPE.md`, and `PROGRESS.md`.
2. Run `sha256sum -c CHECKPOINT.sha256` from the project root before trusting
   this saved state.
3. Treat this dashboard as an index only; it does not authorize a firmware
   image, hardware action, or a claim about device-native preset behavior.

## Current verified state

- Active recovery run: `20260902T003836-0700-model-zero-decoder-entry-routes`.
- Model 0 reaches decoder `0x5e0ec` through primary vtable slot `+0x34` and a
  separate `-0x1c0` this-adjustor/tail-branch route.
- Result:
  `MODEL_ZERO_DECODER_PRIMARY_AND_ADJUSTOR_ENTRY_ROUTES_SOURCE_BOUND_OPTIONAL_FIELD_LOOKUP_UNRESOLVED`.
- Dynamic caller, serialized field names/layout, optional-field lookup/default
  behavior, parser semantics, safe placement, and image emission remain
  unresolved or blocked.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 40/40 passed.
- Complete hardware-free suite: 185 passed, one expected local-artifact skip,
  319.470 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to inspect one named direct decoder caller only
after source-binding its receiver adjustment and all input arguments. Do not
resolve a dynamic call by inference, label a serialized field, invent a code
cave, or emit an image.
