# CP33 Task 4 kernel-half report

Date: 2026-08-24  
Status: DONE

## Scope and frozen base

Work was limited to the four kernel production paths, the four controller-authorized
kernel/retained contract paths, and this report. The controller-owned Task 4 patch and
checksum evidence were not created or edited. The workspace is intentionally non-Git;
no Git operation was performed.

Before implementation, the frozen base was verified from the project root with:

```text
$ sha256sum -c .superpowers/sdd/2026-08-23-cp33-winusb-operations/reviews/task-4-base.sha256
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-base/.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/Makefile.in: OK
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-base/.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c: OK
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-base/.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h: OK
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-base/.io24-build/winusb-api-v1/dev-source/dlls/winusb/Makefile.in: OK
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-base/.io24-build/winusb-api-v1/dev-source/dlls/winusb/main.c: OK
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-base/tests/winusb_function_io_contract.c: OK
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-base/tests/winusb_function_io_contract.sh: OK
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-base/tests/winusb_function_binding_contract.c: OK
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-base/tests/winusb_function_binding_contract.sh: OK
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-base/tests/winusb_user_api_contract.c: OK
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-base/tests/winusb_user_api_contract.sh: OK
```

## TDD evidence

The contract wrapper was first extended with `--initialize`, the real 24-byte
`wine_winusb_request`, a direct-output MDL, and executable coverage while the new
`session.c` was only a compilable skeleton. The accepted feature RED was:

```text
$ tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --initialize; code=$?; echo exit=$code
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--initialize dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0xffffffffc00000bb failures=109
exit=1
```

This was feature RED, not harness RED: actual `main.c` and actual `session.c` compiled,
the retained CP32 contract passed, the intended mode ran, and unsupported Task 4
behavior caused exit 1.

During final lifetime audit, executable lower-boundary assertions were added before
the production lifetime fix. This produced a second focused feature RED:

```text
$ tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --initialize; code=$?; echo exit=$code
72 x FAIL IoCallDriver:149: file->outstanding == 1
72 x FAIL IoCallDriver:150: !file->zero_outstanding.Header.SignalState
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--initialize dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0 failures=144
exit=1
```

The two shown diagnostics are an exact multiplicity-preserving aggregation of the
144 raw diagnostics. It proved session descriptor/select work was not yet protected
against cleanup/close/removal.

## Implementation

- `session.c` performs checked descriptor discovery in the exact device, nine-byte
  configuration header, validated configuration-body order. It independently checks
  NT status and `UrbHeader.Status`, and production explicitly writes the exact URB to
  the built IRP next-stack `Others.Argument1` before `IoCallDriver`.
- The bounded parser rejects short/overrunning descriptors, header/body truncation,
  mismatched `wTotalLength`, endpoint-before-interface, no interface, missing default
  alternate, duplicate alternate, endpoint-count mismatch, and checked size/offset or
  mapped-address overflow.
- Output shorter than 72 is untouched with information zero and no lower call. Exact
  72 and intermediate 100-byte buffers perform three descriptor reads and return only
  the exact 72-byte size header (`total_size=211`, session zero), without select or
  commit. Oversized 212-byte output is rejected unchanged after discovery.
- Exact 211-byte success lays out header 0-71, device 72-89, configuration 90-130,
  interface 131-146, alternates 147-178, and endpoints 179-210. It reports speed 3,
  one interface, two alternates, two endpoints, and a nonzero monotonic cookie.
- Full initialization allocates device, configuration header/body, committed snapshot,
  committed interface state, and select URB. It validates and maps before one select,
  holds no spin lock across allocation or lower waits, and commits snapshot, arrays,
  cookie, and state atomically only after select success.
- Exact RELEASE validates the 24-byte live default-session request, detaches and frees
  the two committed allocations, clears state/cookie, rejects malformed, stale, and
  cross-file requests without mutation, and permits reinitialization with a larger
  distinct nonzero cookie.
- `main.c` now admits each private IOCTL through a file-context outstanding-work
  acquisition. The zero-outstanding event is cleared before any descriptor/select
  lower call and signaled only after dispatch work releases its count. Cleanup/removal
  can change state while work runs, but close cannot free the context or committed
  ownership until the operation drains. The contract observes outstanding=1 and an
  unsignaled event at every actual lower callback, then deterministically removes an
  initialized context with one outstanding unit and observes snapshot, interface, and
  context frees only after drain.
- `Makefile.in` builds `session.c`; the private header exposes only the internal state
  and session entry points needed by `main.c`.
- Under R41/R42, the retained binding wrapper requires and links actual `session.c`.
  Its two strong host fakes fail the retained contract if the CP32-only scenario ever
  unexpectedly builds a Task 4 URB or maps Task 4 output. No weak symbol, unresolved
  fallback, copied production helper, or test-only production seam was added, and the
  exact CP32 terminal pass line is unchanged.

## State and lower-call accounting

- Prevalidation, missing/alien file, bad MDL/map, mapped-end overflow, stopped device,
  and output below 72: 0 descriptor reads, 0 select, 0 commit, output unchanged.
- Size query (72 or 100): 3 descriptor reads, 0 select, 0 retained allocations,
  information 72, coherent uninitialized file.
- Full success (211): 3 descriptor reads plus exactly 1 select; six allocations total,
  four temporary frees, two retained allocations, information 211, initialized file.
- Allocation failures 1 through 6 observe respectively 0, 1, 2, 3, 3, and 3 descriptor
  lower calls, always 0 select, balanced rollback, output unchanged, session zero.
- Builder failures at build 1 and build 4 observe respectively 0 and 3 completed
  descriptor calls and no select. Descriptor NT failure and descriptor USB-status
  failure each stop after one lower call. Select NT failure and select USB-status
  failure each stop after three reads plus one select. All leave output and file state
  uncommitted and balanced.
- Successful RELEASE performs 0 lower calls and frees exactly the snapshot and interface
  state. Malformed/stale/cross-file release performs 0 lower calls and 0 frees.
- Initialized cleanup/surprise/remove with nonzero outstanding waits first, then frees
  exactly context plus the two committed objects; allocation/free totals balance.

## Final GREEN gates

```text
$ tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--initialize dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0 failures=0
exit=0

$ tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --lifecycle
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--lifecycle dispatches=12 mode-ioctls=0 last-ioctl=0 last-status=0 failures=0
exit=0

$ tests/winusb_function_binding_contract.sh .io24-build/winusb-api-v1/dev-source
CP32 winusb function-binding lifecycle checks passed
exit=0
```

All wrappers compile with `-std=c11 -Wall -Wextra -Werror` and classify missing input,
compile/link failure, or abnormal execution as harness failure rather than feature RED.

## Changed paths

- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/Makefile.in`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c` (new)
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c`
- `tests/winusb_function_io_contract.c`
- `tests/winusb_function_io_contract.sh`
- `tests/winusb_function_binding_contract.c` (R42 narrow link fake)
- `tests/winusb_function_binding_contract.sh` (R41 narrow real-unit link)
- `.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-kernel-report.md` (new)

## Self-review and concerns

The implementation was checked for output-before-commit, unbalanced temporary or
committed ownership, spin locks spanning waits/allocations, lower-builder assistance,
conflated NT/USB status, early context destruction, and unintended claim mechanics.
No libusb claim/detach/set-configuration operation was added; Task 6 remains the claim
owner. Evidence is offline host fake/static only. No Wine prefix, USB/sysfs/device,
driver staging/loading/selecting, application, full build/matrix, installation, Git,
or CP24 action occurred.

No kernel-half correctness concern remains from the authorized host-contract scope.
Combined DLL/kernel integration review and controller-generated Task 4 patch/checksum
evidence remain controller-owned follow-up.

## Fix round 1 — kernel review round 0

Date: 2026-08-24  
Review source: `reviews/task-4-kernel-review-round-0.md`  
Rulings applied: R46, R47, R48

### Frozen lower-source check

R47's newly authorized lower path matched its frozen Task 4 base before edit:

```text
$ sha256sum .io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c
3dc8e664735762431e7fa012bd2ea14e90f6260806c72cebbe3c9300af0f2502  .io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c
```

### Fix-round RED

The actual `main.c` plus `session.c` initialize contract was first changed to:

- compile and link with `-fsanitize=address,undefined,alignment`,
  `-fno-sanitize-recover=all`, and `-fno-omit-frame-pointer`;
- run with
  `ASAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=1:detect_leaks=1`
  and `UBSAN_OPTIONS=halt_on_error=1:exitcode=1`;
- allocate a distinct builder IRP for every lower call, copy completion to the supplied
  `IO_STATUS_BLOCK`, poison/free the IRP before the immediate return, and balance every
  builder allocation;
- require a non-success incoming `USBD_STATUS_NOT_ACCESSED` sentinel and make each
  configured successful fake path explicitly write `USBD_STATUS_SUCCESS`;
- decode packed test snapshot records through aligned locals and `memcpy`;
- reject the literal MI05-alt0, MI06-alt0, MI05-alt1 interleaving counterexample; and
- require a literal valid 25-byte default-endpoint fixture to produce one bulk pipe at
  endpoint `0x82`, maximum packet size 64, in the real select URB.

The pre-fix production then failed for the intended sentinel and lifetime reasons:

```text
$ tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --initialize; code=$?; echo exit=$code
FAIL IoCallDriver:183: urb->UrbHeader.Status == USBD_STATUS_NOT_ACCESSED
=================================================================
ERROR: AddressSanitizer: heap-use-after-free
READ of size 4
    #0 ... in submit_urb
...
freed by thread T0 here:
    #1 ... in IoCallDriver
...
previously allocated by thread T0 here:
    #1 ... in IoBuildDeviceIoControlRequest
...
SUMMARY: AddressSanitizer: heap-use-after-free ... in submit_urb
ABORTING
exit=1
```

Temporary build paths, process identifiers, addresses, and build IDs in the raw ASan
trace are intentionally unstable; the diagnostic, allocation/free sites, failing
production function, and exit status above are exact.

### Fixes and executable closure

- `submit_urb()` now initializes every submitted upper URB to
  `USBD_STATUS_NOT_ACCESSED`, uses the builder IRP only before `IoCallDriver`, waits if
  necessary, and consumes the supplied local `IO_STATUS_BLOCK` for both immediate and
  pending completion. It never reads the builder IRP after the call.
- The host lower fake explicitly overwrites the sentinel on success, varies NT and URB
  status independently, adds descriptor/select success-without-status-write failures,
  and runs a successful four-call pending-completion schedule. Every allocated builder
  IRP is poisoned/freed, and allocation/free counts must match after each IOCTL.
- All packed interface, alternate, and endpoint snapshot records in `session.c` are
  accessed through aligned locals plus checked-offset `memcpy`. The test contract does
  the same at exact odd offsets 115, 131, 147, and 179. Address, undefined-behavior,
  and alignment sanitizers execute the complete initialize matrix and report no error.
- The parser retains checked cursor/count arithmetic and rejects any interface number
  that reappears after another interface begins. Contiguous alternates remain valid.
- Select size is now the checked sum of each interface header and every default
  alternate endpoint. The real select URB populates exact interface lengths, pipe
  counts, endpoint addresses, types, and maximum packet sizes from aligned decoded
  records. The retained MI05 default alternate remains an exact zero-pipe case; the
  independent default-endpoint fixture proves the generic one-pipe case.
- On the independently validated lower select success path, current source
  `wineusb.sys/unixlib.c` now sets `req->Hdr.Status = USBD_STATUS_SUCCESS` only after
  pipe-handle population and immediately before returning `STATUS_SUCCESS`. Invalid
  paths retain their existing explicit failure statuses.
- Per R46, Task 4's select remains observation-only. A state change after lower select
  still prevents late upper commit. No claim/configuration rollback or Task 6 mechanic
  was invented here; deterministic rollback of future persistent claims remains an
  explicit Task 6 carry.

### Fix-round GREEN

```text
$ tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--initialize dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0 failures=0
exit=0

$ tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --lifecycle
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--lifecycle dispatches=12 mode-ioctls=0 last-ioctl=0 last-status=0 failures=0
exit=0

$ tests/winusb_function_binding_contract.sh .io24-build/winusb-api-v1/dev-source
CP32 winusb function-binding lifecycle checks passed
exit=0
```

The initialize command is the ASan plus UBSan/alignment gate; sanitizer compiler/link
failure is wrapper exit 2, while the accepted pre-fix production finding exited 1.
Lifecycle and retained binding remain uninstrumented and preserve their prior modes and
terminal lines.

### Round-1 changed paths and limitation

- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c` (R47 narrow edit)
- `tests/winusb_function_io_contract.c`
- `tests/winusb_function_io_contract.sh`
- `.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-kernel-report.md`

The `unixlib.c` result is current-source/static evidence only. Its one-line success
status change was not executed because no contained build/current-source matrix was
authorized in this fix round. The executable upper contract proves that success is
accepted only after an independent lower status write; it does not claim to execute
the edited Unix backend. No Wine, prefix, USB/sysfs/device, driver load/stage/select,
application, full build/matrix, installation, Git, or CP24 action occurred.
