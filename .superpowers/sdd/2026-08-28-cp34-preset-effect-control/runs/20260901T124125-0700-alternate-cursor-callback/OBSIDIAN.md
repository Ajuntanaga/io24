---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T12:50:19-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T124125-0700-alternate-cursor-callback
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

- Active recovery run: `20260901T124125-0700-alternate-cursor-callback`.
- The caller constructs the alternate stack receiver with pinned vtable
  `0x600869ec`. If the alternate branch is reached under ordinary callee-saved
  flow, its first vtable callback is pinned to `0x2cb58`, which returns a
  sign-extended receiver `+0x1c` word captured as `r6:r7`.
- Result:
  `ALTERNATE_CONSTRUCTED_CURSOR_CALLBACK_SOURCE_BOUND_IF_REACHED_SEMANTICS_UNRESOLVED`.
  The word's parser/state semantics, selected component, Voice FX slot one,
  component 201, top-level apply `r1` provenance, and executable placement are
  not established.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 28/28 passed.
- Complete hardware-free suite: 173 passed, one expected local-artifact skip,
  290.082 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to bind only the immediate `+0x4` vtable call at
`0x533c6` on the same constructed receiver. Do not infer cursor semantics,
follow a parser helper, invent a code cave, or emit an image.
