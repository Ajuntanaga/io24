---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T23:30:38-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T232334-0700-slot-two-immediate-materialization-inventory
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

- Active recovery run:
  `20260901T232334-0700-slot-two-immediate-materialization-inventory`.
- A full halfword-aligned static inventory finds exactly one `0x5090` immediate
  candidate: the already-proven component-table constructor at `0x5e03e`.
- Result:
  `ONLY_EXISTING_COMPONENT_TABLE_SLOT_TWO_IMMEDIATE_MATERIALIZATION_SOURCE_BOUND`.
- Split, non-immediate, or dynamic construction routes; the slot-two vtable;
  virtual target; and semantics remain unresolved.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 34/34 passed.
- Complete hardware-free suite: 179 passed, one expected local-artifact skip,
  244.182 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Choose a different source-bound static seam from the task-local evidence index.
Do not repeat this immediate scan as a proxy for a construction route, follow a
virtual target, infer semantics, invent a code cave, or emit an image.
