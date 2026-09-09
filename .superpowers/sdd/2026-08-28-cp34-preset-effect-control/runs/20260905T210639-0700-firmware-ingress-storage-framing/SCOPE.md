# CP34 firmware ingress/storage framing

Timestamp: 2026-09-05T21:06:39-07:00
Status: bounded offline static analysis; no live authority

## Objective

Trace the pinned firmware 1.28 path from an accepted incoming `MemP/Stat`
fragment through record writer `0x3092c`, storage wrapper `0x2bfe4`, and the
paired stored-record reader. Determine whether firmware inserts, replaces,
strips, or exposes any leading native little-endian u32 value `2` between the
incoming payload at message `+0x1d` and the recalled logical payload delivered
back at message `+0x1d`.

Distinguish the storage wrapper's physical metadata from bytes visible to the
structured-state parser. Reconcile the result with the sealed byte-preserving
recall path and current UC5 writer-sink comparison.

## Allowed

- Read-only static analysis of the exact hash-pinned firmware application,
  recovered from the installed UC5 module in memory only.
- Hardware-free analyzer/test implementation and task-local documentation.
- Read-only use of sealed CP34 stages and firmware helpers.

## Forbidden

- Emitting, staging, patching, flashing, or executing a firmware image.
- Treating UC5 behavior as exact UC 4.7.2 behavior.
- Treating wrapper metadata stored outside the logical payload as a parser-
  visible prefix without following the paired reader.
- Changing or replaying the Linux writer or any preset/effect operation.
- USB/device access, interface claim/detach, transfer, ALSA, Wine or protected
  prefix access, network, install, reset, DFU, or REAPER.

## Stop condition

Stop with either a source-bound byte/length map across ingress, storage wrapper,
and paired reader or the first precisely named unresolved object, vtable, or
data-flow edge. Preserve exact version, physical-commit, semantic, and live-
authority boundaries.
