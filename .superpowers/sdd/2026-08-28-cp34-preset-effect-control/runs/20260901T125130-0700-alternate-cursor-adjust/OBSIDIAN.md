---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T13:00:40-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T125130-0700-alternate-cursor-adjust
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

- Active recovery run: `20260901T125130-0700-alternate-cursor-adjust`.
- If alternate control flow reaches its `+0x4` receiver call under normal ABI
  preservation, its zero stack argument chooses raw `0x2cb60`'s local signed
  cursor update/clamp logic for receiver `+0x1c`.
- Result:
  `ALTERNATE_CURSOR_ADJUST_SOURCE_BOUND_IF_REACHED_SEMANTICS_UNRESOLVED`.
  The cursor is not identified as parser state; component identity, Voice FX
  slot one, component 201, top-level apply `r1` provenance, and executable
  placement remain unproven.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 29/29 passed.
- Complete hardware-free suite: 174 passed, one expected local-artifact skip,
  285.589 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to inspect only the immediate four-byte
reader/comparison after this callback at `0x5341c..0x53436`. Do not infer a
parser field, component identity, invent a code cave, or emit an image.
