# Task 9 R147 isolated proof

Timestamp: 2026-08-26T00:27:11-07:00

All candidate tests and every production mutation ran in disposable `/tmp`
trees.  Live tests and active production were not edited.

## Baseline, final, and hashes

| Replay | Exit | Result |
| --- | ---: | --- |
| implementer baseline focused | 0 | `failures=0` |
| implementer baseline retained | 0 | `failures=0` |
| implementer final focused | 0 | `failures=0` |
| implementer final retained | 0 | `failures=0` |
| controller final focused | 0 | `failures=0` |
| controller final retained | 0 | `failures=0` |

```text
45c33598b8cf74298248a4e5e0ad3826527259c8dc8474e7e0d8fe1007c4681a  candidate contract
bd76d84e99227549eb587317971c33707457b56d93de3a90e1e5672b509bab15  candidate fake
ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1  restored copied production
```

## Fresh production-mutant matrix

Each row compiled, executed copied production through fake libusb, emitted
`WineUSB pipe-observe fake-libusb behavior: pass`, exited 1, and reported the
listed nonzero failure count.  Production was restored after every row.

| # | Incorrect production behavior | Failures |
| ---: | --- | ---: |
| 1 | broad RANGE admission and suppression | 102 |
| 2 | widened function membership and direction | 39 |
| 3 | allocate/free before scope rejection | 8 |
| 4 | suppress non-function RANGE tail | 5 |
| 5 | suppress RANGE by function interface count | 5 |
| 6 | synchronous control before local exact response | 3 |
| 7 | accept endpoint direction mismatch | 10 |
| 8 | widen endpoint-recipient membership | 28 |
| 9 | omit exact RANGE success status | 3 |
| 10 | exact-response device/configuration probe | 3 |
| 11 | scope-rejection device/configuration probe | 8 |
| 12 | malformed-header device/configuration probe | 1 |
| 13 | null-buffer device/configuration probe | 2 |
| 14 | oversized generic-rejection probe | 1 |
| 15 | extra endpoint direction-mismatch probe | 4 |
| 16 | direction rejection skips validator | 8 |
| 17 | get-device receives a null handle | 3 |
| 18 | active configuration receives a substituted device | 3 |
| 19 | free configuration receives the wrong descriptor | 3 |
| 20 | mutate the caller handle before validation and use it | 8 |
| 21 | free the correct descriptor before traversal | 77 |
| 22 | endpoint reject corrupts storage, length, and status | 5 |
| 23 | oversized generic reject corrupts the same caller state | 1 |
| 24 | omit the required invalid URB-status write | 14 |

The 24 canonical logs have 24 unique SHA-256 values.  Failed broad
substitutions, inherited logs, and the original unscoped early-free harness
failure are excluded.  The 54-member evidence archive contains the 24 log/exit
pairs, four baseline/final logs, and the final fake binary and disassembly.

## Independent controller replay

The controller rebuilt the candidate in `/tmp/io24-r147-controller.atIrt1`
and freshly exercised three central counterexamples:

- pre-validation handle mutation: exit 1, 8 failures, including comparison to
  the captured pre-call handle;
- function-scoped early descriptor free: exit 1, 77 failures, with the fake
  pass marker and no signal or harness failure;
- endpoint caller-state corruption: exit 1, 5 complete-fixture comparison
  failures.

After exact restoration, focused and retained controller replays both exit 0
with zero failures and copied production matches `ba3172e...d53051`.

## Boundary audits

- compiled fake exports exactly 32 `libusb_*` entries;
- source contains 33 global-witness references including the macro definition;
- for all 32 exports, the first disassembled access to `counts` is
  `counts+0x40`, the global witness;
- the three journal functions then access dedicated counters at offsets
  `0x44`, `0x48`, and `0x4c`, respectively;
- source contains exactly three immediate dedicated increments;
- contract and fake count/record layouts normalize byte-identically, and reset
  clears the complete count and record objects;
- an executable probe proves exact-free poisoning and complete refresh of the
  mutable configuration view;
- the direct patch has 11 hunks across exactly two allowed paths, passes a
  dry-run, and reconstructs both candidate hashes byte-for-byte;
- the bounded added-line scan finds no secret, credential, added include,
  dependency, network, device-node, prefix, staging, firmware, preset, or
  effect surface.

No protected prefix, USB or device access, driver build or staging, network,
firmware, preset/effect, UC/Voice FX, or live-hardware operation occurred.
