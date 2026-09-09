# CP33 Task 5 independent review round 2

Verdict: **PASS** — no Critical, Important, or Minor findings.

## Findings closed

- The round-0 unbounded-retention issue is addressed. A zero-reference record
  is reclaimed directly by Free. A record with admitted calls is deferred, then
  detached and freed by the last release before its root-reference decrement
  can wake the finalizer. The 32-cycle contract keeps outstanding allocations
  constant while its root remains live.
- The cross-root proof gap is addressed. The final contract preserves a retired
  root token and all associated tokens, requires the next root token differ
  from them, and rechecks stale Free/Associated/Descriptor/Speed admission
  while the fresh root is live. Reset-after-root exits feature 1 with five
  failures.
- Token allocation is registry-locked, rejects zero and
  `INVALID_HANDLE_VALUE`, advances monotonically without wrap, and rolls back
  cleanly with `ERROR_NOT_ENOUGH_MEMORY` on exhaustion.
- Admission remains token-only before any caller-value dereference. Lock order,
  final drain, one synchronous RELEASE, and caller-device nonownership remain
  intact.

## Verified evidence

- `task-5-round-2-head.sha256`: 3/3 OK; workspace byte-identical.
- `task-5-round-2-mutations.sha256`: 18/18 OK; nine genuine feature exits 1.
- Eight final offline gates: exit 0.
- Final test SHA: `7547c6f2292c3a8650bb18b0610959eee30927418e1d6b279a5bf6f6e8751fca`.
- Frozen production SHA: `8f4144b2f540f05c16a53bf4f49f1ea29455e30effb2589818ea13a3cc64d753`
  and `4be97b07b4f091619a9c5c86b42a33af31976ffbaf61c7576d42c0a15626a1c0`.
- Frozen pre-fix head: genuine feature RED, exit 1 with 33 failures.

No Wine, contained build, full matrix, prefix, device/live USB, install, or
physical action was performed.
