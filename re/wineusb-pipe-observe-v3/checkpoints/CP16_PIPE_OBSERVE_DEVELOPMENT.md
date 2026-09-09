# CP16 — observation-only pipe diagnostics development build

Reached at 2026-08-21T05:18:52-07:00. Work continued immediately toward
CP17 under the user's request for three checkpoints. Battery was discharging
at 58%; the mandatory pause threshold remains 10%.

## Outcome

PASS, device-free development only. WineUSB now has stable
`IO24_PIPE_OBSERVE` key/value markers that answer four questions left open by
CP15:

1. Which variable-length interfaces and pipes arrive in
   `URB_FUNCTION_SELECT_CONFIGURATION`, before and after the Unix call.
2. Which endpoint and type each generated pipe handle encodes, while retaining
   the existing first-interface-only backend scope.
3. Whether a bulk/interrupt MDL maps to a usable buffer, or whether the request
   uses a direct buffer.
4. Which decoded route reaches libusb and what immediate result libusb returns
   for clear-halt and transfer submission.

No buffer contents, device strings, or other payload data are logged. IRP and
handle values are included only as within-run correlation fields.

## TDD evidence

The behavior and source/binary/runtime contract was written before production
changes. After a test-fixture include and runtime-debug initialization issue
were corrected in the test itself, the valid RED run passed all inherited
behavior checks and exited 1 specifically because
`IO24_PIPE_OBSERVE event=clear_halt` was absent. That durable output is:

    ../logs/contract-red.txt

The GREEN contract calls the real built WineUSB Unix call table against a
device-free fake libusb SONAME. It proves unchanged behavior for:

- failed `libusb_clear_halt()` still returning `STATUS_SUCCESS`;
- bulk and interrupt pipe-handle decoding, submission, and `STATUS_PENDING`;
- invalid pipe type returning `USBD_STATUS_INVALID_PIPE_HANDLE` without a
  submission; and
- SELECT_CONFIGURATION still assigning handles only within the first embedded
  interface presented to the Unix backend.

It also requires every Windows-side and Unix-side marker in source and compiled
binaries and rejects actionable claim, detach, alternate-setting,
set-configuration, or control-transfer calls. The contained GREEN run exited
zero in 0.40 seconds and peaked at 7,408 KiB RSS:

    ../logs/contract-green-contained.txt
    ../logs/contract-green-resource.txt

The retained exact-RANGE fake-libusb/source/binary contract, USB-DI v1
contract, and CP15 usbmon evidence contract all pass in the same hardware-
hidden, networkless containment. Those results are in:

    ../logs/regression-contracts-contained.txt
    ../logs/regression-contracts-resource.txt

## Patch and development build

The observation patch layers on top of exact captured RANGE v2:

    ce4507d1b789e87195965b71e88c76d02a7de5ab504b52d41e1c431c560d949d  re/wine-11.15-wineusb-pipe-observe-v3.patch

It applies with `--batch --forward --fuzz=0`. The resulting 12,445-file tree
matches the development source completely, contains zero symlinks and zero
`.rej`/`.orig` files, and differs from the sealed RANGE-v2 source only at:

    dlls/wineusb.sys/wineusb.c
    dlls/wineusb.sys/unixlib.c

The incremental development build ran with hardware and networking hidden,
all capabilities dropped, a 2 GiB address-space ceiling, CPU and wall limits,
idle I/O priority, and `make -j1`. It exited zero without a warning in either
modified translation unit. The outputs are:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    90d060571d9f8a56aea8d91485802fe500920f741fb5787543a8c141ae104eb9  wineusb.so

The fake PE remains byte-identical because the executable code lives in the
builtin and Unix library. Their development build IDs are respectively
`0857e44f13501e673ba64c795a297fe8a757feb9` and
`8a975849185b8c68b22e8f1d136ec8e58c9814be`. Neither binary adds an undefined
dynamic symbol relative to RANGE v2.

## Safety and next gate

No staged file, harness selector, sandbox, Wine prefix, USB node, driver, or
device was touched at CP16. This patch adds observations only; existing return
values and calls are retained. It does not add claims, detach, configuration
or alternate-setting changes, class OUT, synchronous USB writes, or firmware
behavior.

The user has now authorized connected-device testing. That authorization is
reserved for CP18 after CP17 produces two independent byte-identical builds
and CP18 first passes staging, selector, and USB-hidden driver-load gates. The
protected `.wine-io24` prefix remains out of scope. Pause safely if battery is
10% or lower.

