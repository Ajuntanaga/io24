---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: local-static-pass-review-pending
workflow: offline-static-analysis
updated: 2026-09-05T21:01:39-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260905T204944-0700-uc5-record-writer-sink
checkpoint_manifest: CHECKPOINT.sha256
tags:
  - project/io24
  - topic/presets
  - topic/host
  - practice/recovery
  - status/offline-only
  - status/review-pending
---

# PreSonus Revelator io24 - CP34 UC5 record-writer sink

## Resume first

1. Read task-local `RESUME.md`, this run's `SCOPE.md`, and `PROGRESS.md`.
2. Verify `CHECKPOINT.sha256` from the project root.
3. Treat this page as an index only. It authorizes no device, audio, Wine,
   network, firmware-image, or preset/effect action.

## Current source-bound result

The exact installed UC5 serializer writes its first logical archive byte
directly to physical byte zero of the selected record.

Result:
`UC5_RECORD_WRITER_SOURCE_BOUND_PHYSICAL_BYTE_ZERO_0X7B_NO_PREFIX_INSERTION`.

Serializer `0x18002e9e0` resets the selected record cursor and length to zero,
then binds it at stack writer `+0x18`. Archive call `0x180069dae` presents the
single byte `0x7b` to secondary writer slot `+0x8`. Adapter `0x180065d30`
resolves the selected record and tailcalls record append `0x1800643f0`.

Append copies exactly one byte to
`record.data(+0x10) + record.cursor(+0x2c)`, then changes cursor and length
from zero to one. It inserts no native little-endian u32 `2` and leaves no
prefix headroom. The same record is subsequently fragmented from data `+0x10`
and length `+0x30` without an intervening mutation.

## Exact boundary

`UC5_ONLY_UC472_AND_FIRMWARE_INGRESS_STORAGE_TRANSFORM_UNRESOLVED`.

This is UC5 comparison evidence, not UC 4.7.2 proof. Firmware ingress from
incoming `MemP/Stat` to stored record bytes remains to be bound at byte level.
The connected unit's actual stored bytes, persistence, recall result,
component identity, Voice FX activation, and audibility were not observed.

## Verification

- Intended RED: two expected missing-analyzer assertion failures.
- Focused GREEN: 2/2.
- Related writer/serializer/recall contracts: 6/6.
- Direct analyzer execution and Python compilation: PASS.
- Complete hardware-free suite: 231 passed, one expected skip, 160.888
  seconds, exit 0.
- Independent review remains open.

No device or USB action occurred. Passive sysfs reported BAT0 at 99 percent
and not charging.
