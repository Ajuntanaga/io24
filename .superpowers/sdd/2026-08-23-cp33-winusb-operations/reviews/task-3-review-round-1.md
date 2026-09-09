# CP33 Task 3 independent review — fix round 1

## Initial findings

1. **ADDRESSED.** Close now waits for zero outstanding work, unlinks and
   frees file-owned state, then decrements `file_count` and signals removal
   (`task-3-round-1-head` `winusb.sys/main.c`, lines 296–321). The
   deterministic schedule observes count one, an unsignaled event, and no free
   at the drain boundary (`winusb_function_io_contract.c`, lines 156–180).

2. **NOT ADDRESSED.** Most of the finding is fixed: the contract obtains the
   actual included `wineusb.c` callback and tests Low/High plus both removal
   sentinels (`wineusb_winusb_busif_contract.c`, lines 350–390); lifecycle now
   schedules nonzero outstanding work through REMOVE
   (`winusb_function_io_contract.c`, lines 223–270). However, every real
   callback invocation still supplies a valid context and non-null `&speed`;
   there is no null-output or null-context case, nor a sentinel assertion for
   the null-context failure. The package's explicit mutation lens therefore
   remains incomplete.

3. **ADDRESSED.** The fake serves v1 and v2 separately, and the new successful
   v1 regression verifies exact layout, context, getter, guard preservation,
   and 1/1 balance (`winusb_function_binding_contract.c`, lines 136–149 and
   248–276).

4. **ADDRESSED.** Shared teardown performs matching CLEANUP and CLOSE before
   REMOVE and asserts null publication, zero wait failures, and
   allocation/free balance (`winusb_function_io_contract.c`, lines 95–106).
   Session, alternate, policy, and transfer all use it (lines 274–280).

## Spec Compliance verdict

FAIL. One required callback mutation case remains unsupported. The
offline-only qualification is accepted and is not part of the failure.

## Strengths

- Removal ownership now extends through drain, unlink, destruction, and final
  count transition.
- The real lower callback is executed through the production v2 query.
- Successful v1 coverage is explicitly additive.
- All retained context-creating modes close ownership before REMOVE.
- Diff/package hashes, both 10-entry frozen manifests, and the exact nine-path
  lifecycle seal verified successfully.

## Critical issues

None.

## Important issues

- Initial finding 2 remains partially open: add real-callback cases for
  `GetDeviceSpeed(valid_context, NULL)` and
  `GetDeviceSpeed(NULL, &sentinel)`, checking `STATUS_INVALID_PARAMETER` and
  sentinel nonmutation where an output byte exists
  (`wineusb_winusb_busif_contract.c`, lines 375–390).

No new Critical or Important breakage was introduced by the fix diff.

## Minor issues

None.

## Task quality

Needs fixes.

## Concise reasoning

Three initial findings are fully closed, and the production ownership race is
correctly repaired. The real lower-callback contract still omits the
package-mandated null-input failure cases, leaving a small but explicit
false-GREEN gap; approval should wait for those assertions.
