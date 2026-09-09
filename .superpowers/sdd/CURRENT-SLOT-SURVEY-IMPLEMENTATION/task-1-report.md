# Task 1: fail-closed survey plan validator

Status: complete, offline-only; no Git repository was initialized or changed.

## Implementation

`re/cp34_current_slot_survey.py` provides `validate_plan(path: str) -> dict`
and the `validate-plan PLAN.json` CLI.  It uses only the Python standard
library, reads one JSON input file, hashes its input bytes, prints exactly one
JSON result, exits 0 only for `VALID`, and otherwise exits 2 without a
traceback.  It imports no project driver code and performs no hardware,
network, Wine, ALSA, USB, or device operation.

The validator fail-closes on the fixed CP34 serial, authorization status,
candidate order and current slots, two long manual toggles, source provenance,
lowercase stimulus SHA-256, six-channel ALSA shape, P0/P1/P2 reads,
non-continuous claims, safe evidence location and run-id basename, battery
floor, complete prohibited-action set, and any string containing `UNRECORDED`.

## TDD evidence

Initial RED command:

```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::PlanValidatorTests::test_accepts_exact_current_slot_plan
```

Result: failed as expected while `re/cp34_current_slot_survey.py` was absent
(CLI invocation returned 2 instead of 0).

Initial GREEN used the same command and produced `1 passed in 0.03s`.

For each remaining contract, the focused test was run while the corresponding
condition was absent and failed as expected: non-object input, serial or
authorization, candidate ordering, stop-on-positive, source/unrecorded value,
audio shape, state-read/interface claim, toggle actions, unsafe path/battery/
prohibitions, and schema.  After the minimal associated condition was added,
the preceding contract passed; the final focused suite below confirms all ten
contracts green.

## Exact final commands and results

```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::PlanValidatorTests
```

Result:

```
..........                                                               [100%]
10 passed in 0.49s
```

```
sha256sum re/cp34_current_slot_survey.py tests/test_cp34_current_slot_survey.py
```

Result:

```
3e1eb7ea4590bd7aa08e38b002494451e124d19954eade579819c08023ffab0e  re/cp34_current_slot_survey.py
cde3609bf53b9bab09ca96ca3eea3bd3e07761dad773eaf6abc5fc4b5011c2dc  tests/test_cp34_current_slot_survey.py
```

## Files changed

- `re/cp34_current_slot_survey.py`
- `tests/test_cp34_current_slot_survey.py`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`

## Stage record

The non-Git stage record has exactly the two required SHA-256 rows above.

## Self-review

Reviewed the CLI’s error paths, deterministic ordered reason accumulation,
JSON-only output, status/exit mapping, literal candidate order, and validator
imports.  The implementation is standard-library-only and does not grant or
exercise live authority.

## Concerns

None.  This is an offline preflight gate only; a `VALID` result does not
authorize a live survey or any hardware action.

## Fix round 1

Covering test: `PlanValidatorTests.test_rejects_wrong_toggle_count_short_press_or_mapped_action`.
It now adds an extra candidate `slot_selection` field and an extra action
`mapped_write` field.  The validator rejects both with exact-shape reasons,
preventing additional modeled behavior from being carried alongside otherwise
valid actions.

RED command:

```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::PlanValidatorTests::test_rejects_wrong_toggle_count_short_press_or_mapped_action
```

RED output: `1 failed in 0.12s`; the added candidate field incorrectly
produced exit code 0 before the exact-shape check.

GREEN command (same focused command):

```
.                                                                        [100%]
1 passed in 0.13s
```

Covering suite command:

```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::PlanValidatorTests
```

Output: `10 passed in 0.54s`.

Changed files:

- `re/cp34_current_slot_survey.py`
- `tests/test_cp34_current_slot_survey.py`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`

New stage hashes:

```
5bfba253388cf67ec7f42bf3f6a7e95aff64c9e9486ca9b964e1f1a6add481a4  re/cp34_current_slot_survey.py
ee12d731611d485c5f8b8fb85d371045682972f16c4c9da7790fed477b901ebe  tests/test_cp34_current_slot_survey.py
```

`sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256` output:

```
re/cp34_current_slot_survey.py: OK
tests/test_cp34_current_slot_survey.py: OK
```
