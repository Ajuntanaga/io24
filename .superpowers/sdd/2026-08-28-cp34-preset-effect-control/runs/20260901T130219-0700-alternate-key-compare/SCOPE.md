# CP34 alternate-path static key-comparison boundary

Opened: 2026-09-01T13:02:19-07:00

## Objective

Trace only the alternate path's direct four-byte reader/comparison at
`0x5341c..0x53436`: bind its output local, the device-owned expected key at
`+0x5e8c`, that key's constructor literal, and the equality branch. Record the
static comparison without assigning parser semantics, record order, or a
component identity.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb instruction, existing reader target, constructor-literal,
  device-offset, local-stack, and branch evidence for `0x53392..0x53436` and
  `0x5e04c..0x5e072`.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not follow the equal branch's loop, its later dynamic component dispatch,
  reader source semantics, parser state, iterator semantics, record ordering,
  or a selected component.
- Do not infer Voice FX selection, component 201, top-level apply `r1`
  provenance, parser/default semantics, `godv` linkage, executable placement,
  or a custom firmware implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with a source-bound static key comparison and explicit semantic/component
boundary, or with an exact no-route result. Both outcomes retain parser,
placement, image, and hardware gates as blocked.
