# WineUSB multi-interface handles v1 manifest

## Current state

CP21 is complete. The exact CP20 reproducible triplet is staged and selected by
the Wine sandbox harness. One fresh disposable clone passed a USB-hidden
driver-load, then one authorized live diagnostic directly validated complete
interface-list handle population and the fail-closed null-buffer guard. The
device did not synchronize.

## Pinned base and patch order

Apply the following inputs in order to the Wine 11.15 archive:

    5046f36dae210b198ea69792774d4401feed975d465eca6c251c9394400ec272  wine-11.15.tar.xz
    9e1c3b88a428e3bdd245ee5cdda9dfa423e77ad4abe08c7423bf14dceb073e91  re/wine-11.15-wineusb-usbdi-v1.patch
    ad260f9ab4a1bc138d8ee3fdd7ec3157e0caf8d6a67b490be4bd815092fa5e64  re/wine-11.15-wineusb-urb-observe-v2.patch
    461f68de736ddba876cfaa4d0e385c8eaa0002bd22df05932987ad3f4fe7fe8f  re/wine-11.15-wineusb-class-interface-range-v2.patch
    ce4507d1b789e87195965b71e88c76d02a7de5ab504b52d41e1c431c560d949d  re/wine-11.15-wineusb-pipe-observe-v3.patch
    f7fab610716f7a0cc2349cffe4f3a3edf45ada1a4527c451c7a0c71f718facde  re/wine-11.15-wineusb-multi-interface-handles-v1.patch

Every patch requires `patch --batch --forward --fuzz=0 -p1`.

## Behavior and safety contract

The hardware-free contract uses the real Wine Unix call table with the pinned
fake libusb ABI. It proves that:

- pipes on later variable-length interface records receive stable, fully
  initialized handles;
- a malformed later record rejects the entire request before an earlier pipe
  is partially mutated;
- SELECT_CONFIGURATION performs no libusb allocation, submission, or
  clear-halt action; and
- a nonzero transfer with a null mapped buffer fails before libusb allocation
  or submission.

Contract hashes:

    4e7145fd1416b898de2a6a3905b104779305eb6108fdf02be4c33c65651ab433  tests/wineusb_multi_interface_handles_contract.c
    ec591959e9c76c3751625735df0061c29ac2ed2eebfafdfb20b271e4bd601117  tests/wineusb_multi_interface_handles_contract.sh

The valid behavior RED, telemetry RED, null-buffer safety RED, and final GREEN
outputs are retained under `logs/`.

## Development output only

The contained incremental build under
`.io24-build/wineusb-multi-interface-handles-v1/dev-build/` produced:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    96f5a63a76d5f0e9a73425717d81e17d1fd6883c7a909508e703897a22fe4039  wineusb.so

Only `wineusb.so` changed from CP17/CP18. Its size is 102,600 bytes and build
ID is `be6c3c09298d93e060effd9433dfc5c955a54bfa`. Its 37-name undefined
dynamic-symbol set is unchanged.

## CP20 reproducible clean outputs

Build A and B independently reproduce the development triplet exactly:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    96f5a63a76d5f0e9a73425717d81e17d1fd6883c7a909508e703897a22fe4039  wineusb.so

Both full 12,445-file source trees, configure output, build output, generated
Makefile, compile database, artifacts, build IDs, and pointer-normalized
contract output compare identical. Each side independently passes the current
five-contract suite with hardware and networking hidden.

## CP21 staged and live result

The active harness and frozen CP21 snapshot have SHA-256:

    908d9c900c0f4e9bb0cb2c2b68b2d1af478a6295eb4019de2dc321f65ecc02f5  tests/uc_wine_sandbox.sh
    908d9c900c0f4e9bb0cb2c2b68b2d1af478a6295eb4019de2dc321f65ecc02f5  CP21_HARNESS_SNAPSHOT.sh

Its real-selector contract has SHA-256:

    88efc2f8b56724f4a36e82de97715d26d988960ea86d8ae92e62082b2286fba9  tests/uc_wine_sandbox_multi_interface_handles_v1_selector_contract.sh

A fresh clone passed one USB-hidden driver-load. Two live preflights and one
non-opening audit then guarded exactly one live-read. In two device cycles the
candidate populated endpoint `0x02` as handle `0x202` and endpoint `0x82` as
handle `0x282`. All eight 512-byte bulk-IN URBs decoded through `0x282`, but
Wine's MDL mapper returned null; all eight were rejected before allocation or
submission.

The 237,649-byte USB capture contains 146 control-IN submissions and 146
successful completions, with no bulk, interrupt, or control-OUT bus transfer.
Six clear-halt ioctls failed `EBUSY` because interface 4 was not claimed. No
claim, detach, alternate-setting change, configuration change, reset, or
disconnect occurred. The service reached `RUNNING`, but no UCNET `DA` arrived
and no `synchronize.json` exists.

## Gate

Stop at CP21. The live authorization used for this bounded diagnostic is
consumed, and the requested CP19-CP21 checkpoint sequence is complete. The
next safe work is offline, test-first investigation of
`MmMapLockedPagesSpecifyCache`, `KeInsertQueueDpc`, and the interface/alternate
selection mismatch. Any new live run needs a fresh preflight and explicit
continuation. Keep firmware, full Universal Control, Voice FX, interface
claims/detaches, alternate-setting changes, and the protected prefix out of
scope; stop at 10% battery or lower.
