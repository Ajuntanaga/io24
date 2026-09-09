# CP33 Task 6 round-1 independent review request

Review only; do not edit. Do not run Wine, access external or physical state,
inspect USB/sysfs, stage/select builds, or touch a prefix. This is a bounded
offline C lifetime and fake-driven contract review.

Read:

1. `reviews/task-6-round-0-review.md`
2. ledger rulings R76 through R81
3. `task-6-round-1-report.md`
4. `task-6-round-1.diff` (exact base-to-head correction)
5. the original `task-6.diff` and `task-6-brief.md` where needed for preserved
   Task-6 invariants

Return `PASS` only if every round-0 finding is closed without a regression.
Otherwise report exact path/line, severity, violated invariant, and smallest
safe fix. Explicitly assess:

- Reentrant same-file RELEASE cannot observe/free session ownership until
  lower COMMIT, upper publication, and output copy complete.
- File and device passive-mutex ordering has no cleanup/close/remove deadlock;
  no spin lock is held across waits or lower calls. STOP, SURPRISE, and REMOVE
  cannot change or invalidate state inside SELECT/finalization/publication.
- REMOVE does not hold the finalization mutex across file drain; it makes one
  bounded recovery attempt, then clears retained upper ownership only after
  synchronous lower-child destruction is established.
- Failed COMMIT plus failed ROLLBACK retains the exact token and unpublished
  allocations at device scope. A later initialize makes one recovery attempt
  before SELECT, never spins, and neither loses nor frees ownership early.
- The stated transport limitation is honest: a failed finalization submission
  is assumed not to consume the token; lost acknowledgement is not claimed.
- A successful non-function SELECT with null transaction remains supported,
  while function children still obtain and finalize exact transactions.
- Nonempty explicit ROLLBACK releases in reverse and preserves earlier
  committed claims; later partial failure releases only new claims.
- Actual `main.c`, `session.c`, and `unixlib.c` run through the intended fakes;
  concurrency schedules cannot pass merely through permissive fake mutexes.
- Every Task-6 original invariant remains: ascending/new/function-only claim,
  token validation without dereference, one pending transaction, idempotence,
  busy mapping, release-before-parent, v1/v2 unchanged, and no detach,
  auto-detach, or set-configuration.
- R81 changes only the missing passive-mutex fake boundary and preserves the
  retained binding assertions and wrapper.
- LeakSanitizer ptrace refusal remains only an environment caveat; the
  leak-disabled run still executes ASan/UBSan/alignment plus explicit balances.

Do not broaden findings into future Task 7+ behavior. Do flag any reachable
race, deadlock, use-after-free, lost ownership, false GREEN, or scope drift.
