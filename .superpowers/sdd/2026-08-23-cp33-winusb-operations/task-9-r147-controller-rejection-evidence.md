# Task 9 R147 controller rejection evidence

Timestamp: 2026-08-26

The controller independently reproduced the holistic device-handle false green
at focused exit 0, fake pass marker present, and `failures=0`, then restored
copied production to `ba3172e...d53051`.

The same partial-state root cause extends to two other RANGE admission helpers:

- changing the pipe-table pointer only on the malformed-header exact-RANGE
  rejection passed focused mode at exit 0 with zero failures; and
- changing the device handle only on the exact-RANGE null-buffer rejection
  passed focused mode at exit 0 with zero failures.

The nominal complete snapshot also has a failure-safety defect.  On an
oversized generic reject, changing the pipe-table pointer to null first caused
the whole-fixture and pointer assertions to fail, then the helper dereferenced
the changed null pointer during its deep comparison.  The contract terminated
by signal and the wrapper returned harness exit 2.  A changed pointer must
produce a bounded feature failure without dereferencing untrusted post-call
state.

All mutations and restores occurred only in
`/tmp/io24-r147-controller.atIrt1`.  Live tests and production remained exact.
