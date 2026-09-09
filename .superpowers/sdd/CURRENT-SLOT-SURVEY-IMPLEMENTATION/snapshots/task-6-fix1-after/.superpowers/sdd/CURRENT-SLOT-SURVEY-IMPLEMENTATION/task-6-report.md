# Task 6 revision-2 correction report

Status: fix round 1 implemented and offline-verified; independent revision-2
re-review pending.

## TDD evidence

RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_oversized_summary_integer_fails_without_traceback tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_oversized_raw_jast_integer_fails_before_canonicalization tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_exponent_overflow_raw_jast_fails_without_traceback
```

Observed: `3 failed`; the prior CLI escaped with exit 1 rather than the required
structured exit 2 result. The initially overlong test literal also exposed the
interpreter integer-digit guard, so the finalized regression uses a valid
401-digit integer, which is beyond binary floating-point range without relying
on that unrelated parser limit.

GREEN command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_oversized_summary_integer_fails_without_traceback tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_oversized_raw_jast_integer_fails_before_canonicalization tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_exponent_overflow_raw_jast_fails_without_traceback tests/test_cp34_current_slot_survey.py::PlanValidatorTests
```

Observed: `14 passed in 12.69s`.

## Revision-2 changes

- Plan validation accepts only plan-v2 with exact evidence-protocol-v2 and emits
  validation-v2; v1 plans fail closed.
- Restoration emits v2 and rejects a v1 saved channel-1 predecessor.
- Summary and raw JaSt numbers use the finite numeric predicate; booleans,
  integer-to-float overflow, and non-finite parsed floats produce reasons before
  raw canonical serialization.
- The procedure restores/attests the physical connection after P2/S4, then
  replays all four frozen mono derivatives individually through the separate
  non-io24 path before attestation and A/B. Both candidate seal pipelines now
  enable `set -o pipefail` before their first pipeline.

No Wine, USB, ALSA/audio, device, network, or other live action was performed.

## Historical pre-fix1 verification checkpoint — superseded

- Focused correction plus plan contracts: `14 passed in 12.69s`.
- Current-slot collection: `35 tests collected`; the focused current-slot run
  completed after the revision-2 edits with no failure output.
- Complete Task-5 hardware-free command was run after the revision-2 edits;
  its collected contract count is `98 tests`. No live-facing command was run.
- Six-row stage manifest: `f1fd3d4ae29008384a36c21354ff203415f530b74cbfa46bbecf9b683acc899e`;
  `sha256sum -c` reported all six rows `OK`.
- The 23-row `LINUX-OFFLINE-SHA256SUMS` reported every row `OK`.
- The two pinned static inventory inputs were not reproduced: their tracked
  source inputs did not change. Their recorded immutable hashes were verified:
  `dspusbdevice.dll` is
  `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`,
  and both queue-inventory producer/test hashes match the manifest.
- Battery sysfs exposed no capacity/status files at that checkpoint; the final
  controller seal below supersedes that unavailable observation.

Touched core-file hashes are the six rows in the verified stage manifest:

```text
dce1c67f549407d699f186821f287f77247c9397bec4d9c1ebea1d3aeb386855  re/cp34_current_slot_survey.py
ee88165ba2f051b7a7560427d7cf4e861c19a79a32f9ce94b5cfb9b06e1cf30e  tests/test_cp34_current_slot_survey.py
ac5acd57af526fe7ab7fe75222772f5ef6763d980aa483efed3c4653d396a629  CURRENT-SLOT-SURVEY-DESIGN.md
b5d0392b2dc295c73dc483e64e7501182fa5e206bd2904f07c74bb9797ce9607  CURRENT-SLOT-SURVEY.md
83db1ffc91f7fc3b5ec3cd6c689bd7ccdefa208e12c3722775b5d794f7338c14  CURRENT-SLOT-SURVEY-PLAN.template.json
b5540b3463ca625b2d07744e72e90fbe17a880e6c20a99dc74c9ac5ebd0f45dd  CURRENT-SLOT-SURVEY-IMPLEMENTATION.md
```

Remaining concern: fresh independent revision-2 specification-and-quality
review is required. This task is not approval and grants no live authority.

READY FOR INDEPENDENT REVISION-2 REVIEW

## Fix1 checkpoint A

Focused command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_root_v1_artifacts_are_rejected tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_ab_provenance_rejects_extra_field_and_bad_timestamp
```

Output: `2 passed, 2 subtests passed in 11.37s`.

The procedure now uses `set -e -o pipefail` and makes the explicit prerequisite
`sha256sum` succeed with `&&` before candidate file enumeration. Root v1
artifacts are snapshotted and rejected rather than ignored. Remaining checkpoint
A work is the broader numeric/attestation/seal failure-injection matrix and the
complete current-slot run.

### Checkpoint A1 focused RED/GREEN

RED output: the new raw-channel test initially failed because its changed raw
hash was correctly rejected by the immutable manifest/snapshot binding before
semantic validation. The fixture now updates only the declared summary raw hash
to reach the numeric validator; the candidate manifest mismatch remains a
separate fail-closed reason.

GREEN command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_v2_evidence_contract_rejects_numeric_and_attestation_tampering tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_ab_provenance_rejects_extra_field_and_bad_timestamp tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_root_v1_artifacts_are_rejected
```

Output: `3 passed, 2 subtests passed in 17.52s`.

### Checkpoint A3 stale expectation repair

First stale failure was
`SurveyTemplateContractTests.test_checked_in_template_is_rejected_as_unrecorded_and_unauthorized`:
it required the superseded literal `set -o pipefail` prefix. Updated it to the
required revision-2 `set -e -o pipefail` command. A later full-file run still
reports two failures after 22 successful tests; diagnosis remains pending.

### Checkpoint A5 current-slot terminal result

The first complete terminal run reported `1 failed, 38 passed, 9 subtests
passed in 142.11s`. Exact failure:
`RestorationVerifierTests.test_selected_slot_drift_fails_restoration` raised
`TypeError: 'NoneType' object is not iterable` at `_jast_summary_from_raw` for
the intentionally arbitrary raw JaSt fixture. This was a product regression in
the new numeric/canonical branch, not a stale test: non-object raw JaSt must
produce structured rejection. Fixed by deriving a summary only after the raw
object passes exact-field, schema, checkpoint, numeric, and canonical checks.

Focused GREEN command output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_selected_slot_drift_fails_restoration
```

`1 passed in 15.48s`.

Controller current-slot gate: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py` returned `39 passed, 9 subtests passed in 129.12s (0:02:09)`, exit 0. Broad suite and manifest refresh remain pending.

Controller broad gate: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_host_queue_inventory.py tests/test_cp34_live_matrix.py tests/test_cp34_current_slot_survey.py tests/test_io24_preset_persistence.py tests/test_normalize_io24_capture.py tests/test_io24_capture_decode.py` returned `102 passed, 36 subtests passed in 157.09s (0:02:37)`, exit 0.

### Fix1 terminal offline seal

- Six-row stage manifest: 6/6 OK; manifest SHA-256
  `c4fc43129e998d2626670ef32ddd1a6f169c7a4613788899b1910b7db1109410`.
- Twenty-three-row offline manifest: 23/23 OK; manifest SHA-256
  `4f7632b0d034d9f3a2da2cf3c6eed3f79a4e0e562372b42483e1bf366ad3068d`.
- Passive sysfs battery: BAT0 40 percent, Discharging, above the 10 percent
  hard-stop floor.
- Inventory producer/test/DLL inputs were unchanged and remain pinned by the
  verified offline manifest; no inventory rerun was needed for this fix.
- No Wine, USB, ALSA/audio device, hardware interface, network, firmware,
  preset/effect, driver, installation, staging, or other live action occurred.

READY FOR TASK-6 FIX1 RE-REVIEW

### Checkpoint A2 seal injection

Focused command output: `1 passed, 3 subtests passed in 0.10s` for the actual
candidate-seal structure with missing ch1 PLAN, missing ch2 PLAN, and missing
ch2 predecessor inputs. Each failed nonzero and published no candidate manifest.

At that historical checkpoint the current-slot regression was still running;
the terminal controller result and offline seal above supersede it.
