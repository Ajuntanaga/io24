# CP34 alternate-path cursor-adjust callback boundary

Opened: 2026-09-01T12:52:48-07:00

## Objective

Trace only the same constructed receiver's `+0x4` vtable callback at `0x533c6`:
bind the direct stack argument, its zero-argument branch in raw `0x2cb60`, and
the bounded receiver `+0x1c` update logic. Keep the cursor's semantic meaning,
parser state, and all component identity separate.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb instruction, vtable-word, stack-argument, direct branch, and
  receiver-offset evidence for `0x533b0..0x533c6` and `0x2cb60..0x2cb9c`.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not follow the cursor result beyond its local signed/clamp branches,
  subsequent reader helpers, parser state, iterator semantics, record ordering,
  or component dispatch.
- Do not infer cursor semantics, Voice FX selection, component 201, top-level
  apply `r1` provenance, parser/default semantics, `godv` linkage, executable
  placement, or a custom firmware implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with a source-bound `+0x4` callback and its conditional local cursor
update, or with an exact no-route result. Both outcomes retain parser,
placement, image, and hardware gates as blocked.
