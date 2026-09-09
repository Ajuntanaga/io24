---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: local-static-pass-review-pending
workflow: offline-static-analysis
updated: 2026-09-05T20:42:52-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260905T202119-0700-firmware-stored-record-recall-framing
checkpoint_manifest: CHECKPOINT.sha256
tags:
  - project/io24
  - topic/presets
  - topic/firmware
  - practice/recovery
  - status/offline-only
  - status/review-pending
---

# PreSonus Revelator io24 - CP34 stored-record recall framing

## Resume first

1. Read task-local `RESUME.md`, this run's `SCOPE.md`, and `PROGRESS.md`.
2. Verify `CHECKPOINT.sha256` from the project root.
3. Treat this page as an index only. It authorizes no device, audio, Wine,
   network, firmware-image, or preset/effect action.

## Current source-bound result

Firmware 1.28's selected `Stat` recall path preserves record payload bytes
from reader `0x30be0` through the native application packet router, live
dispatcher `0x420bc`, accumulation buffer, cursor-zero reader, and structured
state method `0x531e0`.

Result:
`STORED_STAT_RECALL_SOURCE_BOUND_BYTE_PRESERVING_NO_PREFIX_INSERTION`.

The exact dynamic seam is:

```text
0x3cc40
  -> 0x41b6c/0x419a0 packet router
  -> 0x3cf20/0x3ce98 zero-selector
  -> 0x420bc with r1 = packet+0xc
```

The callback wrapper is `SetP | 0 | 0 | nested Stat message`. The router
removes only that 12-byte wrapper. Dispatcher `0x42200` then copies
`Stat+0x1d` unchanged, and the first word at `0x531e0` is exactly
`little_endian_u32(stored_record[0:4])`.

No recall-side native-u32 `2` is inserted. A stored prefix `7b690b70` therefore
arrives as `0x700b697b` and cannot pass the required-word gate.

## Reconciliation

The older shorthand `0x3cc40 -> 0x420bc` omitted packet router `0x419a0` and
its zero-selector. The ultimate dispatcher remains correct; the new analyzer
source-binds the intervening object/vtable and register flow.

## Exact boundary

`PHYSICAL_STORED_BYTES_AND_UC472_SERIALIZER_REMAIN_UNOBSERVED`.

The connected unit's actual stored bytes were not read. Physical persistence,
recall success, selected component identity, Voice FX activation, audibility,
and image readiness remain unresolved. UC 4.7.2 source is still unavailable.

The UC5 predecessor establishes logical byte `0x7b` entering writer slot
`+0x8`, not necessarily byte zero of the record buffer. The next safe static
question is whether that writer implementation inserts native u32 `2` before
the archive stream.

## Verification

- Intended RED: two expected missing-analyzer assertion failures.
- Focused GREEN: 2/2.
- Related recall/UC5/cursor contracts: 55/55.
- Python compilation: PASS.
- Complete hardware-free suite: 229 passed, one expected skip, 156.897
  seconds, exit 0.
- Independent review remains open.

No device or USB action occurred. Passive sysfs reported BAT0 at 100 percent
and full.
