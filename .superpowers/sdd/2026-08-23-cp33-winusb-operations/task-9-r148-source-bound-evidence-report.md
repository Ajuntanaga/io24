# Task 9 R148 source-bound mutation evidence report

Timestamp: 2026-08-28T13:12:33-07:00

## Outcome

The controller-verified additive evidence supplement closes the packaging
defect identified by the first R148 targeted preauthorization review. It binds
every claimed mutation result to executable source and does not alter the
original R148 patch, candidate, test sources, fake, frozen production source,
or protected Wine prefix.

This result is not an R148 acceptance or application. The proposal remains
unapplied and Task 9 remains active until clean targeted and holistic
independent reviews are recorded.

## Sealed inputs and live identity

- Original direct patch:
  `23333adc2918a72e2f1b32c53713533620f1be782373d1fcd389f4c598f2d08a`
- Original isolated evidence archive:
  `561da904b991e9fcf41c55f1c95230f7a8f90d5e24c228069e9f606b22dea4a1`
- Frozen live production `unixlib.c`:
  `ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`
- Frozen live upper contract:
  `eb3323df6df6fc40745e992263ada5ab2a83319e40851af55d58d2c46d359380`
- Frozen live lower contract:
  `7dfe09e4dbc0d3463a2c407791c91771326f0c0037d33dd804e64c82ee0b0afa`
- Frozen live fake:
  `c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb`

The replay generator verified these identities before execution and rechecked
the four live paths afterward.

## Source-bound supplement

- Evidence archive:
  `task-9-r148-source-bound-evidence.tar.gz`
- Archive SHA-256:
  `36f43b038bb0bab62fde7975a7acd0a14de8e6f33946ce077e12e6e4c65b6a06`
- Generator SHA-256:
  `7128f9c802b068bc0d1ef226b9420fef776b49d1afa8674ad0b425db02703297`
- Standalone verifier SHA-256:
  `73a1da232b9c24b6efbda22fabbd5cff67a920c12e63e685992faad6ceae3d59`

The archive contains 313 manifest-listed files plus its top-level manifest.
For each of the 29 rows it contains the exact mutated `unixlib.c`, a unified
diff, a deterministic recipe, pre-run and post-run mutated hashes, a restored
source copy and hash, the execution log and exit, a structured result, and a
row manifest. All 29 diffs apply with `patch --fuzz=0` to the sealed base and
reconstruct the recorded mutated file byte-for-byte. The 29 mutated source
hashes are distinct.

All 29 executions were feature REDs: exit 1 with the row-specific expected
nonzero failure count and no harness diagnostic. Rows 1-28 each emitted the
fake pass marker once. Row 29 emitted no fake pass marker and carried the
retained-assertion witness required for the literal unconditional early-release
case. The before/after focused and retained gates all exited 0 with zero
failures and no harness diagnostic.

The independent controller verifier re-extracted the archive into a fresh
temporary directory, checked 313/313 package-manifest entries and all 29 row
manifests, reconstructed all 29 mutants from their diffs, and rechecked the
classification, restoration, baseline/final, embedded-generator, archive-path,
and live-surface invariants. Its result was:

`R148_SOURCE_BOUND_VERIFY PASS archive=36f43b038bb0bab62fde7975a7acd0a14de8e6f33946ce077e12e6e4c65b6a06 manifest=313/313 rows=29 reconstructed=29 unique_mutants=29 clean_replays=4 live_surface=4/4`

## Replay containment and recovery note

The complete replay ran sequentially at low CPU and I/O priority inside a
network-unshared bubblewrap sandbox. The workspace was read-only, `/tmp` was
the only writable work area, `/dev` was minimal, and every wrapper run had a
bounded timeout. No Wine, protected-prefix, USB, device, driver staging,
firmware, preset/effect, or network operation occurred. Battery was 78 percent
and discharging after verification, above the 10 percent stop threshold.

The first generator attempt stopped at row 16 with harness exit 2 because its
transcribed deterministic recipe omitted one closing parenthesis. The source
was restored exactly. The recipe was corrected by one character, row 16 was
validated in a new disposable tree, and the entire 29-row replay was restarted
from row 1 in another new tree. Only the uninterrupted full replay is included
in the sealed archive; the stopped and targeted disposable trees remain
outside it for diagnosis.

## Gate status

Controller verification: `PASS`.

Independent targeted review: pending against the combined original R148 and
source-bound supplement.

Independent holistic review: pending against the combined original R148 and
source-bound supplement.

R148 application and Task 9 closure remain frozen.
