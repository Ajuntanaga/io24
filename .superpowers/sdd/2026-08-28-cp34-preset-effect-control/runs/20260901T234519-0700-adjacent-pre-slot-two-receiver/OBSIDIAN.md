---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T23:52:54-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T234519-0700-adjacent-pre-slot-two-receiver
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

- Active recovery run: `20260901T234519-0700-adjacent-pre-slot-two-receiver`.
- A direct base-initializer call receives source-bound `device +0x508c`.
- That receiver is exactly four bytes before unresolved slot-two
  `device +0x5090`.
- Result: `ADJACENT_PRE_SLOT_TWO_RECEIVER_SOURCE_BOUND_TARGET_UNRESOLVED`.
- Adjacency does not prove object identity, interface adjustment, vtable,
  virtual target, or semantics; direct target `0x5d2cc` was not entered.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 36/36 passed.
- Complete hardware-free suite: 181 passed, one expected local-artifact skip,
  239.985 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to inspect direct target `0x5d2cc` only for an
initial receiver adjustment or static store. Do not follow its calls or virtual
targets, infer semantics, invent a code cave, or emit an image.
