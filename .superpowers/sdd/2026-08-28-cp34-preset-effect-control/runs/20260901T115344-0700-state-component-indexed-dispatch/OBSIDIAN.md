---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T12:00:36-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T115344-0700-state-component-indexed-dispatch
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

- Active recovery run: `20260901T115344-0700-state-component-indexed-dispatch`.
- `0x531e0` builds `device+0x5e78` and calls
  `[table_base + r7 * 8]` through the selected object’s `+0x4` vtable slot.
- Constructor code places Voice FX state interface `device+0x11e4` at table
  slot one; its `+0x4` slot routes through `0x555b8` to `0x5545c`.
- The selection index `r7` is loop/data-dependent and remains unresolved.
- Result:
  `INDEXED_COMPONENT_DISPATCH_SOURCE_BOUND_VOICEFX_SLOT_ONE_ROUTE_SELECTED_INDEX_UNRESOLVED`.
  This does not prove selection of block 201, top-level `r1` provenance,
  parser/default semantics, or executable placement.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Broad hardware-free suite: 169 passed, one expected local-artifact skip,
  225.742 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

The next separate static scope begins with the data-dependent comparison at
`0x53326` that selects `r7`. It may not infer a component identity from the
route alone, follow model-state call `0x54730`, invent a code cave, or emit an
image.
