---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-02T00:02:35-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T235453-0700-pre-slot-two-target-prologue
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

- Active recovery run: `20260901T235453-0700-pre-slot-two-target-prologue`.
- Direct target `0x5d2cc` captures source-bound `device +0x508c` unchanged in
  its first basic block, before its first conditional branch.
- It makes no receiver adjustment or receiver-relative store before that branch.
- Result:
  `PRE_SLOT_TWO_TARGET_CAPTURES_CALLER_RECEIVER_UNADJUSTED_BEFORE_FIRST_BRANCH`.
- Object/interface identity, vtable, later target behavior, and semantics remain
  unresolved.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 37/37 passed.
- Complete hardware-free suite: 182 passed, one expected local-artifact skip,
  240.250 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to inspect one specified post-branch basic block
only after source-binding its branch condition and incoming receiver. Do not
follow a call or virtual target, infer semantics, invent a code cave, or emit an
image.
