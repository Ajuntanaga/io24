# Task 9 R139 targeted review

## Verdict

`REQUEST CHANGES`

Critical findings: none.

Important findings: one scope-conditioned RANGE false green.

Material Minor findings: none.

## Finding

The exact RANGE positive remains function-scoped, while all six repaired
interface-recipient one-field negatives set `device.function=FALSE`. A bad
`unixlib.c` can therefore use the exact predicate for non-function devices but
widen or replace it only for function devices. The corrected negatives then
remain generic and green even though bad function-scoped tuples synthesize the
captured RANGE payload.

The reviewer supplied a concrete mutant that broadens class/interface/IN
function-device requests of length at least 255 and suppresses RANGE for
non-function devices. It passes the complete R139 lower focused mode with zero
failures while incorrectly synthesizing several function-scoped RANGE misses.

The upper expected-packet refresh is necessary and remains strong. The device
recipient negative, exact packet comparison, and `0xab05`/`0xab07` low-byte
scope witnesses remain intact. No separate finding was reported.

## Evidence checked

The reviewer verified the R139 proposal, 2/2 base, 2/2 head, and 14/14
controller-log manifests; confirmed live equality with the frozen head; and
replayed both changed focused host contracts at exit 0 with zero failures.
