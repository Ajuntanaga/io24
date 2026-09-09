---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T11:22:55-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T111327-0700-primary-apply-caller-provenance
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

- Active recovery run: `20260901T111327-0700-primary-apply-caller-provenance`.
- Scope: local straight-line primary-vtable `+0x28` dispatches only, with
  proof required for embedded-owner `+0x11e0` and `r0` preservation.
- Voice FX table `0x10c6bc` contains top-level apply `0x5545c` at raw slot
  `0x10c6e4` (`+0x28`).
- Ten generic slot-shaped dispatches were found, but none locally constructs
  the embedded owner or preserves it as `r0`. They do not identify the table,
  target, or independent `r1` record. Result:
  `NO_LOCAL_STRAIGHT_LINE_EMBEDDED_OWNER_PRIMARY_APPLY_CALLER`.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Broad hardware-free suite: 166 passed, one expected local-artifact skip,
  222.125 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

This static stage is sealed. Any later caller investigation needs an exact new
scope and checkpoint naming a concrete dispatcher or object-transfer boundary.
It may not promote a generic slot match to Voice FX or `r1` proof, follow a
model-state indirect call, or emit an image.
