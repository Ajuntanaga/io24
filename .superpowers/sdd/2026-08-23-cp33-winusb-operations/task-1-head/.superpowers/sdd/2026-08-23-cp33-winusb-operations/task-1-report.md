# CP33 Task 1 report: hardware-free RED boundary

## Summary

Task 1 is complete. The sealed CP32 `patch-check-source` was verified before
the fresh CP33 root was created. Both CP33 production clones were copied from
that immutable source and remain byte-for-byte equal to it. Five offline
contracts compile the actual relevant production translation units with
`cc -std=c11 -Wall -Wextra -Werror` (with narrowly required Wine-header/source
warning suppressions), use fresh temporary build directories, validate their
inputs, and return genuine missing-feature RED rather than harness failure.
No production source was edited. No Wine, prefix, USB, sysfs, driver, device,
Universal Control, Voice FX, selector, or CP24 action was used.

## Exact files and directories created

- `.io24-build/winusb-api-v1/dev-source/` (fresh CP32 clone)
- `.io24-build/winusb-api-v1/patch-check-source/` (fresh CP32 clone)
- `re/winusb-api-v1/checkpoints/`
- `re/winusb-api-v1/logs/cp32-seal-verify.log`
- `re/winusb-api-v1/logs/dspusbdevice-winusb-callsite.log`
- `re/winusb-api-v1/logs/cp33-red.log`
- `re/winusb-api-v1/logs/task-01-red.sha256`
- `tests/winusb_user_api_contract.c`
- `tests/winusb_user_api_contract.sh`
- `tests/winusb_function_io_contract.c`
- `tests/winusb_function_io_contract.sh`
- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_contract.sh`
- `tests/wineusb_winusb_urb_fake_libusb.c`
- `tests/winusb_overlapped_cancel_contract.c`
- `tests/winusb_overlapped_cancel_contract.sh`
- `tests/io24_winusb_vendor_profile_contract.py`
- `.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-1-report.md`

## CP32 seal

Command: `(cd re/winusb-function-binding-v1/checkpoints && sha256sum --check CP32_SHA256SUMS)`.
Result: exit 0; exactly 72 output lines; exactly 72 lines ended in `OK`; no
failed or missing checksum. Full output is retained in
`re/winusb-api-v1/logs/cp32-seal-verify.log`.

The pre-creation guard `test ! -e .io24-build/winusb-api-v1` passed. The root
was created only after that check and the 72-entry seal verification.

## Vendor hash, imports, and call sites

- SHA-256: `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`.
- The PE imports exactly the expected 14 names: `WinUsb_AbortPipe`,
  `WinUsb_ControlTransfer`, `WinUsb_Free`, `WinUsb_GetAssociatedInterface`,
  `WinUsb_GetDescriptor`, `WinUsb_GetOverlappedResult`,
  `WinUsb_GetPipePolicy`, `WinUsb_Initialize`,
  `WinUsb_QueryDeviceInformation`, `WinUsb_ReadPipe`, `WinUsb_ResetPipe`,
  `WinUsb_SetCurrentAlternateSetting`, `WinUsb_SetPipePolicy`, and
  `WinUsb_WritePipe`.
- Static disassembly retained the policy-get site beginning at `0x180084d50`
  and initializer site beginning at `0x180095e20`.
- The frozen policy fixture contains the required nine `(policy,length)`
  pairs grouped as `all`, `out`, `in`, and `get`.
- Untouched CP32 has only 1/14 callable definitions, which is the intended
  vendor-profile RED.

Only `sha256sum` and `objdump` read the vendor DLL for the retained evidence.

## Command-by-command RED results

All commands used absolute source/build/include/vendor paths. Exact commands
and output are retained in `re/winusb-api-v1/logs/cp33-red.log`.

1. `tests/winusb_user_api_contract.sh WINE_SOURCE_ROOT` returned exactly 1.
   Intended RED: public prototypes, definitions, and callable spec exports are
   only 1/14; the other thirteen imported CP33 operations are absent.
2. `tests/winusb_function_io_contract.sh WINE_SOURCE_ROOT` returned exactly 1.
   Intended RED: create and device-control still dispatch to
   `driver_unsupported`; session, select-interface, and control handling are
   absent. The guarded MI05 fixture encodes alternate 0 with zero endpoints
   and alternate 1 with bulk `0x81`/`0x01`, maximum packet size 512.
3. `tests/wineusb_winusb_urb_contract.sh WINE_SOURCE_ROOT WINE_BUILD_ROOT LIBUSB_INCLUDE`
   returned exactly 1. Intended RED: function claims, alternate selection,
   generic control, generation-aware pipes, and retained cancellation are
   absent; reset reports success after a backend clear-halt error.
4. `tests/winusb_overlapped_cancel_contract.sh WINE_SOURCE_ROOT WINE_BUILD_ROOT LIBUSB_INCLUDE`
   returned exactly 1. Intended RED: upper/lower cancel ownership is absent,
   abort cancels all queued transfers instead of one pipe, and removal
   completes pending IRPs without first obtaining physical cancellation.
5. `python3 tests/io24_winusb_vendor_profile_contract.py --wine-source WINE_SOURCE_ROOT --vendor-dll VENDOR_DLL`
   returned exactly 1. Intended RED: the vendor hash, exact 14-import set, two
   call-site ranges, and nine-pair policy fixture are valid, but untouched CP32
   exposes only 1/14 callable implementations.

Every shell wrapper returned 2 with no arguments; the Python wrapper's parser
also returned 2 with missing required arguments. All wrappers validate every
required source, contract, header, build, and vendor input before compilation.

## Harness integrity

The retained final run had no syntax error, missing fake/input, compiler or
linker failure, segmentation fault, crash, or unrelated retained-test failure.
The lower two wrappers compile `dlls/wineusb.sys/unixlib.c` from the untouched
CP33 dev clone and link it against the Task 1 fake libusb plus only the sealed
CP32 `dlls/ntdll/ntdll.so`. The fake exposes accounting for claim, release,
detach, auto-detach, set-configuration, set-alternate, control, bulk,
interrupt, cancel, clear-halt, transfer-free, and close. All four C contracts
use the common guard/accounting convention.

## Production-source equality

Both final commands produced no output and exited 0:

- `diff -qr --no-dereference .io24-build/winusb-function-binding-v1/patch-check-source .io24-build/winusb-api-v1/dev-source`
- `diff -qr --no-dereference .io24-build/winusb-function-binding-v1/patch-check-source .io24-build/winusb-api-v1/patch-check-source`

Thus both production clones still equal CP32 byte-for-byte, including symlink
handling, after all Task 1 work.

## Checkpoint and verification

Checkpoint: `re/winusb-api-v1/logs/task-01-red.sha256`.

It is nonempty with 11 SHA-256 entries: the ten Task 1 contract/fake files and
`re/winusb-api-v1/logs/cp33-red.log`. Running
`sha256sum --check re/winusb-api-v1/logs/task-01-red.sha256` from the project
root returned exit 0 with all 11 entries `OK`.

## Self-review

- Ownership review: only the two fresh clones, ten assigned contract/fake
  files, four assigned logs/hashes, required evidence directories, and this
  report were created; no plan, spec, ledger, handoff, retained evidence, or
  production file was edited.
- Safety review: all evidence is static or synthetic and hardware-free.
- RED review: every accepted failure is a missing CP33 behavior; initial
  harness-only diagnostics were corrected before the retained run.
- Reproducibility review: all wrappers use fresh temporary roots, quoted
  absolute inputs, strict shell options, strict compiler warnings, and stable
  exit codes.

## Concerns

No Task 1 blocker remains. These are deliberately RED contracts: they do not
claim CP33 implementation, GREEN behavior, build reproducibility, Wine runtime,
or physical USB compatibility.
