# Task 9 R141 isolated proof

All test and production mutations were made in disposable `/tmp` copies. The
live R139 test head and R138 production were never edited.

## Candidate baseline

The proposed three-scope contract compiled and executed live production through
`tests/wineusb_winusb_urb_contract.sh ... --control-descriptor` at exit 0 with
`failures=0`.

## Executable mutant matrix

| Mutant | Incorrect behavior | Exit | Failures |
| --- | --- | ---: | ---: |
| R139 broad/suppress | Widen function class/interface/IN length at least 255; suppress all non-function RANGE | 1 | 60 |
| membership suppress/widen | Suppress exact and widen direction only when function low-byte membership is true | 1 | 14 |
| reject allocate/free | Allocate and free a libusb transfer before returning the expected scope error | 1 | 6 |
| non-function tail write | Return the exact 50-byte result, then corrupt the first tail byte only for non-function devices | 1 | 1 |
| non-function suppression | Disable exact RANGE only for non-function devices | 1 | 4 |
| membership recipient widening | Ignore recipient only when function low-byte membership is true | 1 | 10 |

The first mutant passed the frozen R139 contract at exit 0 with zero failures;
the remaining five target the three independent R140 preflight findings and
the full seven-negative scope matrix.

All executions compiled the copied production `unixlib.c` and exercised it
through the fake-libusb boundary. No Wine, prefix, device, driver build/staging,
network, firmware, preset/effect, or live-hardware action occurred. Disposable
trees are deleted after patch comparison and package sealing.
