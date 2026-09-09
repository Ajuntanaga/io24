# Task 9 R144 isolated rejection-witness completion brief

## Objective

Build and verify a disposable R144 successor to rejected R143. Do not apply any
test or production change to the live workspace. The eventual direct proposal
must start from the frozen live R139 head and may reopen exactly:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

R144 must retain every sound R143 change and close the Important finding in
`task-9-r143-holistic-preflight.md`.

## Isolation and ownership

Create a fresh exact `/tmp/io24-r144-proposal.XXXXXX` directory. Own only that
disposable directory and
`.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r144-implementer-report.md`.
Do not edit or revert any other workspace path and do not dispatch subagents.

Copy the live R139 lower contract, fake, wrapper, and included retained
contract. Copy active R138 production into a disposable source tree. Apply the
sealed R143 patch only inside the disposable tree, then make the R144 contract
correction there with `apply_patch`.

## Required correction

Preserve R143's exact-status sentinel, complete three-scope matrix, full caller
storage preservation, `api_calls` ABI tail, and all 32 first-operation fake
entry increments.

Extend the complete backend snapshot to every helper that claims rejection
before backend activity:

1. generic control rejection in `expect_control_reject()`;
2. all exact malformed-admission cases in
   `expect_exact_range_admission_reject()`; and
3. the forked exact null-buffer rejection.

The preferred shape is one side-effect-free Boolean predicate over the full
`io24_backend_snapshot`, with the existing assertion wrapper calling it. Move
`expect_control_reject()` below the snapshot definitions if necessary so it can
capture and compare the complete state. The child process must include the
pure predicate in its `_exit` success condition; an `IO24_CHECK` whose failure
is ignored by `_exit` is not sufficient.

Preserve all existing status, length, complete caller storage, record, count,
allocation, submission, pending, and `DriverContext` checks. Do not weaken or
remove a redundant explicit check merely because the full snapshot covers it.

## Verification

Run focused `--control-descriptor` and retained `--red` commands against the
disposable candidate and copied active production. Baseline and final restored
replays must exit 0 with `failures=0`.

Replay all eleven compiled R143 production mutants, restoring production
hash-identically between runs. Add these three compiled counterexamples:

12. query `libusb_get_device()` and `libusb_get_device_descriptor()` before
    malformed-header rejection;
13. make the same query before null-buffer rejection; and
14. make the same query before generic control rejection, using a request that
    the existing `expect_control_reject()` path exercises.

Each counted mutant must compile successfully, execute actual copied
production through the fake boundary, report the fake-boundary pass marker,
exit feature 1, and show nonzero contract failures. Harness exit 2, compiler
failure, source scanning, or exit 1 without executed assertions is not feature
evidence.

Audit that the candidate fake still has exactly 32 exported `libusb_*` symbols
and 32 first-operation increments, with the 33rd raw macro reference being the
definition.

## Report contract

Write a complete report to `task-9-r144-implementer-report.md`. Include the new
disposable path; live/base, R143, and R144 candidate hashes; focused and
retained baseline/final results; all fourteen mutant exits and failure counts;
fake-boundary audit; production restore identity; direct live-R139 delta scope;
and self-review/concerns. Return only status, report path, result summary, and
concerns.

## Global constraints

Offline and hardware-free only. Do not invoke Wine or any prefix, USB/io24
device or sysfs path, driver build/staging, network, firmware, preset/effect,
UC/Voice FX, or live hardware. Do not alter production, live tests, wrappers,
support, snapshots, manifests, prior evidence, or protected paths. Stop if a
required step cannot be completed entirely inside the disposable tree.
