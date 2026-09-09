# Task 9 R140 targeted preauthorization review

## Verdict

`REQUEST CHANGES`

Critical findings: none.

Important findings: one.

Material Minor findings: none.

The proposed `expect_control_scope_reject()` does not prove the adjudication's
required absence of libusb activity. Its delegated helper checks no completed
control submission, no pending transfer, and a null `DriverContext`, then the
new helper checks status and storage. It does not check transfer allocation
attempts/counts/frees, buffer activity, or submit attempts.

A bad function-scope rejection can allocate and free a libusb transfer, restore
the expected status/storage/context, and pass every R140 mirror. The existing
fake records exactly that activity, so the proposal must assert those counters.

The reviewer verified the 6/6 manifest, live R139 equality, patch dry-run,
one-file scope, exact non-function positive, prior mutants, unchanged device
negative, and retained low-byte witnesses. No other finding was reported.
