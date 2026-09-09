---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T23:42:40-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T233334-0700-base-initializer-member-call-map
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

- Active recovery run: `20260901T233334-0700-base-initializer-member-call-map`.
- Base initializer `0x5d990` has a recovered static normal return at `0x5df6a`.
- Its exact entry prologue has four source-bound outer-member calls at offsets
  `+0xc38`, `+0xc5c`, `+0x11e0`, and `+0x3a70`; none is slot two `+0x5090`.
- Result:
  `BASE_INITIALIZER_ENTRY_PROLOGUE_MEMBER_CALLS_SOURCE_BOUND_SLOT_TWO_ABSENT`.
- Later initializer calls, nonlocal construction, slot-two vtable, virtual
  target, and semantics remain unresolved.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 35/35 passed.
- Complete hardware-free suite: 180 passed, one expected local-artifact skip,
  254.657 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to inspect only one named later base-initializer
callsite after source-binding its `r0` receiver. Do not enter the target, follow
a virtual target, infer semantics, invent a code cave, or emit an image.
