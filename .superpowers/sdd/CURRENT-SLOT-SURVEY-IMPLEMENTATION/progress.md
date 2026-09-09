# SDD ledger — plan: .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-IMPLEMENTATION.md

Started: 2026-08-29
Spec: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-DESIGN.md`
Execution choice: recommended subagent-driven development, selected by the user.
Workspace state: intentionally non-Git; the three Task 1 outputs were absent at baseline.

Ruling: The SDD Git/worktree and commit-range mechanics are replaced with per-task before/after directory snapshots, unified diff packages, implementer reports, and SHA-256 stage records — the binding implementation plan explicitly forbids initializing this workspace as Git — if wrong, review provenance is file/hash based rather than commit based and would need reconstruction in a repository later.

## Preflight conflict and interface table

| Scope | Producer -> consumer or internal agreement | Finding / ruling |
|---|---|---|
| Task 1 | Its ten validator contracts exercise the validator and CLI it creates; its stage records the two created source files. | Clean. |
| Task 2 | Its eight mapping contracts exercise the mapping functions and CLI it adds; it refreshes the same two stage rows. | Clean. |
| Task 3 | Its twelve restoration contracts exercise the verifier and CLI it adds; it refreshes the same two stage rows. | Clean, with the design as authority for evidence layout and positive-only semantics. |
| Task 4 | Its template contract consumes Task 1 validation; its procedure consumes Tasks 1-3 commands; its stage adds all planned offline artifacts. | Clean. |
| Task 5 | Its regression count is existing 63 plus new 31; its records consume Tasks 1-4 artifacts and do not grant live authority. | Clean. |
| Tasks 1 -> 2 | Task 1 creates `re/cp34_current_slot_survey.py`, its tests, and stage file; Task 2 extends and re-hashes those files. | Compatible sequential ownership. |
| Tasks 1 -> 3 | Task 1 provides `validate_plan`, CLI dispatch, tests, and stage file; Task 3 consumes validation and extends the same surfaces. | Compatible; Task 3 must preserve Task 1 contracts. |
| Tasks 1 -> 4 | Task 4's checked-in template is intentionally consumed by Task 1's validator; both touch tests and the stage. | Compatible; template must remain invalid by design. |
| Tasks 1 -> 5 | Task 5 consumes the validator/test/stage artifacts in the full suite and integration records. | Compatible; no live-ready claim follows from validator success. |
| Tasks 2 -> 3 | Task 2 produces map result schema and frozen Mix A channel; Task 3 consumes those fields while sharing CLI/tests/stage. | Compatible; the frozen channel cannot be reselected after effect analysis. |
| Tasks 2 -> 4 | Task 4 documents Task 2's exact `map-channel` command and shares tests/stage. | Compatible; procedure may document but not execute acquisition. |
| Tasks 2 -> 5 | Task 5 consumes mapper implementation, contracts, hashes, and counts. | Compatible. |
| Tasks 3 -> 4 | Task 4 documents Task 3's `verify-restoration` command and shares tests/stage. | Compatible; restoration remains the gate for any positive outcome. |
| Tasks 3 -> 5 | Task 5 consumes verifier implementation, contracts, hashes, and remaining limitations. | Compatible. |
| Tasks 4 -> 5 | Task 5 integrates and seals the procedure/template/stage without widening their authority. | Compatible; `NOT_AUTHORIZED` and `UNRECORDED` sentinels remain fail-closed. |

Preflight result: no plan/spec contradiction requires implementation changes before Task 1.

Task 1: implementation complete; non-Git stage `3e1eb7e...` / `cde3609...`; focused result 10 passed; independent review pending.

Task 1 review: spec gate blocked; one real fail-closed gap enters fix round 1.

Ruling: Candidate-2 eligibility and positive/null outcome semantics are runtime restoration rules assigned explicitly to Task 3, not fields in Task 1's literal plan schema — Task 1 retains `stop_on_first_positive`, while Task 3 must reject an ineligible second candidate — if wrong, a syntactically valid plan could be mistaken for proof that runtime sequencing was enforced before the restoration verifier runs.

Ruling: P2 stable-state equality and event-level non-overlap are post-run evidence checks assigned to Task 3 and the ordered operator procedure assigned to Task 4; Task 1 can only require the three discrete checkpoint declarations and forbid a continuous claim — if wrong, callers may overread plan validation as proof of runtime restoration or non-overlap.

Ruling: Physical source identity fields are intentionally run-specific provenance, so Task 1 validates that they are recorded and that the declared source kind is external line level; it cannot prove the truth or safety of arbitrary physical descriptions from JSON — if wrong, a contradictory or dishonest description could pass the static preflight until the authorization and operator review gate.

Task 1: minor (deferred): `_load` should use a context manager and omit the unused exception binding.

Task 1: fix round 1/5 (1 addressed, 0 open — exact candidate/action shape now fail-closed; non-Git snapshots task-1-fix1-before..task-1-fix1-after).
Task 1: complete (non-Git stage `5bfba25...` / `ee12d73...`, review clean after fix round 1; 1 deferred minor).

Task 2: implementation complete; non-Git stage `7feb313...` / `4fc9947...`; focused result 8 passed plus Task 1 regression 10 passed; independent review pending.

Task 2 review: spec/quality gate blocked; three evidence/serialization issues enter fix round 1.
Task 2: minor (deferred): add explicit boundary contracts for threshold 0.80, near-ties, upper input level, and the cadence tolerance edge if final review judges them merge-blocking.

Task 2: fix round 1/5 (3 addressed, 0 open — exact PCM semantics, single-buffer hash/parse, and strict null JSON; non-Git snapshots task-2-fix1-before..task-2-fix1-after).
Task 2: complete (non-Git stage `dd26812...` / `7fd9b7d...`, review clean after fix round 1; 1 deferred minor group).

Task 3: implementation complete; non-Git stage `201ae06...` / `4d7e40e...`; restoration result 12 passed plus Task 1-2 regression 18 passed; independent review pending.

Task 3 review: gate blocked; JaSt provenance plus three strictness findings enter fix round 1.

Ruling: `P0.json`, `P1.json`, and `P2.json` are the three JaSt summaries and are already loaded and compared, so the review statement that no JaSt summaries are consumed is factually incorrect; however, the design also requires each summary to reference its untouched raw JaSt snapshot, so that underlying provenance gap is real and will be fixed — if wrong, the added raw-reference contract may be stricter than the implementation-plan brief but remains fail-closed and may require adapting future summary generation.

Ruling: `AB.json` must use the existing `re/cp34_live_matrix.py analyze-slot` output schema `cp34-slot-survey-audio-v1`, not a newly invented wrapper schema; its two dry and two active rows must bind by safe relative path and SHA-256 to the frozen-channel derivatives in the evidence snapshot — the implementation plan's architecture explicitly says the new verifier consumes the existing classifier output — if wrong, a future wrapper format would need a deliberate versioned adapter instead of passing this verifier.

Task 3: minor (deferred): require non-negative integer `monotonic_ns` values rather than merely finite increasing numbers if final review deems it blocking.

Task 3: fix round 1/5 (4 addressed, 1 open — analyzer top-level/metric-row schema still incomplete; non-Git snapshots task-3-fix1-before..task-3-fix1-after).

Task 3: fix round 2/5 (1 addressed, 1 new open — oversized JSON integer can escape finite-number validation via `OverflowError`; non-Git snapshots task-3-fix2-before..task-3-fix2-after).

Task 3: fix round 3/5 (1 addressed, 0 open — oversized analyzer integers now fail deterministically; non-Git snapshots task-3-fix3-before..task-3-fix3-after).
Task 3: complete (non-Git stage `1bb029a...` / `7ee2c14...`, review clean after fix round 3; 1 deferred minor).

Task 4: implementation complete; six-row stage manifest verified; all 31 current-slot contracts passed; independent review pending.

Task 4 review: gate blocked; three procedure defects enter fix round 1.
Task 4: minor (deferred): replace “source control” wording with task-local staged/sealed artifact wording.
Task 4: minor (deferred): ensure the final seal enumeration is NUL-safe for whitespace or shell-special filenames if not inherently solved by the overwrite fix.

Task 4: fix round 1/5 (2 addressed, 1 open — final seal pipeline does not propagate upstream enumeration/sort failure; non-Git snapshots task-4-fix1-before..task-4-fix1-after).

Task 4: fix round 2/5 (1 addressed, 0 open — upstream seal-pipeline failures now prevent publication; non-Git snapshots task-4-fix2-before..task-4-fix2-after).
Task 4: complete (six-row non-Git stage verified, 31 tests passed, review clean after fix round 2; 2 deferred minors).

Task 5: implementation complete; regression 94 passed plus 27 subtests; six direct and three RIP-relative inventory sites reproduced; stage 6/6 and offline manifest 23/23 verified; independent review pending.

Task 5 review: REQUEST CHANGES; four load-bearing verifier/evidence gaps enter fix round 1.

Ruling: Task 5 fix ownership expands from integration records into `re/cp34_current_slot_survey.py`, its tests, and the minimal offline buffer-analysis seam in `re/cp34_live_matrix.py` plus its tests — Task 5's mandated rejection gate found real runtime holes and explicitly requires a new RED/GREEN cycle before sealing — if wrong, the fix crosses the original per-task file map and will require splitting into a follow-up implementation plan.

Ruling: Canonical map and A/B decisions must be recomputed from the already snapshotted immutable WAV bytes, not trusted from claimed JSON; the existing offline classifier is the source of truth and may expose a byte-buffer entry point, while the verifier must not duplicate its signal algorithm — if wrong, stricter canonical equality could reject a future intentionally versioned analyzer result until the schema/version adapter is updated.

Ruling: Channel-2 eligibility must re-evaluate the complete sealed channel-1 evidence under the same immutable run snapshot in addition to validating the saved restoration-result invariants — if wrong, the refactor may be stricter than the minimal saved-result gate and require a separately versioned predecessor-evidence bundle.

Task 5: fix round 1/5 (4 addressed, 0 open — canonical map and A/B replay now derive from immutable bytes, all raw captures are mandatory, and channel-2 eligibility recomputes channel-1 evidence; non-Git snapshots task-5-fix1-before..task-5-fix1-after; diff SHA-256 `d5c4afef745e754fcd7441420d91af61b88cf8c62b8564dc822d29afa4a1c2eb`).
Task 5: complete (regression evidence 94 passed plus 27 subtests; stage 6/6 and offline manifest 23/23 verified; scoped independent review clean after fix round 1; deferred timestamp minor remains for final whole-stage triage).

Final whole-stage review: REQUEST CHANGES; seven load-bearing gaps enter the single final fix wave: raw-to-derivative binding, raw JaSt semantic derivation, immutable channel-2 continuation, recursive plan-shape closure, run-path binding, complete five-impulse cadence, and earned post-restoration audible attestation.

Ruling: All seven final-review findings are accepted as blocking and will be addressed together by one fixer in the single final whole-stage fix wave, along with the three identified integration-record inconsistencies where their records are touched — each permits either false positive evidence, an unreachable documented workflow, authority widening, or stale seal claims — if wrong, this wave may impose stricter evidence formats and path/workflow constraints than the intended current-slot survey and require a new versioned design rather than an implementation repair.

Final fix wave: implementation complete; regression evidence 94 passed plus 31 subtests; stage 6/6 `d713a3b...`; offline manifest 23/23 `0bd5759...`; inventories 6 direct plus 3 RIP-indirect; non-Git snapshots final-review-fix1-before..final-review-fix1-after; diff SHA-256 `297c899a7a41a727baae0d0d3ba7951e255f02e529508a9217695b3e3948ab4f`; scoped re-review pending.

Final scoped re-review: REQUEST CHANGES; three original findings remain partial and one new interim-seal defect remains open: fail-closed JaSt numerics, earned four-derivative audible attestation, binding-protocol versioning for candidate-scoped continuation, and `pipefail` on both interim seals. Five other original findings and all three integration-record inconsistencies are closed.

Ruling: The closed final-review cycle will not receive an unauthorized second patch wave; the recommended continuation is a separately versioned correction amendment and fresh bounded TDD/review cycle, relying on the user's instruction to choose the recommended option for all remaining decisions — if wrong, treating the blanket recommendation as approval to amend the binding evidence protocol could exceed the intended design authority and the current stage must remain unsealed until explicit approval.

Revision 2 amendment: `CURRENT-SLOT-SURVEY-DESIGN.md` now defines `cp34-current-slot-evidence-v2`, candidate-scoped immutable manifests/results, a terminal root seal, and four-derivative post-restoration audible attestation; `CURRENT-SLOT-SURVEY-IMPLEMENTATION.md` adds binding Task 6 and supersedes conflicting revision-1 instructions.

Ruling: Revision 2 will bump the accepted plan, validation-result, and restoration-result schemas to v2 while leaving map, A/B, raw-JaSt, summary-JaSt, and audible-attestation schemas unchanged — this makes the changed evidence protocol explicit and rejects stale revision-1 plans/results without needlessly versioning stable payloads — if wrong, downstream offline tooling may require compatibility adapters or a broader schema migration than this bounded correction provides.

Task 6: implementation complete; focused correction plus plan contracts 14 passed; current-slot collection 35 tests; complete offline collection 98 tests with no reported failure; stage 6/6 `f1fd3d4...`; offline manifest 23/23 `1f1dac8...`; non-Git snapshots task-6-before..task-6-after; diff SHA-256 `960683dc3e76fec8bc425bb929fe0ede086fdfb1861c626fb6654264c06fecbd`; fresh independent revision-2 review pending.

Task 6 review: REQUEST CHANGES; five Important findings enter fix round 1: numeric validation does not cover every raw/summary numeric leaf, audible evidence is not bound to four derivative observations and ordering, forbidden root v1 artifacts are ignored, candidate brace groups can mask initial-hash failure, and active records retain stale revision-1 pass claims.

Ruling: Revision-2 audible evidence must use an exact four-row observation contract bound by safe path, SHA-256, dry/active role, heard boolean, separate non-io24 playback/monitoring identity, and monotonic post-physical-restoration/pre-A-B ordering evidence; aggregate counts alone are insufficient — if wrong, the added provenance may exceed what a future authorized operator can record reliably and require a simpler but still independently verifiable attestation adapter.

Ruling: JaSt identifier and processing-map integers must be exact non-boolean integers in explicit bounded domains before canonicalization, while level-like fields remain finite numerics; the CLI additionally converts expected malformed-evidence serialization exceptions into structured exit-2 failure — if wrong, an actual JaSt value outside the chosen bounds could be rejected despite otherwise valid raw provenance.

Ruling: Because the reviewed attestation payload must gain exact four-file observations and monotonic provenance, its schema and the timestamped physical-restoration schema advance to v2, while a new `cp34-current-slot-ab-provenance-v1` binds the saved attestation hash, canonical A/B hash, and later analysis timestamp without changing the existing A/B classifier schema — if wrong, this adds an unnecessary evidence file and schema migration that a simpler action-log extension could have represented.

Task 6: fix round 1/5 implementation complete (5 addressed, re-review pending): total raw/summary numeric validation and bounded processing map, exact physical/audible/AB provenance, explicit root-v1 rejection, failure-injected atomic candidate seals, and current revision-2 integration evidence. Controller verification: current-slot 39 passed plus 9 subtests; broad 102 passed plus 36 subtests; stage 6/6 `c4fc431...`; offline manifest 23/23 `4f7632b...`; BAT0 40 percent discharging; non-Git snapshots task-6-fix1-before..task-6-fix1-after; diff SHA-256 `53c4482c7853b47754f400d8e1793682a958c65808c3a3a14b81d87272b372af`.

Task 6: fix round 1 re-review REQUEST CHANGES; root-v1 rejection, candidate seals, and active records are closed, while parser-limit integers, malformed P0/physical/S4 timestamp crash paths, and playback/monitor/operator-attestation type and non-io24 validation enter fix round 2.

Ruling: `_strict_json_loads` must translate Python's integer-digit conversion `ValueError` into the same deterministic malformed-JSON evidence path consumed by existing callers, rather than globally changing interpreter limits or broadly swallowing verification exceptions — if wrong, a valid but merely very large JSON integer may receive a generic parse reason instead of a field-specific numeric-bound reason.

Ruling: Playback and monitoring identities must be distinct nonempty strings and reject case-insensitive io24 identity markers, while `operator_attested` must be an exact boolean; all timestamp comparisons occur only after exact nonnegative-integer validation — if wrong, a legitimate separately isolated path with an ambiguous io24-like product label could be rejected and require a more explicit versioned path-kind field.

Task 6: fix round 2/5 implementation complete (parser-limit integers, missing-P0 and malformed-timestamp guards, strict audible identity/operator types); controller verification current-slot 40 passed plus 11 subtests, broad 103 passed plus 38 subtests; stage 6/6 `466ed687...`; offline manifest 23/23 `7b14d59a...`; BAT0 22 percent discharging; non-Git snapshots task-6-fix2-before..task-6-fix2-after; diff SHA-256 `61f5912f91c87dc8b86fd77ed071fbeba7da040b7fec9f962d44674b86a6ef97`; scoped re-review pending.

Task 6: fix round 2 re-review REQUEST CHANGES; parser-limit, missing-P0, S4 timestamp, identity/operator validation, and all prior runtime protections are closed; an isolated non-integer physical timestamp still reaches an early comparison, and PLAN mislabels a historical fix1 hash/battery block as current. Both enter fix round 3. BAT0 pre-round check: 17 percent discharging.

Ruling: Fix round 3 is restricted to validating `physical_time` before any audible ordering comparison plus an isolated subprocess regression, and relabeling the contradictory PLAN block; no broader schema or behavior change is justified — if wrong, another hidden ordering consumer may remain outside the focused repair and require a wider provenance refactor.

Task 6: fix round 3/5 implementation complete; isolated physical-timestamp plus golden positive/inconclusive result 3 passed in 42.21s; stage 6/6 `8b78a3fc...`; offline manifest 23/23 `abd28432...`; BAT0 15 percent discharging; non-Git snapshots task-6-fix3-before..task-6-fix3-after; diff SHA-256 `d6243b174c1e74e8cde2107458a9e118826a1f46f173f9b0ae8def4ab98df475`; scoped re-review pending.
