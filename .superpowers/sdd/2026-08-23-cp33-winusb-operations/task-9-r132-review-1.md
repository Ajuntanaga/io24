# CP33 Task 9 R132 successor review 1

Decision: `REQUEST CHANGES`. Production remains frozen.

The rejected candidate is preserved exactly by `task-9-r132-head.sha256`
(2/2, manifest SHA-256
`2bf2c60c9f0c250051c09ddb6f1e9eb49ba6f149562360cdab585b374fcd0cc1`).
The exact base-to-head patch is `task-9-r132.diff` at SHA-256
`906270b295d0776cd4ac0722f79ca323ac2e4a34f90a058d3bdf2213cd23e977`.
Controller execution reproduced function feature exit 1 with 203 failures,
actual-lower feature exit 1 with 12 failures, both retained GREENs, and a
marker-clean ASan/UBSan replay. All base, head, controller-log, and fourteen-
path frozen manifests verified before review.

## Targeted review findings

1. Important: the `wineusb_cs` injection proves that a conflicting entry is
   present while the lock is held, but the IRP and its URB remain valid after
   `LeaveCriticalSection()` removes the entry. A mutant can capture the IRP
   under lock, dereference/classify it after unlock, and still return busy.
   The fixture must change or invalidate the classification fields on lock
   exit, then restore them after dispatch.
2. Important: the two pending controls are byte-identical and have identical
   completion outcomes. Swapped completion contexts/URBs can satisfy FIFO IRP,
   aggregate list/count, and reference assertions. The fixture must capture
   two distinct live completion contexts and URBs, use distinguishable stored
   outcomes, and prove each pair retires exactly once at its own completion.
3. Important: return-time list equality cannot distinguish a busy SELECT that
   was transiently inserted and removed. Production-boundary list-insertion
   observation must prove the armed busy SELECT entry is never passed to
   `InsertTailList`.
4. Important: both two-child schedules put the conflicting child last. A
   multi-entry classifier that examines only `irp_list.Blink` passes. Mirror
   schedules must put the sole conflict first and the later child
   nonconflicting for the same target, or an equivalent middle-conflict
   schedule must prove every position is considered.

## Holistic review finding

The holistic reviewer independently confirmed the per-request record/URB gap
as Important. A shared/reused upper record and URB can remain on the aggregate
list through the first completion and retire after the second while both
original IRPs and file references appear balanced. The smallest correction is
an allocation/context/URB journal that proves two distinct pairs are live,
only the first pair retires at completion one, and only the second retires at
completion two.

Neither reviewer authorized production to reopen. The same two live C
contracts may change only for this review-fix round. The rejected head,
production, support, wrappers, RANGE, and every other test path remain frozen.

