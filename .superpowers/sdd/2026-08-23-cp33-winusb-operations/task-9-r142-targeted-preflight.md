# Task 9 R142 targeted preauthorization review

Timestamp: 2026-08-25

## Verdict

`REQUEST CHANGES`

Critical findings: none.

Important findings: one.

Material Minor findings: none.

## Finding: side-effect-free synchronous libusb calls are invisible

R142 snapshots every currently exposed fake count and record plus transfer
allocation/submission state. That still does not observe successful
`libusb_get_device()` and `libusb_get_device_descriptor()` calls, because the
fake implementations mutate neither structure.

The reviewer reproduced a passing bad implementation in a disposable source
copy. Inside the exact `range_supported` branch it called:

```c
libusb_get_device_descriptor(libusb_get_device(handle), &probe);
```

before returning the correct local RANGE response. The proposed R142 contract
compiled actual production through the fake boundary and still exited 0 with
`failures=0`. The same instrumentation blind spot permits a descriptor probe
before function-scope rejection.

## Required correction

The fake boundary must expose a monotonically changing call witness that is
updated by every libusb entry point available to compiled production, including
otherwise side-effect-free descriptor/device queries. Exact local success and
scope rejection must snapshot and require that witness to remain unchanged.

## Strengths

The 6/6 R142 manifest and live 2/2 R139 head verified. The patch dry-runs and
produces the declared byte-exact candidate. Coherent non-function metadata,
complete guarded caller-buffer preservation, and the full three-scope exact
plus seven-negative matrix are sound.

## Boundary

Read-only offline review. No workspace byte was changed; the executable
counterexample used only a disposable `/tmp` copy. R142 was never applied.
