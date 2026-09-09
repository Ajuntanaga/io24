# CP34 structured-state component-key comparison boundary

Opened: 2026-09-01T12:10:05-07:00

## Objective

Trace only the two local words compared at pinned structured-state method
`0x531e0:0x53326`: the device-owned component-key table word written to
`sp+0x8`, and the bounded four-byte reader output written to `sp+0x4c`.
Record the static Voice FX slot-one key separately and determine whether these
instructions themselves bind `r7` to slot one or component 201.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb instruction, literal, helper-entry, key-table, byte-order, and
  comparison evidence for raw offsets `0x2cf58`, `0x53246..0x5332a`, and
  `0x5e04c..0x5e05e`.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not follow the reader's dynamic underlying source, parser inputs,
  iterator/list helpers, or virtual calls beyond their bounded entry contract.
- Do not infer record ordering, parser/default semantics, component 201,
  `r7 == 1`, optional-field behavior, `godv` linkage, executable placement,
  or a custom firmware implementation from key mechanics alone.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with source-bound local key mechanics and an explicit selection boundary,
or with an exact no-route result. Both outcomes retain parser, placement,
image, and hardware gates as blocked.
