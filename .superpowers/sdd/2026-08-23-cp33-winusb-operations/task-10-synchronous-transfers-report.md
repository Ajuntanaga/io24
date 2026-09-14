# Task 10 synchronous transfers — 2026-09-11

Task 10 is complete locally at the offline source/test boundary.

The public WinUSB DLL now exposes synchronous `WinUsb_ReadPipe`,
`WinUsb_WritePipe`, `WinUsb_AbortPipe`, and `WinUsb_ResetPipe`. The upper
function driver validates the current bulk endpoint and its direction and
policy, forwards the original direct-I/O IRP and MDL, tracks per-interface and
per-pipe outstanding work, maps lower status, rejects a busy reset, and retires
its two allocations exactly once. The lower driver aborts only matching
bulk/interrupt requests and propagates `libusb_clear_halt()` failure through
both NT and USBD status.

The accepted test-first REDs were:

- public and upper `--sync-pipes` were unsupported/missing before their new
  contract modes and implementations;
- truthful reset failed two lower assertions because a clear-halt error was
  reported as success;
- pipe-specific abort canceled three queued requests instead of the one
  matching transfer.

Current focused results:

```
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --sync-pipes
CP33 function executed mode=--sync-pipes dispatches=28 mode-ioctls=25 last-ioctl=0x222022 last-status=0xffffffffc00000b5 failures=0

tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --sync-pipes
CP33 lower executed mode=--sync-pipes completions=0 failures=0

tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --sync-pipes
CP33 public executed mode=--sync-pipes target-mask=0x2e85 present-mask=0x3fdf missing-mask=0 fake-events=43 submits=11 releases=1 completions=0 failures=0

tests/winusb_overlapped_cancel_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --lower
CP33 cancel executed mode=--lower cancels=1 completions=0 failures=0

tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --red
CP33 lower executed mode=--red completions=3 failures=0

git diff --check
exit 0
```

No Wine process, prefix, USB device, firmware, staging, network, or system
operation was used. Task 11 is next: replace the lower raw transfer pointer
with retained transfer identity and one explicit release.
