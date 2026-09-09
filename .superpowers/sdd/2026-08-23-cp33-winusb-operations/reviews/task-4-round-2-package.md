# CP33 Task 4 combined fix round 2 re-review package

- Current rubric: `../task-4-review-rubric.md` (R25-R63), SHA-256
  `e0346c271ef28e754ab61d8b2588f8d574346a7e218709b4ded5ca2bb152bfca`.
- Primary round-1 verdict: `task-4-combined-review-round-1.md` (FAIL).
- Supplemental round-1 verdict: `task-4-round-1-test-review.md` (FAIL).
- Reviewed round-1 rubric archive: `task-4-round-1-rubric.md`, SHA-256
  `2aed11d6d95c3fbb4876cc6128b2efd36649d38583f52dd2428cc14ace48d999`.
- Fix base: `../task-4-round-1-head`, manifest
  `task-4-round-1-head.sha256`.
- Fix head: `../task-4-round-2-head`, manifest
  `task-4-round-2-head.sha256`.
- Three-file fix diff: `task-4-round-2.diff` (498 lines).
- Current full base/head patch:
  `re/winusb-api-v1/logs/task-04-initialize.patch` (2,762 lines).
- Updated DLL report: `../task-4-dll-report.md`, SHA-256
  `d2cdeb834a613d9cbe852cedc83e512bdc071b4393f6f965f00ee64b3aacf052`.
- Authoritative plan/spec hashes remain
  `013feee53959cd8efdf5a13e6a83ffacf2a6517f43def0566ed95f534b0fe981`
  and `8d04b44c89860b34afe0560caa9fa83c12aa80ca1e49f93734ce899dd56294a7`.

## Exact correction scope

Only `tests/winusb_user_api_contract.c` differs functionally from the round-1
head. The regenerated evidence patch and seal are the other two files in the
fix diff. The DLL report is outside the 16-entry checkpoint scope. Production
DLL `main.c` remains byte-frozen at
`6a2ea0ae74185fffbbb81f957bd0af83bda3f044e9212927b8d71920ba700876`.

Current hashes:

```text
badf5808b4ca99ec0334bb315c8b4165f304c9458ce865bbc10a1a14ff49abdc  tests/winusb_user_api_contract.c
d2cdeb834a613d9cbe852cedc83e512bdc071b4393f6f965f00ee64b3aacf052  task-4-dll-report.md
```

## Findings under re-review

1. R61 routes successful totals 211, 181, and 163 through the same helper. The
   full IOCTL event records its output pointer; the helper finds the allocation
   for that exact pointer and requires both allocation and output lengths equal
   the sizing header. Missing header/full events assert without dereferencing a
   null event.
2. R62 adds matching raw/packed `[5,2,5]` groups and requires one postcommit
   rollback release. An adjacent-only production mutation exits feature 1.
3. R63 records the exact waited handle and requires the request's private event.
   `ERROR_ACCESS_DENIED` and `ERROR_INVALID_HANDLE` both survive clobbering
   cleanup. Hardcoded-error and wrong-handle mutations exit feature 1.

Judge R61-R63 and the stricter supplemental findings ADDRESSED or NOT
ADDRESSED. Flag any new Critical/Important regression or false-green gap.

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

Controller-reproduced temporary-copy mutations, all feature exit 1 and all
temporary trees removed:

```text
previous-record-only uniqueness:       failures=2
hardcoded WAIT_FAILED error:            failures=2
wrong private wait handle:              failures=3
conditional non-211 allocation/output: failures=2
unrelated exact allocation plus wrong-sized actual output allocation: failures=1
```

The fifth mutation keeps full output length correct while allocating the actual
181-byte output buffer at `total_size + 1`, alongside a balanced unrelated
exact-sized allocation. It specifically proves allocation/output pointer
identity rather than a size-only search.

## Evidence integrity

```text
round-0 head:                   16/16 OK and immutable
round-1 head:                   16/16 OK and immutable
full patch:                     bf7b3211d3d957d10b7245290e6c89b67572a772a01e965aaa5a7d26bd139b8c
task seal:                      32f0de367c6b3dfab2b70139abb1bce1bb25499b4842f1c90324c7a3db80736c
task seal entries:              exactly 15, unique, 15/15 OK, excludes itself
round-2 fix diff:               e86206977a67da160374335dbdf9c819f9f0404426fae64f30edc724b40bca14
round-2 head manifest:          9af336450d0c823ac3aa31084ff7a168d5f35d91a536f24f9ecb9345b577ac3c
round-2 head entries:           exactly 16, 16/16 OK
full patch headers:             exactly 14
fix diff headers:               exactly 3
workspace vs round-2 head:      16/16 byte-identical
controller_failures:            0
```

R46 remains the explicit Task-6 carry. Review is read-only. Do not edit, use
Git, run Wine, touch a prefix or connected device/sysfs USB path, run a
contained/full build, perform driver/application/install/physical actions, or
retry CP24.
