# Task 9 R143 isolated proof

Timestamp: 2026-08-25T21:45:47-07:00

All candidate test changes and all production mutations occurred in disposable
`/tmp` copies. The live R139 tests and active R138 production were not edited.

## Candidate baseline

The proposed two-file candidate compiled and executed active R138
`unixlib.c` through the existing fake-libusb boundary at exit 0 with
`failures=0`. A final clean replay after restoring every production mutant
also exited 0 with `failures=0`.

Candidate SHA-256 values:

```text
048243af556bd5e68176ca211d74825506f6297f7ed5c85c71e5712e7a3b4f32  tests/wineusb_winusb_urb_contract.c
e1087e04a025d4456b7996a0077e491295096d2ca066b86be71a4ae378a0cb9c  tests/wineusb_winusb_urb_fake_libusb.c
```

Copied active production SHA-256:

```text
ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1  source/dlls/wineusb.sys/unixlib.c
```

## Executable mutant matrix

| # | Incorrect production behavior | Exit | Failures |
| ---: | --- | ---: | ---: |
| 1 | R139 broad/suppress predicate | 1 | 24 |
| 2 | Function-membership exact suppression plus direction widening | 1 | 20 |
| 3 | Allocate/free before function-scope rejection | 1 | 18 |
| 4 | Coherent non-function exact tail corruption | 1 | 1 |
| 5 | Exact suppression only for coherent non-function metadata | 1 | 10 |
| 6 | Synchronous `libusb_control_transfer()` then correct local exact response | 1 | 6 |
| 7 | First-49-byte caller corruption after generic function/in-scope direction miss | 1 | 1 |
| 8 | Function-membership recipient widening | 1 | 10 |
| 9 | Omit exact local `header->Status = USBD_STATUS_SUCCESS` | 1 | 3 |
| 10 | Exact-path `libusb_get_device_descriptor(libusb_get_device(handle), &probe)` | 1 | 3 |
| 11 | The same device/descriptor probe before function-scope rejection | 1 | 6 |

Every counted row compiled successfully, executed the actual copied production
entry point through the fake boundary, reported the fake behavior pass marker,
and exited feature status 1 with contract failures. The copied production file
was restored hash-identically after every row.

One initial draft of row 1 bypassed an existing helper, failed compilation
under `-Werror` with harness exit 2, and is excluded from feature evidence. The
helper-preserving row shown above was then compiled and executed successfully.

## Complete fake-boundary audit

`nm -D --defined-only` on the disposable audit shared object reported exactly
32 externally defined names beginning `libusb_`. Source inspection found
exactly 32 fake entry-point increments and confirmed each is the first
operation of its entry. The 33rd raw macro reference is its definition.

## Patch and lineage identity

`task-9-r143-proposed-boundary-witness.patch` touches exactly the two requested
test files and has SHA-256
`bf02b6dc45849612ceb3929c93189f757ad25f45e8784c56134bb34fa5f5b82b`.
It dry-runs from the live R139 head. Disposable application produced both
candidate files byte-for-byte.

The apparent `ff9bea...` versus `ba3172...` production discrepancy is resolved:
the first hash belongs to the named pre-edit R138 production-base snapshot,
while the second is the active post-implementation R138 file. Across the nine
authorized R138 paths, the live/base comparison has exactly the six changed and
three unchanged paths recorded in `task-9-r138-implementer-report.md`. Both
R143 disposable production copies match the active `ba3172...` file.

No Wine, protected prefix, USB/device/sysfs, driver build/staging, network,
firmware, preset/effect, UC/Voice FX, or live-hardware action occurred.
