# WineUSB multi-interface handles v1 manifest

## Current state

CP19 is complete. The development source and artifact remain offline and are
not selected by the Wine sandbox harness. No device, Wine prefix, transient
service, or host USB node was opened during this checkpoint.

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

## Gate

CP20 must independently extract, apply all six patches with fuzz zero, build,
test, and byte-compare two clean trees. Do not stage this development output.
Only a reproduced triplet may advance to a new selector, disposable clone,
USB-hidden driver-load, and bounded live diagnostic. Keep firmware, Voice FX,
interface claims/detaches, alternate-setting changes, and the protected prefix
out of scope; stop at 10% battery or lower.
