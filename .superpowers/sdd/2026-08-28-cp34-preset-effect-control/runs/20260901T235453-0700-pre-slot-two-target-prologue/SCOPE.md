# CP34 pre-slot-two direct-target prologue boundary

Opened: 2026-09-01T23:54:53-07:00

## Objective

Inspect only direct target `0x5d2cc`'s initial straight-line prologue to
determine whether it adjusts the source-bound receiver `device +0x508c` or
performs a direct static store before its first call or control-flow transfer.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb prologue instructions, receiver arithmetic, and direct-store
  evidence at target `0x5d2cc` through its first call or branch only.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not follow or enter a target call, virtual entry, parser state, record
  ordering, or component semantics.
- Do not treat any adjustment or store as an object/interface identity, vtable
  binding, executable construction proof, or audible-effect evidence.
- Do not infer Voice FX selection, component 201, top-level apply `r1`
  provenance, `godv` linkage, executable placement, or a custom-firmware
  implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with a source-bound target-prologue receiver result, or an exact no-route
result. Either outcome leaves object identity, vtable, dynamic targets,
semantics, parser, placement, image, and hardware gates blocked.
