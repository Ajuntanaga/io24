---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: active
workflow: offline-static-analysis
updated: 2026-09-01T02:14:16-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T004535-0700-runtime-storage-placement
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

1. Read the task-local `RESUME.md` and this run's `PROGRESS.md`.
2. Run `sha256sum -c CHECKPOINT.sha256` from the project root before trusting
   the saved state.
3. Resume only the recorded next safe action. This note is a dashboard mirror;
   it does not replace the task-local checkpoint.
4. After every task-local save, checksum-match the vault copy to this local
   mirror before relying on it as a dashboard entry point.

## Current verified state

- Active run: `20260901T004535-0700-runtime-storage-placement`.
- Scope: offline static analysis of the pinned local UC 4.7.2 artifact only.
- Pinned complete package SHA-256:
  `790f668608448b7c9f244c360ad72e3c51f71b4e8a3d828eab0e08cd03b35de1`.
- Pinned application SHA-256:
  `65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.
- The parent-owned sidecar layout is source-bound inside the existing Voice FX
  parent: stock-reserved `+0x2884`; proposed extension tail
  `+0x2885..+0x288f`.
- The top-level structured-state entry is source-bound:
  `0x10c6e4 -> 0x5545c`, with secondary adjustor
  `0x10c704 -> 0x555b8 -> 0x5545c`.
- The analyzer reports
  `TOP_LEVEL_AND_MODEL_ZERO_STATE_APPLY_SOURCE_BOUND; OPTIONAL_FIELD_LOOKUP_UNRESOLVED`.
- The parent state loader also dispatches to model 0's secondary state
  interface: `0x5559a -> model+4 -> 0x10c8d4 -> 0x548dc -> 0x546ec`.
- Separately, the model-0 primary vtable routes the tagged `godv` callback to
  `0x5bb6c`. It stores five stock values at `+0x340..+0x350` and derives mix
  at `+0x358`; its relationship to `0x546ec` is deliberately unresolved.
- The two complete, hash-validated bodies have no immediate direct cross-edge;
  state apply has six indirect `blx` sites, so this does not resolve their
  interprocedural relationship.
- The first named state-apply indirect call is now bounded: `0x54730` uses the
  caller-supplied structured-state receiver's vtable slot `+8` and receives
  `model+0x340` as its output argument. No concrete target is source-bound.

## Current boundary

- Optional-field lookup/default implementation is not recovered.
- No safe executable extension-body home is established:
  `extension_body=NO_SAFE_HOME`.
- The 36-byte ITCM all-FF span is trampoline-only; the only trailing all-FF
  range is 92 bytes and remains `UNPROVEN_NOT_EXECUTABLE_HOME`.
- Model IDs 0–5 remain stock-dispatchable; model 5 is not reclaimable.

## Safety gates

No modified image, firmware staging, flashing, DFU, reset, USB/device access,
audio, preset/effect operation, Wine access, or network action is authorized
or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Last verification

- Focused analyzer contracts: 17 passed, including the `0x54730` receiver
  boundary and dynamic-target result.
- Broad hardware-free suite: 162 passed, one expected local-artifact skip,
  163.340 seconds.
- The latter emitted only the pre-existing temporary-WAV `ResourceWarning` in
  `re/cp34_current_slot_survey.py:260`.

## Next safe action

This bounded static pass is sealed. Preserve the `0x54730`
caller-supplied-vtable boundary; do not trace another indirect call, invent a
parser hook/code cave, or emit an image without a new bounded scope and saved
checkpoint. Before and after every future bounded stage, refresh
`PROGRESS.md`, root `RESUME.md`, this note, and `CHECKPOINT.sha256`.
