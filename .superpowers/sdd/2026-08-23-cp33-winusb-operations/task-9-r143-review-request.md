# Task 9 R143 preauthorization review request

Timestamp: 2026-08-25T21:45:47-07:00

## Review boundary

Review the sealed R143 proposal before any authorization or live application.
The live tests must remain the rejected R139 head. Do not edit any workspace
file. Any executable adversarial check must occur only in a new disposable
`/tmp` tree, use copied active production, and remain offline and hardware-free.

The proposed patch may reopen exactly:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

Everything else remains frozen, including production, upper tests, wrappers,
support, RANGE artifacts, snapshots, manifests, prior evidence, Wine/prefix,
USB/device/sysfs, build/staging, firmware, presets/effects, UC/Voice FX, and
live hardware.

## Required identity checks

1. Verify `task-9-r143-adjudication.sha256` completely from its own directory.
2. Verify live `task-9-r139-test-head.sha256` from the project root.
3. Verify the R143 patch SHA-256 is
   `bf02b6dc45849612ceb3929c93189f757ad25f45e8784c56134bb34fa5f5b82b`,
   touches exactly the two named test paths, and dry-runs at `-p1` from live.
4. Verify disposable application produces candidate SHA-256 values
   `048243af...b4f32` and `e1087e04...a0cb9c` byte-for-byte.
5. Confirm live and disposable production are bound to active R138
   `unixlib.c` SHA-256 `ba3172e...d53051`; adjudicate the pre-edit
   `ff9bea...` snapshot distinction rather than treating it as a second head.

## Required correctness review

Review R142's complete three-scope matrix and all preservation assertions, then
answer these successor-specific questions:

1. Does the non-success sentinel make every exact positive prove that
   production itself writes `USBD_STATUS_SUCCESS`?
2. Does the `api_calls` tail field have ABI-identical layout in contract and
   fake, survive reset semantics, and participate in the complete snapshot?
3. Does every externally defined fake `libusb_*` entry increment the witness
   as its first operation, including early-return and side-effect-free calls?
4. Can production perform any fake-boundary libusb action on exact success or
   scope rejection without changing a snapshotted value?
5. Do the eleven counted mutants genuinely compile, execute copied production
   through the fake boundary, and fail for feature assertions rather than
   harness behavior? Treat the initial exit-2 draft as excluded evidence.
6. Does the new global witness disturb retained paths, hide a different
   backend call, introduce an ABI mismatch, or create another plausible false
   green?

## Verdict format

Return `PASS` only if there is no Critical, Important, or material Minor
finding. Otherwise return `REQUEST CHANGES` with severity, exact path/line or
artifact evidence, and—where safely possible—an executable counterexample.
State exactly which artifacts and commands were inspected. Do not rely on a
source scan or a nonzero harness exit alone as feature evidence.
