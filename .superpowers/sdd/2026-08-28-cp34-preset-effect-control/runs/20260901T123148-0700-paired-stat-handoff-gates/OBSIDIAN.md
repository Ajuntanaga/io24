---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T12:38:32-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T123148-0700-paired-stat-handoff-gates
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

- Active recovery run: `20260901T123148-0700-paired-stat-handoff-gates`.
- Under the caller's zero-gated normal continuation and the standard
  callee-saved `r6` convention, adjacent direct `Stat` handoffs configure
  `0x531e0` with `(r1, r3) = (0, 1)` then `(1, 0)`.
- If their prior helpers reach the entry gates, the first configuration enables
  the later selector gate; the second configuration branches to the alternate
  path before that selector gate.
- Result:
  `PAIRED_STAT_HANDOFF_ENTRY_GATES_SOURCE_BOUND_COMPONENT_SELECTION_UNRESOLVED`.
  This does not establish parser completion, a selected component, Voice FX
  slot one, component 201, top-level apply `r1` provenance, or executable
  placement.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 27/27 passed.
- Complete hardware-free suite: 172 passed, one expected local-artifact skip,
  244.176 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to inspect only the direct setup at alternate
branch target `0x5338e`. Do not infer a component identity, follow a parser
helper, invent a code cave, or emit an image.
