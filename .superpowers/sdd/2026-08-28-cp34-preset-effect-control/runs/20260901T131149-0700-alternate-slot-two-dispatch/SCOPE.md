# CP34 alternate equal-branch slot-two dispatch boundary

Opened: 2026-09-01T13:11:49-07:00

## Objective

Trace only the first direct equal-branch component-table dispatch at
`0x53470..0x5347c`: bind its retained table offset, the constructor's slot-two
object store, the interface `+0x4` call shape, and its separation from Voice
FX slot one. Do not follow either dynamic target.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb instruction, retained-register, constructor-store, table-offset,
  and vtable-slot evidence for `0x53392`, `0x53470..0x5347c`, and
  `0x5e060..0x5e072`.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not follow the preliminary receiver `+0x4` call at `0x5346e`, the slot-two
  interface target at `0x5347c`, table-object construction beyond its direct
  store, parser state, record ordering, or component semantics.
- Do not infer Voice FX selection, component 201, top-level apply `r1`
  provenance, parser/default semantics, `godv` linkage, executable placement,
  or a custom firmware implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with source-bound slot-two table dispatch and explicit Voice FX exclusion,
or with an exact no-route result. Both outcomes retain parser, placement, image,
and hardware gates as blocked.
