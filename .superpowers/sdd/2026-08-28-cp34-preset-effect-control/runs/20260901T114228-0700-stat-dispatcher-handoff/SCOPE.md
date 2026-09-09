# CP34 `Stat` dispatcher first-handoff boundary

Opened: 2026-09-01T11:42:28-07:00

## Objective

Source-bind only the first transfer from the pinned live `Stat` dispatcher
`0x420bc` through its `+0x38` vtable call to structured-state method `0x531e0`.
Record the exact argument-register setup and distinguish the dispatcher's input
record pointer from the `r1`/`r2` values captured by `0x531e0`. Preserve the
separate top-level apply `0x5545c` `r1` provenance as unresolved unless this
exact handoff itself proves it.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact vtable-word, Thumb-instruction, conditional-branch, and call-ABI
  evidence for `0x420bc`, `0x42200`, and `0x531e0` only.
- Hardware-free analyzer contracts, documentation, and checksum evidence.

## Explicit limits

- Do not follow the component-selection loop inside `0x531e0`, any state
  interface call beyond this first handoff, or the excluded model-state
  indirect call `0x54730`.
- Do not infer parser/default behavior, optional-field lookup, `godv` linkage,
  executable placement, or a concrete `0x5545c` caller from this ABI evidence.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with a source-bound first-handoff ABI and an explicit statement about
whether it binds `0x5545c`'s independent `r1`, or with an exact no-handoff
boundary. Either result keeps all parser, placement, image, and hardware gates
blocked.
