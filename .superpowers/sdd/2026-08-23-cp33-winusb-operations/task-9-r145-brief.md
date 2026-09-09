# Task 9 R145 isolated endpoint-call allowlist brief

## Objective and scope

Build a disposable R145 successor to rejected R144. The eventual proposal must
apply directly from the frozen live R139 head and may reopen exactly:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

No live test or production edit is authorized. Create a fresh exact
`/tmp/io24-r145-proposal.XXXXXX` tree. Own only that tree and
`task-9-r145-implementer-report.md`; do not alter any other workspace path or
dispatch subagents.

## Required correction

Apply the sealed R144 patch only inside the disposable tree. Preserve every
R144 assertion and mutation lens.

Append three ABI-identical counters to `struct io24_fake_counts` in contract
and fake for:

- `libusb_get_device()`;
- `libusb_get_active_config_descriptor()`; and
- `libusb_free_config_descriptor()`.

Keep `IO24_FAKE_API_CALL()` as the first operation of every exported fake
entry. Increment the dedicated counter immediately after it in those three
functions.

In `expect_control_endpoint_reject()`, capture a complete backend snapshot and
make an expected copy. Increment the expected `api_calls` and the three
dedicated counters by exactly one each, then call actual production and require
the complete backend state to equal that expected copy. Preserve the explicit
invalid-parameter, zero-control, no-pending, null-`DriverContext`, and forbidden
checks. This helper must allow exactly the retained active-config authority
sequence and no omitted, substituted, or extra libusb action.

## Verification

Run focused `--control-descriptor` and retained `--red` baseline and final
replays against copied active R138 production. Require exit 0 and zero failures.

Freshly compile and execute all fourteen R144 mutants, restoring production to
`ba3172e...d53051` after every run. Add:

15. the passing extra endpoint direction-mismatch device/descriptor query from
    `task-9-r144-cybersecurity-preflight.md`; and
16. direction-mismatch rejection that skips the active-endpoint validator.

Every counted mutant must execute copied production through the fake boundary,
emit the fake pass marker, exit feature 1, and report nonzero failures. No
compiler failure, harness exit 2, source scan, or non-executed exit 1 counts.

Reaudit exactly 32 exported `libusb_*` entries, 32 first-operation global
witnesses, and three correctly placed dedicated increments. Run a bounded
secret/payload scan of the two-file delta and verify it adds no dependency,
network, device, prefix, or staging surface.

## Report and safety

Report candidate hashes, baseline/final results, all sixteen fresh mutant
results, audit results, production restoration, exact direct-patch scope, and
concerns in `task-9-r145-implementer-report.md`.

Offline and hardware-free only. Do not invoke Wine/prefix, USB/device/sysfs,
driver build/staging, network, firmware, preset/effect, UC/Voice FX, or live
hardware. Stop if any required step cannot remain disposable.
