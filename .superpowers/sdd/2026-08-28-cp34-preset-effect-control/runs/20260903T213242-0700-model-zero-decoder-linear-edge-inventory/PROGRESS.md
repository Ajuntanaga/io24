# CP34 model-0 decoder linear immediate-edge inventory - progress

Status: locally verified, offline-only static evidence; independent review is
still open.

## Recovery starting point

The preceding `20260902T003836-0700-model-zero-decoder-entry-routes`
checkpoint verified its own task-local files, but its pinned source and test
hashes no longer matched the live files. The live files contain one additional
logical unit: `_model_zero_decoder_direct_edge_inventory_boundary_evidence()`
and its contract. No newer task-local run recorded their current hashes.

The recovered unit scans the retained image with the existing linear immediate
edge helper and preserves dynamic/interprocedural caller provenance as
unresolved. No historical RED transcript was present in the recovered files,
so this checkpoint records replayed GREEN evidence only and does not claim a
preserved RED result.

## 2026-09-03T21:32:42-07:00 - local verification complete

- The focused contract for the recovered inventory passed 1/1 in 17.99
  seconds.
- The firmware-static module passed 41/41 in 17.84 seconds.
- The complete hardware-free suite passed 185 tests with one expected
  local-artifact skip and 47 subtests in 215.55 seconds.
- No modified image, firmware staging, flashing, DFU, reset, USB/device
  access, audio, preset/effect operation, Wine access, or network action
  occurred.

## Source-bound result

- Decoder raw offset: `0x5e0ec`.
- The linear immediate-edge inventory found only the known adjustor
  `b.w` at `0x5e26c` targeting `0x5e0ec`.
- It found no immediate `BL` candidate in that inventory.
- Result:
  `MODEL_ZERO_DECODER_LINEAR_IMMEDIATE_EDGE_INVENTORY_SOURCE_BOUND_DYNAMIC_CALLER_UNRESOLVED`.

This does not establish caller absence or semantic reachability. Dynamic and
interprocedural callers, receiver and record provenance, optional-field
lookup/default behavior, parser semantics, safe placement, and image emission
remain unresolved or blocked.

## Next safe action

Do not broaden this linear result into a complete caller claim. Any later
static continuation needs a separately named scope that binds one specific
decoder caller's call instruction, receiver adjustment, and input arguments
from source. It must retain all image and hardware blocks. Independent review
of this local checkpoint remains required before treating it as a closure gate.
