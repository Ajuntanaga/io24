# CP34 adjacent pre-slot-two receiver boundary

Opened: 2026-09-01T23:45:19-07:00

## Objective

Trace only the later base-initializer direct call at `0x5df3e`: source-bind its
stack-local `r0` receiver, derive its outer-object offset, and compare that
offset with the unresolved slot-two address `device +0x5090`. Do not enter the
callee.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb stack-local store/load, receiver arithmetic, direct call, and
  offset-adjacency evidence at `0x5dc18..0x5dc30` and `0x5df36..0x5df3e`.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not enter direct target `0x5d2cc`, follow a virtual target, parser state,
  record ordering, or component semantics.
- Do not treat four-byte adjacency as an object/interface identity, vtable
  binding, or executable construction proof.
- Do not infer Voice FX selection, component 201, top-level apply `r1`
  provenance, `godv` linkage, executable placement, or a custom-firmware
  implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with a source-bound adjacent receiver result, or an exact no-route result.
Either outcome leaves object identity, vtable, dynamic target, semantics,
parser, placement, image, and hardware gates blocked.
