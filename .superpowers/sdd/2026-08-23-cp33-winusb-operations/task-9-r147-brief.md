# Task 9 R147 isolated immutable-authority and descriptor-lifetime brief

## Objective and scope

Build a disposable R147 successor to rejected R146. The eventual proposal must
apply directly from the frozen live R139 head and may reopen exactly:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

No live test or production edit is authorized. Create a fresh exact
`/tmp/io24-r147-proposal.XXXXXX` tree. Own only that tree and
`task-9-r147-implementer-report.md`; do not alter any other workspace path or
dispatch subagents.

## Correction 1: immutable caller and authority snapshot

Apply the sealed R146 patch only in the disposable tree. Preserve its global
and dedicated counters, journal, exact order, pointer lineage, complete backend
snapshots, three-scope RANGE matrix, caller guards, and all inherited lenses.

Before both `expect_control_reject()` and
`expect_control_endpoint_reject()` invoke production:

1. copy the complete `struct io24_control_fixture` into an expected fixture;
2. snapshot the pointed-to `struct io24_pipe_table` when present;
3. set only the expected fixture's URB status to
   `USBD_STATUS_INVALID_PARAMETER`;
4. set the live URB status to the non-success
   `USBD_STATUS_NOT_ACCESSED` sentinel.

After production returns, require the complete live fixture to equal the
expected fixture byte-for-byte, and require the pipe-table pointer and complete
pointed table to remain unchanged. This must preserve device handle and scope,
params, IRP/stack, setup, transfer pointer/length, caller storage and guards,
and every other fixture field while proving production writes invalid URB
status. Use the pre-call expected device handle, never live post-call state, for
the journal authority assertion.

If current correct production changes any other fixture byte legitimately,
identify and narrowly allow that exact field with evidence; do not weaken to
partial status/length/storage assertions.

## Correction 2: executable descriptor lifetime

Replace static returned top-level config objects with one fake-owned mutable
`struct libusb_config_descriptor` view. On each successful
`libusb_get_active_config_descriptor()`, shallow-copy the selected immutable
source config into that view and return the view. On
`libusb_free_config_descriptor()` with that exact pointer, safely poison at
least `bNumInterfaces`, `wTotalLength`, and `interface` so a subsequent
production traversal cannot observe the prior descriptor. A later get call
must refresh the complete view. Do not free real memory or cause a harness
crash.

Existing valid endpoint-recipient positive cases must remain pending/green.
Moving the correct free before traversal must instead make those production
positives fail by feature assertions at exit 1.

## Correction 3: real first-operation witness

In each exported fake entry, declarations before
`IO24_FAKE_API_CALL()` must be uninitialized declarations only. The global
witness must be the first executable operation, and the relevant dedicated
counter increment must be the immediate next executable operation. In
`libusb_get_active_config_descriptor()`, move `result = NULL` and every
other initialization after those two operations. Verify source and
disassembly.

## Verification

Run focused `--control-descriptor` and retained `--red` baseline and final
replays against copied active R138 production. Require exit 0 and zero
failures.

Freshly compile and execute all nineteen R146 mutants, restoring production to
`ba3172e...d53051` after every run. Add:

20. mutate `params->device->handle` to non-null `0x4444` before endpoint
    validation, then use that mutated handle;
21. free the correct active descriptor immediately after lookup, traverse it
    afterward, and remove the original late free;
22. after a correct endpoint-rejection authority sequence, corrupt caller
    storage, transfer length, and URB status while returning invalid parameter;
23. perform the same corruption on oversized generic pre-backend rejection;
24. omit the required invalid URB-status write on a rejection path while
    preserving its return and all other state.

Every counted mutant must compile and execute actual copied production through
fake libusb, emit its pass marker, exit feature status 1, and report nonzero
failures. The early-free mutant must be a safe feature failure, not a compiler
failure, signal, harness exit 2, or source-only result.

Reaudit:

- exactly 32 exported `libusb_*` entries and 32 first-executable global
  witnesses in source and disassembly;
- exactly three immediate dedicated increments;
- ABI-identical count and record layouts and whole-structure resets;
- refreshed/poisoned mutable descriptor behavior;
- complete fixture and pipe-table rejection snapshots;
- all twenty-four fresh mutant logs and exact production restoration; and
- a bounded R147-only scan for secrets/payloads and added dependency, network,
  device, prefix, staging, firmware, preset, or effect surface.

## Report and safety

Report candidate hashes, baseline/final results, all twenty-four fresh mutant
results, audit results, direct frozen-R139 patch scope, exact production
restoration, and concerns in `task-9-r147-implementer-report.md`.

Offline and hardware-free only. Do not invoke Wine/prefix, USB/device/sysfs,
driver build/staging, network, firmware, preset/effect, UC/Voice FX, or live
hardware. Stop if any step cannot remain disposable.

