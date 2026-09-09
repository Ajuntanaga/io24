# CP33 Task 3 independent review — round 0

## Spec Compliance verdict

FAIL. Offline-only evidence; no live/runtime validation is claimed.

## Strengths

- Metadata v2 is additive, exact-sized, and leaves the v1 declaration intact.
- The lower speed callback uses `CONTAINING_RECORD`, cached speed state, and
  delays output assignment until success.
- Upper-FDO consumption requests v2, validates returned fields and canonical
  speed, and balances the reference on normal post-query paths.
- Create state gating, distinct context allocation, delayed `FsContext`
  publication, and basic cleanup/close idempotence are clear and scoped.
- The initial seal contains the authorized five production and three contract
  paths.

## Critical issues

None.

## Important issues

1. Removal ownership is released too early. Close decrements `file_count` and
   signals `removal_event` before waiting for `outstanding == 0` and before
   freeing the file context (`winusb.sys/main.c`, initial head lines 290, 294,
   and 300). REMOVE waits only on that prematurely signaled event (initial head
   line 385). Device removal may therefore complete while file ownership and
   outstanding work remain live. Keep the removal ownership count/event active
   through drain and final context destruction, or introduce a separate
   lifetime counter.

2. The contracts produce a false GREEN for required lower-speed and lifecycle
   drain behavior. The bus test invokes its own synthetic `get_speed()`
   (`wineusb_winusb_busif_contract.c`, initial head lines 133 and 285); actual
   lower `wineusb.c` received compilation only (`task-3-report.md`, line 118).
   No behavioral test would catch descriptor-based inference, reversed
   Low/High mapping, incorrect containment, or output mutation after removal.
   The lifecycle scenario closes only zero-outstanding contexts and closes the
   final context before REMOVE (`winusb_function_io_contract.c`, initial head
   lines 188, 208, and 211), so it cannot detect premature removal signaling
   or prove deferred free.

3. R23's retained-v1 requirement is not met additively. The binding fake
   replaces its v1 interface/query with v2-only behavior
   (`winusb_function_binding_contract.c`, initial head lines 130, 134, and
   187). Version 1 appears only as a rejected wrong-version case (initial head
   line 234); the fake no longer retains a successful v1 regression path.

4. Unchanged contract modes tear down with a live `FsContext`: session,
   alternate, policy, and transfer create a file and call REMOVE without
   cleanup/close (`winusb_function_io_contract.c`, initial head lines 214, 216,
   218, and 220). With real event semantics these modes block in REMOVE; a
   permissive host wait fake masks leaked ownership.

## Minor issues

None.

## Task quality

Needs fixes.

## Concise reasoning

The additive metadata implementation is largely sound, but the file-ownership
event does not represent the full context lifetime, allowing removal to
proceed before outstanding drain and destruction. Required contracts do not
exercise that race or the real lower speed callback, retained v1 fake coverage
was replaced rather than preserved, and other contract modes remove devices
with open contexts. These are specification and false-GREEN failures, so
approval is not warranted.
