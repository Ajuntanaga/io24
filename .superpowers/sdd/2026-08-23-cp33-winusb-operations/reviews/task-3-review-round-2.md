# CP33 Task 3 independent review — fix round 2

## Sole finding

**ADDRESSED.** The contract calls the actual callback returned through the
included production v2 query, then verifies:

- Valid context plus `NULL` output returns `STATUS_INVALID_PARAMETER`.
- Null context plus a `0x3c` sentinel returns `STATUS_INVALID_PARAMETER`
  without changing the sentinel.
- Both calls preserve the complete device snapshot and query guard bytes.

Evidence: `task-3-round-2-head/tests/wineusb_winusb_busif_contract.c`, lines
370 and 383.

## Spec Compliance verdict

PASS. Offline-only qualification is accepted and not a failure.

## Strengths

- The fix is narrowly test-only; production behavior remains frozen.
- Invalid-input assertions cover status, sentinel preservation, device state,
  and guard integrity.
- SHA-256 comparisons confirm all five production paths, the wrapper,
  lifecycle contract, and binding contract are byte-identical to round 1.
- The frozen diff and head-manifest hashes match the package.
- The lifecycle seal has exactly nine entries, no self-reference, and verifies
  9/9.

## Critical issues

None.

## Important issues

None. No new Critical or Important breakage was introduced.

## Minor issues

None.

## Task quality

Approved.

## Concise reasoning

The sole remaining false-GREEN gap is closed with executable checks against
the actual production callback. Scope preservation and checkpoint coherence
independently verify, so Task 3 is ready to pass final review.
