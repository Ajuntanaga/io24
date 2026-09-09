# CP33 Task 6 independent review request

Review only; do not edit any file and do not run Wine, touch a Wine prefix,
inspect USB/sysfs, stage or select builds, or access hardware. The bounded
change set is `task-6.diff`, derived from `task-6-base` and `task-6-head`.

Read, in order:

1. `task-6-brief.md`
2. `task-6-report.md`
3. `task-6.diff`
4. the authoritative design/plan sections for Task 6 and ledger rulings
   R31, R46, R47, R76, R77, and R78

Return `PASS` only if the complete change is correct. Otherwise give bounded,
actionable findings with exact path and line, the violated invariant, and the
smallest safe correction. Explicitly assess every risk below:

- Tests execute the real `unixlib.c` and `session.c` translations through the
  intended fake boundaries; no source scan or copied-production false GREEN.
- A SELECT is completely validated before any claim side effect.
- Only function-owned, newly required interfaces are claimed, in ascending
  interface-number order; parent/non-function behavior remains unchanged.
- Partial claim failure releases only the current transaction's successful
  journal in reverse order and preserves earlier committed claims.
- Each child permits at most one pending transaction. Wrong, stale, malformed,
  repeated, and already-finalized tokens fail without dereference or mutation.
- Commit merges the journal exactly once; rollback releases only that journal
  in reverse order; repeated post-commit selection is claim-idempotent.
- `LIBUSB_ERROR_BUSY` maps to failed USBD status and `STATUS_DEVICE_BUSY`.
- An upper post-SELECT rejection synchronously finalizes rollback before
  returning failure or freeing temporary state, with no published output or
  session. A normal upper success commits exactly once before return.
- Child destruction releases pending and committed claims exactly once before
  the parent/shared handle reference is decremented.
- No detach, auto-detach, or `libusb_set_configuration` path was introduced.
- R77 adds only an unsupported control-transfer fake; it does not fake success,
  weaken the retained contract, or count as Task 6 feature evidence.
- Metadata v1/v2 ABI and behavior remain unchanged; no metadata v3 exists.
- `unixlib.h` is byte-for-byte unchanged at the R78 base hash.
- The raw sanitizer wrapper's ptrace-only LeakSanitizer failure is accurately
  classified: determine whether the assertion-GREEN run with leak detection
  disabled is sufficient for Task 6, or identify a concrete missing check.

Do not treat formatting, speculation, or future Task 7+ functionality as a
Task 6 defect. Do flag any correctness, recovery, lifetime, ABI, or executable
coverage gap that can invalidate the Task 6 claim.
