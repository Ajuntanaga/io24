# CP33 Task 4 DLL-half independent review — fix round 1

Verdict: **FAIL**. No Critical finding. This is a correctness/ABI review, not
a cybersecurity assessment.

## Round-0 findings

1. **Important 1 — NOT ADDRESSED.** Sizing transport errors now survive event
   cleanup, but full-request transport failure calls `HeapFree` without
   saving/restoring `LastError`. The fake heap does not clobber it. A pending
   sizing completion that unexpectedly returns TRUE also leaks the earlier
   `ERROR_IO_PENDING` instead of reporting local protocol inconsistency as
   `ERROR_BAD_DEVICE`.
2. **Important 2 — NOT ADDRESSED.** Header-field validation/freeze improved,
   but the exact `65535 + 72` total cap regressed. A self-consistent near-4-GiB
   sizing header reaches allocation.
3. **Important 3 — NOT ADDRESSED overall.** Production now walks raw
   interfaces sequentially and enforces per-alternate address uniqueness, but
   the required alt1-before-alt0 and matched raw/record duplicate-address
   counterexamples are absent.
4. **Important 4 — NOT ADDRESSED.** Added handle/mode/event/wait cases are
   useful, but the contract still omits failing/wrong `IO_STATUS_BLOCK`,
   immediate full failure, pending full success, all pending/failed RELEASE
   variants, exact created-event-to-overlapped-to-close identity, and heap
   error clobbering.
5. **Important 5 — ADDRESSED.** The wrapper compiles and links every collected
   production source with consistent sanitizer flags.

## Minors

- Release terminal accounting is addressed.
- Required mutation breadth is not addressed.

Both authorized gates pass, but Critical/Important closure is incomplete.
