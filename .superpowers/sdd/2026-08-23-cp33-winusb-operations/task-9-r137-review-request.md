# Task 9 R137 additive-evidence review request

## Authority and boundary

Read R137 and its completion entry at the end of `task-9-report.md`, plus the
R137 decision in `task-9-r136-review.md`. Production remains frozen. This is a
read-only review of the unchanged R136 candidate together with one additive
copied-fixture package. A PASS may reopen only the already-bounded Task-9
production correction; it cannot complete Task 9 or claim Wine, USB, device,
firmware, preset, effect, or hardware behavior.

## Immutable inputs

- R136 head: `task-9-r136-head.sha256`, 3/3, manifest SHA-256
  `f1f81159399034bf492f419c6e3fda61fadc2305251cd2833b9710ad0ec98298`.
- R136 review record: `task-9-r136-review.md`; holistic PASS and targeted
  REQUEST CHANGES solely for missing ordinal-two executable evidence.
- Prior R136 evidence: `task-9-r136-mutants/manifest.sha256`, 54/54, manifest
  SHA-256
  `ca111ccab7208d44704bee1ab411e1d5c3d636c31bcd709abca4fea1e4aa4148`.
- Additive R137 evidence:
  `task-9-r137-second-intervals/manifest.sha256`, 56/56 unique non-self files,
  manifest SHA-256
  `5d273ba5347f12783e227580da2c56d20f59c66b1d14769504d9342b842b4513`.

Verify each manifest from its documented directory, then rerun
`task-9-r137-second-intervals/replay.sh` from the repository root. Confirm the
R136 head and prior bundle remain exact. Do not edit or regenerate artifacts.

## Required replay result

| Case | Compile | Run | Failures | Retained | Direct/helper/bad markers |
| --- | ---: | ---: | ---: | ---: | ---: |
| second admission, R135 hookless control | 0 | 1 | 203 | 0 | 0 |
| second admission, unchanged R136 hook | 0 | 1 | 204 | 1 | 0 |
| second completion, hook-bypass control | 0 | 1 | 203 | 0 | 0 |
| second completion, unchanged R136 hook | 0 | 1 | 204 | 1 | 0 |

Both normalized control/corrected comparisons must be exact after removal of
only the intended retained-latch line and normalization of source line numbers
and the terminal failure count. Each fixture must arm only operation ordinal
two, make exactly two helper allocations and two helper frees, preserve the
original four admitted objects and 4/4 pairwise retirement journal, preserve
request outcomes, and expose no alternate-selection or later-task behavior.

## Independent review lenses

The targeted reviewer must decide whether the four copied fixtures close the
sole R137 ordinal-two gap with fair controls. Inspect the exact source copies,
mutation diffs, arm placement, helper route, allocation/free assertions,
retirement and outcome preservation, stored logs/exits, replay script, and
normalized pair comparison. Try to construct a candidate that omits only the
second admission or second completion retained hook while the package still
passes.

The holistic reviewer must re-evaluate the unchanged R136 candidate together
with both the original 54-file package and the additive 56-file package. Hunt
for false greens, source-only substitutes, fixture seams visible to production,
state leakage, arithmetic/wrap dependence, unfair hook bypass, missing failed
attempt coverage, weakened original-IRP/accounting guarantees, or scope creep
into Tasks 11-13. Confirm that the additive package did not reopen any live
source or prior artifact and that the existing lower, mutex, list, identity,
retirement, reset, and terminal-join evidence remains intact.

Return `PASS` only with no Critical, Important, or material Minor finding.
Otherwise return `REQUEST CHANGES` with severity, exact file/line evidence, a
passing bad implementation or evidence bypass, and the smallest correction.
The two reviews must be independent and read-only. No Wine, prefix, device,
USB/sysfs device path, driver/build/staging, network, firmware, preset/effect,
or live hardware action is authorized.
