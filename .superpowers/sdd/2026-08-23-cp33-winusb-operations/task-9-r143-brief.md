# Task 9 R143 isolated successor brief

## Objective

Build and verify a disposable R143 successor to rejected R142. Do not apply any
test or production change to the live workspace. The eventual proposal must
apply directly from the frozen live R139 head and reopen exactly two test paths:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

R143 must retain every sound R142 matrix/preservation assertion and close both
Important findings in `task-9-r142-targeted-preflight.md` and
`task-9-r142-holistic-preflight.md`.

## Isolation and ownership

Create a new exact `/tmp/io24-r143-proposal.XXXXXX` directory. You own only
that disposable directory and
`.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r143-implementer-report.md`.
You are not alone in the workspace: do not edit or revert any other workspace
path, and do not dispatch subagents.

Copy the live R139 lower test, fake, wrapper, and included retained contract
into the disposable tree. Copy live R138 production into a disposable source
tree and link only its include directory as needed. Apply the sealed R142 patch
only inside the disposable tree, then make the R143 changes there with
`apply_patch`.

## Required R143 changes

### 1. Observable exact-status write

In `expect_exact_range_success()`, set
`f->urb.UrbHeader.Status = USBD_STATUS_NOT_ACCESSED` immediately before calling
the actual production entry point. Retain the existing required
`USBD_STATUS_SUCCESS` postcondition. This must kill a production mutant that
omits `header->Status = USBD_STATUS_SUCCESS` from
`complete_io24_clock_source_range()`.

### 2. Boundary-wide libusb call witness

Add an `unsigned api_calls` field to the end of `struct io24_fake_counts` in
both the contract and fake so their ABI-shaped definitions remain identical.
Define one fake-local increment macro and invoke it as the first operation of
every externally defined `libusb_*` function in
`tests/wineusb_winusb_urb_fake_libusb.c`, including otherwise side-effect-free
device, descriptor, bus/port/speed, config/IAD, lifecycle/event, open/close,
error-string, synchronous transfer, asynchronous transfer, claim/config/alt,
cancel, and clear-halt entry points. A call with an invalid or null argument is
still a boundary call and must increment before returning.

Do not instrument libusb header macros/static-inline helpers or any
`io24_fake_*` inspection/control helper. `io24_fake_libusb_reset()` already
zeroes the complete count structure. R142's full count snapshot must therefore
detect any libusb entry between snapshot and exact success or scope rejection.

Audit the fake after editing: every externally defined symbol beginning exactly
`libusb_` must contain the witness increment. Do not merely source-scan as
feature evidence; the executable mutants below are mandatory.

## Verification

Run `tests/wineusb_winusb_urb_contract.sh ... --control-descriptor` against the
disposable candidate and copied actual R138 production. Candidate baseline and
final restored replay must both exit 0 with `failures=0`.

Run these eleven compiled production mutants one at a time, restoring the exact
production copy between runs. Every counted mutant must compile successfully,
reach the actual fake-libusb boundary, exit feature 1, and report a nonzero
failure count:

1. R139 broad/suppress predicate.
2. Function-membership exact suppression plus direction widening.
3. Allocate/free before function-scope rejection.
4. Coherent non-function exact tail corruption.
5. Exact suppression only for coherent non-function metadata.
6. Synchronous `libusb_control_transfer()` followed by the correct local exact
   response.
7. Targeted first-49-byte caller-buffer corruption after generic submission for
   the function/in-scope direction miss.
8. Function-membership recipient widening.
9. Omit the exact local `header->Status = USBD_STATUS_SUCCESS` write.
10. Call `libusb_get_device_descriptor(libusb_get_device(handle), &probe)` in
    the exact path before returning the correct local response.
11. Make the same device/descriptor probe immediately before the expected
    function-scope rejection.

Harness exit 2, compiler failure, a source scan, or an exit 1 without executed
contract failures is not feature evidence.

## Report contract

Write the complete report to
`.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-9-r143-implementer-report.md`.
Include:

- disposable directory path;
- exact live/base and candidate SHA-256 values for both proposed files;
- baseline and final replay command/result;
- the eleven-mutant table with exit and failure counts;
- the complete audited list of externally defined `libusb_*` functions;
- confirmation that copied production was restored byte-identically after
  every mutant;
- any harness attempt that exited 2, kept separate from evidence;
- self-review and concerns.

Return only status, report path, one-line baseline/mutant summary, and concerns.

## Global constraints

Offline host and hardware-free only. Do not invoke Wine or any prefix, USB/io24
device or sysfs path, driver build/staging, network, firmware, preset/effect,
UC/Voice FX, or live hardware. Do not alter production, live tests, wrappers,
support, snapshots, manifests, prior evidence, or protected paths. Stop if a
required step cannot be completed entirely inside the disposable tree.
