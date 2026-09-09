# Task 9 R149 independent preauthorization review request

Timestamp: 2026-08-28T15:49:12-07:00

## Status and authority

Review, but do not apply, the R149 test-only proposal. R148 was rejected after
holistic review proved two lifecycle-oracle false greens. R149 supersedes it
and applies directly from the still-frozen live head.

This request authorizes read-only review only. It does not authorize edits,
application, Wine or protected-prefix use, USB/device access, staging, network
access, production work, or Task 9 closure.

## Exact review set

- `task-9-r149-proposed-lifecycle-oracle.patch`
  - SHA-256:
    `69ad5fb4e1f406a947313ba662cfefff73a45e6d1487086994c3ae0f1d18fa95`
- `task-9-r149-isolated-evidence.tar.gz`
  - SHA-256:
    `f9d9879bf0806482d555c7c69fe7e75348e173df0344634b758fb48fffe00527`
- `task-9-r149-verify.sh`
  - SHA-256:
    `88eccca8a613d552692cf3112ed79cba72746284c44e7013f3d49154896d30d9`
- `task-9-r149-controller-verification.log`
- `task-9-r149-allocation-audit.log`
- `task-9-r149-allocation-audit.exit`
- `task-9-r149-harness-classification.log`
- `task-9-r149-implementer-report.md`
- `task-9-r148-holistic-adjudication-20260828T1522PDT.md`
- `task-9-report.md`

Use `task-9-r149.sha256` for the sealed controller-side review set.

## Targeted review contract

Return `PASS` only if direct evidence supports all of the following:

1. The rejection-state helper establishes allocation liveness before every
   deep pipe-table read and safely returns false for a released or unknown
   same-valued pointer.
2. The allocation observer records release and address reuse without weakening
   the older allocation-count, free-order, or close-order audit.
3. The fake's returned active-configuration graph is mutable at every traversed
   layer, exact release poisons the complete graph, and refresh produces a
   coherent bounded graph.
4. Both source mutants apply with zero fuzz, reconstruct the recorded source,
   escape R148 at exit 0, and fail R149 through actual product assertions at
   exit 1 in all three declared executions.
5. Clean focused/retained gates remain exit 0, actual harness cases remain exit
   2, and no timeout, crash, or unused compilation is counted as feature RED.

## Holistic review contract

Review the complete direct proposal from the frozen live head, not only the
small R148-to-R149 delta. Confirm that all earlier R148 rejection-state,
retained-failure, fake-boundary, layout, reset, journal, and mutable-view
contracts remain coherent.

Check the bounded deep-copy indices and failure paths, allocation interposition
and reset ordering, symbol/link behavior, forked rejection execution, and
possible address-reuse or stale-entry cases. Confirm the direct patch touches
exactly the three declared test paths and reconstructs the sealed candidates
byte-for-byte. Look for any remaining material false green, unsafe read,
unintended scope, or regression.

## Required verdict

Provide `PASS` or `REQUEST CHANGES`, with file-and-line or archive-path evidence
for every finding. A `PASS` is review evidence only and grants no application
authority. Both targeted and holistic verdicts must be clean before a separate
live-edit decision can be considered.
