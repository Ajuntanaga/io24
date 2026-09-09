---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T09:41:33-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T093320-0700-state-receiver-type
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
3. Treat this note as a dashboard mirror, not as a substitute for task-local
   evidence or a firmware/hardware authorization.

## Current verified state

- Active recovery run: `20260901T093320-0700-state-receiver-type`.
- Scope: static-only receiver-type recovery for the already bounded model-0
  state-apply call at raw `0x54730`, using the pinned local UC 4.7.2 artifact.
- The prior pinned package and application SHA-256 values remain
  `790f668608448b7c9f244c360ad72e3c51f71b4e8a3d828eab0e08cd03b35de1`
  and `65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.
- Two static literals (`0x10c520`, `0x10c6e4`) reference the top-level
  state-apply entry `0x5545c`. They do not identify the incoming receiver.
- That input is captured from `r1` to `r4`, dynamically dispatched through
  slots `+0` and `+4`, forwarded unchanged to model 0, then dynamically
  dispatched through slot `+8` at `0x54730`.
- Result: `NO_CONCRETE_RECEIVER_TYPE_IN_VALIDATED_TOP_LEVEL_FLOW`.
  The receiver type and its `0x54730` target remain unresolved; no parser
  semantics, optional defaults, `godv` bridge, or executable placement was
  inferred.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Broad hardware-free suite: 163 passed, one expected local-artifact skip,
  219.202 seconds; the existing temporary-WAV `ResourceWarning` was unchanged.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

This static pass is sealed. A future investigation of caller construction must
be separately scoped and checkpointed; it must not treat entry literals as a
receiver type, follow another indirect call, or emit an image.
