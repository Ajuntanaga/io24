# CP34 slot-two local construction-route boundary

Opened: 2026-09-01T23:14:54-07:00

## Objective

Trace only the straight-line tail of the component-table constructor after it
stores `device + 0x5090` in slot two. Determine whether this same constructor
forwards that address to a direct subconstructor call before returning.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb instruction and control-flow evidence for
  `0x5e04a..0x5e08a` only.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not enter the direct base initializer, follow any callee, virtual entry,
  parser state, record ordering, or component semantics.
- Do not infer Voice FX selection, component 201, top-level apply `r1`
  provenance, `godv` linkage, executable placement, or a custom-firmware
  implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with a source-bound local direct-subconstructor route, or with an exact
result that the named straight-line tail retains the object only as a table
entry and returns. Either outcome leaves a construction route elsewhere,
dynamic target, semantics, parser, placement, image, and hardware gates
blocked.
