# CP33 Task 4 combined fix round 1 re-review package

- Current rubric: `../task-4-review-rubric.md` (R25-R60), SHA-256
  `2aed11d6d95c3fbb4876cc6128b2efd36649d38583f52dd2428cc14ace48d999`.
- Round-0 verdict: `task-4-combined-review-round-0.md` (FAIL).
- Reviewed round-0 rubric archive: `task-4-round-0-rubric.md`, SHA-256
  `ac94bc0f88def9efbaae409979c8ed616fc6b54788fae6142f244f508af17ef5`.
- Failed fix base: `../task-4-head`, manifest `task-4-head.sha256`.
- Fix head: `../task-4-round-1-head`, manifest
  `task-4-round-1-head.sha256`.
- Four-file fix diff: `task-4-round-1.diff` (525 lines).
- Full base/head patch: current
  `re/winusb-api-v1/logs/task-04-initialize.patch` (2,737 lines).
- Updated DLL report: `../task-4-dll-report.md`, SHA-256
  `cfec9e7ef8ec21c23d9dea1e19c83f65a8c14adddf6b05093906e65bb7cbc8bb`.
- Authoritative plan/spec SHA-256 remain
  `013feee53959cd8efdf5a13e6a83ffacf2a6517f43def0566ed95f534b0fe981`
  and `8d04b44c89860b34afe0560caa9fa83c12aa80ca1e49f93734ce899dd56294a7`.

## Exact correction scope

Only two production/test paths differ from the failed head:

```text
.io24-build/winusb-api-v1/dev-source/dlls/winusb/main.c
tests/winusb_user_api_contract.c
```

The regenerated evidence patch and seal are the other two changes in the
four-file fix diff. The report is intentionally outside the 16-entry checkpoint
scope. Every other Task-4 scope path is byte-identical to the failed reviewed
head.

Current hashes:

```text
6a2ea0ae74185fffbbb81f957bd0af83bda3f044e9212927b8d71920ba700876  dlls/winusb/main.c
6e533ef07acb7dce93014938824f1b89985a460e9b056943a2f0eb1eeeb78859  tests/winusb_user_api_contract.c
cfec9e7ef8ec21c23d9dea1e19c83f65a8c14adddf6b05093906e65bb7cbc8bb  task-4-dll-report.md
```

## Findings under re-review

1. R58 replaces numeric interface sorting with equality rejection against every
   prior packed interface while retaining exact contiguous ranges and raw order.
   Executable fixtures cover valid `[5 alt0, 2 alt0]`, duplicate interface 5
   rejection, and valid endpoint `0x81` reuse across alt0/alt1.
2. R59 captures `GetLastError()` on `WAIT_FAILED` before clobbering event
   cleanup. The fake schedules `ERROR_ACCESS_DENIED` and the public failure
   preserves it; unexpected other wait results retain the generic mapping.
3. R60 records the sizing header and heap allocation, then requires the second
   INITIALIZE output and snapshot allocation to equal advertised `total_size`.
   A temporary production copy with `header.total_size + 1` exited feature 1
   with `failures=7`; the temporary tree was removed.

Judge each round-0 finding ADDRESSED or NOT ADDRESSED. Also flag any new
Critical/Important regression or false-green gap introduced by this fix. The
complete Task-4 integration remains review scope, but unchanged kernel/wrapper
paths need not be rereviewed absent a cross-layer effect.

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

Controller independently reproduced the R60 temporary-copy mutation:

```text
full INITIALIZE output = header.total_size + 1: exit 1, failures=7
temporary tree cleanup: exit 0
```

## Evidence integrity

```text
failed head:                    16/16 OK and immutable
full patch:                     a0c6c29b0c96fbdbc2b29fbbfbc814a6bb890d54f6e208498029b58a05449af9
task seal:                      aced54e746436694e0e2b919e935164e027e50a94936ca6783c77b0e0da0a470
task seal entries:              exactly 15, unique, 15/15 OK, excludes itself
round-1 fix diff:               3140710a3e03b9fbc3d04b9d8f498c39b7d18fa6de359b75c51995af4db5a48b
round-1 head manifest:          eaaee204760fdbd7c63dc5f333d70282ce9df1e2aed55e9e567be9a01167f39d
round-1 head entries:           exactly 16, 16/16 OK
full patch diff headers:        exactly 14
fix diff headers:               exactly 4
workspace vs round-1 head:      16/16 byte-identical
controller_failures:            0
```

R46 remains the explicit Task-6 carry. Review is read-only. Do not edit, use
Git, run Wine, touch a prefix or connected device/sysfs USB path, run a
contained/full build, perform driver/application/install/physical actions, or
retry CP24.
