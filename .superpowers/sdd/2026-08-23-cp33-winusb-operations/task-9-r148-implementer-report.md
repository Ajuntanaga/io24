# Task 9 R148 isolated implementer report

Timestamp: 2026-08-26T02:45:04-07:00

## Isolation, scope, and candidate

All R148 source changes and executions were confined to copied files below
`/tmp/io24-r147-controller.atIrt1`. The live R139 tests and active R138
production remained frozen. The direct proposal changes exactly:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

Exact proposal identities:

- direct patch `task-9-r148-proposed-unified-rejection-state.patch`:
  `23333adc2918a72e2f1b32c53713533620f1be782373d1fcd389f4c598f2d08a`;
- candidate lower contract:
  `56a7aace5141dff885e4859659cc1e729031deeba76e371cbbcc1b64ebdf7cf5`;
- candidate fake:
  `bd76d84e99227549eb587317971c33707457b56d93de3a90e1e5672b509bab15`;
- restored copied and live production:
  `ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`.

The patch has twelve hunks, changes only the two allowed paths, dry-runs from
the frozen R139 head, and reconstructs both candidate files byte-for-byte.

## R148 corrections

R148 factors complete rejection-state comparison into two side-effect-free
helpers. The complete fixture is compared byte-for-byte. The pipe-table
pointer is compared before any pointed value is read; a changed or null
post-call pointer returns false without dereference, while an unchanged
captured non-null pointer receives the deep comparison.

The same complete snapshot now covers generic, endpoint, function-scope,
malformed/mismatched/undersized exact-RANGE, and forked exact-RANGE null-buffer
rejections. Pre-call handle lineage remains authoritative for endpoint journal
checks.

The lower contract now distinguishes retained product assertion failures from
loader or symbol failures. A retained exit 1 with nonzero retained assertions
is accumulated into the lower failure count, the requested lower group still
runs, the normal execution summary is printed, and the top-level result is
feature exit 1. Retained exit 1 without assertions and every other retained
error remain harness exit 2.

## Baseline and final replay

Copied active production compiled and executed through the candidate fake.

| Replay | Exit | Result |
| --- | ---: | --- |
| baseline `--control-descriptor` | 0 | `completions=1 failures=0` |
| baseline retained `--red` | 0 | `completions=3 failures=0` |
| final `--control-descriptor` | 0 | fake pass marker, `completions=1 failures=0` |
| final retained `--red` | 0 | fake pass marker, `completions=3 failures=0` |
| direct-patch reconstruction focused | 0 | fake pass marker, `completions=1 failures=0` |

Usage, missing-module, missing-symbol, and unsupported-mode checks each remain
harness exit 2.

## Fresh 29-row production-mutant matrix

Every row compiled actual copied `unixlib.c` and executed it through the
candidate fake. Rows 1-28 emitted the fake pass marker, exited feature 1, and
reported nonzero failures. Row 29 intentionally emitted retained assertion
evidence instead of a false pass marker, continued into the requested lower
group, printed the normal lower summary, exited feature 1 with 96 failures, and
had no signal or harness substitution.

| Rows | Failure counts |
| --- | --- |
| 1-8 | 427, 50, 8, 1, 5, 3, 10, 5 |
| 9-16 | 3, 3, 8, 1, 1, 1, 8, 8 |
| 17-24 | 3, 3, 3, 8, 77, 5, 1, 1 |
| 25 | exact scope rejection changes the handle: 1 |
| 26 | malformed exact RANGE nulls the pipe-table pointer: 2 |
| 27 | exact RANGE null-buffer rejection changes the handle: 1 |
| 28 | exact scope rejection mutates the pointed pipe table: 1 |
| 29 | unconditional early descriptor release: 96 |

Canonical log names and outcomes are:

| # | Canonical log | Failures |
| ---: | --- | ---: |
| 1 | `01-broad-range.log` | 427 |
| 2 | `02-function-direction-widen.log` | 50 |
| 3 | `03-scope-backend-activity.log` | 8 |
| 4 | `04-nonfunction-tail-corrupt.log` | 1 |
| 5 | `05-nonfunction-suppress.log` | 5 |
| 6 | `06-sync-control-local-range.log` | 3 |
| 7 | `07-accept-direction-mismatch.log` | 10 |
| 8 | `08-endpoint-membership-widen.log` | 5 |
| 9 | `09-omit-range-status.log` | 3 |
| 10 | `10-range-config-probe.log` | 3 |
| 11 | `11-scope-config-probe.log` | 8 |
| 12 | `12-malformed-config-probe.log` | 1 |
| 13 | `13-null-buffer-config-probe.log` | 1 |
| 14 | `14-oversized-config-probe.log` | 1 |
| 15 | `15-extra-direction-probe.log` | 8 |
| 16 | `16-skip-direction-validator.log` | 8 |
| 17 | `17-endpoint-null-handle.log` | 3 |
| 18 | `18-endpoint-substitute-device.log` | 3 |
| 19 | `19-endpoint-null-late-free.log` | 3 |
| 20 | `20-endpoint-handle-before-reject.log` | 8 |
| 21 | `21-endpoint-early-config-free.log` | 77 |
| 22 | `22-endpoint-reject-output-corrupt.log` | 5 |
| 23 | `23-oversized-reject-output-corrupt.log` | 1 |
| 24 | `24-oversized-omit-status.log` | 1 |
| 25 | `25-exact-scope-handle.log` | 1 |
| 26 | `26-malformed-null-pipe-table.log` | 2 |
| 27 | `27-exact-null-buffer-handle.log` | 1 |
| 28 | `28-exact-scope-deep-pipe.log` | 1 |
| 29 | `29-unconditional-early-free.log` | 96 |

The canonical directory contains exactly 29 logs and 29 exit files. Every
exit is 1, every failure count is nonzero, no counted log contains a harness
or crash diagnostic, and all 29 log SHA-256 values are distinct. Copied
production was restored to the declared hash after every row.

## Boundary and reconstruction audits

- the freshly compiled fake exports exactly 32 `libusb_*` entries;
- source has 33 global-witness references including the macro definition;
- the first compiled access to `counts` is `counts+0x40` for all 32 exports;
- the three journal entries next reach dedicated offsets `0x44`, `0x48`, and
  `0x4c`, matching exactly three immediate source increments;
- normalized count and record layouts are identical between contract and fake;
- reset clears each complete count and record object once;
- an executable probe passes exact-free poisoning plus complete mutable-view
  refresh;
- the direct patch reconstructs both candidate hashes and the reconstructed
  focused wrapper exits 0 with zero failures;
- the R147-to-R148 fake delta is empty; the contract delta is 52 additions and
  six removals; and
- the bounded direct-patch scan finds no added include, command-launch or
  remote-I/O call, host-device path, or prefix literal.

## Evidence and restoration

`task-9-r148-isolated-evidence.tar.gz` contains 101 manifest-listed files plus
its manifest. Archive SHA-256 is
`561da904b991e9fcf41c55f1c95230f7a8f90d5e24c228069e9f606b22dea4a1`;
fresh extraction verified all 101 entries.

The frozen live hashes at report time remain:

- upper contract:
  `eb3323df6df6fc40745e992263ada5ab2a83319e40851af55d58d2c46d359380`;
- lower contract:
  `7dfe09e4dbc0d3463a2c407791c91771326f0c0037d33dd804e64c82ee0b0afa`;
- lower fake:
  `c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb`;
- production `unixlib.c`:
  `ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`.

No live application or device-facing action occurred. R148 remains a proposal
pending two clean independent reviews and new exact authorization.
