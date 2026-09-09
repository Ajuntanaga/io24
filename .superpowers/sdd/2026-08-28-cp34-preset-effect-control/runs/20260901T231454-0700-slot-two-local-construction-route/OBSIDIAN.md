---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T23:21:17-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T231454-0700-slot-two-local-construction-route
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

- Active recovery run: `20260901T231454-0700-slot-two-local-construction-route`.
- The component-table constructor retains `device +0x5090` only in table slot
  two, then returns. Its exact post-store tail contains no direct call.
- Result: `NO_LOCAL_DIRECT_SLOT_TWO_SUBCONSTRUCTOR_CALL`.
- An embedded-object construction route elsewhere, slot-two vtable, virtual
  target, and semantics remain unresolved.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 33/33 passed.
- Complete hardware-free suite: 178 passed, one expected local-artifact skip,
  227.406 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to inspect one source-bound construction callsite
outside this wrapper only after identifying its caller and receiver address.
Do not follow a virtual target, infer semantics, invent a code cave, or emit an
image.
