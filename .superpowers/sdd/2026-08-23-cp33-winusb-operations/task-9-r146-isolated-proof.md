# Task 9 R146 isolated proof

Timestamp: 2026-08-25T23:12:42-07:00

All candidate test changes and production mutations occurred in disposable
`/tmp` trees. Live tests and active production were not edited.

## Baseline and final replay

The candidate compiled copied active R138 `unixlib.c` and executed it through
fake libusb. Fresh baseline and final restored runs both passed:

| Mode | Baseline | Final |
| --- | --- | --- |
| `--control-descriptor` | exit 0, `failures=0` | exit 0, `failures=0` |
| retained `--red` | exit 0, `failures=0` | exit 0, `failures=0` |

Candidate hashes:

```text
68082796be702013ea4b58284bb2666d0037f5ce50c889c7b53f45a5548b4fc5  tests/wineusb_winusb_urb_contract.c
399b21b57ad6519042683510159a62268a0b24e109924a69f365beec72f340fc  tests/wineusb_winusb_urb_fake_libusb.c
```

Copied production was restored after every mutation and at final close to:

```text
ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1  source/dlls/wineusb.sys/unixlib.c
```

## Fresh executable mutant matrix

| # | Incorrect copied-production behavior | Exit | Failures |
| ---: | --- | ---: | ---: |
| 1 | Broad RANGE admission/suppression | 1 | 102 |
| 2 | Widened function membership/direction | 1 | 36 |
| 3 | Allocate/free before scope rejection | 1 | 8 |
| 4 | Non-function RANGE-tail suppression | 1 | 5 |
| 5 | Coherent non-function suppression | 1 | 5 |
| 6 | Synchronous control plus local exact response | 1 | 3 |
| 7 | Direction-mismatch acceptance | 1 | 8 |
| 8 | Endpoint-recipient membership widening | 1 | 28 |
| 9 | Omit exact success-status write | 1 | 3 |
| 10 | Exact-response device/descriptor probe | 1 | 3 |
| 11 | Scope-rejection device/descriptor probe | 1 | 8 |
| 12 | Malformed-header device/descriptor probe | 1 | 1 |
| 13 | Null-buffer device/descriptor probe | 1 | 2 |
| 14 | Oversized generic-rejection device/descriptor probe | 1 | 1 |
| 15 | Extra endpoint direction-mismatch probe | 1 | 4 |
| 16 | Direction rejection skips validator | 1 | 8 |
| 17 | Get-device receives null handle | 1 | 3 |
| 18 | Active-configuration receives substituted device | 1 | 3 |
| 19 | Free-configuration receives wrong descriptor | 1 | 3 |

Every row compiled, executed actual copied production through fake libusb,
emitted `WineUSB pipe-observe fake-libusb behavior: pass`, and failed for
contract assertions. No compiler failure, harness exit 2, source scan, or
unexecuted exit 1 is counted.

## Independent controller adversarial replay

In separate `/tmp/io24-r146-security.7qECfw`, the controller freshly
executed three same-count variants:

- null get-device handle: exit 1, 3 authority failures;
- correct get-device call but null active-config device: exit 1, 3 lineage
  failures;
- free `NULL` before lookup and omit the acquired descriptor free: exit 1,
  12 ordinal/lineage failures.

All emitted the fake pass marker. After exact restoration, focused replay
returned exit 0 with `failures=0` and production matched `ba3172e...d53051`.

## Boundary and surface audit

The compiled fake exports exactly 32 `libusb_*` symbols. All 32 have the
global witness as their first executable operation; the raw source has 33
macro references including its definition. Exactly three dedicated increments
immediately follow the relevant witness. Contract and fake journal definitions
are identical, complete reset covers the journal, and only individually
verified journal fields are admitted into the expected full snapshot.

The R146-only delta adds no secret, credential, network, dependency, device,
prefix, staging, firmware, preset, or effect surface. No Wine/prefix,
USB/device/sysfs, build/staging, network, firmware, preset/effect, UC/Voice FX,
or live-hardware action occurred.

The direct patch
`task-9-r146-proposed-endpoint-authority-journal.patch` is SHA-256
`ec62d2a8d3ca3d0cb65b20ba52f466af277281efc858997bf5e313728dec214f`,
touches exactly the two requested test paths, dry-runs from live R139, and
reconstructs both candidate hashes byte-for-byte.

