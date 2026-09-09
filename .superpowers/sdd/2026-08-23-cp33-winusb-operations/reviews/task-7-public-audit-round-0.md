# CP33 Task 7 public-slice audit round 0

Result: **CORRECTION REQUIRED** before combined review. This is not a claim
that the current public entry point is functionally broken for its validated
snapshot input.

Reviewed hashes:

- DLL `main.c`: `7443e374...`
- DLL `winusb_private.h`: `5b9df910...`
- DLL `Makefile.in`: `aed7eb71...`
- DLL `io.c`: `872946bf...`
- user contract: `05506855...`
- user wrapper: `78198925...`

## Gaps

1. R71 requires two independently issued associated handles and an executable
   lens in which swapping internal indices 1 and 2 fails. The current focused
   mode creates only associated slot zero and observes request index 1.

2. The mode covers an immediate submit failure and pending success, but omits
   pending completion failure and explicit final event/allocation/root-release
   balance for each error schedule.

3. `has_alternate()` performs snapshot offset arithmetic after only count-level
   checks. Initialization already validates and privately copies the snapshot,
   but the use site should explicitly bind `total_size`, offsets, record arrays,
   and additions to the immutable `root->snapshot_size` with overflow-safe
   checks. No test-only private-object access is permitted.

## Bounded continuation

Under R90, edit only DLL `io.c` and the user C contract. Preserve the other
four public-slice hashes. Add the contract first, use the existing valid
three-interface fixture, and demonstrate the new index observation rejects a
bounded 1/2-swap mutation. Then run the focused public gate and retained handle
and initialize modes. Combined Task-7 review remains gated on all slices.
