# CP33 Task 9 R149 holistic review

Preserved: 2026-08-28T16:49:37-07:00

Verdict: **REQUEST CHANGES**

## Findings

### 1. Important: same-address free plus reallocation remains a material false green

The observer records only the current live state for an address. On `free`, it
marks the entry dead. When `calloc` returns the same address, it overwrites that
entry as live again and increments only global counters.

Evidence:

- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_fake_libusb.c:43-48`
- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_fake_libusb.c:66-113`

`io24_pipe_table_audit_pointer_live()` consequently returns `1` for the
replacement allocation without exposing its allocation epoch:

- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_fake_libusb.c:133-140`

The rejection oracle then checks only pointer equality, current liveness, and
equal bytes:

- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_contract.c:1022-1030`

Its backend snapshot does not capture the pipe-table observer's allocation
count, free count, order, or per-pointer generation:

- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_contract.c:981-990`
- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_contract.c:1039-1065`

Therefore a rejection-path source variant that copies the current table value,
frees the table, reallocates the same-sized table at the same address, and
restores the copied bytes can satisfy pointer equality,
`pointer_live() == 1`, byte equality, and the complete backend snapshot even
though allocation identity changed.

The sealed row is not this counterexample. It performs only
`free(params->device->pipe_table)` and no replacement allocation:

- `task-9-r149-isolated-evidence.tar.gz::oracle/01-same-address-table-release.patch:3-14`

Accordingly, the existing row's exit 1 proves only released-and-still-dead
detection:

- `task-9-r149-isolated-evidence.tar.gz::final/rows/01-same-address-table-release/result.json:1-12`
- `task-9-r149-isolated-evidence.tar.gz::matrix.tsv:5`

This counterexample follows directly from the observer and comparator
semantics; it is not already executed in the sealed matrix.

Required correction: preserve a monotonic per-allocation generation or epoch
and snapshot `{pointer, epoch}` across the call, or compare equivalent
per-pointer lifetime identity. Add a source-bound free/reallocate/restore case
that must exit 1 even when the allocator reuses the address.

### 2. Important: the baseline snapshot still performs an unchecked deep read

`capture_control_reject()` copies `*snapshot.pipe_table` before asking the
allocation observer whether the pointer is live:

- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_contract.c:1001-1013`

The liveness check exists only in the post-call comparator:

- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_contract.c:1022-1030`

`reset_control()` accepts successful fixture selection but does not
independently establish table-allocation liveness before the later snapshot:

- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_contract.c:867-891`

Thus a production regression that frees the published table before returning
success from fixture setup can make the nominal oracle read released storage
before it reaches its safety predicate. Depending on allocator behavior, this
becomes an invalid lifetime read, stale-byte comparison, or harness crash
rather than an ordinary executable assertion.

Required correction: check liveness before the baseline dereference and
represent a non-live or unknown baseline safely. The simpler design is one
observer-backed snapshot helper that validates liveness, captures the
allocation epoch, and only then copies the table.

Validation: change the successful select/commit path in an isolated source copy
to release the published table while leaving its pointer unchanged before
returning. `--control-descriptor` must produce a bounded exit-1 product
assertion without an invalid read, signal, timeout, or harness exit 2.

## Lifecycle-oracle determination

- Prior defect 1, pipe-table lifetime: the exact free-only R148 case is caught,
  but the underlying allocation-identity defect is not fully closed because
  same-address reallocation can restore current liveness and equal bytes.
- Prior defect 2, cached nested configuration lifetime: closed for the declared
  traversal. The fake bounds and deep-copies interface, alternate-setting, and
  endpoint descendants, then poisons all layers on exact release.

Evidence for the second closure:

- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_fake_libusb.c:213-262`
- `task-9-r149-isolated-evidence.tar.gz::candidate/tests/wineusb_winusb_urb_fake_libusb.c:310-352`
- `task-9-r149-isolated-evidence.tar.gz::oracle/02-cached-nested-config-release.patch:3-41`
- `task-9-r149-isolated-evidence.tar.gz::final/rows/02-cached-nested-config-release/result.json:1-14`

The focused and retained executions fail through product assertions at exit 1
with no harness diagnostic.

## Other reviewed areas

No additional material regression was found in the earlier R148
rejection-state, retained-failure, layout, reset, journal, RANGE,
endpoint-authority, or caller-preservation contracts.

Confirmed evidence includes:

- exact three-path proposal scope and zero-fuzz dry-run;
- independent streaming reconstruction of all three candidate hashes;
- live production and test inputs remain at all five frozen hashes;
- bounded descendant indices and invalid/overflow returns in the mutable
  configuration view;
- identical count/record layouts between the contract and fake;
- always-linked observer with the older reclamation assertions still
  environment-opt-in;
- clean focused/retained controls before and after at exit 0;
- declared lifecycle rows at exit 1;
- usage, unsupported-mode, and missing-input paths at harness exit 2; and
- allocation-reclamation audit exit 0 with zero failures.

R149 remains unapplied. This **REQUEST CHANGES** verdict is review evidence
only and grants no application, production, Wine, USB/device, staging, or Task
9 closure authority.
