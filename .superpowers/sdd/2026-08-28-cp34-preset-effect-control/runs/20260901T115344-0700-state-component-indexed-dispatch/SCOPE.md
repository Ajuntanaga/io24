# CP34 structured-state indexed component-dispatch boundary

Opened: 2026-09-01T11:53:44-07:00

## Objective

Trace only the indexed object dispatch inside pinned structured-state method
`0x531e0`: establish its device-owned table base, exact index use, constructor
binding of the Voice FX state-interface table entry, and that entry's `+0x4`
route to adjustor `0x555b8` / top-level apply `0x5545c`. Keep the dynamic
selected index separate from a proven block-201 selection unless the bounded
instructions alone bind it.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact constructor, table-offset, Thumb-instruction, vtable-word, and
  immediate-adjustor evidence for `0x5e014`, `0x531e0`, and `0x555b8`.
- Hardware-free analyzer contracts, documentation, and checksum evidence.

## Explicit limits

- Do not traverse parsing/iteration helpers that produce the selected index,
  follow a selected component beyond its first `+0x4` interface call, or follow
  the excluded model-state indirect call `0x54730`.
- Do not infer that an indexed call has selected component 201, or infer
  optional-field/default semantics, `godv` linkage, executable placement, or a
  custom firmware implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with a source-bound indexed table route and explicit selected-index
status, or with an exact no-route boundary. Both outcomes retain parser,
placement, image, and hardware gates as blocked.
