# Task 9 R142 isolated proof

Timestamp: 2026-08-25

All test and production changes were made in disposable `/tmp` copies. The live
R139 test head and R138 production were never edited.

## Candidate baseline

The proposed coherent three-scope contract compiled and executed the actual
R138 `unixlib.c` through
`tests/wineusb_winusb_urb_contract.sh ... --control-descriptor` at exit 0 with
`failures=0`. A final clean replay after restoring every mutant produced the
same result.

Candidate test SHA-256:

`c4175a58739f09b5d05ccbec6870fbc6cc4dd24ba2ff311272e7e3bff3d53051`

## Executable mutant matrix

| Mutant | Incorrect behavior | Exit | Failures |
| --- | --- | ---: | ---: |
| R139 broad/suppress | Widen function class/interface/IN length at least 255; suppress all non-function RANGE | 1 | 66 |
| membership suppress/widen | Suppress exact and widen direction only when function low-byte membership is true | 1 | 20 |
| reject allocate/free | Allocate and free a libusb transfer before expected function-scope rejection | 1 | 18 |
| non-function tail write | Return the exact 50-byte result, then corrupt the first tail byte only for coherent non-function state | 1 | 1 |
| coherent non-function suppression | Disable exact RANGE only when function metadata is false/zero/empty | 1 | 10 |
| synchronous backend then local | Issue `libusb_control_transfer()`, then return the correct local exact answer | 1 | 6 |
| targeted 49-byte caller write | After generic submit, copy only the first 49 captured bytes for the function/in-scope direction miss | 1 | 1 |
| membership recipient widening | Ignore recipient only when function low-byte membership is true | 1 | 10 |

The first mutant is the bad behavior previously proven to pass the frozen R139
contract at exit 0 with zero failures. The next four retain R141 coverage, and
the coherent-state, synchronous-backend, and 49-byte variants directly exercise
the three independent R141 preauthorization findings.

Each counted mutant compiled successfully and reached the actual production
entry point through the fake-libusb boundary. One initial tail-mutant draft had
an undeclared local variable and exited with harness status 2; it was corrected
and rerun before evidence was counted. Harness setup failures are not feature
evidence.

## Patch identity

`task-9-r142-proposed-coherent-three-scope.patch` dry-runs against the live R139
test and touches exactly one file with 172 insertions and 26 deletions. Applying
it to a disposable copy produced SHA-256
`c4175a58739f09b5d05ccbec6870fbc6cc4dd24ba2ff311272e7e3bff3d53051`, byte
identical to the isolated candidate.

No Wine, protected prefix, USB/device/sysfs, driver build/staging, network,
firmware, preset/effect, UC/Voice FX, or live-hardware action occurred.
