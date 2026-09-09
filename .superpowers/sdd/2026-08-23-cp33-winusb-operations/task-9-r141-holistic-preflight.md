# Task 9 R141 holistic preauthorization review

Timestamp: 2026-08-25

## Verdict

`REQUEST CHANGES`

Critical findings: none.

Important findings: two.

Material Minor findings: none.

## Finding 1: exact-success backend snapshot is incomplete

`expect_exact_range_success()` checks transfer allocation and asynchronous
submission counters but omits `io24_fake_libusb_counts()->control` and the full
fake record. Production can issue a synchronous `libusb_control_transfer()` and
then copy the local exact RANGE answer. The expected payload, length, tail,
allocation, submission, pending, and `DriverContext` assertions still pass,
despite forbidden backend activity.

The correction must snapshot and compare the complete fake-libusb count and
record state, plus allocation attempts/count, submission attempts, reported
actual length, and pending state, around both exact success and scope rejection.

## Finding 2: non-function fixtures are internally impossible

R141 changes only `device.function` to false while retaining
`function_interface_count == 1`, `function_root == 5`, and membership bitmap
`{5}`. A real non-function device has zero count, zero root, and an empty
function-membership bitmap. Production can therefore misbehave only under the
coherent non-function state and pass every R141 non-function cell.

The correction must construct non-function fixtures with all four function
metadata fields made mutually consistent while preserving the selected generic
control-transfer setup needed by the test.

## Boundary

Read-only, offline preauthorization review. R141 was never applied. No live
test, production, support, wrapper, prior evidence, Wine/prefix, USB/device,
driver build/staging, network, firmware, preset/effect, or hardware path was
changed or invoked.
