# Task 9 R141 three-scope RANGE adjudication request

Timestamp: 2026-08-25

## Verdict requested

Authorize one test-only correction in exactly:

- `tests/wineusb_winusb_urb_contract.c`

The complete live-R139-to-proposed delta is
`task-9-r141-proposed-three-scope-matrix.patch`. No upper test, production,
support, wrapper, RANGE, snapshot, prior manifest, prior evidence, device,
Wine/prefix, build/staging, firmware, preset/effect, or live-hardware path is
requested for reopening.

## Rejected predecessors

R139 was applied exactly but rejected after both mandatory reviewers proved a
scope-conditioned false green. R140 was never applied: both independent
preauthorization reviewers rejected it for missing function/in-scope coverage,
missing non-function tail guards, and incomplete no-backend-activity checks.
Both predecessor packages remain immutable evidence.

## Proposed complete matrix

The proposal retains every sound R139 byte and replaces R140 with a consistent
three-scope matrix:

1. Exact RANGE positives run as non-function, function/out-of-scope, and
   function/in-scope fixtures. One shared assertion requires exact status,
   reported length, 50-byte payload, prefix and full tail guards, zero transfer
   allocation attempts/counts/frees, zero buffer activity, zero submit
   attempts, no pending transfer, and null `DriverContext`.
2. A helper adds interfaces 0 and 1 to the existing interface-5 function and
   updates its count from 1 to 3, yielding the same internally consistent
   `{0,1,5}` membership for every function/in-scope case.
3. Each of the six interface-recipient one-field negatives runs in all three
   scopes. Function/out-of-scope must reject with unchanged length/storage and
   zero allocation, buffer, or submit activity. Non-function and
   function/in-scope must route through generic libusb without synthesizing the
   captured RANGE bytes.
4. The recipient negative also runs in all three scopes and routes generically
   in each, closing membership-conditioned recipient widening.

Structural admission negatives, null-buffer isolation, endpoint/generic
requests, and the `0xab05`/`0xab07` low-byte witness remain unchanged.

## Isolated proof

Only disposable test and production copies were changed. The proposed test
against live R138 production exited 0 with `failures=0`. It then caught:

- R139 broad/suppress scope mutant: exit 1, failures=60;
- function/in-scope exact suppression plus direction widening: exit 1,
  failures=14;
- allocate/free-before-scope-reject mutant: exit 1, failures=6;
- non-function tail-corruption mutant: exit 1, failures=1;
- non-function exact-suppression mutant: exit 1, failures=4;
- function/in-scope recipient-widening mutant: exit 1, failures=10.

Every run compiled copied actual `unixlib.c` at the fake-libusb boundary. No
source scan was counted as feature evidence.

## Next gate

Do not apply without explicit controller authorization. If authorized, verify
the live 2/2 R139 head, this adjudication manifest, and patch dry-run; apply
only the one-file sealed delta; replay focused and retained host gates; replay
the six sealed mutants; freeze the corrected test; and obtain two clean
independent reviews before resuming R138 sanitizer, full final-head mutants,
production review, or final sealing.
