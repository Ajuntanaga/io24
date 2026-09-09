# CP34 base-initializer member-call map

Opened: 2026-09-01T23:33:34-07:00

## Objective

Starting only from the known direct base-initializer entry `0x5d990`, recover
its reachable static return boundary and inventory the entry-prologue direct
calls whose `r0` receiver is locally formed from the outer object. Determine
whether any such prologue call source-binds the slot-two embedded-object
receiver.

## Permitted work

- Read-only CFG and instruction-level static analysis of the retained, pinned
  UC 4.7.2 application, starting at `0x5d990` and stopping at direct callees.
- Exact Thumb call, branch, return, receiver-formation, and local table/store
  evidence only.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not enter or decompile any direct callee, follow a virtual target, parser
  state, record ordering, or component semantics.
- Do not treat a decoded branch path as a semantic object identity without
  source-bound receiver evidence.
- Do not infer Voice FX selection, component 201, top-level apply `r1`
  provenance, `godv` linkage, executable placement, or a custom-firmware
  implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with a source-bound entry-prologue member-call map and any slot-two
receiver result it supports, or an exact limited result if the function boundary
or receiver path cannot be recovered. Later initializer calls are explicitly
outside this scope. Either outcome leaves dynamic targets, semantics, parser,
placement, image, and hardware gates blocked.
