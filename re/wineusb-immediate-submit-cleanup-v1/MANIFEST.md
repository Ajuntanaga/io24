# WineUSB immediate-submit cleanup v1 manifest

## Current state

CP25 and CP26 are complete offline.  Immediate libusb submission rejection now
completes synchronously with failure, clears the IRP cancellation handle, sets
the URB failure status, and frees all transfer-owned allocations on the bulk,
GET_DESCRIPTOR, and vendor-control paths.  The adjacent invalid-pipe and
control-buffer-allocation failure paths also no longer retain freed cancellation
handles.

Nothing from this lineage is staged or selected by the Wine sandbox harness.
No Wine service, USB node, device interface, prefix, or network was exposed.

## Pinned base and patch order

Apply these inputs in order to the Wine 11.15 archive:

    5046f36dae210b198ea69792774d4401feed975d465eca6c251c9394400ec272  wine-11.15.tar.xz
    9e1c3b88a428e3bdd245ee5cdda9dfa423e77ad4abe08c7423bf14dceb073e91  re/wine-11.15-wineusb-usbdi-v1.patch
    ad260f9ab4a1bc138d8ee3fdd7ec3157e0caf8d6a67b490be4bd815092fa5e64  re/wine-11.15-wineusb-urb-observe-v2.patch
    461f68de736ddba876cfaa4d0e385c8eaa0002bd22df05932987ad3f4fe7fe8f  re/wine-11.15-wineusb-class-interface-range-v2.patch
    ce4507d1b789e87195965b71e88c76d02a7de5ab504b52d41e1c431c560d949d  re/wine-11.15-wineusb-pipe-observe-v3.patch
    f7fab610716f7a0cc2349cffe4f3a3edf45ada1a4527c451c7a0c71f718facde  re/wine-11.15-wineusb-multi-interface-handles-v1.patch
    081975cfffea75a2a6058836829ceb5c1508e8c52e8b98065ba9e9a153f7b876  re/wine-11.15-wineusb-immediate-submit-cleanup-v1.patch

Every patch requires `patch --batch --forward --fuzz=0 -p1`.

## Device-free behavior contract

The contract loads the real WineUSB Unix call table against the pinned fake
libusb SONAME.  It proves:

- bulk, GET_DESCRIPTOR, and vendor immediate-submit rejection returns
  `STATUS_UNSUCCESSFUL` with `USBD_STATUS_REQUEST_FAILED`;
- all three paths clear `DriverContext[0]`, leave no pending transfer, and free
  the transfer context and any control buffer;
- an invalid decoded pipe cannot leave a freed transfer as a cancellation
  handle; and
- real control-buffer allocation failure returns `STATUS_NO_MEMORY` without a
  stale cancellation handle or libusb submission.

Contract hashes:

    c84d9a5693949da36af8d1ed1329c04fa68b9beec3a8d7aad184eba398a3a352  tests/wineusb_immediate_submit_cleanup_contract.c
    ff2384e028fd2325eaaf61c69de613b42c084f8988a50be1205d2495176ce755  tests/wineusb_immediate_submit_cleanup_contract.sh

## Reproducible output

The development build and two clean builds independently produce:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    93a30fce04fc59fb034d9c88b6becd9931c56892cf97f5eca7f27db99aa68264  wineusb.so

The first two artifacts remain byte-identical to CP21.  Only `wineusb.so`
changes.  It is 98,448 bytes with build ID
`22434621eb75a3f3bbc8e6823b271df03908b14e`; its named undefined-symbol set and
three dynamic dependencies are unchanged from CP21.

Each clean side passes the immediate-submit cleanup, multi-interface handles,
pipe-observe, exact RANGE-v2, USB-DI v1, and CP15 evidence-analyzer contracts in
a network-, device-, USB-, and sysfs-hidden namespace.

## Gate

Stop at CP26 for this software lineage.  It is reproducible but not staged or
selected.  Interface-4 routing/ownership analysis remains separate.  Any
driver load, live read, claim, detach, alternate-setting or configuration
change, OUT transfer, firmware access, full Universal Control, Voice FX, or
protected-prefix access requires its own explicit authorization and fresh
preflight.  CP24's live authorization remains consumed.
