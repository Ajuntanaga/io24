# CP34 direct `Stat` selector-enable argument boundary

Opened: 2026-09-01T12:16:55-07:00

## Objective

Trace only the fourth argument (`r3`) at the already pinned direct `Stat`
dispatcher handoff `0x42266 -> 0x531e0`, then bind its first callee-side gate
at `0x531f4..0x53234`. Establish whether that exact handoff enables the
component-key selector gate if execution reaches it after prior helpers; retain
selected-component and parser semantics as separate questions.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb instruction, vtable-slot, register-setup, and branch-target
  evidence for `0x4225a..0x42266` and `0x531f4..0x53234`.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not trace the dynamic component key, reader source, iterator semantics,
  record ordering, or any call beyond the direct handoff/gate instructions.
- Do not infer `r7 == 1`, Voice FX selection, component 201, top-level apply
  `r1` provenance, parser/default semantics, `godv` linkage, executable
  placement, or a custom firmware implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with a source-bound enabled/disabled selector-gate result for this one
direct `Stat` handoff, conditioned on reaching that gate, or with an exact
no-route boundary. Both outcomes retain parser, placement, image, and hardware
gates as blocked.
