---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: locally-verified-independent-review-open
workflow: offline-static-analysis
updated: 2026-09-05T23:50:44-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260905T231733-0700-appl-zero-selector-receiver
checkpoint_manifest: CHECKPOINT.sha256
tags:
  - project/io24
  - topic/firmware
  - practice/recovery
  - status/offline-only
---

# PreSonus Revelator io24 - CP34 final receiver correction

## Resume first

1. Read the authoritative task-local `RESUME.md`, this run's `SCOPE.md`, and
   `PROGRESS.md`.
2. Verify `CHECKPOINT.sha256` from the project root.
3. Treat this page as an index only. It authorizes no device, audio, Wine,
   network, firmware-image, or preset/effect action.

## Current verified state

- Lazy initializer `0x3d4f0` calls derived constructor `0x5e014` on global
  `0x20216660`.
- Base constructor `0x5d990` temporarily installs `0x6008d3a8`.
- The derived body forms final vtable `0x6012cb40` from exact header
  `0x6012cb38 + 8` and stores it at `0x5e036`.
- Final slot zero is `0x420bc`; final slot `+0x38` is `0x531e0`.
- `0x41580` is registered after construction as teardown. Its base-table writes
  are not final live state.
- Both `0x42266` and `0x42280` reach `0x531e0` on the exact `{0,0}` stored-
  recall selector route.
- Result:
  `ZERO_SELECTOR_STAT_ROUTE_SOURCE_BOUND_FINAL_DERIVED_SLOT_0X38_0X531E0`.

The earlier no-op run is retracted semantically and retained unchanged for
provenance. Its checkpoint now has ten expected stale shared-file rows and must
not be used to restore active files; seven immutable/task-local rows still
verify.

## Verification

- Affected modules: 53/53.
- Firmware-static module: 47/47.
- Compilation: PASS.
- Complete hardware-free suite: 235 passed, one expected skip, 47 subtests,
  158.89 seconds, exit 0.
- Independent review remains open.

## Boundary

`0X531E0_RUNTIME_COMPLETION_SELECTED_COMPONENT_AND_PHYSICAL_OUTCOMES_REMAIN_UNRESOLVED`.

The exact UC 4.7.2 serializer remains unavailable. Physical backend commit,
device-resident preset round trip, Voice FX activation, and audibility remain
unobserved. Device connection supplies no authority for live access.

## Safety

No firmware image, USB/device action, ALSA, preset/effect operation, Wine,
network, reset, DFU, install, staging, flash, or REAPER action occurred.
