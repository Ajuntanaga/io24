---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T23:12:18-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T230307-0700-slot-two-base-initializer-vtable
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

- Active recovery run: `20260901T230307-0700-slot-two-base-initializer-vtable`.
- The component-table constructor immediately calls direct base initializer
  `0x5d990` with the unadjusted outer receiver. The initializer writes static
  interface tables at outer offsets `+0` and `+4`.
- The separate slot-two address is constructed afterwards as `device +0x5090`.
  This does not bind its vtable, virtual target, or semantics.
- Result:
  `OUTER_RECEIVER_BASE_VTABLES_SOURCE_BOUND_SLOT_TWO_VTABLE_UNRESOLVED`.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 32/32 passed.
- Complete hardware-free suite: 177 passed, one expected local-artifact skip,
  211.171 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to source-bind an embedded-object construction
route for `device +0x5090` only if it can be proved without following a virtual
target. Do not infer semantics, invent a code cave, or emit an image.
