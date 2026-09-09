# Task 9 R147 isolated implementer report

All candidate work was isolated in `/tmp/io24-r147-proposal.fTp5m4`; only the
two allowed test/fake files changed there. The sealed R146 patch applied only
in that tree. Candidate hashes are contract
`45c33598b8cf74298248a4e5e0ad3826527259c8dc8474e7e0d8fe1007c4681a`, fake
`bd76d84e99227549eb587317971c33707457b56d93de3a90e1e5672b509bab15`, and
restored copied production
`ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`.

R147 adds complete fixture and deep pipe-table snapshots for generic and
endpoint rejections; snapshots set only expected invalid status and use the
pre-call handle for journal lineage. The fake has a refreshable shallow-copied
config view, safe poisoning on exact free, and declaration-only pre-witness
locals; focused and retained final replays both exit 0 with `failures=0`.

The fake compiles and exports 32 `libusb_*` symbols; raw global-witness source
count is 33 including its definition. Copied production was restored to the
base hash before final replay.

## Final matrix and canonical logs

Rows 1--19 below are valid individual reruns. Every canonical log compiled
copied production through the fake, emitted the pass marker, exited 1, reported
nonzero feature failures, and was followed by an exact production restore.

| rows | canonical log pattern | failures |
| --- | --- | --- |
| 1--19 | `mutants/NN-varied-r147.log` | 102, 39, 8, 5, 5, 3, 10, 28, 3, 3, 8, 1, 2, 1, 4, 8, 3, 3, 3 |
| 20 | `mutants/20-handle-before-validation.fresh.log` | 8 |
| 21 | `mutants/21-early-free-safe.log` | 77 |
| 22 | `mutants/22-endpoint-corrupt-state.fresh.log` | 5 |
| 23 | `mutants/23-oversized-corrupt-state.fresh.log` | 1 |
| 24 | `mutants/24-omit-invalid-status.fresh.log` | 14 |

The unscoped early-free log and failed broad-substitution artifacts are
explicitly excluded. Fresh final `--control-descriptor` and retained `--red`
replays both exited 0 with `failures=0`; final copied production is exactly
`ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`.

The fake compiled and exported 32 `libusb_*` symbols, and
`audit/fake-final.objdump` was captured. Controller audits remain separate and
pending; this report does not claim unrun source/disassembly ordering,
mutable-view refresh/poison, direct frozen-R139 reconstruction, or bounded
delta-scan results.

No Wine/prefix, USB/sysfs, network, staging, firmware, preset/effect, or live
hardware operation occurred.
