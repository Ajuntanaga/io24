# Task 9 R148 holistic review adjudication

Timestamp: 2026-08-28T15:22:25-07:00

## Scope and authority

This was a controller-side, offline adjudication of two contract-test findings.
It used disposable source copies under `/tmp/io24-r148-empirical.71iEvc`.
No project implementation, live test, fake, wrapper, manifest, Wine prefix,
USB/device path, build/staging tree, firmware, preset/effect state, or network
resource was changed.

The sealed predecessor remains:

- `RESUME.md`:
  `0f4e44b88d6b9d0bd1680f3965fe1f3d287a841ee53194b2311e911c8921d91a`;
- `task-9-r148-source-bound.sha256`:
  `3c6b77125c36f157ab8e25e4f212fc0869aed7b5b3112dec5f07f025038260d0`.

## Review verdicts recovered

- The independent targeted source-bound review returned `PASS` with no
  findings in its assigned provenance and RED-classification scope.
- The independent holistic review returned `REQUEST CHANGES` with two
  Important contract-oracle findings.
- The controller independently reproduced both findings below. R148 therefore
  remains unapplied and not accepted.

## Finding 1: same-address pipe-table release is not observed

The first disposable case inserted one release on the exact out-of-scope
class-interface rejection path while leaving the caller-visible pointer value
unchanged. The candidate oracle checked pointer identity and then compared the
pointed-to bytes, but it did not first check the fake allocator's live count.

The disposable production-copy hash was:

`52a71eef6aa37bc3ef0b1021979b614e8291ee560728275b4cb3476bc9311eaf`.

The focused wrapper result was:

`exit=0 mode=--control-descriptor completions=1 failures=0`

Log SHA-256:

`bb68ef4c1a0ddd1ace6a8c72ec9ef6bb6c2ecd4b8f1a32fea1266fec902e092e`.

This is a false green: an allocation-lifetime change occurred, but the R148
candidate contract reported a clean focused pass.

## Finding 2: cached nested configuration data survives fixture release

The second disposable case cached `bNumInterfaces` and `interface`, released
the top-level configuration object, and then completed the unchanged nested
traversal. The fake's nested interface/alternate/endpoint arrays remain static,
so its current top-level invalidation does not witness this ordering change.

The disposable production-copy hash was:

`96b683a186681a6a3e37b25468e55779f3754ff4a59d1f75228ed4c5f7336eeb`.

The candidate results were both clean:

- `exit=0 mode=--control-descriptor completions=1 failures=0`;
- `exit=0 mode=--red completions=3 failures=0`.

Log SHA-256 values:

- focused:
  `81e954a86935ba9a89147d467736431683e7aa5aaf04e4ff3583af0550d55181`;
- retained:
  `82341105290d6508705aeac84b885cda3bae05a102dc054d0be3adb8da3e5751`.

This is also a false green: the ordering changed, but both R148 candidate modes
reported clean passes.

## Frozen live identities

After adjudication, the live files remained:

- production `unixlib.c`:
  `ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`;
- lower contract:
  `7dfe09e4dbc0d3463a2c407791c91771326f0c0037d33dd804e64c82ee0b0afa`;
- fake:
  `c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb`.

## Required next proposal

A successor test-only proposal must address both oracle gaps before any R148
application can be reconsidered:

1. establish pipe-table allocation liveness before any deep comparison and
   turn lifetime loss into an ordinary feature RED without reading released
   storage;
2. make nested configuration lifetime executable, then include the cached
   nested-data early-release case in the source-bound matrix.

This adjudication grants no edit or application authority.

