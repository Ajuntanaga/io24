# Task 9 R146 endpoint-authority journal adjudication request

Timestamp: 2026-08-25T23:12:42-07:00

## Verdict requested

Authorize one test-only correction in exactly:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

The complete live-R139-to-proposed delta is
`task-9-r146-proposed-endpoint-authority-journal.patch`. Its SHA-256 is
`ec62d2a8d3ca3d0cb65b20ba52f466af277281efc858997bf5e313728dec214f`.
It changes 239/31 lines in the lower contract and 16/15 lines in fake libusb.
No production, upper test, support, wrapper, RANGE implementation, snapshot,
prior manifest/review, Wine/prefix, device/USB/sysfs, build/staging, firmware,
preset/effect, or live-hardware path is requested for reopening.

## Rejected predecessors

R143's global call witness did not cover every rejection helper. R144 extended
the complete snapshot but left the endpoint-rejection exception unconstrained.
R145 counted exactly one get-device, active-configuration, and
free-configuration call, but did not bind those calls to their order or
authority arguments. A copied production variant using
`libusb_get_device(NULL)` retained the same three counts and passed R145 at
exit 0 with zero failures.

R143 through R145 were never applied. The live lower contract and fake remain
the frozen rejected R139/R132 bytes.

## Proposed correction

R146 retains every R145 assertion and appends ABI-identical journal fields to
both `io24_fake_record` definitions. The journal records:

- global API ordinals for get-device, get-active-configuration, and
  free-configuration;
- get-device handle input and device result;
- active-configuration device input and descriptor result; and
- free-configuration descriptor input.

Pointer values use `uintptr_t`. Each target fake entry keeps the global
witness as its first executable operation and its dedicated counter increment
as the immediate next operation. Whole-record reset zeroes the journal.

`expect_control_endpoint_reject()` first preserves R145's exact three-call
counter delta. After actual production returns, it requires consecutive global
ordinals in the retained order and proves:

`f->device.handle -> get-device result -> active-config input`

and:

`active-config result -> free-config input`.

Both intermediate results must be non-null. Only after those relations pass
does the helper copy the verified journal values into the expected record and
compare the complete backend snapshot. The invalid status, zero-control,
no-pending, null-context, forbidden-operation, caller-buffer, and all
generic/malformed/null zero-backend checks remain intact.

## Isolated proof

All candidate and mutation work occurred under
`/tmp/io24-r146-proposal.Zsw8AT`. Both fresh baseline and final restored
focused/retained runs compiled active R138 production through fake libusb and
exited 0 with `failures=0`.

Candidate SHA-256 values:

- contract:
  `68082796be702013ea4b58284bb2666d0037f5ce50c889c7b53f45a5548b4fc5`;
- fake:
  `399b21b57ad6519042683510159a62268a0b24e109924a69f365beec72f340fc`.

All nineteen fresh copied-production mutants compiled, reached fake libusb,
emitted its pass marker, exited feature status 1 with nonzero failures, and
were followed by exact restoration to active R138 production SHA-256
`ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`.
The matrix includes all sixteen R145 variants plus null get-device authority,
substituted active-config device, and wrong descriptor free.

Controller replay independently passed focused and retained modes, then
independently killed the three same-count authority variants with 3, 3, and 12
feature failures respectively. A final restored focused run passed.

The fake audit reports exactly 32 exported `libusb_*` entries, 32 global
first-operation witnesses, three immediate dedicated increments, identical
journal definitions, full-record reset, and six journal assertion expressions
covering all eight observations before the complete snapshot comparison.

## Patch and production identity

The sealed patch dry-runs from the verified live R139 head. Applying it to a
fresh two-file copy produces both candidate hashes byte-for-byte. Active live
and disposable production match post-R138
`ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`.
The distinct `ff9bea...` file is the named pre-edit R138 production-base
snapshot, already reconciled across the nine authorized production paths; it
is not a competing head.

## Next gate

Do not apply without two independent clean preauthorization reviews and new
explicit controller authorization for this exact patch hash and two-file
scope. Immediately before any authorized application, reverify the R146
manifest, live R139 2/2 head, active production hash, patch hash, and patch
dry-run.

After application, replay focused and retained gates plus all nineteen
mutants, freeze the corrected two-file head, and obtain two clean independent
post-application reviews. Only then may the frozen R138 sanitizer, complete
final-head production mutant, freeze/manifest, and final production-review
closure resume. Task 9 is not complete.
