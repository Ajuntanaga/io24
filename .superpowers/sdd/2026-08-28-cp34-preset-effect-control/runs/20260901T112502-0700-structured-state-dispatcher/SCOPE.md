# CP34 structured-state dispatcher boundary

Opened: 2026-09-01T11:25:02-07:00

## Objective

Trace only source-bound static references to the outer structured-state tag
(`Stat`, if present in the pinned application) and any direct route from that
dispatcher into top-level apply `0x5545c`. Determine whether the exact
dispatcher materializes or constrains the independent `r1` record.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- FourCC/string literal inventory, PC-literal/comparison references, and
  immediate control-flow evidence within an exact structured-state dispatcher
  slice.
- Hardware-free analyzer contracts, documentation, and checksum evidence.

## Explicit limits

- A host JSON key or standalone `Stat` byte sequence is not parser proof;
  require source-bound application code and direct control-flow evidence.
- Do not follow any model-state indirect call, including `0x54730`, or assign
  it a target.
- Do not infer optional-field lookup/default behavior, `godv` linkage, or safe
  executable placement from a dispatcher tag or call relationship.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with either a source-bound outer dispatcher and explicit `r1` result, or
an exact no-dispatcher/no-route boundary. Both outcomes retain image emission
and every hardware action as blocked.
