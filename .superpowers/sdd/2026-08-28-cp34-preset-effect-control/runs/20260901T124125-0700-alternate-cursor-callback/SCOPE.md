# CP34 alternate-path constructed cursor callback boundary

Opened: 2026-09-01T12:41:25-07:00

## Objective

Trace only the constructed stack receiver that reaches alternate-path callback
`0x53398`: bind construction at `0x42236 -> 0x2ccf4`, the stored vtable and
its first callback word, then the callback's direct result capture at
`0x5339c..0x533a6`. Establish the exact data location returned without naming
its parser or record semantics.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb instruction, PC-literal, vtable-word, direct callback, and
  register-capture evidence for `0x2ccf4..0x2cd1a`, `0x2cb58..0x2cb5c`,
  `0x42236..0x42244`, and `0x5338e..0x533a6`.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not follow the returned value's later arithmetic, subsequent reader
  helpers, parser state, iterator semantics, record ordering, or component
  dispatch.
- Do not infer a cursor's semantic meaning, Voice FX selection, component 201,
  top-level apply `r1` provenance, parser/default semantics, `godv` linkage,
  executable placement, or a custom firmware implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with a source-bound constructed receiver/callback/result route and an
explicit semantic boundary, or with an exact no-route result. Both outcomes
retain parser, placement, image, and hardware gates as blocked.
