# CP33 Task 4 DLL-half independent review — fix round 2

Verdict: **FAIL**

No Critical issue or new production correctness defect was found. Two Important
executable-contract gaps remain.

## Important findings

1. **R51 counterexamples are not executed, and the duplicate-pipe mutation
   targets the wrong byte.** The enum values exist at
   `tests/winusb_user_api_contract.c:232-234`, but the mutation loop at line 482
   ends at `SNAPSHOT_BAD_RAW_ENDPOINT`. Neither new case runs. The duplicate
   mutation writes raw byte 52, the second endpoint descriptor's `bLength`;
   `bEndpointAddress` is byte 54. Extend the loop, target byte 54, retain the
   matching packed-record mutation, and prove removal of either production
   order/uniqueness check makes the contract fail.
2. **R55 pending RELEASE variants do not prove completion was consumed.** The
   immediate/pending schedules share assertions that do not check completion
   count, device/`OVERLAPPED` identity, or scheduled result/error. A production
   mutation that returns immediately on `ERROR_IO_PENDING` remains green. Assert
   one exact completion for pending release and zero for immediate/wait-failed
   release.

Production's sequential raw walk, per-alternate endpoint uniqueness, exact
release request/device/event/close linkage, error preservation, bounded header,
and transport handling appear correct.

## Prior-finding disposition

- Full-request `LastError` across clobbering `HeapFree`: **addressed**.
- Pending sizing TRUE maps to `ERROR_BAD_DEVICE`: **addressed**.
- Exact `72 + UINT16_MAX` cap: **addressed**.
- Raw alternate order and duplicate endpoints: **not addressed executably**.
- NT-success/bad IOSB status and information: **addressed**.
- Immediate/pending full failure and pending full success: **addressed**.
- RELEASE scheduling and identity: **partially addressed**.
- All-source compile/link and sanitizer flags: **addressed**.
- Release terminal counter: **addressed**.
- Required mutation breadth: **not addressed** due finding 1.

## Minor

The DLL report places round 2 before a stale “Residual review blockers” section
and older history. Mark the latter historical or restore chronological order.

## Authorized gates

```text
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=13 submits=3 releases=1 completions=0 failures=0
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
```

## Reviewed hashes

```text
b4f1ead66779024c7c0125e90b2ab8a5ac1c3fcc2b4a970d9dd9f7b63d475fb6  dlls/winusb/main.c
24f14f2714613f4f1d27ba337aea3385aad1bcd99fa8e7cc1731cb00a9ba81a7  tests/winusb_user_api_contract.c
f601c75e890afb48771f77e976041139ee33e3ce4331cb380c1e601af9bf4ebc  tests/winusb_user_api_contract.sh
95f2b9e29fae5472fe995d4e1e37e9dac19f94c916685647c49f0d37aa3bd79a  task-4-dll-report.md
```
