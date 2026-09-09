# CP33 Task 5 independent review round 0

Verdict: **FAIL** — one Important lifetime issue.

## Important

Every nonfinal `WinUsb_Free` moved its record to `root->retired_handles`, while
records were reclaimed only when the final live handle destroyed the root.
Repeated `WinUsb_GetAssociatedInterface`/`WinUsb_Free` cycles under a live
default handle therefore grew user memory linearly without bound. The accepted
contract reissued each slot only once and checked balance only after final root
Free, so it missed the long-lived-root case.

The bounded correction must separate the opaque public token from reclaimable
record storage, reclaim a record after its admitted API references drain, and
retain stale-token rejection without allocator-address ABA.

All eight offline gates were otherwise green, and the five original mutation
lenses each failed. No other Critical, Important, or Minor finding was found.
No Wine, contained build, full matrix, prefix, device, live USB, install, or
physical action was performed.
