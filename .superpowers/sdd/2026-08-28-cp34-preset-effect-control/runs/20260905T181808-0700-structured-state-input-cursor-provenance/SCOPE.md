# CP34 structured-state input cursor provenance

Opened: 2026-09-05T18:18:08-07:00

## Objective

Trace only the incoming record-stream object and cursor passed by the linked
`Stat` path at `0x42266` into structured-state method `0x531e0`. Bind the
caller-side object construction, any source-bound cursor adjustment before the
call, and the first four bytes actually visible to `0x531e0` if the pinned code
and retained record representation prove them.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 io24 application.
- Exact Thumb instruction, literal, vtable, call, object-layout, and cursor
  evidence immediately upstream of `0x42266` and at the `0x531e0` entry.
- Hardware-free comparisons against retained factory records and existing pure
  record codecs where the caller-side representation is source-bound.
- Test-first analyzer contracts, documentation, checksum evidence, and a local
  dashboard mirror after verification.

## Explicit limits

- Do not infer a storage/recall transformation from naming, raw archive layout,
  or a pointer adjustment that is not source-bound through the call.
- Do not claim physical storage, stored-record equality, selected component
  identity, parser semantics, Voice FX activation, audibility, safe executable
  placement, or firmware readiness.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image. Do not access USB/device nodes, the io24, ALSA, presets/effects, Wine,
  network resources, `/home/ajuntanaga/.wine-io24`, or REAPER.

## Completion rule

Close with the narrowest source-bound statement about the object and cursor
presented at `0x42266`. If the first word remains data-dependent or the caller
does not expose the actual recalled record representation, preserve it as
unresolved rather than inventing framing or storage semantics.
