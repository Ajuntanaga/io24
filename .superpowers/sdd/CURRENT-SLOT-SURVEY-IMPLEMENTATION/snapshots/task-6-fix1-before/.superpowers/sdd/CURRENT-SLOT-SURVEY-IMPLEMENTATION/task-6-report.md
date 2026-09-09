# Task 6 revision-2 correction report

Status: pending complete offline regression and independent revision-2 review.

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

## Verification and seals

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
- Battery sysfs exposed no capacity/status files in this environment, so passive
  battery state is unavailable rather than inferred.

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
