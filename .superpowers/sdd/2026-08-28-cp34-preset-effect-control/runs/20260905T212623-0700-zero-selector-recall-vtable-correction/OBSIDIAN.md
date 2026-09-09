---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: local-static-correction-pass-review-pending
workflow: offline-static-analysis
updated: 2026-09-05T23:10:14-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260905T212623-0700-zero-selector-recall-vtable-correction
checkpoint_manifest: CHECKPOINT.sha256
tags:
  - project/io24
  - topic/presets
  - topic/firmware
  - practice/recovery
  - status/offline-only
  - status/correction
  - status/review-pending
---

# PreSonus Revelator io24 - CP34 zero-selector vtable correction

## Resume first

1. Read task-local `RESUME.md`, this run's `SCOPE.md`, and `PROGRESS.md`.
2. Verify `CHECKPOINT.sha256` from the project root.
3. Treat this page as an index only. It authorizes no device, audio, Wine,
   network, firmware-image, or preset/effect action.

## Current source-bound result

Stored recall's `{0,0}` selector returns primary device `0x20216660` with
vtable `0x6008d3a8`. Its slot `+0x38` is `0x3ccb4`, a success/no-op. Both
dispatcher callbacks therefore target `0x3ccb4`, not `0x531e0`.

Result:
`ZERO_SELECTOR_STAT_ROUTE_SOURCE_BOUND_PRIMARY_SLOT_0X38_NOOP_NOT_0X531E0`.

Raw candidate table `0x10cb40` was previously paired without receiver
provenance. Exact base address `0x6012cb40` occurs zero times in the image.

Storage byte preservation through the paired reader and accumulation copy
remains valid. `0x531e0` parser semantics remain valid only in isolation; its
caller and the nonzero host `{Appl,0}` selected receiver are unresolved.

## Superseded claims

Any older handoff or report claiming zero-selector recall, cursor-zero
accumulation, linked/unlinked `Stat` callbacks, or ingress/storage reaches
`0x531e0` is superseded by this run. The authoritative handoff labels those
historical sections explicitly.

## Verification

- Corrective contracts: 6/6.
- Route-sensitive lane contracts: 7/7.
- Firmware-static module: 47/47.
- Compilation: PASS.
- Complete hardware-free suite: 235 passed, one expected skip, 47 subtests,
  168.44 seconds, exit 0.
- Independent review remains open.

Boundary:
`NONZERO_APPL_ZERO_SELECTED_RECEIVER_AND_0X531E0_CALLER_REMAIN_UNRESOLVED`.

No device or USB action occurred. Passive sysfs reported BAT0 at 95 percent
and charging.
