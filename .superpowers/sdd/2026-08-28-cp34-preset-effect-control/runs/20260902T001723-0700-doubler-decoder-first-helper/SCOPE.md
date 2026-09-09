# CP34 model-0 decoder first-helper boundary

Opened after sealed run `20260901T235453-0700-pre-slot-two-target-prologue`.

## Objective

Inspect only the first direct helper call within pinned model-0 structured
decoder `0x5e0ec`: its stack-local argument setup, immediate target, and the
target helper's count-handling prefix.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb instructions from the decoder entry through direct call `0x5e192`
  and from helper `0x5e094` through its immediate count-return branches.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not follow later decoder calls, dynamic targets, record traversal, field
  spelling, model selection, tagged-state paths, or return consumers.
- Do not label the helper a serialized-field reader, optional-field parser, or
  default implementation from descriptor/count mechanics alone.
- Do not infer Voice FX selection, component 201, audible effect behavior,
  executable placement, recovery behavior, or a custom-firmware implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with an exact source-bound local-descriptor/count-boundary result. It
must retain `OPTIONAL_FIELD_LOOKUP_UNRESOLVED`, `NO_SAFE_HOME`, the
image-emission block, and every hardware gate.
