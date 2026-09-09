# CP34 model-0 decoder input-iteration boundary

Opened after sealed run `20260902T001723-0700-doubler-decoder-first-helper`.

## Objective

Inspect only the pinned model-0 decoder's captured-input iteration through its
first model-local candidate comparison loop. Bind instruction-level pointer
stride, FP-register handling, and loop branches without assigning serialized
record or field meaning.

## Permitted work

- Read-only static analysis of the retained, pinned UC 4.7.2 application.
- Exact Thumb and VFP instructions from decoder `0x5e0ec`'s input setup through
  the candidate mismatch branch at `0x5e142` and input endpoint loop.
- Hardware-free verifier contracts, documentation, checksum evidence, and
  direct Markdown dashboard mirroring after a sealed checkpoint.

## Explicit limits

- Do not follow later decoder helpers, dynamic targets, state-record traversal,
  selected-candidate consequences, field spelling, or tagged-state paths.
- Do not interpret FP-register word handling as a serialized schema, field type,
  optional-field lookup, default behavior, or parser implementation.
- Do not infer Voice FX selection, component 201, audible effect behavior,
  executable placement, recovery behavior, or a custom-firmware implementation.
- Do not build, modify, emit, stage, sign, upload, or operate on a firmware
  image; do not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close with an exact source-bound word-iteration/candidate-comparison result. It
must retain `OPTIONAL_FIELD_LOOKUP_UNRESOLVED`, `NO_SAFE_HOME`, the
image-emission block, and every hardware gate.
