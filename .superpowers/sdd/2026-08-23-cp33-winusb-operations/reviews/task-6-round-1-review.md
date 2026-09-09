# CP33 Task 6 round-1 independent review

Verdict: **PASS**

No material issue found.

- Publication/lifetime: per-file serialization covers initialize/release
  through COMMIT, publication, and output copy; the reentrant RELEASE witness
  executes actual `main.c`/`session.c` and would fail with a permissive mutex.
- Locking/removal: lock order is consistent; no spin lock spans waits or lower
  calls. STOP, SURPRISE, and REMOVE serialize against finalization. REMOVE
  releases the mutex for file drain, attempts recovery once, forwards
  synchronous lower REMOVE, then clears retained upper ownership.
- Recovery: failed COMMIT plus failed ROLLBACK retains the exact token and
  allocations device-wide. Each later initialize performs one recovery attempt
  before SELECT, without spinning or freeing early. The lost-acknowledgement
  limitation is stated honestly.
- Behavior/regression: null-token non-function SELECT remains successful;
  function transactions remain exact. Explicit rollback is reverse-order, and
  later partial failure preserves earlier committed claims. Original claim,
  idempotence, busy mapping, teardown ordering, metadata v1/v2, and
  forbidden-operation invariants remain intact.
- Coverage/scope: actual `main.c`, `session.c`, and `unixlib.c` are compiled
  through their intended fakes. R81 adds only a mutually exclusive
  passive-mutex fake; retained assertions and wrappers remain frozen. The
  current round-1 manifest verifies 13/13.

Nonblocking caveat: raw LeakSanitizer remains unavailable under ptrace. The
reported leak-disabled run retains ASan, UBSan, and alignment instrumentation
plus explicit allocation balances. The reviewer did not rerun build-producing
wrappers during the read-only review.
