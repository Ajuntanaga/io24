# Task 9 R135 successor review request

## Authority and boundary

Read R135 at the end of `task-9-report.md` and the exact rejection in
`task-9-r134-review.md`.  Production remains frozen.  A PASS may accept only
the Task-9 RED evidence needed for a separate, narrow production correction;
it cannot complete Task 9, CP33, firmware/preset/effect capture, or hardware
behavior.

## Immutable candidate and lineage

- Rejected R134: `task-9-r134-head.sha256`, manifest SHA-256
  `7af721f59ec7d9b50ae47ebfee6c18aa8f9abcc1b72ce88490abcca6c4c56fd4`.
- R135 successor: `task-9-r135-head.sha256`, 2/2, manifest SHA-256
  `fe3bd2130c4af10935088c22cf9541182d78816b2b1bb50213613073da1815ae`.
- Exact R134-to-R135 function-only delta: `task-9-r135.diff`, 34 lines,
  SHA-256 `386d67d278c61c1e530cefedab58c3fd662f218bdc586519fdc6b4584db93936`.
- R135 function SHA-256:
  `31c3070fd206088d91b383157bc09b98bc40abd956efb9fcef2806e17cc090aa`.
- Frozen lower SHA-256:
  `9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348`.
- Frozen fourteen-path manifest: `task-9-r132-frozen.sha256`.
- Implementer report: `task-9-r135-implementer-report.md`, SHA-256
  `a5215de270e242709f12501a5119d55febd7e7052214c2109a3e3ff058b93ebf`.
- Controller logs: `task-9-r135-controller-logs.sha256`, 12/12, manifest
  SHA-256 `68fc11ef18bc1cee0c5a514989e8117edfca543820f4c9488e7e4a35d03553e8`.

Verify each manifest/diff and both live-to-R135 comparisons before relying on
them.

## Fresh controller replay

- Function focused: exit 1; 35 dispatches, 29 mode IOCTLs, exactly 203 named
  feature failures; no compiler/linker/harness/crash marker.
- Function lifecycle: exit 0; 12 dispatches and zero failures.
- Actual lower focused: exit 1 with exactly 12 named permit failures.
- Actual lower retained: exit 0.
- Manual ASan/UBSan/alignment: compile exit 0; focused exit 1 with the same 203
  failures; zero sanitizer, leak, crash, or harness marker.

## R135 correction and required adversarial review

R134's direct attempt observer remains unchanged.  R135 additionally snapshots
the monotonically increasing shared `pool_allocations` counter when each exact
completion interval begins and requires the count unchanged at interval end.
The retained allocator used by textually included actual `winusb.sys/main.c`
increments that counter before its failure branch.  The two completion
intervals remain disarmed during alternate-selection calls, and reset clears
the snapshot.

The substantive disposable mutant copied actual `main.c`, `session.c`,
`transfer.c`, and `winusb_private.h`.  New `main.c` allocation/free helpers
were called from transfer completion to create/copy/use/free replacement
transfer/URB pairs while the four admitted originals retired in the expected
pairwise order.  An executable mutant counter required exactly four retained
helper allocations.  Against immutable R134 it remained at 203 failures with
the direct observer quiet; against R135 it reached 204 with only
`pool_allocations == control_completion_pool_allocations_before` added.  A
separate failed-helper probe also reached the shared lens while the direct
observer remained quiet.

Independently determine whether the direct attempt count plus the shared
monotonic snapshot covers every relevant successful and failed allocation
route through both separately compiled `transfer.c` and textually included
actual `main.c`, without admitting counter reset/wrap/confounding or counting
intervening alternate work.  Inspect the mutant's substance rather than
trusting its numeric delta.  Confirm the admission journal, stored distinct
outcomes, exact pairwise retirement, mutex/endpoint-map evidence, locked lower
classification, insertion/order mirrors, join terminal, reset isolation, and
Tasks 11-13 exclusions all remain intact.  Hunt for false greens, observer
self-dependence, expectation weakening, or an unsafe ownership claim.

Return `PASS` only with no Critical, Important, or material Minor finding.
Otherwise return `REQUEST CHANGES` with severity, exact file/line evidence, a
passing bad implementation, and the smallest correction.  Do not edit any
file.  No source-text scan substitutes for feature evidence.  No Wine, prefix,
USB/sysfs device path, driver/build/staging, network, firmware, preset/effect,
or live hardware action is authorized.
