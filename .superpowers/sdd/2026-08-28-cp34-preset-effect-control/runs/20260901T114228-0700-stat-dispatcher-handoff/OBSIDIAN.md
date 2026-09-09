---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T11:49:43-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T114228-0700-stat-dispatcher-handoff
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

- Active recovery run: `20260901T114228-0700-stat-dispatcher-handoff`.
- Scope: the first live `Stat` dispatcher handoff only:
  `0x420bc → 0x42200 → vtable +0x38 → 0x531e0`.
- The pinned live vtable maps `0x10cb40` to dispatcher `0x420bc` and its
  `+0x38` slot at `0x10cb78` to `0x531e0`.
- The dispatcher’s first structured-state call passes `r1` from `r6` and a
  local stack argument in `r2`; `0x531e0` captures those values separately.
- Result:
  `STAT_DISPATCHER_FIRST_VTABLE_HANDOFF_SOURCE_BOUND_TOP_LEVEL_R1_UNRESOLVED`.
  The later component loop and top-level apply `0x5545c` `r1` are intentionally
  untraced; this does not establish parser/default semantics or placement.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Broad hardware-free suite: 168 passed, one expected local-artifact skip,
  219.485 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

This static stage is sealed. A later investigation needs a separate exact scope
for one component-selection-to-state-interface transfer within `0x531e0`. It
may not infer parser/default behavior, follow the excluded model-state indirect
call, invent a code cave, or emit an image.
