# CP34 firmware stored-record recall framing

Timestamp: 2026-09-05T20:21:19-07:00
Status: bounded offline static analysis; no live authority

## Objective

Trace the pinned firmware's selected `Stat` record from reader `0x30be0`
through fragment callback `0x2f8ac`, the bound manager/application router, and
the live-device dispatcher far enough to source-bind the exact framing and
first bytes presented at `0x531e0`.

Resolve whether this native recall route adds, strips, advances past, or
otherwise transforms the stored tagged archive, including whether it supplies
the required native u32 value `2`. Reconcile any result with the current UC5
save serializer comparison without treating UC5 as UC 4.7.2 evidence.

## Allowed

- In-memory recovery of the exact pinned firmware from the installed,
  hash-verified UC5 module; do not emit a firmware image.
- Read-only ARM/Thumb disassembly and task-local static analysis.
- Hardware-free analyzer/test implementation and documentation.
- Read-only use of sealed CP34 reports, manifests, and analyzers.

## Forbidden

- Inferring an edge through an indirect call without source-bound target and
  argument provenance.
- Treating a stored archive, callback object, or similarly named `Stat` tag as
  byte-identical without following the construction/copy path.
- Changing or replaying the Linux writer, prepending a guessed word, or
  claiming physical storage, recall success, Voice FX activation, or audibility.
- Firmware image creation/emission, patching, staging, signing, upload, flash,
  reset, DFU, install, or execution.
- USB/device access, interface claim/detach, transfer, ALSA, capture,
  preset/effect operation, Wine/protected-prefix access, network, or REAPER.

## Stop condition

Stop with either an exact source-bound byte/framing route into `0x531e0`, or the
first precisely named unresolved dynamic/interprocedural edge. Preserve all
physical, semantic, image-readiness, and live-authority boundaries.
