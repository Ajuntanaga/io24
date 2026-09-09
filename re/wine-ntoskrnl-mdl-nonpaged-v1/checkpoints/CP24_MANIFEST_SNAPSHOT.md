# CP24 staged-live manifest

## State

CP24 is complete at the consumed-live-read boundary. The exact CP23 kernel
pair and CP21 WineUSB triplet are staged and selected by the frozen CP24
harness. The live diagnostic was run once and was not retried. It did not
synchronize.

## Selected kernel

    259d80fc4c68df9db3202f6aee7eb42e36bed11593480527f044decf84029c2e  x86_64-windows/ntoskrnl.exe
    3c338b34e2f33f3d50772cbea3bd3654bbe9ccaf235b5c16081ed8e9cebd6026  x86_64-unix/ntoskrnl.exe.so

## Selected WineUSB

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  x86_64-unix/wineusb.sys.so
    96f5a63a76d5f0e9a73425717d81e17d1fd6883c7a909508e703897a22fe4039  x86_64-unix/wineusb.so

## Selection and runtime

    720a780bb9bde1c24064ad848b86472dde66e19a230920402ab2d589c765304a  CP24_HARNESS_SNAPSHOT.sh
    06386e6ee382c32469b8096cc68c5cd4dd3ed71f7f5f52a10d2d514e293b4461  uc_wine_sandbox_ntoskrnl_mdl_nonpaged_v1_selector_contract.sh
    7ac414022d500e332be0e4196a9183d376791829fe51ce841f856273d9b96a0a  uc_wine_sandbox_multi_interface_handles_v1_selector_contract.sh
    ab998beda7e6544cf56d574b66212ee3129d17e4f7b97cf3378582d5ef105da8  live-service-usb.txt
    2717a3f6cabfaf65acccbc03a6b8b1e540620cce82e9ecc0b7dbd0b688591807  runtime/SHA256SUMS

The runtime manifest contains 110 entries. The final analysis contract
recomputes the raw counts and passes.

## Boundary

The next safe checkpoint is offline and test-first. It should reproduce and
repair immediate `libusb_submit_transfer()` failure cleanup/status handling,
audit the descriptor and vendor-control sibling paths, and keep interface
routing as a separate question. No future live run is authorized. Firmware,
Voice FX, full Universal Control, class-OUT, protected-prefix access,
claim/detach, alternate-setting changes, and configuration changes remain
forbidden without new explicit authorization.
