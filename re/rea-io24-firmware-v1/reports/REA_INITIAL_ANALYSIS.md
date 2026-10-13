# io24 firmware: initial REA analysis

Date: 2026-10-13

## Scope and safety

This case is limited to static, offline inspection of the Revelator io24 firmware package already present in Universal Control 4.7.2. The source DLL and extracted vendor package were read only. No USB device was opened, claimed, detached, reset, or written; no DFU or firmware operation was attempted; extracted content was not executed.

## Evidence

- Source: `Documents/Universal Control/hwaccess/dspusbdevice.dll`
- Source DLL SHA-256: `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`
- Preserved package: `originals/io24-uc472-vendor-package.bin`
- Package size: 1,222,292 bytes (`0x12a694`)
- Package SHA-256: `790f668608448b7c9f244c360ad72e3c51f71b4e8a3d828eab0e08cd03b35de1`

The package was produced by the project's existing offline `io24_firmware.py` extractor, not read from a connected device.

## Vendor-package structure already verified

- Firmware version: 1.28
- Protected length: `0x12a68d`
- Metadata offset: `0x205e0`
- Metadata size: 192 bytes
- Format version: 1
- Target: `0x194f0407`
- Image ID: 1
- Stored CRC32: `0xed65737c`

## REA result

REA 6.4.0 invoked its pinned Unblob 26.6.4 integration against the preserved package. REA evidence ID:

`ev_6fe089d014a8dcdf2c909265f713558af661c5493945768aa5c905d15975e959`

Unblob identified the whole package as `TTComp archive data, binary, 4K dictionary` (`application/x-compress-ttcomp`). It emitted no chunks or child files (`published_bytes: 0`). Therefore REA/Unblob recognizes the compression family but does not unpack this vendor container by itself.

This is a useful format result, not evidence that the image is empty or encrypted. In particular, readable strings and the CRC table described below show that at least part of the image is directly visible. Treat the whole-file TTComp classification as a format candidate rather than a confirmed description of every byte.

## REA region inspection

REA's pinned Binwalk 3.1.0 integration completed a one-thread, read-only signature scan. REA evidence ID:

`ev_76b6b46772ab7dca7e740a7d0e4a2e19ea2a13401b99d6d9fc5087d826861ced`

It reported one region:

- Offset: 426,976 (`0x683e0`)
- Reported size: 16 bytes
- Signature: `crc32`
- Description: `CRC32 polynomial table, little endian`
- Size basis: provider-reported; validation unknown

The bytes at `0x683e0` begin `00 00 00 00 96 30 07 77 2c 61 0e ee ba 51 09 99`, matching the start of a little-endian CRC32 table. Immediately preceding it are readable strings including `WQTEvt`, `WQTRun`, and `WQTQue`. This supports the conclusion that the vendor image contains directly inspectable program data despite Unblob's whole-file TTComp magic match.

The normalized REA result is preserved as `reports/rea-binwalk-normalized.json`.

## Binwalk build provenance

- Upstream: ReFirmLabs Binwalk tag `v3.1.0`, commit `4fdab3d464d97b68e0af9088df3f9e2e1545b21c`
- Container image ID: `sha256:ed3b10030e2dbfddf24d74bd4a6638e0f852626f61d0c72b24f91ae6210aed4e`
- REA launcher SHA-256: `e2a62476e80ea834e0c2120044163f45566ea4d020f0610247e5802809ae9c2b`

Ubuntu 24.04's Rust 1.75 required two build-compatibility adjustments, preserved under `tools/`: the tag's declared Plotters 0.3.6 was selected instead of lockfile-selected 0.3.7, and three uses of the later-stabilized `std::path::absolute` were replaced by the equivalent absolute-or-current-directory join. No signature or scanning logic was changed.

## Reproduction

Build the pinned scanner once:

```bash
git clone --depth 1 --branch v3.1.0 \
  https://github.com/ReFirmLabs/binwalk.git /tmp/io24-rea-binwalk-v3.1.0
git -C /tmp/io24-rea-binwalk-v3.1.0 apply \
  "$PWD/re/rea-io24-firmware-v1/tools/binwalk-3.1.0-rust175.patch"
docker build \
  -f "$PWD/re/rea-io24-firmware-v1/tools/Dockerfile.rea-scan" \
  -t io24-rea-binwalk:3.1.0 \
  /tmp/io24-rea-binwalk-v3.1.0
```

Run REA extraction and inspection:

```bash
REA_UNBLOB_COMMAND=/home/ajuntanaga/.local/bin/unblob \
  npx -y rea-agents@6.4.0 extract-firmware \
  "$PWD/re/rea-io24-firmware-v1/originals/io24-uc472-vendor-package.bin" \
  "$PWD/re/rea-io24-firmware-v1/extracted/rea-unblob-v1" \
  --max-depth 3 --format json
```

```bash
REA_BINWALK_COMMAND="$PWD/re/rea-io24-firmware-v1/tools/binwalk-3.1.0-docker" \
  npx -y rea-agents@6.4.0 inspect-firmware-regions \
  "$PWD/re/rea-io24-firmware-v1/originals/io24-uc472-vendor-package.bin" \
  --format json --full-output
```
