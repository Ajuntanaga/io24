---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T12:29:56-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T121655-0700-stat-selector-enable
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

- Active recovery run: `20260901T121655-0700-stat-selector-enable`.
- The pinned direct `Stat` handoff at `0x42266` explicitly supplies `r3 = 1`
  to `0x531e0`; that callee captures it before a zero gate. If earlier helpers
  reach the gate, this value enables its fallthrough into the component-key
  selector path.
- Result:
  `DIRECT_STAT_HANDOFF_ENABLES_SELECTOR_GATE_IF_REACHED_COMPONENT_SELECTION_UNRESOLVED`.
  The gate value is verified for this one direct call, but earlier-helper
  completion, `r7`, Voice FX slot one, component 201, parser/default semantics,
  top-level `r1` provenance, and executable placement remain unproven.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Firmware-static module: 26/26 passed (revalidated after the wording fix).
- Complete hardware-free suite: 171 passed, one expected local-artifact skip,
  223.650 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

Use a new bounded static scope to compare the paired second direct `+0x38`
handoff's `r1`/`r3` entry values and gates. Do not infer a component identity,
follow a parser helper, invent a code cave, or emit an image.
