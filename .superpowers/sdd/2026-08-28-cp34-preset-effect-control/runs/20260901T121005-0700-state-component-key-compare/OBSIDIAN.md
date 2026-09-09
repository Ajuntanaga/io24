---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T12:14:30-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T121005-0700-state-component-key-compare
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

- Active recovery run: `20260901T121005-0700-state-component-key-compare`.
- The `0x53326` comparison receives a device-owned candidate key through
  `sp+0x8` and a direct four-byte reader's byte-reversed output through
  `sp+0x4c`; equality alone copies loop counter `r6` to `r7`.
- Constructor layout supplies static key `opt ` (`0x6f707420`) for slot zero
  and static literal `0xc9` beside the Voice FX slot-one interface. Those
  literals do not prove runtime selection of slot one or component 201.
- Result:
  `COMPONENT_KEY_COMPARE_SOURCE_BOUND_DYNAMIC_SLOT_SELECTION_UNRESOLVED`.
  This does not prove record order, parser/default semantics, top-level `r1`
  provenance, `godv` linkage, executable placement, or a firmware image.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 25/25 passed.
- Complete hardware-free suite: 170 passed, one expected local-artifact skip,
  237.283 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new, bounded static scope to trace the branch-control argument entering
`0x531e0`, or establish that its direct caller does not materialize it. Do not
infer a Voice FX slot selection from the key comparison, follow an unbounded
parser helper, invent a code cave, or emit an image.
