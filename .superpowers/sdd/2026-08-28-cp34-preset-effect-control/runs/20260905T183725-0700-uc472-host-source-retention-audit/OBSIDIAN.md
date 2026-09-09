---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: source-unavailable-network-authority-required
workflow: offline-source-retention-audit
updated: 2026-09-05T18:37:25-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260905T183725-0700-uc472-host-source-retention-audit
checkpoint_manifest: CHECKPOINT.sha256
tags:
  - project/io24
  - topic/presets
  - topic/firmware
  - practice/recovery
  - status/offline-only
  - status/source-unavailable
---

# PreSonus Revelator io24 - UC 4.7.2 source boundary

## Resume first

1. Read task-local `RESUME.md`, this run's `SCOPE.md`, and `PROGRESS.md`.
2. Verify `CHECKPOINT.sha256` from the project root.
3. Treat this dashboard as an index only. It authorizes no network, image,
   device, audio, Wine, or preset/effect action.

## Current result

`UC472_HOST_SERIALIZER_SOURCE_UNAVAILABLE_IN_BOUNDED_LOCAL_ROOTS`

The four source artifacts recorded under `/tmp` by the independently reviewed
2026-08-30 UC 4.7.2 run are gone. Bounded exact-name/exact-size searches found
no accessible local copy. The installed UC 5.0 artifacts have different sizes
and hashes and are not substitutes.

The exact leading `Stat` representation remains unresolved. Do not prepend
integer `2`, change the Linux writer, or replay any device operation.

## Next safe action

Reacquiring the exact installer hash requires separate explicit network
authorization. After reacquisition, extract offline, verify the exact UC 4.7.2
module hash, and trace its serializer before making any framing change.
