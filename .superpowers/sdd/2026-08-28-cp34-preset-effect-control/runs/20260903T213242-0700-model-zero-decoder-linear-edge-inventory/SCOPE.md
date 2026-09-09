# CP34 model-0 decoder linear immediate-edge inventory

Opened while resuming from the checksum-valid
`20260902T003836-0700-model-zero-decoder-entry-routes` checkpoint. The live
analyzer and its contract contained a newer, uncheckpointed inventory of
immediate edges into model-0 decoder `0x5e0ec`.

## Objective

Recover and validate only that existing linear-decode inventory. Record the
known this-adjustor tail branch and any immediate `BL` candidates found by the
same deterministic full-image scan, without treating a linear sweep as a
complete control-flow graph.

## Permitted work

- Read-only static analysis of the retained pinned UC 4.7.2 application.
- Existing Capstone-based linear immediate-edge enumeration, focused contract,
  firmware-static module, complete hardware-free regression, documentation,
  and checksum evidence.
- Reconciliation of the prior checkpoint against the live source and test
  hashes.

## Explicit limits

- Do not claim that there are no direct callers in the executable program;
  this inventory is limited to immediate edges found by its linear decode.
- Do not identify a dynamic or interprocedural caller, receiver adjustment,
  input record, serialized field, optional-field default, parser behavior,
  Voice FX selection, or device-resident preset behavior.
- Do not build, modify, emit, stage, sign, upload, or operate on an image; do
  not access USB, device, audio, presets/effects, Wine, network, or
  `/home/ajuntanaga/.wine-io24`.

## Completion rule

Close only as a locally verified static evidence checkpoint. It must preserve
`OPTIONAL_FIELD_LOOKUP_UNRESOLVED`, `NO_SAFE_HOME`, the image-emission block,
every hardware gate, and the open independent-review gate.
