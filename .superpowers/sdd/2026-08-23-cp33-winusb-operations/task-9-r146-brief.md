# Task 9 R146 isolated endpoint authority-journal brief

## Objective and scope

Build a disposable R146 successor to rejected R145. The eventual proposal must
apply directly from the frozen live R139 head and may reopen exactly:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

No live test or production edit is authorized. Create a fresh exact
`/tmp/io24-r146-proposal.XXXXXX` tree. Own only that tree and
`task-9-r146-implementer-report.md`; do not alter any other workspace path or
dispatch subagents.

## Required correction

Apply the sealed R145 patch only inside the disposable tree. Preserve every
R145 assertion and mutation lens, including the global witness, the three
dedicated counters, and complete snapshots.

Append an ABI-identical journal to both definitions of
`struct io24_fake_record`. It must observe at least:

- the global API ordinal for each of get-device, get-active-configuration, and
  free-configuration;
- the handle passed to get-device and the device it returns;
- the device passed to get-active-configuration and the descriptor it returns;
- the descriptor passed to free-configuration.

Use `uintptr_t` for pointer observations. Keep `IO24_FAKE_API_CALL()` as the
first operation of every exported fake entry and the relevant dedicated
counter as the immediate next operation. Record each ordinal after that
increment and record inputs/results without adding another fake-boundary call.
Whole-structure reset must zero every added observation.

In `expect_control_endpoint_reject()`, retain the exact counter delta, invoke
actual production, and then require:

1. consecutive ordinals at prior `api_calls + 1`, `+ 2`, and `+ 3` in
   get-device, get-active-configuration, free-configuration order;
2. get-device input equals `f->device.handle`;
3. get-device result is non-null and equals the active-configuration input;
4. active-configuration result is non-null and equals the free input;
5. after copying only those verified journal values into the expected record,
   the complete backend snapshot equals the expected state.

Preserve invalid status, zero control, no pending transfer, null
`DriverContext`, forbidden-operation checks, caller-buffer guards, and every
generic/malformed/null no-backend snapshot.

## Verification

Run focused `--control-descriptor` and retained `--red` baseline and final
replays against copied active R138 production. Require exit 0 and zero
failures.

Freshly compile and execute all sixteen R145 mutants, restoring production to
`ba3172e...d53051` after every run. Add:

17. replace `libusb_get_device(device->handle)` with
    `libusb_get_device(NULL)`;
18. call get-device normally but pass a substituted device to
    get-active-configuration; and
19. call free-configuration with the wrong descriptor and/or before lookup,
    while preserving the same three API counts and omitting the real free.

Every counted mutant must execute copied production through the fake boundary,
emit the fake pass marker, exit feature 1, and report nonzero failures. No
compiler failure, harness exit 2, source scan, or non-executed exit 1 counts.

Reaudit exactly 32 exported `libusb_*` entries, 32 first-operation global
witnesses, three immediate dedicated increments, ABI-identical journal layout,
reset coverage, and the ordinal/pointer-lineage checks. Run a bounded
secret/payload scan of the R146-only two-file delta and verify it adds no
dependency, network, device, prefix, staging, firmware, preset, or effect
surface.

## Report and safety

Report candidate hashes, baseline/final results, all nineteen fresh mutant
results, audit results, production restoration, exact direct-patch scope, and
concerns in `task-9-r146-implementer-report.md`.

Offline and hardware-free only. Do not invoke Wine/prefix, USB/device/sysfs,
driver build/staging, network, firmware, preset/effect, UC/Voice FX, or live
hardware. Stop if any required step cannot remain disposable.

