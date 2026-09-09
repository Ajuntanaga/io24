# CP33 Task 9 R149 targeted review

Preserved: 2026-08-28T16:49:37-07:00

Verdict: **PASS**

No material issue was found within the five targeted criteria.

## 1. Allocation liveness before deep reads

PASS. The rejection matcher first checks pointer identity, then requires
`io24_pipe_table_audit_pointer_live(...) == 1`, and only afterward performs
`memcmp`; released and unknown pointers therefore return false without
dereference.

Evidence:

- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_contract.c:1022-1029`
- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_fake_libusb.c:133-140`

The observer returns `0` for released entries and `-1` for unknown pointers.

## 2. Allocation accounting and address reuse

PASS. Same-address reallocation reactivates the retained entry and increments
allocations; release preserves pointer identity while updating frees and free
order. Existing allocation/free/live/failure and close-order checks remain
intact.

Evidence:

- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_fake_libusb.c:66-145`
- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_contract.c:89-100,261-315`
- `task-9-r149-allocation-audit.log:330`
- `task-9-r149-allocation-audit.exit:1`

The sealed reclamation audit ended with `completions=3 failures=0` and exit 0.

## 3. Complete mutable configuration lifetime

PASS. The returned configuration, interface, alternate-setting, and endpoint
layers use separate mutable bounded storage. Bounds, negative counts, and null
descendants fail with libusb errors before returning a view. Exact release
poisons every copied layer, while subsequent retrieval reconstructs all
descendant pointers coherently.

Evidence:

- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_fake_libusb.c:16-19,213-261`
- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_fake_libusb.c:218-250,310-351`

## 4. Source-bound variant behavior

PASS. Both variants are precise production-source changes. Row 1 releases the
same-valued table on the target rejection path. Row 2 caches nested descendants
and releases the top-level configuration before traversal. The verifier
performs zero-fuzz reconstruction and byte comparison for every R148/R149 row
instance.

Evidence:

- `task-9-r149-isolated-evidence.tar.gz::oracle/01-same-address-table-release.patch:3-14`
- `task-9-r149-isolated-evidence.tar.gz::oracle/02-cached-nested-config-release.patch:3-42`
- `task-9-r149-verify.sh:100`
- `task-9-r149-isolated-evidence.tar.gz::matrix.tsv:2-7`

R148 lets all three executions escape at exit 0. R149 produces actual assertion
failures at exit 1 with counts 1, 10, and 5. Assertion and normal-summary
evidence appears at:

- `task-9-r149-isolated-evidence.tar.gz::final/rows/01-same-address-table-release/focused.log:95,246-247`
- `task-9-r149-isolated-evidence.tar.gz::final/rows/02-cached-nested-config-release/focused.log:4-6,43-49,254`
- `task-9-r149-isolated-evidence.tar.gz::final/rows/02-cached-nested-config-release/retained.log:4-6,64,69,324`

## 5. Exit classification and clean regression gates

PASS. The wrapper reserves exit 2 for usage, unsupported mode, missing input,
compile/link failures, and abnormal lower exits, while propagating product
exits 0/1. Retained exit 1 is preserved only when backed by assertion failures;
loader/symbol or other invalid retained results become harness exit 2.

Evidence:

- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_contract.sh:3-13`
- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_contract.c:1571-1591`
- `task-9-r149-isolated-evidence.tar.gz::matrix.tsv:2-7`
- `task-9-r149-harness-classification.log:1`

All four final clean gates are exit 0 with zero failures, all three declared
variant executions are exit 1, and R148's corresponding executions are exit 0.
Actual harness cases remain exit 2. No timeout, crash, compiler failure, loader
failure, or unused compilation is counted as feature evidence.

## Non-blocking verifier note

The documented recovery route says to run the verifier without arguments at
`RESUME-20260828T1549PDT.md:94`. That intended invocation independently
returned exit 0 and `R149_VERIFY PASS`.

The script also accepts an undocumented optional workspace argument at
`task-9-r149-verify.sh:4`; passing `.` exits 2 because the relative proposal
path is resolved after `patch -d` changes directory at lines 90-95. This is a
minor CLI robustness defect, not an evidentiary or product-oracle failure under
the declared interface.

This PASS is review evidence only. It grants no authority to apply R149,
modify production or live test surfaces, use Wine or the protected prefix,
access USB/hardware, or close Task 9.
