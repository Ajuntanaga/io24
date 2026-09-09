# Task 9 R146 preauthorization review request

Timestamp: 2026-08-25T23:12:42-07:00

## Review boundary

Review the sealed R146 proposal before any authorization or live application.
Live tests must remain the rejected R139 head. Do not edit any workspace file.
Any executable adversarial check must use a new disposable `/tmp` tree,
copied active production, and fake libusb only.

The proposed patch may reopen exactly:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

Everything else remains frozen, including production, upper tests, support,
wrappers, RANGE artifacts, snapshots, manifests, prior evidence, Wine/prefix,
USB/device/sysfs, build/staging, firmware, presets/effects, UC/Voice FX, and
live hardware.

## Required identity checks

1. Verify `task-9-r146-adjudication.sha256` completely from its directory.
2. Verify live `task-9-r139-test-head.sha256` from the project root and the
   unchanged live fake SHA-256 `c48fbe4c...52acb`.
3. Verify the R146 patch SHA-256 is
   `ec62d2a8d3ca3d0cb65b20ba52f466af277281efc858997bf5e313728dec214f`,
   touches only the two named paths, and dry-runs from live.
4. Verify disposable application produces candidate hashes
   `68082796...b4fc5` and `399b21b5...340fc`.
5. Bind live and disposable production to active R138
   `ba3172e...d53051`; keep the named pre-edit `ff9bea...` snapshot distinct.

## Required correctness and cybersecurity review

Review the complete inherited R143-R145 matrix and answer:

1. Are count and record layouts ABI-identical, including alignment and
   `uintptr_t` fields, and does reset cover all added state?
2. Does every exported fake `libusb_*` entry keep the global witness as its
   first executable operation, with the three dedicated increments immediately
   next?
3. Do the ordinal assertions prove an uninterrupted get-device,
   get-active-config, free-config order relative to the captured global count?
4. Is get-device bound to `f->device.handle`, active-config to the returned
   device, and free-config to the non-null returned descriptor?
5. Are only individually verified journal fields copied into the expected
   record before the complete snapshot comparison?
6. Can a same-count wrong handle, wrong device, wrong descriptor, reordered
   free, extra call, or omitted validator still pass?
7. Do all generic, malformed, null, exact-success, and scope-rejection paths
   retain their complete zero-backend or unchanged-backend guarantees?
8. Do caller storage, lengths, status, pending state, allocation/submission,
   and `DriverContext` assertions remain complete?
9. Did all nineteen mutants compile and execute copied production through fake
   libusb, fail for feature assertions, and restore production after each?
10. Does the two-file delta add any secret, dependency, network, device,
    prefix, staging, firmware, preset/effect, or other security surface?

## Verdict format

Return `PASS` only if there is no Critical, Important, or material Minor
finding. Otherwise return `REQUEST CHANGES` with severity, exact
path/line/artifact evidence, and an executable counterexample where safely
possible. State the artifacts and commands inspected. Do not count a source
scan, compiler failure, harness exit 2, or unexecuted exit 1 as feature
evidence.

