# Task 9 R149 isolated implementer report

Timestamp: 2026-08-28T15:49:12-07:00

## Outcome and authority

R149 is a controller-verified, test-only successor proposal for the two
Important lifecycle-oracle gaps that rejected R148. It remains unapplied and
unreviewed. Task 9 remains active, and this report grants no live-edit,
production, Wine, USB/device, staging, or closure authority.

All candidate edits and executions occurred in disposable copies under
`/tmp/io24-r149-proposal.taXRrO`. The direct proposal changes exactly:

- `tests/wineusb_winusb_urb_contract.c`;
- `tests/wineusb_winusb_urb_fake_libusb.c`; and
- `tests/wineusb_winusb_urb_contract.sh`.

The proposal applies directly to the frozen live head and reconstructs all
three candidate files byte-for-byte with zero fuzz.

## Exact identities

- direct proposal patch:
  `69ad5fb4e1f406a947313ba662cfefff73a45e6d1487086994c3ae0f1d18fa95`;
- candidate lower contract:
  `29082348c3d29d75a99e9290c0c54fe8586a3fc8d4bc248e61f1633a1efe59ac`;
- candidate fake:
  `1096aa0298a3950103d1ce1a5497b2afb07d43b41a8832fa03954282ef8a9539`;
- candidate wrapper:
  `6c2b64c2e1a7b328af951f6d33df36739b51683eeb8bfbac98ccaa6dbadea7cf`;
- evidence archive:
  `f9d9879bf0806482d555c7c69fe7e75348e173df0344634b758fb48fffe00527`;
- standalone verifier:
  `88eccca8a613d552692cf3112ed79cba72746284c44e7013f3d49154896d30d9`.

Frozen live identities remain:

- production `unixlib.c`:
  `ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`;
- upper contract:
  `eb3323df6df6fc40745e992263ada5ab2a83319e40851af55d58d2c46d359380`;
- lower contract:
  `7dfe09e4dbc0d3463a2c407791c91771326f0c0037d33dd804e64c82ee0b0afa`;
- fake:
  `c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb`;
- wrapper:
  `4076a1bda411fe2295f8f1afe2c6f54ee0a49bbf93632a95d03c316a2a0b0829`.

## R149 corrections

The lower rejection-state helper now requires the captured pipe-table pointer
to be a currently live tracked allocation before reading its bytes. Pointer
identity still gates the check, and an unknown or released pointer returns
false without dereference.

The fake allocation observer now preserves released pointer identity, reports
per-pointer liveness, recognizes address reuse, and resets before each fresh
fixture allocation. The wrapper always compiles this observer into the fake;
the older reclamation audit remains opt-in through its existing environment
flag.

The fake active-configuration result is now a bounded deep mutable view of the
configuration, interface, alternate-setting, and endpoint graph. Exact release
poisons every returned layer. Invalid or oversized source graphs fail with a
libusb error instead of producing a partial view.

Relative to R148, the successor adds 135 lines and removes five across the
three files. Most of that delta makes the nested fake view explicit and
readable; the lower liveness assertion itself is two additions.

## TDD and source-bound results

The final oracle was first rerun against the exact R148 candidate. Both clean
controls exited 0 with zero failures, while all three source-bound lifecycle
executions also escaped at exit 0 with zero failures. This is the required TDD
RED witness.

The same oracle against R149 produced:

| Execution | Exit | Assertions | Classification |
| --- | ---: | ---: | --- |
| clean `--control-descriptor` | 0 | 0 | clean control |
| clean retained `--red` | 0 | 0 | clean control |
| same-address table release, focused | 1 | 1 | feature RED |
| cached nested config after release, focused | 1 | 10 | feature RED |
| cached nested config after release, retained | 1 | 5 | feature RED |
| final clean `--control-descriptor` | 0 | 0 | clean restoration |
| final clean retained `--red` | 0 | 0 | clean restoration |

No counted mutant timed out, crashed, emitted `HARNESS:`, or substituted exit 2
for a product assertion. The wrapper's usage, unsupported-mode, and
missing-input cases were separately executed and each remained harness exit 2.

The first R149 run used an intentionally literal nested-release mutant on
every traversal. It produced real assertions but cascaded into a later
retained timeout, so that run was classified harness-invalid and excluded. The
mutant was narrowed to one deterministic early-release traversal, then rerun
against both R148 and R149 from fresh copied trees. Only the uninterrupted,
bounded revised matrix is sealed.

## Evidence and controller verification

`task-9-r149-isolated-evidence.tar.gz` contains 86 manifest-listed files plus
its manifest. Both rows include exact mutated and restored production source,
zero-fuzz diffs, deterministic recipes, pre/post/restored hashes, logs, exits,
structured results, and row manifests. The matrix binds the two mutants to all
six R148/R149 executions.

The standalone verifier checked all 86 manifest entries, four row manifests,
four zero-fuzz row reconstructions, the direct three-path proposal
reconstruction, clean and feature-exit classifications, safe archive paths,
and all five frozen live identities. It returned:

`R149_VERIFY PASS archive=f9d9879bf0806482d555c7c69fe7e75348e173df0344634b758fb48fffe00527 manifest=86/86 rows=2 executions=3 tdd_red=3 clean=4 proposal_paths=3 live_surface=5/5`

The older opt-in pipe-table reclamation audit was also rerun under R149 and
exited 0 with `completions=3 failures=0`.

## Gate status

Controller construction and verification: `PASS`.

Independent targeted review: pending.

Independent holistic review: pending.

R149 application and Task 9 closure remain frozen. Battery was 53 percent and
charging at this checkpoint.
