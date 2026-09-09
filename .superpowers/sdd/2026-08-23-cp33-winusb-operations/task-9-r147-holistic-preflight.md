# Task 9 R147 holistic preauthorization review

Timestamp: 2026-08-26

Decision: REQUEST CHANGES.

## Verified integrity

The exact 11-entry manifest, manifest SHA-256, proposal patch SHA-256, two-file
scope, direct frozen-R139 reconstruction, declared candidate hashes, and clean
focused/retained baselines all verified.

## Important finding

`expect_control_scope_reject()` preserves only storage, transfer length,
status, backend state, and driver context.  It does not use the complete
fixture and deep pipe-table snapshot used by the generic and endpoint helpers.

In disposable `/tmp` production, the reviewer changed the device handle only
for the exact class-interface OUT function/out-of-scope tuple
`(request=2, value=0x0100, index=0x0500, length=256)`.  The patched R147 focused
replay still exited 0, emitted the fake pass marker, and reported `failures=0`.
This is an executable scope-conditioned rejection-state false green.

No workspace file was edited by the reviewer.
