# Task 9 R134 mandatory review

## Candidate and integrity

The reviewed successor is the immutable 2/2 `task-9-r134-head.sha256`
snapshot at manifest SHA-256
`7af721f59ec7d9b50ae47ebfee6c18aa8f9abcc1b72ce88490abcca6c4c56fd4`.
The R133-to-R134 delta is the exact 74-line `task-9-r134.diff` at SHA-256
`39187e38e5a98c2c0f2b0c77ab9428e03bdfe38a2c75b80546f8bfc39ee43e5f`.
Both reviewers verified the candidate/base manifests, fourteen frozen paths,
twelve controller artifacts, exact diff, and live equality.  Controller replay
remains function feature RED at 203 failures, actual-lower feature RED at twelve
failures, both retained modes GREEN, and ASan/UBSan marker-clean.

## Targeted review

PASS with no Critical, Important, or material Minor finding.  The reviewer
confirmed that the new observer counts every call to the function contract's
`ExAllocatePool` before its failure paths, is independent of admission
tracking, precisely encloses both completions, excludes alternate-selection
work, resets safely, and retains the distinct outcome and pairwise retirement
evidence.  Current production's transfer record and URB allocations use that
observed route.

## Holistic review

REQUEST CHANGES with one Important false-green.  The function contract renames
`ExAllocatePool` and `ExFreePool` while it includes
`winusb_function_binding_contract.c`, which textually includes actual
production `winusb.sys/main.c`.  Allocator calls compiled into `main.c`
therefore use the retained allocator, not R134's new observed allocator.

A bad implementation can add allocation/free helpers in `main.c`, call them
from transfer completion to create replacement transfer/URB objects, use
copied links and outcomes, retire the four admission-journaled originals in
the required order, and free the replacements through the retained helper.
Both allocator families update the same global pool totals, so balance,
statuses, list state, reference order, and the R134 zero-attempt observer can
all still pass.

The smallest correction does not require reopening binding support.  Snapshot
the shared `pool_allocations` count in
`control_completion_allocation_begin()` and require it unchanged in
`control_completion_allocation_end()`, while retaining the per-attempt
observer.  The retained allocator increments that shared count before its
failure branch, covering successful and failed `main.c`-routed attempts.  Add
a bounded recreation mutant that uses the `main.c` helper route.

All other R132-R134 evidence reviewed cleanly, including identity/outcome and
pairwise retirement, endpoint-map mutex evidence, locked-list invalidation,
production insertion observation, order mirrors, safe join terminal, exact
frozen paths, and Tasks 11-13 exclusions.

## R135 decision

Production cannot reopen.  Preserve `task-9-r134-head` as rejected evidence
and reopen only live `tests/winusb_function_io_contract.c`.  The actual-lower
contract remains frozen at SHA-256
`9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348`.
All production, support, wrappers, RANGE, other tests, snapshots, and prior
evidence remain frozen.

The successor must add the completion-scoped shared-allocation snapshot,
retain R134's direct attempt observer, and catch a bounded recreation mutant
whose allocation/free helpers are compiled through actual `main.c`.  Fresh
focused/retained, ASan/UBSan, exact-snapshot, frozen-path, and two-clean-review
gates remain mandatory before production can reopen.
