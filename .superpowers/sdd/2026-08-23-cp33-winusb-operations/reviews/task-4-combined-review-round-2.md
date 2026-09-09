# CP33 Task 4 combined independent review — fix round 2

Verdict: **PASS**

No Critical or Important issue remains. No material correctness regression or
false-green contract gap was found.

## Disposition

- **R61 — addressed.** Heap allocation and full INITIALIZE record size/pointer;
  the shared helper binds the exact output pointer to its allocation and the
  sizing header for totals 211, 181, and 163, with safe missing-event handling.
- **R62 — addressed.** Matching raw/packed `[5,2,5]` data rejects with one
  rollback release; frozen production compares every interface with all prior
  records.
- **R63 — addressed.** The fake records the exact waited handle and private
  event; two distinct errors survive clobbering close cleanup, and RELEASE also
  checks its private event.
- Prior R58-R60 and all supplemental round-1 false-green findings are addressed.

All six authorized host gates exited zero. Persisted mutation evidence was
consistent with independent executable assertions:

```text
previous-record-only uniqueness: failures=2, exit=1
hardcoded wait error:             failures=2, exit=1
wrong private wait handle:        failures=3, exit=1
conditional non-211 +1:           failures=2, exit=1
isolated wrong allocation pointer/size: failures=1, exit=1
```

Evidence verified: round-0/round-1/round-2 manifests each 16/16; task seal 15
unique entries, excludes itself, 15/15; workspace equals round-2 head; exact
three-file fix scope; full patch 2,762 lines/14 headers; round-2 diff 498
lines/3 headers. R46 remains the explicit Task-6 carry.

```text
rubric             e0346c271ef28e754ab61d8b2588f8d574346a7e218709b4ded5ca2bb152bfca
plan               013feee53959cd8efdf5a13e6a83ffacf2a6517f43def0566ed95f534b0fe981
spec               8d04b44c89860b34afe0560caa9fa83c12aa80ca1e49f93734ce899dd56294a7
production DLL     6a2ea0ae74185fffbbb81f957bd0af83bda3f044e9212927b8d71920ba700876
user contract      badf5808b4ca99ec0334bb315c8b4165f304c9458ce865bbc10a1a14ff49abdc
reviewed DLL report d2cdeb834a613d9cbe852cedc83e512bdc071b4393f6f965f00ee64b3aacf052
full patch         bf7b3211d3d957d10b7245290e6c89b67572a772a01e965aaa5a7d26bd139b8c
task seal          32f0de367c6b3dfab2b70139abb1bce1bb25499b4842f1c90324c7a3db80736c
round-2 diff        e86206977a67da160374335dbdf9c819f9f0404426fae64f30edc724b40bca14
round-2 manifest    9af336450d0c823ac3aa31084ff7a168d5f35d91a536f24f9ecb9345b577ac3c
round-2 package     a6305e4a48409ac11078caf2bf9c11f93b3cb24d046c7a8682330c2d5e3991ff
```

The sole Minor was stale report-only scope wording. It was corrected after the
review to distinguish implementer-owned pre-regeneration scope from the
controller's regenerated patch/seal; the checkpoint files and manifests were
unchanged. Post-correction report SHA-256:
`3e11cb0699608a5dd81e0265df3a8bea8578d12f5b077c511d6c18f898dbbabf`.
