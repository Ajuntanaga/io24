# CP34 state-apply receiver-type recovery

Opened: 2026-09-01T09:33:20-07:00

## Objective

Continue the active offline CP34 custom-firmware analysis by examining only
the already-bounded state-apply indirect call at raw `0x54730`. Determine
whether static construction, call-site, or vtable evidence in the pinned local
UC 4.7.2 application can source-bind the caller-supplied structured-state
receiver to one concrete type and target.

## Permitted work

- Read-only static analysis of the retained local UC 4.7.2 artifact in memory.
- Disassembly and data-flow evidence for the receiver forwarded through
  `0x55462 -> 0x55592 -> 0x546f0 -> 0x54730`.
- Hardware-free analyzer contracts, documentation, and checkpoint evidence.

## Explicit limits

- Do not trace a second state-apply indirect call.
- Do not infer a concrete vtable from register shape, tag names, or host JSON.
- Do not claim parser semantics, optional-field defaults, a `godv` bridge, or
  executable placement unless direct source-bound evidence establishes it.
- Do not build, modify, emit, stage, sign, upload, or otherwise operate on a
  firmware image.
- Do not access USB, a device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close this stage with either a source-bound concrete receiver/target result, or
an explicit unresolved result with its evidence boundary. Both outcomes retain
image emission and all hardware actions as blocked.
