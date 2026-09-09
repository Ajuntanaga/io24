---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T11:08:13-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T110029-0700-secondary-state-interface-caller
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

1. Read the task-local `RESUME.md`, this run's `SCOPE.md`, and `PROGRESS.md`.
2. Run `sha256sum -c CHECKPOINT.sha256` from the project root before trusting
   this saved state.
3. Treat this dashboard as an index only; it does not authorize a firmware
   image, hardware action, or a claim about device-native preset behavior.

## Current verified state

- Active recovery run: `20260901T110029-0700-secondary-state-interface-caller`.
- Scope: the embedded-owner secondary state-interface route to top-level apply
  in the pinned local UC 4.7.2 application.
- Constructor evidence loads primary vtable `0x10c6bc`, installs it at
  embedded-owner `+0x11e0`, derives secondary vtable `0x10c700` (`+0x44`),
  and installs it at `+0x11e4`.
- Secondary slot `0x10c704` (`+0x4`) targets adjustor `0x555b8`; it subtracts
  four from `r0` and branches to top-level apply `0x5545c`.
- This binds the embedded-owner `r0` route only. No direct static caller or
  construction/concrete type for independent `r1` was source-bound. Result:
  `SECONDARY_INTERFACE_ROUTE_SOURCE_BOUND_CALLER_AND_R1_UNRESOLVED`.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Broad hardware-free suite: 165 passed, one expected local-artifact skip,
  193.787 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

This static stage is sealed. Any later caller investigation needs an exact new
scope and checkpoint that identifies a concrete dispatcher or record-
construction boundary; it may not infer `r1` type from the secondary table,
follow a model-state indirect call, or emit an image.
