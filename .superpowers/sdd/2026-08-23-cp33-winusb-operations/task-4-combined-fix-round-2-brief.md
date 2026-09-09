# CP33 Task 4 combined fix round 2 brief

This is a contract/report-only correction under R61-R63. The authoritative
Task-4 plan/spec, both round reviews, supplemental test review, and current
rubric apply. `task-4-round-1-head` is the immutable fix base.

## Ownership

Only these paths may change:

```text
tests/winusb_user_api_contract.c
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-dll-report.md
```

Base hashes:

```text
6e533ef07acb7dce93014938824f1b89985a460e9b056943a2f0eb1eeeb78859  tests/winusb_user_api_contract.c
cfec9e7ef8ec21c23d9dea1e19c83f65a8c14adddf6b05093906e65bb7cbc8bb  task-4-dll-report.md
```

All production paths, wrappers, other contracts, frozen snapshots, evidence,
ledger, rubric, packages, and reviews are immutable. In particular DLL
`main.c` must remain SHA-256
`6a2ea0ae74185fffbbb81f957bd0af83bda3f044e9212927b8d71920ba700876`.

## Required executable proof

1. Route every valid initialization fixture through one shared helper that
   reads the sizing header and verifies the second INITIALIZE output length and
   the successful snapshot allocation for totals 211, 181, and 163.
2. Record the full IOCTL output pointer. Require it be identical to the exact
   successful allocation pointer whose size equals advertised `total_size`;
   an unrelated same-sized allocation cannot satisfy the check.
3. Add a three-interface nonadjacent duplicate `[5, 2, 5]` in matching raw and
   packed order. It must reject postcommit with one release. In a temporary
   production copy, reduce uniqueness to previous-record-only and prove feature
   exit 1.
4. Record the exact handle passed to `WaitForSingleObject` and require it be the
   private event associated with that request. Exercise at least two distinct
   scheduled `WAIT_FAILED` errors through clobbering close cleanup. Temporary
   hardcoded-error and wrong-wait-handle mutations must each exit feature 1.
5. In a temporary production copy, allocate and submit
   `header.total_size + (header.total_size != 211)` and prove the non-211 path
   exits feature 1. Also demonstrate that allocation/output pointer identity is
   observed. Remove every temporary tree safely.

Preserve all earlier header/parser/release/lifecycle checks and terminal output.
Do not add a production seam, source-only substitute, fixed retained-total
shortcut, or Task-5 behavior.

## Authorized commands

```text
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --surface-only
```

Append exact normal and mutation results, final hashes, and scope comparison to
the DLL report. Do not regenerate controller evidence. No Wine, prefix,
device/sysfs USB, contained/full build, driver/application/install/physical
action, Git, or CP24 retry is authorized.
