---
type: handoff
area: io24
project: PreSonus Revelator io24 CP34
status: local-static-pass-review-pending
workflow: offline-static-analysis
updated: 2026-09-05T21:19:17-07:00
authoritative_resume: /home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
active_run: 20260905T210639-0700-firmware-ingress-storage-framing
checkpoint_manifest: CHECKPOINT.sha256
tags:
  - project/io24
  - topic/presets
  - topic/firmware
  - practice/recovery
  - status/offline-only
  - status/review-pending
---

# PreSonus Revelator io24 - CP34 firmware ingress/storage framing

## Resume first

1. Read task-local `RESUME.md`, this run's `SCOPE.md`, and `PROGRESS.md`.
2. Verify `CHECKPOINT.sha256` from the project root.
3. Treat this page as an index only. It authorizes no device, audio, Wine,
   network, firmware-image, or preset/effect action.

## Current source-bound result

Firmware 1.28 preserves logical payload byte zero across accepted
`MemP/Stat` ingress, storage wrapping, selected-record read, and recall.

Result:
`FIRMWARE_STAT_INGRESS_RECALL_SOURCE_BOUND_LOGICAL_BYTE_ZERO_UNCHANGED_NO_PREFIX_INSERTION`.

Record writer `0x3092c` passes payload source `message+0x1d` and the exact u16
fragment length to wrapper write `0x2bfe4`. That wrapper stores a backend-
address entry shaped as `CRC32 | payload length | payload`, with eight bytes
of wrapper overhead. Paired reader `0x2c0a8` consumes the CRC/length fields,
reads only the payload into its caller destination, validates CRC32, and does
not expose the wrapper header.

Stored-record reader `0x30a90` reads the separate total length into message
`+0x19`, advances past that wrapped entry, and reads serialized payload into
message `+0x1d`. The sealed recall path supplies those bytes unchanged to
cursor-zero gate `0x531e0`.

Thus incoming prefix `7b690b70` remains `7b690b70` and is consumed as native
word `0x700b697b`, not the required `0x00000002`. Firmware adds no hidden
parser-visible prefix.

## Exact boundary

`PHYSICAL_BACKEND_COMMIT_AND_UC472_SERIALIZER_REMAIN_UNOBSERVED`.

The exact UC 4.7.2 serializer is still missing. The connected unit's actual
stored bytes, physical commit, persistence, selected component, Voice FX
activation, and audibility were not observed. No live or framing action is
authorized.

## Verification

- Intended RED: two expected missing-analyzer assertion failures.
- Focused GREEN: 2/2.
- Related ingress/recall/host/persistence contracts: 32 tests and 6 subtests.
- Python compilation: PASS.
- Complete hardware-free suite: 233 passed, one expected skip, 160.306
  seconds, exit 0.
- Independent review remains open.

No device or USB action occurred. Passive sysfs reported BAT0 at 99 percent
and not charging.
