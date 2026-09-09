---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T13:10:01-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T130219-0700-alternate-key-compare
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

- Active recovery run: `20260901T130219-0700-alternate-key-compare`.
- The alternate path compares a four-byte reader result with its current device
  word at `+0x5e8c`, whose constructor default is `opt `, then branches on
  equality. Runtime key value, reader semantics, record order, and component
  meaning remain unproven.
- Result:
  `ALTERNATE_STATIC_KEY_COMPARE_SOURCE_BOUND_IF_REACHED_SEMANTICS_UNRESOLVED`.
  This is not a parser field or a Voice FX/component selection proof.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 30/30 passed.
- Complete hardware-free suite: 175 passed, one expected local-artifact skip,
  288.630 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to inspect only the first equal-branch block at
`0x5345a..0x5347c`. Do not follow its dynamic component interface call, infer
component identity, invent a code cave, or emit an image.
