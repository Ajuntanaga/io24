---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: local-static-pass-review-pending
workflow: offline-static-analysis
updated: 2026-09-05T20:17:07-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260905T200005-0700-uc5-structured-state-serializer-comparison
checkpoint_manifest: CHECKPOINT.sha256
tags:
  - project/io24
  - topic/presets
  - topic/firmware
  - practice/recovery
  - status/offline-only
  - status/review-pending
---

# PreSonus Revelator io24 - CP34 UC5 serializer comparison

## Resume first

1. Read task-local `RESUME.md`, this run's `SCOPE.md`, and `PROGRESS.md`.
2. Verify `CHECKPOINT.sha256` from the project root.
3. Treat this page as an index only. It authorizes no network, image, device,
   audio, Wine, or preset/effect action.

## Current source-bound result

The exact installed UC5 module's same-slot host path snapshots a selected
record with serializer `0x18002e9e0`, then sends that record through the
dynamic `{Appl,0}/{Stat,slot}` path to `MemP` fragmenter `0x180052270`.

The serializer binds the selected record as its writer output and calls archive
opener `0x180069c40` with a null/empty name. The opener's first output is one
byte `0x7b` (`{`). The fragmenter obtains the record data at `+0x10` and copies
it through the PE import `memcpy` before queue call `0x1800546b0`.

Result:
`UC5_SAVE_SERIALIZER_SOURCE_BOUND_TAGGED_MAP_OPENER_NOT_NATIVE_U32_TWO`.

## Exact boundary

The result is UC5-only. The exact UC 4.7.2 host source remains unavailable,
and no source-bound edge yet connects firmware stored-record recall output to
the later live `Stat` dispatcher input. Do not infer that a u32 `2` prefix is
sufficient, alter the local writer, or replay a device operation.

Physical storage, recall transformation, selected component identity, Voice FX
activation, audibility, and firmware-image readiness remain unresolved.

## Verification

- Intended RED: two expected missing-analyzer assertion failures.
- Focused GREEN: 2/2.
- Related serializer/queue contracts: 5/5.
- Complete hardware-free suite: 226 passed, one expected skip, 47 subtests,
  155.19 seconds, exit 0.
- Independent review remains open.

## Next safe action

Either reacquire the exact pinned UC 4.7.2 installer under separate network
authority, or open a separately named offline firmware stage to trace stored
record recall toward the live structured-state dispatcher. Neither includes a
device action.
