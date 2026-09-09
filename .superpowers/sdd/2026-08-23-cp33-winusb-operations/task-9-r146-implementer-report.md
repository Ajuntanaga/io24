# Task 9 R146 isolated implementer report

## Isolation, scope, and candidate

All implementation and execution work was contained in
`/tmp/io24-r146-proposal.Zsw8AT`. No live test, production, build, manifest,
review, resume, device-facing, or other workspace file was edited. The sealed
R145 patch dry-ran and applied only in that temporary tree. The resulting
direct patch was verified there against frozen R139 and changes exactly:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

| path | frozen R139 SHA-256 | sealed R145 SHA-256 | R146 SHA-256 |
| --- | --- | --- | --- |
| contract | `7dfe09e4dbc0d3463a2c407791c91771326f0c0037d33dd804e64c82ee0b0afa` | `54ef231be5aca88eec2c5ade8a27979be63947538e0eda6635acbae18010f64f` | `68082796be702013ea4b58284bb2666d0037f5ce50c889c7b53f45a5548b4fc5` |
| fake | `c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb` | `855268ed48a60b4448874bb75c0c63091a28ec2b610805edcdcf6744a91b16bc` | `399b21b57ad6519042683510159a62268a0b24e109924a69f365beec72f340fc` |

R146 appends ABI-identical journal fields to both `io24_fake_record`
definitions: ordinals for get-device, active-configuration, and
free-configuration; get-device input/result; active-configuration input/result;
and free-configuration input. Pointer observations use `uintptr_t`. The fake
records each ordinal after the global first-operation witness and its immediate
dedicated counter increment, without an additional boundary call. Existing
whole-record `memset` reset covers the full journal.

Endpoint rejection retains R145's exact count delta, checks ordinal order and
pointer lineage after actual production returns, copies only those verified
journal values into the expected record, and then compares the complete
snapshot. Status, zero-control, no-pending, null-context, forbidden-operation,
caller-buffer, and generic/malformed/null no-backend assertions remain intact.

Copied active production was restored after every mutation and before final
replay to `ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`.

## Baseline and final replay

The local offline harness compiled copied actual production and executed it
through the fake boundary. Fresh baseline and final restored replay both pass:

| mode | baseline | final |
| --- | --- | --- |
| `--control-descriptor` | exit 0, `failures=0` | exit 0, `failures=0` |
| retained `--red` | exit 0, `failures=0` | exit 0, `failures=0` |

## Fresh 19-mutant replay

Each row was freshly compiled and executed against final R146 test code and
copied production. Every row emitted `WineUSB pipe-observe fake-libusb
behavior: pass`, exited feature status 1, had nonzero failures, and was
followed by exact production restoration. None counted as a compiler failure,
harness exit 2, source scan, or unexecuted exit 1.

| # | mutation | exit | failures |
| ---: | --- | ---: | ---: |
| 1 | broad RANGE admission/suppression | 1 | 102 |
| 2 | widened function membership/direction | 1 | 36 |
| 3 | allocate/free before scope rejection | 1 | 8 |
| 4 | non-function RANGE-tail suppression | 1 | 5 |
| 5 | non-function coherent suppression | 1 | 5 |
| 6 | synchronous control plus local exact response | 1 | 3 |
| 7 | direction-mismatch acceptance | 1 | 8 |
| 8 | endpoint-recipient membership widening | 1 | 28 |
| 9 | omit success-status write | 1 | 3 |
| 10 | exact-response device/descriptor probe | 1 | 3 |
| 11 | scope-rejection device/descriptor probe | 1 | 8 |
| 12 | malformed-header device/descriptor probe | 1 | 1 |
| 13 | null-buffer device/descriptor probe | 1 | 2 |
| 14 | oversized generic-rejection device/descriptor probe | 1 | 1 |
| 15 | extra endpoint direction-mismatch probe | 1 | 4 |
| 16 | direction rejection skips validator | 1 | 8 |
| 17 | get-device receives null handle | 1 | 3 |
| 18 | active-configuration receives substituted device | 1 | 3 |
| 19 | free-configuration receives wrong descriptor | 1 | 3 |

## Audit and bounded surface scan

The compiled fake exports exactly 32 `libusb_*` entries. All 32 have the global
witness as their first executable operation; two entries have local declarations
before that operation. Exactly three relevant dedicated increments occur
immediately after the witness. Raw source has 33 macro references because one
is the macro definition. Contract and fake journal definitions compare
byte-for-byte equal; reset coverage is one full-record reset; and the endpoint
contract has six journal assertion expressions covering all eight
ordinal/pointer observations, plus its complete expected snapshot comparison.

The R146-only two-file diff is 75 lines. Its bounded secret/payload and added
dependency, network, device, prefix, staging, firmware, preset, and effect scan
returned no matches. The temporary direct patch dry-ran, applied, and produced
byte-identical candidate tests from frozen R139. No final workspace patch was
created.

No Wine/prefix, USB/device/sysfs, build/staging, network, firmware,
preset/effect, UC/Voice FX, or live hardware action occurred.

## Concern

The endpoint oracle deliberately constrains a single three-call active-config
authority sequence. A justified future backend sequence change must update the
counter delta, journal lineage expectation, and executed mutant evidence as one
reviewed change.
