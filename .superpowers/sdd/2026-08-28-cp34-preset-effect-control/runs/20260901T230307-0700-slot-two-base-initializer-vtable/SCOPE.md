# CP34 slot-two base-initializer vtable boundary

Opened: 2026-09-01T23:03:07-07:00

## Objective

Trace only the direct constructor call immediately preceding the already
source-bound `device + 0x5090` slot-two object store. Determine whether the
callee's straight-line, source-bound initialization installs a concrete vtable
at that object address. Do not resolve or invoke any virtual entry.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb call, argument-preservation, literal/table, and direct-store
  evidence within the caller at `0x5e014` and its immediate callee only.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not follow an indirect call, virtual target, constructor subcall, parser
  state, record ordering, or component semantics.
- Do not infer Voice FX selection, component 201, top-level apply `r1`
  provenance, `godv` linkage, executable placement, or a custom-firmware
  implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with a source-bound concrete slot-two vtable installation, or an exact
no-direct-vtable-installation result. Either outcome leaves dynamic entry
targets, semantics, parser, placement, image, and hardware gates blocked.
