# Task 9 R136 implementer report

## Status and scope

Status: implementation and bounded offline evidence complete; production remains
frozen.  This intentionally non-Git workspace was not initialized and no commit
was created.

Live edits are limited to:

- `tests/winusb_function_io_contract.c`
- `tests/winusb_function_binding_contract.c`

New task-local evidence is limited to:

- `.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r136-mutants/`
- `.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r136-implementer-report.md`

No live production, bus-interface contract, wrapper, support, RANGE, prior
snapshot/manifest/report, task report, or progress file was edited.  Work was
offline and hardware-free.  There was no Wine/prefix, USB-device/sysfs access,
driver build/staging, network, firmware, preset/effect, or hardware action.  The
only sysfs reads were `cat /sys/class/power_supply/BAT0/capacity`; observed
capacities were 53, 52, 43, 39, 39, and 37 percent, always above the 10-percent
stop threshold.

## Initial integrity

Before the live edit, both owned files matched the immutable R136 base.  The
checks were:

```text
sha256sum -c .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r136-base.sha256
sha256sum -c .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r135-head.sha256
sha256sum -c .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r132-frozen.sha256
```

Results: exits 0/0/0, respectively 2/2, 2/2, and 14/14 `OK`.  Manifest
SHA-256 values were:

- R136 base: `16db761f908070f8220684b99a50055210d5b8bf9a7ee5ce8c0c50df615c6321`
- rejected R135 head: `fe3bd2130c4af10935088c22cf9541182d78816b2b1bb50213613073da1815ae`
- frozen fourteen paths: `343e2929b6f03cd9af0b2f957e2edfbfef4dc3fd0c86126906c75c6882d08a53`

Initial owned-file SHA-256 values were:

- function contract: `31c3070fd206088d91b383157bc09b98bc40abd956efb9fcef2806e17cc090aa`
- binding contract: `dd9f1f86ffa6ce35e00715fbead4f971678caa6890faa20d3b97c657b36eb25a`

## Implemented correction

The retained binding allocator now invokes an optional
`IO24_RETAINED_POOL_ATTEMPT_HOOK()` at `ExAllocatePool` entry before its
failure branch.  Its default definition is a no-op, so the standalone retained
fixture behaves identically unless the including function contract opts in.

The function contract opts in with two nonwrapping Boolean retained-attempt
latches.  Each of the two `begin_pending_control()` admissions is surrounded by
an exact retained interval.  Each exact `complete_pending_task9_irp()` interval
arms both the direct and retained latches.  The alternate-selection operations
remain outside the completion intervals.  The direct completion observer was
converted from an unsigned counter to a Boolean latch, and the rejected R135
shared `pool_allocations` snapshot/equality was removed.  Reset clears all new
observer state.  The existing four-object admission journal, distinct
context/URB identities, distinct stored outcomes, pairwise retirement, list,
outstanding, and reference evidence remain intact.

## Fresh clean execution evidence

Battery immediately before final verification was 39 percent.

Focused function contract:

```text
tests/winusb_function_io_contract.sh \
  .io24-build/winusb-api-v1/dev-source --control-descriptor
```

Result: exit 1; exactly 203 expected feature failures; zero harness, crash,
compiler/linker, or sanitizer markers.  Terminal summary:

```text
CP33 function executed mode=--control-descriptor dispatches=35 mode-ioctls=29 last-ioctl=0x22200a last-status=0xffffffffc000009a failures=203
```

Retained lifecycle and standalone binding:

```text
tests/winusb_function_io_contract.sh \
  .io24-build/winusb-api-v1/dev-source --lifecycle
tests/winusb_function_binding_contract.sh \
  .io24-build/winusb-api-v1/dev-source
```

Results: exits 0/0; failure counts 0/0; diagnostic-marker counts 0/0.
Lifecycle summary was `dispatches=12 mode-ioctls=0 last-ioctl=0
last-status=0 failures=0`; standalone binding printed
`CP32 winusb function-binding lifecycle checks passed`.

Manual ASan/UBSan focused replay:

```text
cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -D__WINESRC__ \
  -fsanitize=address,undefined,alignment -fno-sanitize-recover=all \
  -fno-omit-frame-pointer \
  -Itests -I.io24-build/winusb-api-v1/dev-source/include \
  -I.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys \
  -I.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys \
  tests/winusb_function_io_contract.c \
  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c \
  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/transfer.c \
  -o "$san_root/contract"
ASAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=1:detect_leaks=1 \
UBSAN_OPTIONS=halt_on_error=1:exitcode=1 \
  "$san_root/contract" --control-descriptor
```

Result: compile exit 0; execution exit 1; exactly 203 feature failures.
AddressSanitizer, UndefinedBehaviorSanitizer, runtime-error, LeakSanitizer,
harness/crash, and compiler/linker marker counts were all zero.  The validated
temporary binary and logs were removed.

## Replayable bounded mutant evidence

The complete copied fixtures, logs, exits, replay script, and instructions are
under:

```text
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r136-mutants/
```

They were replayed with:

```text
sh .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r136-mutants/replay.sh
```

Replay exit was 0.  Every case compiled with exit 0 and executed with exit 1:

| Case | Failures | Retained-lens failures | Direct-lens failures | bad markers |
| --- | ---: | ---: | ---: | ---: |
| `admission/r135` | 203 | 0 | 0 | 0 |
| `admission/r136` | 204 | 1 | 0 | 0 |
| `completion/bypass` | 203 | 0 | 0 | 0 |
| `completion/r136` | 204 | 1 | 0 | 0 |
| `failed/r136` | 204 | 1 | 0 | 0 |

The sole added line in each corrected case was:

```text
FAIL control_retained_allocation_end:225: !control_retained_allocation_attempted
```

The admission mutant routes a two-object replacement pair through copied
actual `main.c` during the first admission, later copies/uses/frees it during
the matching completion, and normally retires both admitted original pairs.
Its helper-call/free assertions are 2/2 and its original journal remains 4/4.
Immutable R135 remains false-green at 203; corrected R136 adds only the exact
retained-admission failure.

The completion mutant routes four recreated objects through copied actual
`main.c` during the two exact completion intervals, uses/frees them, and retires
the admitted originals in the retained order.  Its helper-call/free assertions
are 4/4 and its original journal remains 4/4.  The hook-bypass fixture uses the
hookless R135 binding support; the only compile-only adjustment in its copied
function source is `__attribute__((used))` on the otherwise unreferenced hook
function.  It remains false-green at 203; the final hook adds only the exact
retained-completion failure.

The failed-attempt fixture forces one copied actual-main helper allocation to
return null inside the first completion interval.  It asserts one helper call,
the null result, zero helper frees, and the fake's one pre-failure diagnostic
increment.  It then restores only that disposable diagnostic count so teardown
balance remains independent.  The Boolean retained lens still adds the sole
204th failure, proving the hook runs before failure handling.

Successful compiler logs are empty by design; each complete runtime stream and
each exit is stored beside its exact copied sources.  The artifact manifest was
verified with:

```text
cd .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r136-mutants
sha256sum -c manifest.sha256
```

Result: exit 0, 54/54 `OK`, zero failed entries.  `manifest.sha256` SHA-256 is
`ca111ccab7208d44704bee1ab411e1d5c3d636c31bcd709abca4fea1e4aa4148`.
No compiled binary remains in the evidence tree.

## Final integrity, identities, and delta

Fresh final verification repeated:

```text
sha256sum -c .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r136-base.sha256
sha256sum -c .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r135-head.sha256
sha256sum -c .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r132-frozen.sha256
sha256sum tests/wineusb_winusb_busif_contract.c \
  tests/winusb_function_io_contract.c \
  tests/winusb_function_binding_contract.c
```

Results: manifest exits 0/0/0 with 2/2, 2/2, and 14/14 `OK`.  Final hashes:

- frozen bus-interface contract: `9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348`
- function contract: `b18c2f40cc0fbb4bf37ad076293cacf26ecdc43c995b3434fd262abc91f2356a`
- binding contract: `0c066f0fb0e46e01ef42ed166762a9d27edce2b62cc5cead76b8c1a6849237b0`

The combined exact R136-base-to-live diff is 142 lines at SHA-256
`afb8e748b4fe23a43ce086e48e3341155275c77be93cfb9b6ddafa2e6695ec3c`.

## Self-review and concerns

Self-review found no expectation weakening, arithmetic observer, source-scan
evidence, alternate operation inside a completion interval, or live-production
change.  The retained hook is default-no-op and precedes the retained failure
branch; all attempt signals are Boolean and reset between schedules.

The clean function contract intentionally remains genuine feature RED at the
same 203-failure production boundary.  This report makes no production reopen,
cleanup/cancellation/teardown, hardware, firmware, preset, or effect claim.
Mandatory independent review and any controller-owned candidate sealing remain
outstanding.
