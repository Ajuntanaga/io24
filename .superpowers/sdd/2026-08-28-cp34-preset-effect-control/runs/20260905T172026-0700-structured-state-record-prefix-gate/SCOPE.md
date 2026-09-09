# CP34 structured-state record-prefix gate

Opened: 2026-09-05T17:20:26-07:00

## Objective

Trace only the pre-selection gate at pinned structured-state method `0x531e0`:
bind the wrapper used to read its first four input bytes, the required value at
`0x53212`, and the branch that either reaches or bypasses component selection.
Compare that requirement with the exact prefix of the retained factory Slap
Echo archive and the existing hardware-free `MemP/Stat` record encoder.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 io24 application.
- Exact Thumb instruction, literal, vtable, helper, and branch evidence for raw
  offsets `0x2cd20..0x2ce4a` and `0x531e0..0x53224`.
- Hardware-free record-prefix comparison using the retained factory Slap Echo
  record and the existing pure preset codec.
- Test-first analyzer contracts, documentation, checksum evidence, and an
  Obsidian dashboard mirror after the local checkpoint is sealed.

## Explicit limits

- Do not claim that bytes submitted through `MemP/Stat` are physically stored
  unchanged, or that the recall/storage path performs no transformation.
- Do not infer parser semantics, record equality, a selected component index,
  block 201 activation, nonvolatile storage, or audible Voice FX from this gate.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image. Do not access USB, the io24 device, ALSA, presets/effects, Wine,
  network resources, or `/home/ajuntanaga/.wine-io24`; do not disturb REAPER.

## Completion rule

Close with a source-bound statement of the four-byte entry requirement and the
exact raw-archive comparison. If no static edge proves how a raw `{` archive
becomes the required value `2`, preserve that transformation as unresolved
rather than declaring storage or recall rejected.
