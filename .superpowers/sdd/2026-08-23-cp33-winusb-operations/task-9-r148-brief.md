# Task 9 R148 unified rejection-state and lifetime-RED brief

## Objective and scope

Build a disposable successor to rejected R147.  The eventual proposal must
apply directly from frozen live R139 and may reopen exactly:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

No live test or production edit is authorized.  Start from the exact R147
candidate only in a fresh `/tmp/io24-r148-proposal.XXXXXX` tree.  Own only that
tree and `task-9-r148-implementer-report.md`.

## Correction 1: one safe complete rejection snapshot

Retain R147's pre-call complete fixture copy, captured pipe-table pointer, deep
pipe-table value, invalid expected URB status, live non-success status sentinel,
and captured pre-call device handle.

Factor safe match helpers with these rules:

1. compare the complete post-call fixture with the expected fixture;
2. compare the post-call pipe-table pointer with the captured pointer;
3. deep-compare the table only when that pointer still equals the captured
   pointer and the captured pointer was non-null; and
4. never dereference a changed or null post-call pointer.

Use this same complete snapshot for every control-rejection oracle, including:

- generic shape/scope rejection;
- endpoint-recipient rejection;
- function/out-of-scope RANGE rejection;
- malformed-header and mismatched/undersized exact-RANGE admission rejection;
  and
- exact-RANGE null-buffer rejection inside its child process.

The null-buffer child must evaluate the safe complete match directly before
exiting.  Retain all backend, allocation, storage, length, status, guard, and
driver-context checks; the complete snapshot is additive where those checks
carry useful diagnostics.

## Correction 2: retained product failure is feature RED

The embedded retained pipe contract returns 1 both for product assertion
failures and for loader/symbol failures.  Its translation-unit-local
`failures` counter distinguishes them.

In the lower contract's `main()`:

- keep usage, loader, symbol, signal, compiler, and unsupported exit paths as
  harness status 2;
- when the retained call returns 1 with a nonzero retained failure counter,
  preserve those failures as feature failures, load the production module,
  continue the requested lower group, emit the normal `CP33 lower executed`
  summary, and return feature status 1;
- when the retained call returns 1 with zero retained failures, keep treating
  it as a harness failure; and
- leave the clean baseline path byte-for-byte equivalent in behavior.

This must make the literal unconditional early-descriptor-release mutation a
real production-through-fake RED rather than harness exit 2.  The lower
execution summary plus retained assertion output is the required execution
witness for that row; do not print a false pass marker.

## Verification

Run fresh focused `--control-descriptor` and retained `--red` baseline and final
replays against copied active R138 production.  Require exit 0 and zero
failures.

Freshly compile and execute all 24 R147 mutants and add:

25. on the exact function/out-of-scope class-interface OUT rejection, change
    `params->device->handle` before returning invalid parameter;
26. on malformed-header exact-RANGE rejection, change the pipe-table pointer
    to null before returning invalid parameter;
27. on exact-RANGE null-buffer rejection, change the device handle before
    returning invalid parameter;
28. on function/out-of-scope rejection, change a field inside the pointed pipe
    table while preserving its pointer; and
29. unconditionally free the correct active configuration immediately after
    lookup in `pipe_token_is_current()`, traverse afterward, and remove the
    original late free.

Rows 1--28 must compile, execute actual copied production through the fake,
emit the fake pass marker, exit feature status 1, and report nonzero failures.
Row 29 must compile, execute actual copied production through the fake, emit
retained assertion evidence and the `CP33 lower executed` summary, exit feature
status 1, report nonzero failures, and produce no signal or harness exit 2.
Restore copied production to
`ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`
after every row.

Reaudit the complete R147 gates: 32 exported fake entries, first executable
global witness in source and disassembly, three immediate dedicated increments,
ABI-identical journal layouts, whole-object resets, mutable configuration-view
poison and full refresh, direct frozen-R139 reconstruction, 29 distinct
canonical logs, and a bounded two-file delta scan.

## Report and safety

Report exact candidate and patch hashes, baseline/final results, all 29 fresh
mutant outcomes and canonical log names, safe pointer behavior, literal
early-release classification, audit results, restoration, and concerns in
`task-9-r148-implementer-report.md`.

Remain offline and hardware-free.  Do not invoke the protected prefix, device
or USB paths, driver build/staging, network, firmware, preset/effect, UC/Voice
FX, or live hardware.
