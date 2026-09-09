# Task 9 R149 independent review adjudication

Timestamp: 2026-08-28T16:51:23-07:00

## Scope and authority

This was a file-first, offline adjudication of two independent read-only
reviews. The reviewers received only the sealed R149 paths, the targeted or
holistic contract assigned to their seat, and the frozen-workspace boundary.
They did not receive or restore stale conversation context.

No R149 byte was applied. No production, live contract, Wine or protected
prefix, USB/device, build/staging, network, firmware, preset/effect, or live
hardware surface was accessed or changed.

Before review, `sha256sum --check task-9-r149.sha256` verified every listed
entry. Three non-failing `Failed to create stream fd` host-tooling warnings
appeared; no checksum failed.

## Independent verdicts

- Targeted: `PASS` on all five declared criteria. It recorded one non-blocking
  verifier usability note: the documented no-argument invocation passes, but
  the script's undocumented relative workspace argument fails after its
  internal directory change.
- Holistic: `REQUEST CHANGES` with two Important fixture-lifetime findings.

The preserved reports are:

- `task-9-r149-targeted-review-20260828T1649PDT.md`;
- `task-9-r149-holistic-review-20260828T1649PDT.md`.

## Blocking findings

### Allocation identity can still be restored invisibly

The fake observer records current liveness for an address but no monotonic
per-allocation generation. A release followed by a same-address allocation and
byte restoration can therefore satisfy pointer equality, current liveness,
and byte equality even though the allocation identity changed. The sealed
free-only row proves dead-allocation detection, not this replacement case.

A successor must snapshot and compare a monotonic allocation generation or an
equivalent allocation identity, and must include a source-bound
release/reallocate/restore case that fails through product assertions at exit
1.

### Baseline capture reads before it validates lifetime

`capture_control_reject()` copies the published pipe table before consulting
the observer. A fixture-setup regression that releases the table before
returning success can therefore cause an invalid lifetime read, stale-byte
comparison, or harness failure before the post-call liveness predicate runs.

A successor must use an observer-backed snapshot helper that validates
liveness and captures allocation identity before copying the table. An
isolated successful-setup early-release case must produce a bounded product
assertion at exit 1 without a signal, timeout, invalid read, or harness exit 2.

## Adjudication

R149 is rejected and remains unapplied. Task 9 remains active and blocked at
the test-oracle review gate. The cached nested-configuration lifetime defect is
closed for the declared traversal, but the pipe-table lifetime defect is not
fully closed.

The five frozen live identities were rechecked after preserving the reviews
and remain byte-for-byte equal to `RESUME-20260828T1549PDT.md`:

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

## Exact next step

No successor work is authorized by these reviews. If the user authorizes a
bounded successor proposal, begin from the same frozen live head and limit the
candidate to the test-only paths strictly needed for allocation-generation
observation, safe baseline capture, and their executable regression cases.
Keep the no-argument verifier invocation authoritative; its optional path
handling may be repaired as evidence-tooling hygiene without treating that
minor issue as a product defect.

Any successor must be controller-verified and receive new clean targeted and
holistic read-only verdicts before a separate application decision. Do not
resume the R138 closure gate, advance Task 9, or apply any proposal on this
adjudication alone.
