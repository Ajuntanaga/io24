# CP34 paired direct `Stat` handoff entry-gate boundary

Opened: 2026-09-01T12:31:48-07:00

## Objective

Compare only the two adjacent direct dispatcher `+0x38` calls at `0x42266`
and `0x42280`: bind their `r1`/`r3` values, the caller-side zero condition
that supplies the first value, and the first callee entry gates at
`0x531e8..0x53234`. Establish how the two calls configure selector versus
alternate gates **if each call reaches those gates after prior helpers**.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb instruction, vtable-slot, direct register-setup, call-return
  convention, and callee entry-gate evidence for `0x4222c..0x42280` and
  `0x531e0..0x53234`.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not follow the first call's dynamic body beyond its normal ABI-preserving
  return convention, dynamic helper/reader/parser behavior, iterator semantics,
  record ordering, or a selected component.
- Do not infer Voice FX selection, component 201, top-level apply `r1`
  provenance, parser/default semantics, `godv` linkage, executable placement,
  or a custom firmware implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with source-bound paired entry-gate values conditioned on each call
reaching the gates, or with an exact no-route boundary. Both outcomes retain
parser, placement, image, and hardware gates as blocked.
