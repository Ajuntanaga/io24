# Task 9 R136 mandatory review

## Candidate and verified integrity

The reviewed candidate is immutable `task-9-r136-head.sha256`, 3/3, at
manifest SHA-256
`f1f81159399034bf492f419c6e3fda61fadc2305251cd2833b9710ad0ec98298`.
Its exact two-file base-to-head delta is 142 lines at SHA-256
`2e6b0f8973785d9e07df829008108ea77a7a19965e0e266e53f059b652001949`.
Both reviewers verified the base/head/frozen/controller/mutant manifests, live
equality, and replayed the 54-file evidence bundle at BAT0 31 percent.  The
declared five cases reproduced exactly.  Controller evidence remains function
feature RED at 203, actual-lower feature RED at twelve, lifecycle/standalone
binding/lower retained GREEN, and ASan/UBSan marker-clean.

## Holistic review

PASS with no Critical, Important, or material Minor finding.  It accepted the
default-no-op retained hook, before-failure invocation, Boolean/reset-safe
latches, exact admission/completion scopes, alternate exclusion, balanced
replay cases, direct journal, identity/outcome/pairwise retirement, mutex,
locked-list/insertion/order, terminal join, frozen paths, and Tasks 11-13
boundaries.

## Targeted review

REQUEST CHANGES with one Important evidence gap.  The live code arms both
admissions and both completions, but every preserved retained-allocation case
executes only operation ordinal one:

- admission helper allocation is armed only for the first dispatch;
- completion helper allocation occurs only in the first completion (both
  replacement pairs are preallocated there);
- the failed-attempt probe also targets only the first completion; and
- the replay matrix contains no second-index case.

A passing bad candidate can remove the retained begin/end calls around only
the second admission and second completion.  All five R136 cases still target
the first arms and retain their exact declared results.  The package therefore
does not executable-prove all four intervals without falling back to source
inspection.

All other R136 evidence reviewed cleanly.

## R137 decision

Production cannot reopen.  Preserve the live 3/3 R136 candidate, its 54-file
bundle, controller logs, manifests, and reports byte-for-byte.  No live source,
test, support, wrapper, production, RANGE, or prior artifact is reopened.

Authorize only a new additive task-local second-ordinal replay package.  It
must contain exact source copies/diffs, compile/run logs and exits, instructions,
a replay script, and a SHA-256 manifest for:

- second-admission hookless/R135 control at the unchanged 203 failures;
- second-admission R136 at 204 with exactly one retained-latch failure;
- second-completion hook-bypass control at 203; and
- second-completion R136 at 204 with exactly one retained-latch failure.

Each case must arm only operation ordinal two, balance helper allocations and
frees, preserve the original 4/4 journal and outcomes, compile successfully,
exit feature 1, and have zero direct-lens, harness, crash, or sanitizer marker.
Fresh independent reviews of the unchanged R136 head plus the sealed additive
package remain mandatory before production can reopen.
