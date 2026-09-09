# CP33 Task 4 kernel-half implementation brief

This is the kernel half of approved Task 4. The authoritative plan/spec and
controller rulings R25–R63 apply. The frozen base is `task-4-base`; do not edit
the DLL half, controller evidence, ledger, snapshots, plan, or specification.

## Owned paths

- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/Makefile.in`
- new `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c`
- `tests/winusb_function_io_contract.c`
- narrowly expanded `tests/winusb_function_io_contract.sh`
- report only: `.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-kernel-report.md`

## Test-first boundary

First make `--initialize` an executable feature mode, compile/link the actual
new `session.c`, and replace the initialize scenario's bespoke request with
the exact 24-byte `struct wine_winusb_request` plus a fake direct-output MDL.
Record genuine feature RED after the intended production units compile and
execute. Usage, missing input, compiler/linker failure, crash, or retained
Task 3 regression is harness exit 2, never accepted RED.

The executable contract must cover:

- device descriptor read, nine-byte configuration header read, then exactly
  the validated 41-byte retained MI05 configuration read;
- descriptor `bLength < 2`, a descriptor extending beyond `wTotalLength`,
  truncated header/body, mismatched `wTotalLength`, endpoint before interface,
  no interface, no alternate zero, and duplicate alternate for one interface;
- every checked-add/multiply/offset rejection reachable through the production
  parser boundary, including an explicit overflow witness without adding a
  production test-only entry point;
- direct output shorter than 72 with no write/commit; exactly 72 as a
  noncommitting validated size query with information 72 and `total_size=211`;
  exact 211-byte success with complete offsets/counts/records; and bounded
  rejection of oversized/malformed lengths;
- allocation failure at each temporary/committed allocation boundary and
  lower select-configuration failure, with exact rollback;
- state/session/reserved/version/size/file/MDL mapping rejection and guarded
  `SystemBuffer` plus output nonmutation;
- a second/concurrent initialization attempt failing without disturbing the
  first committed session;
- exact `IOCTL_WINE_WINUSB_RELEASE` success for the live default session,
  stale/wrong-size/version/reserved/session/interface rejection without
  mutation, balanced committed frees, and reinitialization with a distinct
  nonzero monotonic cookie;
- retained Task 3 lifecycle/removal behavior after the new committed snapshot
  and arrays are freed.

## Production invariants

- `IRP_MJ_DEVICE_CONTROL` dispatches initialization through the exact private
  IOCTL. Input stays in `SystemBuffer`; output is only the mapped direct MDL.
- Reserve `UNINITIALIZED -> INITIALIZING` under the file lock, release all spin
  locks for allocations/lower waits, and atomically commit only after full
  parse, output validation, and lower selection. Every failure restores a
  coherent uninitialized file with session zero and no snapshot/interface
  ownership.
- Use checked `SIZE_T` addition/multiplication and descriptor cursor movement.
  No unchecked offset, count, or allocation calculation is allowed.
- The size-query path may perform only the three descriptor reads. It returns
  a 72-byte header with session zero and exact final metadata, but performs no
  select, claim, file-state commit, or retained allocation.
- The full path repeats validated discovery, maps and validates sufficient
  direct output before state-changing lower work, issues exactly one
  `URB_FUNCTION_SELECT_CONFIGURATION`, and commits only on lower success.
  Task 6, not this task, owns libusb claim mechanics.
- R34 requires production—not the fake builder—to set the lower IRP's
  next-stack `Others.Argument1` to the exact URB. R35 requires independent NT
  and `UrbHeader.Status` success for each descriptor and select operation.
- The retained MI05 full snapshot is exact: header 0–71; device 72–89;
  configuration 90–130; interface record 131–146; alternates 147–178;
  endpoints 179–210. It reports one interface, two alternates, two endpoints,
  speed `0x03`, and a nonzero monotonic cookie.
- `session.c` contains bounded parse/build/session helpers; `main.c` owns
  dispatch/lifecycle glue. The sys Makefile builds `session.c`.
- R33 requires the release IOCTL in this task so DLL rollback is real rather
  than fake-only. It returns an initialized file coherently to uninitialized;
  Task 13 retains ownership of cancellation/drain once transfers exist.
- Cleanup/close/removal free committed Task 4 ownership only after the Task 3
  drain invariant. No new live, Wine, prefix, USB, sysfs, or build path exists.

## Gates and handoff

Run at minimum:

```bash
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --lifecycle
tests/winusb_function_binding_contract.sh .io24-build/winusb-api-v1/dev-source
```

Do not create Task 4 patch/hash evidence. Append exact RED/GREEN commands,
outputs, changed paths, rollback proof, and concerns to the kernel report.
