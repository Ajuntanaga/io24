# Task 2 independent review rubric

The reviewer is read-only and returns separate spec-compliance and task-quality
verdicts.

## Exact owned scope

- Production: `include/winusb.h`, new `include/winusbio.h`, new
  `include/wine/winusb.h`, `include/Makefile.in`, and
  `dlls/winusb/winusb.spec` in the CP33 development source only.
- Tests: `tests/winusb_user_api_contract.c`, the R12-authorized
  `tests/winusb_user_api_contract.sh`, and
  `tests/winusb_function_io_contract.c`.
- Evidence: `re/winusb-api-v1/logs/task-02-abi.patch` and
  `task-02-abi.sha256`.
- No other production, test, plan, specification, ledger, snapshot, handoff,
  immutable CP32, or patch-check file may change.

## Required test-first evidence

- R11 is closed before production edits: fake `DeviceIoControl` records its
  `lpBytesReturned` pointer, and the focused policy caller proves that pointer
  does not alias its public `ValueLength`. The frozen vendor policy-8 input
  capacity remains 4.
- Compile-time public/private surface assertions precede production changes.
  Their pre-implementation run is genuine feature RED exit 1, not usage,
  missing-input, compiler/harness, crash, or unrelated RED.
- `--surface-only` is a documented, narrowly implemented wrapper mode and
  succeeds after the production surface exists.
- GREEN evidence covers the surface/ABI contract and all three retained CP32
  binding commands named by the task, with clean output.

## Public surface

- Policy identifiers are exactly `0x01` through `0x09`; device-speed query and
  speed values are exact.
- `WINUSB_SETUP_PACKET` has the exact five public fields and size 8.
- The exact fourteen vendor-imported APIs have the required prototypes and
  calling convention.
- `winusbio.h` is installed by `include/Makefile.in`; the private Wine header
  is not installed publicly.
- Exactly fourteen `winusb.spec` entries become real `stdcall` exports,
  `WinUsb_ControlTransfer` uses `int64` for the setup packet, and the eight
  unimported legacy names remain explicit stubs.

## Private ABI

- ABI version and transfer caps are exact.
- Function codes `0x800` through `0x80b` appear exactly once with their exact
  buffered/direct methods; none uses `METHOD_NEITHER`.
- `wine_winusb_request` is 24 bytes and `wine_winusb_snapshot` is 72 bytes.
  Interface, alternate, and endpoint snapshot records are each 16 bytes;
  alternate and pipe requests are each 32 bytes; descriptor, policy, and
  control requests are each 40 bytes.
- Every request embeds the common request header, carries explicit lengths
  where relevant, and contains reserved fields intended to be zero-validated.
- Every ABI member is a fixed-width `UINT8`, `UINT16`, `UINT32`, `UINT64`, or
  an array of those. No pointer, handle, `ULONG`, `BOOL`, `size_t`, native enum,
  pointer-sized integer, compiler-dependent bitfield, or flexible array is in
  the private structures.
- Normal and optional available `-m32` compilation/preprocessing prove the
  same layouts without installing tools or weakening assertions.

## Evidence and preservation

- `task-02-abi.patch` is reproducible and contains deltas for only the five
  production paths specified by R13, with new files represented correctly.
- `task-02-abi.sha256` includes and verifies the patch, both focused C
  contracts, and the R12 wrapper.
- Metadata bus-interface v1 is untouched. CP32 and the patch-check clone remain
  immutable. No Wine, prefix, device, sysfs USB, driver, application, physical
  operation, build/stage/select action, CP24 retry, installation, or Git action
  occurred.

## Verdict

Return spec compliant only if every exact surface/layout/export/evidence item
is supported by the scoped diff and report. Return task quality approved only
if the tests enforce the declarations/layouts independently, cannot accept a
harness failure as RED, and introduce no Critical or Important issue.
