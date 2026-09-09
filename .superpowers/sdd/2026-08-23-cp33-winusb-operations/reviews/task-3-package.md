# Task 3 scoped review package

- Task brief: `../task-3-brief.md`.
- Task review rubric: `../task-3-review-rubric.md`.
- Implementer report: `../task-3-report.md`.
- Controller rulings: `../progress.md` R8, R15, R17, and R23.
- Base label: `task-3-base`.
- Head label: `task-3-head`.
- Base manifest: `task-3-base.sha256` (7 present-file entries; the new private
  header and lifecycle seal are recorded absent in `../task-3-base-state.txt`).
- Head manifest: `task-3-head.sha256` (9 entries, including the lifecycle
  seal).
- Full scoped diff: `task-3.diff` (1,048 lines).
- Head-manifest-file SHA-256:
  `102245be22ee04a18d126c15c21090b3c3d8ca5c49e423b911f9f8be797c88f2`.
- Diff SHA-256:
  `26da5a8281c391e7b491d01083c0eba2923653e41f9f455e5b46507a1b333f52`.

## Required review scope

Read the brief, rubric, report, and diff once. Return independent verdicts for
spec compliance and task quality. Review the additive metadata-v2 definition,
lower speed callback and unchanged v1 context, upper exact-v2 consumption and
reference balance, device/file lifecycle, PnP/removal behavior, all three
contracts, and the eight-entry lifecycle seal. R23 authorizes the narrowly
additive retained-binding fake change while requiring its v1 coverage and
terminal CP32 pass line to remain intact.

Apply the prepared mutation/race lens: exact-not-minimum v2 size, no speed
output mutation after removal, unchanged metadata-object `BusContext`, 1/1
reference balance, create rejection outside STARTED, no early `FsContext`
publication, distinct file contexts, idempotent cleanup/close, no free before
zero outstanding, and create/cleanup/close behavior across surprise removal.

## Binding constraints

- CP32 and patch-check sources are immutable; only the five Task 3 production
  paths in the diff may change.
- Metadata bus-interface v1 declaration, layout, context, and behavior remain
  byte-for-byte valid. V2 is a separate additive exact-size/version interface.
- V2 uses `&device->winusb_metadata` as `BusContext`; the speed callback uses
  `CONTAINING_RECORD`, reads only removal/high-speed state, and does not mutate
  output on failure.
- The upper FDO must query and validate exact v2, call both getters, cache the
  speed/version, and dereference exactly once on every post-query path.
- Create publishes a distinct `FsContext` only after STARTED-state allocation
  and locked insertion succeed. Cleanup closes admission; close unlinks/counts
  once and frees only after zero outstanding; removal closes admission and
  waits for file ownership.
- No Wine, prefix, USB/device/sysfs, staging, driver, application, install,
  Git, or CP24 action is permitted or claimed.

## Fresh controller verification

```text
metadata bus-interface: exit 0, pass
function lifecycle: exit 0, failures=0
retained CP32 function binding: exit 0, unchanged terminal pass line
task-03-lifecycle.sha256: exactly 8 entries, 8/8 OK, no self-hash
task-3-base.sha256: 7/7 snapshot entries OK
post-dispatch filesystem audit: exactly the 5 production, 3 contract, and 1
  lifecycle-seal paths changed; no out-of-scope working path has a new mtime
controller_failures=0
```

Review is read-only. Do not rerun the full suite, edit files, use Git, run
Wine, touch a prefix/device/sysfs USB path, build/stage/select/load a driver,
start applications, install tools, perform a physical operation, or retry
CP24.
