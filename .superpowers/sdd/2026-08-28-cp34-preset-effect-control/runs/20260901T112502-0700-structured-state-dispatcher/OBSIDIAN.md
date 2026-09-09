---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: sealed
workflow: offline-static-analysis
updated: 2026-09-01T11:35:56-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260901T112502-0700-structured-state-dispatcher
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

- Active recovery run: `20260901T112502-0700-structured-state-dispatcher`.
- Scope: pinned application-code `Stat` FourCC tag sites and immediate edges
  to top-level apply `0x5545c` only.
- Seven little-endian `tatS` literals (`Stat` FourCC `0x53746174`) have pinned
  PC-relative loads, tagged-record `+0x8` loads, and compare instructions.
- The only immediate edge found by a full-image linear decode is the known
  secondary-interface adjustor tail branch `0x555bc -> 0x5545c`. No verified
  `Stat` tag-evidence instruction is its source.
- Result:
  `STRUCTURED_STATE_TAG_SITES_SOURCE_BOUND_DIRECT_APPLY_ROUTE_UNRESOLVED`.
  The direct caller and independent `r1` record provenance remain unresolved;
  this does not establish parser/default semantics or executable placement.

## Safety gates and verification

- Focused contract: 1/1 passed.
- Broad hardware-free suite: 167 passed, one expected local-artifact skip,
  231.293 seconds; only the existing temporary-WAV `ResourceWarning` appeared.
- No modified image, firmware staging, flashing, DFU, reset, USB/device access,
  audio, preset/effect operation, Wine access, or network action is authorized
  or performed. Do not access `/home/ajuntanaga/.wine-io24`.

## Next safe action

This static stage is sealed. A later investigation needs an exact new scope for
a dispatcher-to-apply transfer boundary. It may not promote a tag comparison to
parser/default proof, follow the excluded model-state indirect call, invent a
code cave, or emit an image.
