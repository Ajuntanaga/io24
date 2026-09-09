# Task 9 R133 mandatory re-review

Recorded: 2026-08-25T14:29:54-07:00

## Candidate and integrity

The reviewed candidate is the immutable 2/2 `task-9-r133-head.sha256`
snapshot at manifest SHA-256
`2d1ad6b0da1cf9d39b059e13e4a9953c83b4fcbd79a3b6df26f0825a56228ba1`.
Both reviewers independently verified the base, rejected R132 head, corrected
R133 head, fourteen frozen paths, controller logs, exact deltas, and live
candidate equality.  The controller evidence remains genuine focused feature
RED (function exit 1 with 203 failures; actual lower exit 1 with 12 failures),
retained GREEN, and ASan/UBSan marker-clean.

## Targeted re-review

PASS with no Critical, Important, or material Minor finding.  The reviewer
accepted the distinct context/URB identity and retirement checks, lock-exit
invalidation, production-boundary insertion observer, both-order classifier
traps, frozen-path integrity, and Tasks 11-13 exclusions.

## Holistic re-review

REQUEST CHANGES with one Important finding.  At the R133 snapshot's lines
194-198, `control_pool_pause_allocations()` disables allocation observation;
line 3372 calls it before both completions.  Free tracking remains active, but
a completion-time clone can allocate replacement record/URB objects, copy the
admitted pair, unlink via copied links, free the four originally journaled
objects in the expected order, use and free the untracked replacements, and
preserve exact IRP outcomes, counts, and global allocation balance.
`control_pool_check_complete(4, 4)` would still pass.  The contract therefore
does not yet prove that each admitted context/URB pair remains the sole pair
through its completion.

All other R133 corrections reviewed cleanly, including the distinct stored
outcomes, post-unlock mutation, actual included-production `InsertTailList`
observation, first/last mirror schedules, safe join terminal, and local-fixture
retirement boundary.

## R134 decision

Production cannot reopen.  Preserve `task-9-r133-head` as rejected evidence
and reopen only live `tests/winusb_function_io_contract.c`.  The actual-lower
contract is frozen at SHA-256
`9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348`.

The smallest authorized correction must independently count or forbid
allocations only around each `complete_pending_task9_irp()` invocation, without
including the intervening alternate-selection calls, and a bounded
completion-time recreation mutant must fail through that executable observer.
Fresh focused/retained and ASan/UBSan evidence, an exact successor snapshot,
frozen-path verification, and two clean independent re-reviews remain
mandatory before production can reopen.
