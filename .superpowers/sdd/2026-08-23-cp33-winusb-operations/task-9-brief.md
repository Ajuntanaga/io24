# CP33 Task 9 brief — generic control and descriptor fallback

## Purpose

Complete the next offline WinUSB layer needed for Universal Control to become a
reference oracle for the io24 behavior the native host still does not know:
the preset/effect sequence and its relation to the device firmware.  Task 9
does not run that capture.  It implements and host-tests generic control and
descriptor translation so the later complete stack can carry it safely.

## Authority and frozen input

- Approved plan: `docs/superpowers/plans/2026-08-23-cp33-winusb-operations.md`, Task 9.
- Approved design: `docs/superpowers/specs/2026-08-23-cp33-winusb-operations-design.md`, control/descriptor translation.
- Controller rulings: R108-R110 in `progress.md`.
- Repaired Gate-2 seal: 29/29 at
  `431d7e0d885f80d10aaa70907b61b2a7ff2f4066a5b3204a8988fcf6f908e421`.
- Exact base: `task-9-base.sha256`, 15/15 existing paths at
  `34ba2f90f2e2d3ddba1b75b5dcc0ca5341503a7c5ad33c1c9a2879144dfdee51`.
- New `dlls/winusb.sys/transfer.c` is explicitly absent at base.
- Frozen lower Unix wrapper support:
  `tests/wineusb_winusb_urb_contract.sh` at
  `4076a1bda411fe2295f8f1afe2c6f54ee0a49bbf93632a95d03c316a2a0b0829`.

## Change ownership

Production, locked until accepted RED review:

1. `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/transfer.c` (new)
2. `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/Makefile.in`
3. `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c`
4. `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h`
5. `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/wineusb.c`
6. `.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c`
7. `.io24-build/winusb-api-v1/dev-source/dlls/winusb/main.c`
8. `.io24-build/winusb-api-v1/dev-source/dlls/winusb/io.c`

Test-first ownership:

9. `tests/winusb_function_io_contract.c`
10. `tests/wineusb_winusb_urb_contract.c`
11. `tests/winusb_user_api_contract.c`
12. `tests/winusb_function_io_contract.sh`
13. `tests/winusb_user_api_contract.sh`
14. `tests/wineusb_winusb_urb_fake_libusb.c`
15. `tests/wineusb_winusb_busif_contract.c`
16. `tests/wineusb_winusb_busif_contract.sh`

Implementers do not edit this brief, progress, snapshots, manifests, reports,
retained logs, the lower Unix wrapper, or retained RANGE sources.

## Test-first gate

Before any production edit, add a distinct `--control-descriptor` mode at all
four actual boundaries:

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --control-descriptor
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --control-descriptor
```

Each accepted RED must compile and execute actual production at its intended
fake boundary, reach the new assertions, and exit feature 1 for absent control
or descriptor behavior.  Usage rejection, missing input, compiler/link error,
crash, prerequisite failure, source scan, or harness exit 2 is not RED.

Review the complete eight-path test delta before unlocking production.  In
particular, the function wrapper must compile the real new `transfer.c`; the
bus-interface mode must execute actual `wineusb.c`; and the fake libusb must
observe timeout and exact control-OUT payload without changing default modes.

## Required contract matrix

- Setup and public buffer length agree; accept 0 through 4096 and reject 4097.
- Nonzero length requires the direct MDL and mapped capacity; no raw user
  pointer or `METHOD_NEITHER` path is permitted.
- CONTROL_IN and descriptor use OUT_DIRECT; CONTROL_OUT uses IN_DIRECT.
- Copy the eight setup bytes exactly except interface-recipient low-byte
  canonicalization; preserve its high byte.
- Admit standard, class, and vendor types plus device, interface, endpoint,
  and other recipients; reject reserved bits/values before mutation/submission.
- Device recipient requires the root/default handle.  Endpoint recipient must
  be an exact current member of the represented interface, including direction.
- Build `URB_FUNCTION_CONTROL_TRANSFER` with `TransferBuffer = NULL`, the
  incoming `MdlAddress`, direction from setup bit 7 only, and the original IRP.
- Lower generic control uses one libusb setup, timeout 5000, exact OUT bytes
  after the setup, and bounded IN copy/actual length.
- Cached device/configuration `(index=0, language=0)` on the default handle
  never submit.  Existing selector mismatch remains invalid parameter.
- String and other descriptors use one synchronous fallback IOCTL and
  `URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE` with the direct output MDL.
- Success requires both NT and URB success; failure returns zero bytes.  Bound
  success by request length, MDL byte count, and lower actual length.
- Cover immediate success/failure, pending completion, allocations, malformed
  MDL, lower error mapping, oversized actual length, and exactly-once upper
  free/decrement.
- Add real per-interface accounting for Task-9 transfer records.  Do not claim
  caller-overlapped cancellation, cleanup, or removal safety owned later.

## RANGE invariant

Use one canonical exact RANGE predicate/response helper from both legacy
class-interface and generic-control routes.  Retain these frozen sources:

```text
c04391b8e0156ea3a4ffeeff69d76862976ffa922394d95712b96db268a5878c  tests/wineusb_class_interface_range_contract.c
6b1ccba2f22a749052e88f179c55fb7a6d9e71a6eed1dfa99ca63f451a7f22b3  tests/wineusb_class_interface_range_contract.sh
```

The positive exact fixture remains synthetic and no one-field-negative
direction/type/recipient/request/value/index/length variant may synthesize its
captured bytes.

## Final gates

Require the four focused modes above plus the retained RANGE command with its
exact current arguments.  Add isolated final-head mutants for method swap,
MDL replacement, nested IRP, missing interface canonicalization, missing
actual-length bound, timeout zero, and widened RANGE.  Independently review
the exact sixteen-path base-to-head diff before creating
`re/winusb-api-v1/logs/task-09-control-descriptor.sha256`.

## Safety boundary

Offline host contracts only.  Do not run Wine, access any Wine prefix, perform
a contained build, stage/select a driver, open USB/sysfs device paths, claim or
detach an interface, change configuration/alternate, issue a physical transfer,
run Universal Control or Voice FX, or read/write/transition firmware.  Keep the
interface unplugged and stop cleanly at battery 10% or lower.
