# Task 9 R136 successor review request

## Authority and boundary

Read R136 at the end of `task-9-report.md` and the exact rejection in
`task-9-r135-review.md`.  Production remains frozen.  A PASS may accept only
the Task-9 RED evidence for a separate narrow production correction; it cannot
complete Task 9, CP33, firmware/preset/effect capture, or hardware behavior.

## Immutable candidate and lineage

- Rejected R135: `task-9-r135-head.sha256`, manifest SHA-256
  `fe3bd2130c4af10935088c22cf9541182d78816b2b1bb50213613073da1815ae`.
- Exact owned base: `task-9-r136-base.sha256`, 2/2, manifest SHA-256
  `16db761f908070f8220684b99a50055210d5b8bf9a7ee5ce8c0c50df615c6321`.
- R136 successor: `task-9-r136-head.sha256`, 3/3 including the frozen lower
  contract, manifest SHA-256
  `f1f81159399034bf492f419c6e3fda61fadc2305251cd2833b9710ad0ec98298`.
- Exact two-file base-to-head delta: `task-9-r136.diff`, 142 lines, SHA-256
  `2e6b0f8973785d9e07df829008108ea77a7a19965e0e266e53f059b652001949`.
- Function SHA-256:
  `b18c2f40cc0fbb4bf37ad076293cacf26ecdc43c995b3434fd262abc91f2356a`.
- Binding-support SHA-256:
  `0c066f0fb0e46e01ef42ed166762a9d27edce2b62cc5cead76b8c1a6849237b0`.
- Frozen lower SHA-256:
  `9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348`.
- Frozen fourteen-path manifest: `task-9-r132-frozen.sha256`.
- Implementer report: `task-9-r136-implementer-report.md`, SHA-256
  `6473118e2ea3d4043fb7cd11f5b01ff24e0ffb208312863e18c73847e8c30c55`.
- Controller logs: `task-9-r136-controller-logs.sha256`, 14/14, manifest
  SHA-256 `5230e9d586913ea0695cae67800f9f9a04d9b5319e993acd993749db504e78ab`.

Verify every declared manifest/diff and all three live-to-R136 comparisons.

## Fresh controller execution

- Function focused: exit 1; 35 dispatches, 29 mode IOCTLs, exactly 203 named
  feature failures; no compiler/linker/harness/crash marker.
- Function lifecycle: exit 0; 12 dispatches and zero failures.
- Standalone binding: exit 0 with its retained lifecycle pass line.
- Actual lower focused: exit 1 with exactly 12 named permit failures.
- Actual lower retained: exit 0.
- Manual ASan/UBSan/alignment: compile exit 0; function focused exit 1 with the
  same 203 failures; zero sanitizer, leak, crash, or harness marker.

## R136 correction

Binding support adds one optional allocator-attempt hook at retained
`ExAllocatePool` entry before its failure branch.  Its default is a no-op.
Function C enables the hook and records a nonwrapping Boolean retained-attempt
latch.  Exact retained intervals surround each of the two pending admissions.
Each exact completion interval arms both a nonwrapping direct latch and the
retained latch.  Alternate-selection calls remain outside those intervals.
The rejected unsigned shared-count snapshot/equality is removed, and reset
clears all latch state.  The direct four-object admission journal remains.

## Replayable adversarial evidence

`task-9-r136-mutants/manifest.sha256` seals 54/54 source, log, exit,
instruction, and replay artifacts at manifest SHA-256
`ca111ccab7208d44704bee1ab411e1d5c3d636c31bcd709abca4fea1e4aa4148`.
Independent controller replay of `task-9-r136-mutants/replay.sh` exited 0:

| Case | Failures | Retained lens | Direct lens | Bad markers |
| --- | ---: | ---: | ---: | ---: |
| admission R135 control | 203 | 0 | 0 | 0 |
| admission R136 | 204 | 1 | 0 | 0 |
| completion hook bypass | 203 | 0 | 0 | 0 |
| completion R136 | 204 | 1 | 0 | 0 |
| failed retained attempt | 204 | 1 | 0 | 0 |

Inspect the exact copied actual `main.c`, `session.c`, `transfer.c`, private
header, function C, and binding C in every case.  Admission preallocates a
replacement record/URB pair through actual-main helpers during the first
dispatch, later uses/frees that pair, retires both admitted originals, and
asserts helper allocation/free 2/2 plus original journal 4/4.  Completion
recreates four helper-routed objects across the two completions, asserts helper
allocation/free 4/4 and original journal 4/4, and has an exact hook-bypass
control.  The failed case proves the hook fires before retained failure
handling; it restores only the disposable fake's diagnostic allocation count
after asserting its one-attempt delta so teardown remains independent.

## Required adversarial review

Determine whether the default-no-op hook preserves standalone behavior and
whether the enabled nonwrapping latches cover successful and failed retained
attempts during both admissions and completions without counting alternates,
leaking reset state, or depending on arithmetic.  Inspect mutant substance and
replayability, including allocation/free balance, outcome/list/reference
preservation, exact arms, and whether the hook-bypass comparison is fair.
Confirm the direct admission journal, direct completion lens, distinct stored
outcomes, exact pairwise retirement, endpoint-map mutex, locked lower list,
insertion/order mirrors, terminal join, frozen paths, and Tasks 11-13
exclusions remain intact.  Hunt for false greens, expectation weakening,
fixture-only seams exposed to production, or unsafe ownership claims.

Return `PASS` only with no Critical, Important, or material Minor finding.
Otherwise return `REQUEST CHANGES` with severity, exact file/line evidence, a
passing bad implementation, and the smallest correction.  Do not edit files.
No source scan substitutes for feature evidence.  No Wine, prefix, USB/sysfs
device path, driver/build/staging, network, firmware, preset/effect, or live
hardware action is authorized.
