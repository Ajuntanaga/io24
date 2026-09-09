# CP34 primary state-apply caller provenance

Opened: 2026-09-01T11:13:27-07:00

## Objective

Trace only primary-vtable virtual-call candidates at slot `+0x28` where the
receiver can be source-bound to the Voice FX embedded owner at `+0x11e0`.
Determine whether an exact caller reaches top-level apply `0x5545c` and whether
that caller materially constructs or constrains its independent `r1` record.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact `+0x11e0` receiver construction, primary-vtable `+0x28` dispatch,
  register flow into that one dispatch, and hardware-free analyzer contracts.
- Documentation and checksum evidence only.

## Explicit limits

- A matching `+0x28` slot does not establish the receiver vtable or call
  target; require construction evidence for primary vtable `0x10c6bc`.
- Do not follow any model-state indirect call, including `0x54730`, or assign
  it a target.
- Do not infer parser behavior, optional-field defaults, `godv` linkage, or
  safe executable placement from this dispatch evidence.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with either a source-bound primary caller and an explicit `r1`
provenance result, or a bounded no-candidate/unresolved result. Both outcomes
retain image emission and every hardware action as blocked.
