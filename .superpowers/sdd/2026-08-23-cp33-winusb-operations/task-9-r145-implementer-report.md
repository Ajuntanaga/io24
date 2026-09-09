# Task 9 R145 isolated implementer report

## Isolation and candidate

All implementation and replay work was contained in
`/tmp/io24-r145-proposal.LBkOuK`. Live tests, production, builds, wrappers,
snapshots, and device-facing paths were not edited. The sealed R144 patch
dry-ran and was applied only in that tree, then R145 reopened exactly:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

| path | frozen R139 SHA-256 | sealed R144 SHA-256 | R145 SHA-256 |
| --- | --- | --- | --- |
| contract | `7dfe09e4dbc0d3463a2c407791c91771326f0c0037d33dd804e64c82ee0b0afa` | `2a9365fa828674f8f5ae040df6ceefc4d664a3af1a3365f5df2dd786dfd9c50b` | `54ef231be5aca88eec2c5ade8a27979be63947538e0eda6635acbae18010f64f` |
| fake | `c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb` | `e1087e04a025d4456b7996a0077e491295096d2ca066b86be71a4ae378a0cb9c` | `855268ed48a60b4448874bb75c0c63091a28ec2b610805edcdcf6744a91b16bc` |

R145 appends ABI-identical `get_device`, `get_active_config_descriptor`, and
`free_config_descriptor` counters to both fake-count definitions. Those fake
exports call the global witness first and immediately increment their dedicated
counter. `expect_control_endpoint_reject()` snapshots the complete backend,
expects exactly three global calls plus one of each allowed dedicated call, and
then compares the whole expected state. It retains the explicit invalid-status,
zero-control, no-pending, null-context, and forbidden-operation checks.

The copied active production used for every executable replay was restored to
`ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`
after each mutation and before final runs. A full adjacent `wineusb.sys` source
closure was copied only into the temporary tree; it is setup support, not
proposal scope.

## Baselines and final replays

Both replay modes compiled copied actual production and executed it through the
fake libusb boundary. The fresh source-closure baseline and final restored
replay each returned exit 0 and `failures=0`.

| mode | baseline | final |
| --- | --- | --- |
| `--control-descriptor` | exit 0, `failures=0` | exit 0, `failures=0` |
| retained `--red` | exit 0, `failures=0` | exit 0, `failures=0` |

Two earlier partial-closure setup attempts failed at compilation (first missing
`winusb_busif.h`, then its `msos_id.h` dependency). They did not execute a
harness or production, were superseded by the full temp-only closure, and are
not mutant evidence.

## Fresh 16-mutant replay

Every row below was freshly compiled and executed against the final R145 test
candidate and copied active production. Each emitted `WineUSB pipe-observe
fake-libusb behavior: pass`, exited feature status 1, reported nonzero
failures, and was followed by an exact production restore. No counted row had
a compiler failure, harness exit 2, source-only result, or unexecuted exit 1.

| # | mutant | exit | failures |
| ---: | --- | ---: | ---: |
| 1 | broad RANGE admission/suppression | 1 | 102 |
| 2 | widened function membership/direction | 1 | 36 |
| 3 | allocate/free before scope rejection | 1 | 8 |
| 4 | non-function RANGE-tail suppression | 1 | 5 |
| 5 | non-function coherent suppression | 1 | 5 |
| 6 | synchronous control plus local exact response | 1 | 3 |
| 7 | direction-mismatch acceptance corruption | 1 | 8 |
| 8 | endpoint-recipient membership widening | 1 | 28 |
| 9 | omit success-status write | 1 | 3 |
| 10 | exact-response device/descriptor probe | 1 | 3 |
| 11 | scope-rejection device/descriptor probe | 1 | 8 |
| 12 | malformed-header device/descriptor probe | 1 | 1 |
| 13 | null-buffer device/descriptor probe | 1 | 2 |
| 14 | oversized generic-rejection device/descriptor probe | 1 | 1 |
| 15 | extra endpoint direction-mismatch device/descriptor query | 1 | 1 |
| 16 | direction-mismatch rejection skips active-endpoint validator | 1 | 2 |

## Witness audit, surface scan, and self-review

The compiled fake exports exactly 32 `libusb_*` symbols. All 32 exported
entries have `IO24_FAKE_API_CALL()` as their first operation. The raw source
contains 33 macro references because one is the macro definition. The three
dedicated increments were each found exactly once, immediately after their
respective global-witness call.

The bounded R145-only two-file delta was scanned for secret/payload and added
dependency, network, device, prefix, staging, firmware, preset, or effect
surface. It added none. The diff contains only counter fields, complete-state
comparison, endpoint allowlist accounting, and the three adjacent fake
increments.

No Wine or prefix, USB/device/sysfs, driver build/staging, network, firmware,
preset/effect, UC/Voice FX, or live hardware operation occurred.

## Concern

The proposal intentionally allows the retained active-endpoint validation
sequence only as `get_device`, `get_active_config_descriptor`, and
`free_config_descriptor`, once each. Any legitimate production evolution that
needs a different endpoint-validation backend schedule must update this local
allowlist and its executable counterexample evidence deliberately.
