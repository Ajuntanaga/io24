# CP33 Task 5 completion report

## Outcome

Task 5 and Gate 1 are complete. Public WinUSB handle ownership now uses
registry-validated opaque tokens, bounded record lifetime, one final RELEASE,
cached device/configuration descriptor reads, and cached speed queries.

Independent review passed with no Critical, Important, or Minor findings after
closing an unbounded retired-record lifetime issue and a cross-root token-proof
gap.

## Final bounded state

```text
dlls/winusb/main.c          8f4144b2f540f05c16a53bf4f49f1ea29455e30effb2589818ea13a3cc64d753
dlls/winusb/winusb_private.h 4be97b07b4f091619a9c5c86b42a33af31976ffbaf61c7576d42c0a15626a1c0
tests/winusb_user_api_contract.c 7547c6f2292c3a8650bb18b0610959eee30927418e1d6b279a5bf6f6e8751fca
```

All eight final offline gates exit zero. All nine final-head mutations exit
feature 1. The frozen pre-fix head remains a genuine 33-failure RED.

Gate seal `re/winusb-api-v1/logs/gate-1-handle-metadata.sha256` is
`e1d164ec9197be4385cc4d0a8279cf7e906d1972379390a6ca8fb3567f670122`,
contains exactly 35 unique entries, excludes itself, and verifies 35/35.

## Carry

R71 remains mandatory for Task 7: use an associated handle in an actual
alternate-setting request and prove lower `interface_index` equals public
`AssociatedInterfaceIndex + 1`; swapping internal indices 1 and 2 must fail.

No Wine, contained build, full matrix, prefix, device/live USB, install, or
physical action was performed.
