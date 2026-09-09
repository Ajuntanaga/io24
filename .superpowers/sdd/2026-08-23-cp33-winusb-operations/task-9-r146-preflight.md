# Task 9 R146 preauthorization verdict

Timestamp: 2026-08-25

## Verdict

R146 is rejected before authorization or live application. Both independent
reviewers returned `REQUEST CHANGES`. Live tests remain the frozen rejected
R139 head.

## Blocking findings

1. A correct-pointer descriptor free moved before descriptor traversal passes,
   admitting a use-after-free.
2. Production can mutate `params->device->handle` before validation, use the
   wrong handle, and satisfy the post-call self-referential comparison.
3. Endpoint and generic reject paths can corrupt URB status, transfer length,
   and caller storage while preserving the tested return/backend state.
4. Active-config fake initialization executes before its claimed first
   boundary witness.

The controller and targeted reviewer independently reproduced the early-free
false green. The holistic reviewer independently reproduced all three
Important classes and confirmed the witness-order mismatch in disassembly.

The earlier `task-9-r146-cybersecurity-preflight.md` PASS is superseded by
these post-seal executable findings. Its bytes remain preserved inside the
original 12/12 proposal manifest as part of the audit trail.

## Successor requirement

R147 may retain R146 only in a disposable tree. It must:

- snapshot immutable pre-call fixture/device/parameter and pipe-table authority;
- require complete caller fixture preservation with only the expected invalid
  URB status change on generic and endpoint rejection;
- make fake descriptor free safely invalidate/poison a refreshable descriptor
  view so premature free becomes an executable feature failure;
- move all local initialization after the active-config global witness and
  immediate dedicated increment; and
- freshly kill every R146 mutant plus wrong-handle-state, premature-free,
  endpoint corruption, oversized-generic corruption, and omitted-invalid-status
  variants.

No live test or production edit is authorized.

