# Task 9 R148 source-bound independent review request

Timestamp: 2026-08-28T13:12:33-07:00

## Status and authority

R148 is an unapplied proposal based on the frozen rejected R139 head. This
request authorizes read-only review only. It does not authorize edits,
application, Wine or protected-prefix use, USB/device access, staging, network
access, or advancement of the R138 closure gate.

The first targeted review of the original package returned `REQUEST CHANGES`
because the 29 mutation rows did not include source-bound provenance. Review
the original R148 package together with the additive supplement below. Do not
treat the supplement as an independent acceptance or as a replacement for a
full correctness review.

## Exact review set

- `task-9-r148-proposed-unified-rejection-state.patch`
  - SHA-256:
    `23333adc2918a72e2f1b32c53713533620f1be782373d1fcd389f4c598f2d08a`
- `task-9-r148-isolated-evidence.tar.gz`
  - SHA-256:
    `561da904b991e9fcf41c55f1c95230f7a8f90d5e24c228069e9f606b22dea4a1`
- `task-9-r148-source-bound-evidence.tar.gz`
  - SHA-256:
    `36f43b038bb0bab62fde7975a7acd0a14de8e6f33946ce077e12e6e4c65b6a06`
- `task-9-r148-provenance-replay.py`
  - SHA-256:
    `7128f9c802b068bc0d1ef226b9420fef776b49d1afa8674ad0b425db02703297`
- `task-9-r148-source-bound-verify.sh`
  - SHA-256:
    `73a1da232b9c24b6efbda22fabbd5cff67a920c12e63e685992faad6ceae3d59`
- `task-9-r148-source-bound-controller-verification.log`
- `task-9-r148-source-bound-evidence-report.md`
- `task-9-r148-brief.md`
- `task-9-r148-implementer-report.md`
- `task-9-r148-isolated-proof.md`
- `task-9-r148-review-request.md`
- `task-9-report.md`

Use `task-9-r148-source-bound.sha256` to verify the eight controller-side
supplement and handoff files.

## Targeted review contract

Return `PASS` only if all of the following are supported by direct evidence:

1. Every matrix row is bound to its exact mutated source, deterministic recipe,
   diff, mutated pre/post hashes, restored source/hash, execution log/exit, and
   structured classification.
2. Every diff applies with zero fuzz to the sealed base and reconstructs the
   recorded mutated source exactly.
3. Every row executes copied production through the candidate fake boundary;
   exit 1 and nonzero product assertions establish feature RED, while exit 2,
   timeout, crash, preflight rejection, or an unused compilation does not.
4. Rows 1-28 have the expected single fake pass marker. Row 29 has the retained
   assertion witness, no fake pass marker, normal lower-group continuation, and
   feature exit 1 rather than a harness substitution.
5. Before/after focused and retained gates are clean, all sources restore
   exactly, and the supplement does not weaken or bypass the original R148
   oracle.

## Holistic review contract

Review the complete R148 proposal for correctness, regression risk, recovery,
scope, and missing validation. Confirm that the unified safe rejection-state
predicates close the R147 defects across generic, endpoint, function-scope,
malformed/mismatched/undersized admission, and forked null-buffer rejection;
that pointer identity gates every deep pipe-table read; and that retained
product assertion failures remain distinguishable from genuine harness
failures.

Also verify the direct patch reconstructs the claimed candidate, the lower and
fake ABI/layout/reset/journal contracts remain coherent, and the additive
supplement is confined to evidence generation and verification. A clean verdict
requires no Critical, Important, or material Minor finding.

## Required verdict

Provide `PASS` or `REQUEST CHANGES`, with file-and-line or archive-path evidence
for every finding. A `PASS` is review evidence only; it grants no application
authority. Both targeted and holistic independent verdicts must be clean before
the controller can consider a separate live-edit authorization.
