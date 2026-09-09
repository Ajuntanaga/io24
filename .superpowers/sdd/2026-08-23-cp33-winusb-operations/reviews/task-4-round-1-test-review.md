# CP33 Task 4 R58-R60 supplemental test review

Verdict: **FAIL**

Current production behavior appears correct, but three Important false-green
gaps remain in the executable contract.

1. R58's duplicate fixture is adjacent `[5,5]`; an adjacent-only production
   comparison remains green while accepting `[5,2,5]`. Add a three-interface
   nonadjacent duplicate and prove the adjacent-only mutation fails.
2. R59's fake ignores the wait handle and tests only `ERROR_ACCESS_DENIED`.
   Record/assert the exact private event and vary at least two errors so
   hardcoded propagation and wrong-handle waits fail.
3. R60 searches for any allocation with the advertised size rather than tying
   the allocation pointer to the full IOCTL output pointer. Record the output
   pointer and require exact identity with the exact-sized allocation.

The descending `[5,2]`, adjacent duplicate, and cross-alternate endpoint-reuse
fixtures are internally consistent. Fresh initialize/surface gates and the
round-1 16-entry manifest passed. No file or live state was modified.
