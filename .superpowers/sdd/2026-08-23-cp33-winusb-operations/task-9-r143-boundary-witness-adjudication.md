# Task 9 R143 complete-boundary witness adjudication request

Timestamp: 2026-08-25T21:45:47-07:00

## Verdict requested

Authorize one test-only correction in exactly:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

The complete live-R139-to-proposed delta is
`task-9-r143-proposed-boundary-witness.patch`. Its SHA-256 is
`bf02b6dc45849612ceb3929c93189f757ad25f45e8784c56134bb34fa5f5b82b`.
No production, upper test, support, wrapper, RANGE implementation, snapshot,
prior manifest, prior review, device, Wine/prefix, build/staging, firmware,
preset/effect, or live-hardware path is requested for reopening.

## Rejected predecessor

R142 was a sealed proposal and was never applied. Both mandatory
preauthorization reviewers rejected it independently:

1. its detailed backend snapshot could not observe side-effect-free libusb
   calls, so an exact or rejected path could query a device descriptor and
   still pass; and
2. `reset_control()` initialized URB status to zero, which is already
   `USBD_STATUS_SUCCESS`, so exact positives could pass when production omitted
   the required success-status write.

The live tests therefore remain the frozen rejected R139 head.

## Proposed correction

R143 retains R142's coherent three-scope matrix, complete backend snapshots,
and caller-buffer preservation checks, and closes exactly the two R142
findings:

1. `expect_exact_range_success()` writes
   `USBD_STATUS_NOT_ACCESSED` immediately before the production call and still
   requires `USBD_STATUS_SUCCESS` afterward.
2. Both contract-side definitions of `struct io24_fake_counts` gain the same
   tail `api_calls` field. The fake increments it as the first operation of
   every externally defined `libusb_*` entry point. The existing complete
   count snapshot therefore detects even otherwise side-effect-free libusb
   traffic on exact-success and function-scope-rejection paths.

The fake-boundary audit found exactly 32 exported `libusb_*` symbols and 32
entry-point increments. The raw source contains 33 macro references because
one is the macro definition. No fake-local `io24_fake_*` helper or libusb
header inline/macro is instrumented.

## Isolated proof

Only disposable `/tmp` copies were changed. The R143 candidate compiled and
executed actual active R138 `unixlib.c` through the fake-libusb boundary and
exited 0 with `failures=0` both before and after mutant replay. Candidate
SHA-256 values are:

- contract: `048243af556bd5e68176ca211d74825506f6297f7ed5c85c71e5712e7a3b4f32`;
- fake: `e1087e04a025d4456b7996a0077e491295096d2ca066b86be71a4ae378a0cb9c`.

The candidate rejected all eleven bounded bad production variants at feature
exit 1: the retained eight R142 variants plus omitted success-status write,
exact-path device/descriptor probe, and scope-rejection device/descriptor
probe. Every counted variant compiled and executed production through the
fake boundary. One initial broad-mutant draft produced harness exit 2 due to
an unused helper under `-Werror`; it was corrected and rerun, and the failed
draft is excluded from feature evidence.

The sealed patch dry-runs against the verified live R139 head. Applying it to
a disposable two-file copy produces both candidate hashes byte-for-byte.

## R138 lineage reconciliation

The implementer correctly flagged that
`task-9-r138-production-base/.../unixlib.c` has SHA-256 `ff9bea...` while the
copied active file has SHA-256 `ba3172...`. The former is explicitly the
pre-edit R138 snapshot. Controller comparison of all nine authorized R138
production paths found exactly the six changes listed by the R138 implementer
report and the expected three byte-identical files. The disposable R143
production copy and its restore base are both byte-identical to active
`unixlib.c` at
`ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`.
The proposal therefore uses the active authorized R138 lineage; the differing
pre-edit snapshot is not an ambiguity or a competing production head.

## Next gate

Do not apply without explicit controller authorization. First require two
independent clean preauthorization reviews of the sealed R143 package. If the
controller then authorizes this exact two-file delta, reverify the R143
manifest, the live 2/2 R139 head, and patch dry-run; apply only the sealed
patch; replay focused and retained host gates and all eleven mutants; freeze
the corrected two-file test head; and obtain two clean independent
post-application reviews.

Only after the corrected oracle is accepted may R138 sanitizer, full
final-head mutants, production freeze/manifest, independent production review,
or Task 9 sealing resume.
