---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T09:54:06-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T094641-0700-state-apply-caller-construction
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

- Active recovery run: `20260901T094641-0700-state-apply-caller-construction`.
- Scope: static ownership/caller context of the two existing `0x5545c` entries
  in the pinned local UC 4.7.2 application.
- The shared implementation is present at `0x10c520` (`+0x38` from primary
  table `0x10c4e8`) and `0x10c6e4` (`+0x28` from `0x10c6bc`).
- The first table has two validated installations at `r8+0x22c`; its owner
  identity is unresolved. The second is installed at `r4+0x11e0` as the
  Voice FX owner entry.
- Neither installation materializes the input state receiver captured from
  `r1` at `0x55462`; its concrete type and dynamic `0x54730` target remain
  unresolved. Result: `OWNER_INSTALLATIONS_DO_NOT_BIND_INPUT_RECEIVER_TYPE`.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Broad hardware-free suite: 164 passed, one expected local-artifact skip,
  205.779 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

This static stage is sealed. Any later caller-construction analysis needs an
exact new scope and checkpoint; it may not use an owner table as proof of the
input receiver type, follow another indirect call, or emit an image.
