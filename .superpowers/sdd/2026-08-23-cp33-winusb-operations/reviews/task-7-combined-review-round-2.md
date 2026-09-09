# CP33 Task 7 combined review round 2

## Spec compliance

Result: **FAIL**. Task 7 remains open because of one reachable memory-safety
defect, one transactional preservation defect, and incomplete plan-mandated
mutation evidence.

## Strengths

- The 17-path manifest is scoped correctly and the workspace matches the
  frozen `task-7-head` snapshot.
- Public alternate handling bounds snapshot arithmetic, carries exact
  interface indices, acquires one opaque handle, submits once, and releases
  ownership on every path.
- Lower tokens are portable nonzero generation-tagged values and validate
  current state, generation, record fields, function membership, committed
  claims, and alternate selection.
- SELECT_INTERFACE stages allocations before its single backend call and
  preserves caller fields/table state on validation or backend failure.
- R99 proves reclamation for explicit rollback, unresolved staged destruction,
  and committed destruction; both omitted-free mutants exit feature 1.
- The reviewed change contains no detach, auto-detach, set-configuration,
  Wine, prefix, USB, staging, or live-device action.

## Critical finding

### Uninitialized alternate-selection cleanup pointer

`winusb_session_set_alternate()` declares `select` without initialization at
`dev-source/dlls/winusb.sys/session.c:1005`. Early invalid-state,
unknown-alternate, and allocation-failure paths jump to cleanup before the
allocation at line 1071. Cleanup can then pass the indeterminate pointer to
`ExFreePool()` at line 1131. The existing focused contract exercises these
paths but neither sanitizer instrumentation nor the fake allocator rejects an
unknown free, so the GREEN is false-capable.

Required correction: add a real-translation-unit RED lens that detects the
unknown free, then initialize and own the cleanup pointer safely.

## Important findings

### Partial claim extension discards earlier committed pipes

SELECT_CONFIGURATION allocates a fresh empty table and copies only
`next_generation` (`wineusb.sys/unixlib.c:1491`), adds only the current
request's pipes (`unixlib.c:1513`), then frees the old table and installs the
partial map on COMMIT (`unixlib.c:1632`). Previously claimed interfaces remain
claimed while their unchanged tokens become stale. The current extension test
uses zero-pipe interfaces and cannot observe the loss.

Required correction: begin a function-child extension from the committed
table, replace only records named by the transaction, and prove a prior
descriptor-backed token remains usable after a separate successful extension.

### Missing R97/R98 mutation witnesses

R97/R98 require each R97-only assertion family to have an isolated final-head
mutation that exits feature 1. Current evidence lacks retained mutants for:

- generation incremented once per pipe rather than once per selection;
- staged table publication before COMMIT;
- loss of the old table/token on rollback.

These three bounded mutation witnesses are plan-mandated and block Task 7.

## Minor finding

The successful sync-pipe evidence contains an expected negative
`err:wineusb ... Failed to clear halt` diagnostic. Separate or explicitly
annotate the deliberate negative schedule so a passing log does not resemble
an unexpected backend failure.

## Cannot verify from retained logs

- Raw initialize evidence records LeakSanitizer refusing the ptraced runtime;
  the separate ASan/UBSan run with leak detection disabled is GREEN, but upper
  LeakSanitizer-backed leak freedom is unverified.
- Several final logs lack embedded commands and exact shell exit markers;
  terminal pass/failure counts support success but do not alone reconstruct
  exact exit provenance.

## Assessment

Task quality: **Needs fixes**.
