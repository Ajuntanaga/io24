# Wine 11.15 wineusb USBDI V1 overlay

Built and validated offline on 2026-08-18 PDT. This is a disposable diagnostic
overlay, not an installed Wine replacement. One explicitly authorized,
contained live-device result is recorded in `../IO24_HANDOFF.md`; it did not
reach UCNET synchronization.

## Source and patch

- Upstream source: `wine-11.15.tar.xz`
- Source SHA-256:
  `5046f36dae210b198ea69792774d4401feed975d465eca6c251c9394400ec272`
- Detached-signature SHA-256:
  `d4677b0d5b547c9a0591f70d5f1ec7d4dcb4fe2473f24dcc5b610cbaca551c15`
- GPG signer fingerprint:
  `DA23579A74D4AD9AF9D3F945CEFAC8EAAF17519D`
- Patch: `../wine-11.15-wineusb-usbdi-v1.patch`
- Patch SHA-256:
  `9e1c3b88a428e3bdd245ee5cdda9dfa423e77ad4abe08c7423bf14dceb073e91`

The patch handles `IRP_MN_QUERY_INTERFACE` for
`GUID_USB_BUS_INTERFACE_USBDI`. It deliberately rejects versions 3 and 2 so
PaeDSPUSB falls back to the exact 0x48-byte V1 interface observed in its
disassembly. V1 exports the required callback table, takes the interface
reference before returning, and reports actual operating speed from
`libusb_get_device_speed`. The callbacks not used on the observed start path
return `STATUS_NOT_SUPPORTED` instead of fabricating data.

## Focused test

- `../../tests/wineusb_usbdi_contract.c`:
  `58a4564f080002d5b8455e26c65516cacbff1f24bf902c07058702aef4b86d3d`
- `../../tests/wineusb_usbdi_contract.sh`:
  `f3f05ac1f04abde48f3357cfaf7b7b1f8cf79e9408c8907d3a42018d4f6f7fa0`

The test was first observed red against pristine Wine 11.15 because the USBDI
helper did not exist. After applying the patch, it passed all rejection,
0x48-byte ABI, callback-table, reference, and guard-buffer checks. A fresh
post-build rerun also passed.

## Build containment and dependencies

The build used an out-of-tree directory under `/tmp`, `make -j1`, idle I/O
priority, nice level 15, a 2 GiB address-space limit, and a 900-second timeout.
It was configured as a 64-bit Wine builtin with USB enabled and MinGW disabled.
All three changed translation units and the complete `dlls/wineusb.sys/all`
target compiled and linked without warnings or errors from the patch.

No host package was installed. Four pinned Ubuntu packages were downloaded to
and extracted under `/tmp` only:

- `m4` 1.4.21-1:
  `1890e37e38fd64bc10630e508f4a013a76bddbe05be2ed89e68df28463712b55`
- `flex` 2.6.4-8.2build2:
  `622d3959e0424ca276a01946a44a30c327d4bd6963f96b070b94e9b80b541bb8`
- `bison` 3.8.2+dfsg-1build4:
  `7a9d4ce17f45d687ed38758bdc79efc8b5c7d79987dc5298de25961691b6bd09`
- `libusb-1.0-0-dev` 1.0.29-2build1:
  `d13f2b678577d0b4bd1cc0197f850c5da4a114a81ec3ec4f51663585d0fc28a8`

The host's matching `libusb-1.0-0` runtime is version 1.0.29-2build1.

## Staged artifacts

- `x86_64-windows/wineusb.sys` (fake PE):
  `b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e`
- `x86_64-unix/wineusb.sys.so` (Wine builtin):
  `f6e8bc0bb15b1d29e94ccb49a09ddb0ae801aaacbdace62d6144b176444fbb07`
- `x86_64-unix/wineusb.so` (libusb Unix library):
  `8d45157a7ba70479e95c27ec844601d83e5df85e34e73c7bfff36b4ab9df0b0e`

Because MinGW was unavailable, the fake PE and builtin must be used together
through `WINEDLLPATH`; the fake PE is not a standalone replacement for
`/opt/wine-staging/lib/wine/x86_64-windows/wineusb.sys`.

## USB-hidden overlay check

`tests/uc_wine_sandbox.sh driver-load` hash-pins and read-only binds all three
artifacts. On 2026-08-18 at 23:38 PDT, the USB-hidden gate passed in 17.537
seconds with 112.1 MiB peak memory and zero swap. The loader was forced to the
builtin `wineusb.sys`, initialized it successfully, and the existing registry,
NT DDI, SSE2, and PaeDSPUSB start/query gates all remained green. Bubblewrap
mounted a private empty `/sys` and `/dev` without `/dev/bus/usb`; no device I/O
was possible.

This offline run did not exercise `IRP_MN_QUERY_INTERFACE`, because no USB PDO
existed with hardware hidden. A subsequent, explicitly authorized patched
`live-read` advanced beyond that query into standard device-descriptor reads,
then stopped at the descriptor request/completion path without receiving a
UCNET `DA` announcement. See `../IO24_HANDOFF.md` for the bounded run, raw-log
hashes, and postflight evidence. Any repeat hardware read requires a new
explicit authorization.
