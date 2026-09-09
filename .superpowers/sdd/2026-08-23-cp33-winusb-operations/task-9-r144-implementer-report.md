# Task 9 R144 isolated implementer report

## Isolation and delta

All work was contained in `/tmp/io24-r144-proposal.q7GOKX`. Live production,
tests, wrappers, support, snapshots, and device-facing paths were untouched.
The sealed R143 two-file patch dry-ran and was applied only there; R144 then
changed only `tests/wineusb_winusb_urb_contract.c`.

| path | live R139 SHA-256 | R143 SHA-256 | R144 SHA-256 |
| --- | --- | --- | --- |
| `tests/wineusb_winusb_urb_contract.c` | `7dfe09e4dbc0d3463a2c407791c91771326f0c0037d33dd804e64c82ee0b0afa` | `048243af556bd5e68176ca211d74825506f6297f7ed5c85c71e5712e7a3b4f32` | `2a9365fa828674f8f5ae040df6ceefc4d664a3af1a3365f5df2dd786dfd9c50b` |
| `tests/wineusb_winusb_urb_fake_libusb.c` | `c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb` | `e1087e04a025d4456b7996a0077e491295096d2ca066b86be71a4ae378a0cb9c` | `e1087e04a025d4456b7996a0077e491295096d2ca066b86be71a4ae378a0cb9c` |

R144 converts the complete backend comparison to the side-effect-free
`control_backend_unchanged()` predicate. Generic pre-backend rejections,
malformed exact admission rejections, and the forked exact null-buffer child
all capture and require the entire snapshot, including R143's `api_calls`
witness. The child predicate is part of the `_exit()` condition. Existing
status, storage, count, record, allocation, submission, pending, and context
assertions remain explicit.

Endpoint-recipient validation remains a distinct retained helper because the
active-endpoint validator intentionally performs descriptor lookup; it does
not claim pre-backend rejection. This preserves its prior contract while every
helper that does claim pre-backend rejection now uses the full predicate.

Copied active production was restored after each mutation to SHA-256
`ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`.

## Baselines and final replays

The disposable candidate and copied production ran through the local offline
function-binding build and libusb headers.

| command mode | baseline | final restored replay |
| --- | --- | --- |
| `--control-descriptor` | exit 0, `failures=0` | exit 0, `failures=0` |
| `--red` retained suite | exit 0, `failures=0` | exit 0, `failures=0` |

## Mutant replay

Each of the fourteen rows below was freshly compiled and executed against the
final R144 candidate and copied active production. Every log emitted the
fake-boundary pass marker, exited feature status 1, and reported nonzero
contract failures; production was restored hash-identically after each run.

| # | mutant | exit | failures |
| ---: | --- | ---: | ---: |
| 1 | broad/suppress predicate | 1 | 19 |
| 2 | membership suppression plus direction widening | 1 | 15 |
| 3 | allocate/free before scope rejection | 1 | 8 |
| 4 | coherent non-function tail corruption | 1 | 1 |
| 5 | coherent non-function suppression | 1 | 5 |
| 6 | synchronous control then local exact response | 1 | 3 |
| 7 | first-49-byte direction-miss corruption | 1 | 1 |
| 8 | membership recipient widening | 1 | 10 |
| 9 | omit success-status write | 1 | 3 |
| 10 | exact device/descriptor probe | 1 | 3 |
| 11 | scope-rejection device/descriptor probe | 1 | 8 |
| 12 | malformed-header device/descriptor probe | 1 | 1 |
| 13 | exact null-buffer device/descriptor probe | 1 | 1 |
| 14 | generic oversized-control rejection device/descriptor probe | 1 | 1 |

All fourteen mutant logs contain `WineUSB pipe-observe fake-libusb behavior:
pass`. Production restore SHA matched after every run. No harness exit 2
occurred in the R144 replay.

## Fake-boundary audit and self-review

The compiled fake exports exactly 32 `libusb_*` symbols. Each has the R143
first-operation increment; the raw source has 33 `IO24_FAKE_API_CALL()`
references because the extra reference is the macro definition. The fake ABI
tail remains `api_calls` in both contract and fake definitions.

No Wine/prefix, USB or sysfs, driver build/staging, network, firmware,
preset/effect, or live hardware action occurred.
