# Checkpoint 0 — offline inputs and safety boundary

Captured at `2026-08-19T19:01:43-07:00` before reconstructing the WineUSB
observation-v2 build.

## Safety state

- sysfs matches for `194f:0422`: **0**;
- no Wine, wineserver, Xvfb, Universal Control, or io24 service process was
  observed;
- protected prefix `/home/ajuntanaga/.wine-io24` retained mtime
  `2026-08-12 00:31:35.825186221 -0700`, inode 3427833;
- no USB node will be exposed during build or offline testing;
- no host package installation is authorized or required.

## Pinned inputs

```text
5046f36dae210b198ea69792774d4401feed975d465eca6c251c9394400ec272  wine-11.15.tar.xz
d4677b0d5b547c9a0591f70d5f1ec7d4dcb4fe2473f24dcc5b610cbaca551c15  wine-11.15.tar.xz.sign
9e1c3b88a428e3bdd245ee5cdda9dfa423e77ad4abe08c7423bf14dceb073e91  re/wine-11.15-wineusb-usbdi-v1.patch
ad260f9ab4a1bc138d8ee3fdd7ec3157e0caf8d6a67b490be4bd815092fa5e64  re/wine-11.15-wineusb-urb-observe-v2.patch
58a4564f080002d5b8455e26c65516cacbff1f24bf902c07058702aef4b86d3d  tests/wineusb_usbdi_contract.c
f3f05ac1f04abde48f3357cfaf7b7b1f8cf79e9408c8907d3a42018d4f6f7fa0  tests/wineusb_usbdi_contract.sh
54aa7b599b32037056725d58d79ada9a3757e35695972933790f6555774bca85  tests/uc_wine_sandbox.sh
```

The retained source archive was previously verified by the isolated Wine
release-key fingerprint `DA23579A74D4AD9AF9D3F945CEFAC8EAAF17519D`.

## Build-only package inputs

The host has the matching runtime `libusb-1.0-0` version
`1.0.29-2build1`, but does not have `m4`, `flex`, `bison`,
`libusb-1.0-0-dev`, or the libusb development header installed. The prior
known-good build used these exact disposable packages:

```text
1890e37e38fd64bc10630e508f4a013a76bddbe05be2ed89e68df28463712b55  m4 1.4.21-1
622d3959e0424ca276a01946a44a30c327d4bd6963f96b070b94e9b80b541bb8  flex 2.6.4-8.2build2
7a9d4ce17f45d687ed38758bdc79efc8b5c7d79987dc5298de25961691b6bd09  bison 3.8.2+dfsg-1build4
d13f2b678577d0b4bd1cc0197f850c5da4a114a81ec3ec4f51663585d0fc28a8  libusb-1.0-0-dev 1.0.29-2build1
```

They were not present in the local apt or io24 caches at this checkpoint.
They may be downloaded into `.io24-build/wineusb-observe-v2/packages/` and
extracted locally, but must not be installed on the host. A hash mismatch,
package-version mismatch, or dependency outside this pinned set is a hard
pause.

## Next checkpoint

Checkpoint 1 is reached only when a clean archive extraction accepts USB-DI
v1 and observation v2 with zero fuzz, the pinned packages are locally
extracted, Wine configures out-of-tree under resource limits, and all three
WineUSB artifacts compile. No artifact may be staged before Checkpoint 2's
USB-hidden tests pass.
