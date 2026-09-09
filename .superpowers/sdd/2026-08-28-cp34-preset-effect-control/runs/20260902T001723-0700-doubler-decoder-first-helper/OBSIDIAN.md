---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-02T00:17:23-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260902T001723-0700-doubler-decoder-first-helper
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

- Active recovery run: `20260902T001723-0700-doubler-decoder-first-helper`.
- Stock model-0 decoder `0x5e0ec` first directly calls `0x5e094` at `0x5e192`.
- That call receives two locally initialized stack descriptors (`sp+0x2c` and
  `sp+0x4`); its helper prefix proves count handling only.
- Result:
  `DOUBLER_DECODER_FIRST_HELPER_LOCAL_DESCRIPTORS_SOURCE_BOUND_OPTIONAL_FIELD_LOOKUP_UNRESOLVED`.
- Serialized field names, optional-field lookup/default behavior, parser
  semantics, safe placement, and image emission remain unresolved or blocked.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 38/38 passed.
- Complete hardware-free suite: 183 passed, one expected local-artifact skip,
  256.479 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to inspect one named decoder operation that
consumes the captured incoming pointer. Do not follow later calls, label a
serialized field, invent a code cave, or emit an image.
