# Task 1 fix round 5 scoped re-review

Verdict: **FAIL — the original returned-length false-GREEN is closed, but one
pointer-identity assertion remains unenforced**.

## Finding verdict

The focused policy contract now proves valid input capacity 8, typed response
actual length 4 and value `0x13579bdf`, caller-visible `ValueLength == 4`, exact
value bytes, unchanged tail sentinels, and intact guards. The frozen vendor
policy-8 path remains at input capacity 4.

The fake `DeviceIoControl` boundary still does not record its
`lpBytesReturned` pointer or prove that it differs from the public caller's
`ValueLength` pointer. A wrapper could pass the caller's pointer as the
internal IOCTL byte-count target, allow the fake to write response-structure
size 48, then overwrite it with response value length 4. The current assertions
would pass despite violating the round-5 binding constraint.

Evidence: `task-1-round-5-head/tests/winusb_user_api_contract.c:79-84`,
`:159-180`, `:263-268`, `:295`, and `:317`.

## Preservation and breakage

All prior Task 1 corrections remain preserved: typed public requests,
boundary-authored vendor trace, distinct public masks and function IOCTLs,
initialization-returned handles, actual production translation-unit execution,
Python `OSError` remapping to harness exit 2, control-only setup subtraction,
lower/cancel fake deltas, 24 distinct modes, and feature-1 versus harness-2
separation. No additional Critical or Important regression was found.

The reviewer verified the 15-entry round-5 head manifest and did not rerun the
full suite. The controller independently verified 5/5 aggregate REDs, 24/24
modes, 13/13 probes, CP32 72/72, both production-clone diffs zero, and the Task
1 checkpoint 11/11.

## Controller adjudication

This finding is real and bounded. The five-round breaker forbids a Task 1 fix
round 6. Under ruling R11, Task 2 must add the missing fake-boundary pointer
recording and non-alias assertion as its first test-only RED hardening, before
any Task 2 production edit. Task 1's offline RED boundary remains usable and
its production roots remain immutable; Task 1 is not described as review-clean.
