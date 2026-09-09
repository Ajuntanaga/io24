---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T13:19:22-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T131149-0700-alternate-slot-two-dispatch
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

- Active recovery run: `20260901T131149-0700-alternate-slot-two-dispatch`.
- The alternate equal branch dispatches the table object at device `+0x5e88`
  (slot two, constructed as `device + 0x5090`) through its `+0x4` interface
  slot. Voice FX is at distinct slot one, device `+0x5e80`.
- Result:
  `ALTERNATE_EQUAL_BRANCH_SLOT_TWO_DISPATCH_SOURCE_BOUND_NOT_VOICEFX`.
  Slot-two target/semantics, parser behavior, component identity, top-level
  apply `r1` provenance, and executable placement remain unproven.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 31/31 passed.
- Complete hardware-free suite: 176 passed, one expected local-artifact skip,
  286.710 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to identify the direct vtable binding for device
`+0x5090` only if one is present. Do not infer semantics, follow an indirect
target, invent a code cave, or emit an image.
