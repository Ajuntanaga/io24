# CP34 secondary state-interface caller boundary

Opened: 2026-09-01T11:00:29-07:00

## Objective

Trace only the already identified Voice FX embedded-owner secondary
state-interface route: its `+0x11e4` field, validated secondary vtable, and
the single virtual slot that adjusts into top-level apply `0x5545c`. Determine
whether a static caller can source-bind the `r1` argument supplied at that
exact boundary, without treating a vtable slot offset alone as type proof.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- The Voice FX parent construction, embedded `+0x11e4` interface field,
  secondary-vtable slot, adjustor, and direct static callers of that interface
  route only.
- Hardware-free analyzer contracts, documentation, and checkpoint evidence.

## Explicit limits

- Do not follow any model-state indirect call, including the unresolved
  `0x54730` dispatch, or assign it a target.
- Do not infer caller or receiver type from a matching vtable slot number,
  adjacency, tag names, host JSON, or a shared apply implementation.
- Do not claim parser behavior, optional-field defaults, a `godv` bridge, or a
  safe executable home unless separately source-bound.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with either a source-bound secondary-interface caller and `r1` provenance
result, or an explicit unresolved boundary. Both outcomes retain image emission
and every hardware action as blocked.
