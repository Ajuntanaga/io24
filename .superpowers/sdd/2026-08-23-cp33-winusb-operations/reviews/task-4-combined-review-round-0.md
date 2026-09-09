# CP33 Task 4 combined independent review — round 0

Verdict: **FAIL**

No Critical or Minor finding. Three Important blockers remain.

## Important findings

1. **Valid grouped interfaces can commit in the kernel and then be rejected by
   the DLL.** The kernel accepts unique contiguous groups in descriptor order
   (`session.c:251,380`). The DLL additionally requires each later interface
   number to be greater (`dlls/winusb/main.c:267-271`). R40 requires grouping
   and uniqueness; R51 requires actual raw order, not numeric sorting. Add a
   valid descending two-interface fixture, reject duplicate interfaces, and
   prove endpoint-address reuse across distinct alternates remains allowed.
2. **Wait failures discard their meaningful error.** `submit_request()` maps
   every non-`WAIT_OBJECT_0` result to `ERROR_GEN_FAILURE`
   (`dlls/winusb/main.c:86-91`). The fake wait never sets last error and the
   test hardcodes the generic value (`tests/winusb_user_api_contract.c:345,479`).
   Preserve the exact error on `WAIT_FAILED` through event cleanup.
3. **The user contract does not enforce the exact full-request size.**
   Production currently allocates/submits `header.total_size`, but the fake
   accepts any initialize output length at least 72 and `initialize_handle()`
   checks only the first request (`tests/winusb_user_api_contract.c:361,434`).
   Assert the second output and snapshot allocation are exactly the sizing
   header's `total_size`, and prove a temporary `+1` mutation fails.

## Verified results

All six authorized host gates exited zero. Evidence and scope are internally
consistent: base 12/12, task seal exactly 15 and 15/15, head exactly 16 and
16/16, review diff byte-identical to the evidence patch, workspace matching the
failed frozen head, exact eight-production/six-contract scope, and R47's exact
one-line lower delta.

```text
plan              013feee53959cd8efdf5a13e6a83ffacf2a6517f43def0566ed95f534b0fe981
spec              8d04b44c89860b34afe0560caa9fa83c12aa80ca1e49f93734ce899dd56294a7
review package    b70af4507c519420b4d0517fc8f280f5fcaac9e3f0fbb42c4088e9068088ac75
review rubric     ac94bc0f88def9efbaae409979c8ed616fc6b54788fae6142f244f508af17ef5 (`task-4-round-0-rubric.md`)
combined diff     3eb87ca5cf3e4ae4be206e03d3b9416cf9080f3d0559a33f5400354f63383639
evidence seal     586438f53079c078dba9826ab1d65fea5392fdd4b2421ea0e98ebdeb5ce03400
head manifest     4fa6eae036038cb28ecf4096099e4b278afb659e7d8298e8034a9e0ca6ff94bd
```

R46 remains a valid explicit Task-6 carry. No separate kernel-half defect or
out-of-scope action was found.
