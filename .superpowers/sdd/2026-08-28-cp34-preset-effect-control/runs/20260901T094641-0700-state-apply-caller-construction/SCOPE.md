# CP34 top-level state-apply caller-construction recovery

Opened: 2026-09-01T09:46:41-07:00

## Objective

Trace only the static ownership and invocation context of the two existing
top-level structured-state apply entry literals for raw `0x5545c` (`0x10c520`
and `0x10c6e4`). Determine whether their owner construction or call-site
evidence constrains the incoming `r1` structured-state receiver to a concrete
type.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Vtable/literal, constructor, and direct caller evidence for these two entry
  references only.
- Hardware-free analyzer contracts, documentation, and checkpoint evidence.

## Explicit limits

- Do not follow another model-state indirect call or assign a target to
  `0x54730` without direct construction evidence.
- Do not infer receiver type from adjacent vtable layout, tag names, host JSON,
  or a common top-level apply implementation.
- Do not claim parser behavior, optional-field defaults, a `godv` bridge, or a
  safe executable home unless separately source-bound.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with either a source-bound owner/caller construction result that states
whether it constrains the incoming receiver, or an explicit non-constraint
boundary. Both outcomes retain image emission and every hardware action as
blocked.
