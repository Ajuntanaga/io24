# CP33 Task 4 combined independent review package

- Review rubric: `../task-4-review-rubric.md`.
- Frozen base: `../task-4-base` (12 present pre-task paths).
- Reviewed head: `../task-4-head` (14 production/test paths plus 2 evidence files).
- Combined base/head diff: `task-4.diff` (2,703 lines).
- Controller evidence patch: `re/winusb-api-v1/logs/task-04-initialize.patch`.
- Controller evidence seal: `re/winusb-api-v1/logs/task-04-initialize.sha256`.
- Head manifest: `task-4-head.sha256` (16 entries).
- Kernel report/review: `../task-4-kernel-report.md`,
  `task-4-kernel-review-round-1.md` (PASS).
- DLL report/review: `../task-4-dll-report.md`,
  `task-4-dll-review-round-3.md` (PASS).
- Authoritative plan/spec SHA-256:
  `013feee53959cd8efdf5a13e6a83ffacf2a6517f43def0566ed95f534b0fe981`,
  `8d04b44c89860b34afe0560caa9fa83c12aa80ca1e49f93734ce899dd56294a7`.

## Exact scope

Eight production paths and six contract paths differ from the frozen base:

```text
.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c
.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/Makefile.in
.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c
.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h
.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c
.io24-build/winusb-api-v1/dev-source/dlls/winusb/Makefile.in
.io24-build/winusb-api-v1/dev-source/dlls/winusb/main.c
.io24-build/winusb-api-v1/dev-source/dlls/winusb/winusb_private.h
tests/winusb_function_io_contract.c
tests/winusb_function_io_contract.sh
tests/winusb_function_binding_contract.c
tests/winusb_function_binding_contract.sh
tests/winusb_user_api_contract.c
tests/winusb_user_api_contract.sh
```

`session.c` and the DLL private header are new. The other twelve paths were
present in the frozen base. R47's `unixlib.c` delta is one explicit
`USBD_STATUS_SUCCESS` assignment on the validated select-success path.

## Fresh controller verification

All six combined gates exited zero:

```text
user initialize: CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=13 submits=3 releases=1 completions=0 failures=0
user surface: CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
kernel initialize: CP33 function executed mode=--initialize dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0 failures=0
kernel lifecycle: CP33 function executed mode=--lifecycle dispatches=12 mode-ioctls=0 last-ioctl=0 last-status=0 failures=0
retained binding: CP32 winusb function-binding lifecycle checks passed
metadata bus: WineUSB WinUSB metadata bus-interface contract: pass
```

The kernel initialize gate compiles `main.c` plus `session.c` under
ASan/UBSan/alignment and frees immediate builder IRPs in the fake. The DLL
wrapper compiles and links every collected real production unit under its
sanitizer flags.

Controller mutation checks used temporary source copies only:

```text
remove raw alternate-setting match: --initialize exit 1, failures=3
remove endpoint-uniqueness loop:     --initialize exit 1, failures=3
```

Both temporary copies were removed. Workspace production hashes did not
change.

## Evidence integrity

```text
task-4-base.sha256:             12/12 OK
task-04-initialize.patch:       3eb87ca5cf3e4ae4be206e03d3b9416cf9080f3d0559a33f5400354f63383639
task-04-initialize.sha256:      586438f53079c078dba9826ab1d65fea5392fdd4b2421ea0e98ebdeb5ce03400
task-04 seal entries:           exactly 15, 15/15 OK, excludes itself
task-4-head.sha256:             4fa6eae036038cb28ecf4096099e4b278afb659e7d8298e8034a9e0ca6ff94bd
task-4 head entries:            exactly 16, 16/16 OK
task patch vs review diff:      byte-identical
workspace vs frozen head:       16/16 byte-identical
controller_failures:            0
```

## Review lens

Review the complete combined diff and R25-R57. In addition to the rubric,
verify that the two independently reviewed halves agree on the private ABI and
session lifecycle; that no fake supplies production-owned status, request,
layout, ordering, or completion behavior; that short-output initialization is
noncommitting; that full initialization commits only after validated lower
success; and that every postcommit DLL rejection sends exactly one live-session
release while precommit rejection sends none.

R46 is an explicit Task-6 carry: Task 4's lower select remains observation-only
and has no persistent claim/configuration side effect. Task 6 must
transactionally undo future claims if a post-select/precommit state change is
scheduled.

Review is read-only. Do not edit files, use Git, run Wine, touch a prefix or
device/sysfs USB path, build/stage/select/load a driver, start applications,
install tools, perform a physical operation, or retry CP24.
