# CP34 UC5 record-writer sink

Timestamp: 2026-09-05T20:49:44-07:00
Status: bounded offline static comparison; no live authority

## Objective

Trace the exact installed UC5 archive writer invoked at
`0x180069dae` through virtual slot `+0x8` to the selected record's physical
buffer and length members. Determine whether that writer inserts, reserves,
or otherwise materializes a leading native little-endian u32 value `2` before
the archive opener's first logical byte `0x7b`.

Reconcile the result with the now source-bound firmware fact that stored
`Stat` recall adds no prefix before the cursor-zero gate at `0x531e0`.

## Allowed

- Read-only static analysis of the exact installed, hash-pinned UC5
  `dspusbdevice.dll`.
- Hardware-free analyzer/test implementation and task-local documentation.
- Read-only use of sealed CP34 stages and PE helpers.

## Forbidden

- Treating the archive writer's logical input byte as physical record byte
  zero without following the writer implementation and output-object flow.
- Treating current UC5 as exact UC 4.7.2 behavior.
- Changing or replaying the Linux writer or any preset/effect operation.
- USB/device access, interface claim/detach, transfer, ALSA, Wine or protected
  prefix access, network, install, firmware image, staging, flash, reset, DFU,
  or REAPER.

## Stop condition

Stop with either a source-bound writer-to-record byte layout, including the
first physical bytes and length effects, or the first precisely named
unresolved vtable/object/data-flow edge. Preserve all version, physical,
semantic, and live-authority boundaries.
