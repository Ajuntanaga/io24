# Task 3: post-run restoration verifier

Status: complete and sealed; offline/read-only implementation only.

## Implementation

`re/cp34_current_slot_survey.py` now provides
`verify_restoration(run_dir: str, candidate: str) -> dict` and the CLI:

```text
verify-restoration RUN_DIR --candidate ch1-slot1
```

The result schema is `cp34-current-slot-restoration-v1`. Exit zero is reserved
for `RESTORED`; every failure exits two with `RESTORATION_FAILED`. The result
includes `SIGNATURE_PRESENT` or `INCONCLUSIVE`, the exact candidate scope,
frozen channel, all snapshotted input hashes, deterministic accumulated
reasons, and the verbatim limitation `JaSt cannot prove every internal DSP
byte.`

The verifier revalidates the snapshotted `PLAN.json`, enforces the fixed
candidate/slot/channel, exact event sequence and strictly increasing monotonic
timestamps, exactly two long manual toggles, P1 inversion, exact P2 readable
state restoration, Task 2's `cp34-current-slot-map-v1` interface, frozen-channel
use through S4 and the A/B/attestation evidence, valid six-channel S4 WAV,
physical connection restoration, and the channel-2 predecessor gate. A second
candidate is eligible only when the channel-1 restoration result is exactly
`RESTORED` plus `INCONCLUSIVE`.

The input manifest is exact over every actual pre-verification input. It rejects
unsafe absolute/parent/non-normalized paths, duplicates, missing files, rows for
absent files, omitted actual inputs, symlinks, special files, and hash
mismatches. Only `EVIDENCE-SHA256SUMS`, `RESTORATION.json`, `REPORT.md`, and
`SHA256SUMS` are excluded. Files are read once into immutable buffers; parsing,
hashing, plan validation, map-raw comparison, and S4 validation all use those
same bytes. Inputs use strict JSON decoding, and CLI output uses
`allow_nan=False`.

No project driver is imported. The implementation has no USB, ALSA, Wine,
network, hardware, install, stage, transfer, firmware, reset, or write path.
The positive CLI test also proves that the evidence tree is byte-for-byte
unchanged after verification.

## TDD evidence

Initial enabled-first RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_enabled_first_restores_with_signature_present
```

Initial RED output before CLI registration:

```text
F                                                                        [100%]
FAILED tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_enabled_first_restores_with_signature_present
1 failed in 0.07s
```

The failure was the expected `AssertionError: 2 != 0` from the unregistered
command.

GREEN command: the same focused command.

GREEN output:

```text
.                                                                        [100%]
1 passed in 0.06s
```

The remaining eleven contracts were then added around bypassed-first/null
evidence, slot drift, inverse enable state, multiple P2/physical failures,
extra events, short presses, concealed mapped writes, missing S4, exact
manifest failures, physical attestation, and conditional channel-2 eligibility.

Self-review strengthened the mapped-write contract so an extra
`mapped_write: true` field cannot hide beside a nominal manual-toggle kind.
Its focused RED command was:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_mapped_write_is_rejected
```

RED output:

```text
F                                                                        [100%]
FAILED tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_mapped_write_is_rejected
1 failed in 0.08s
```

The exact failure was that `mapped_write_prohibited` was absent from the
reported reasons. Exact per-kind event fields and explicit mapped-write-key
rejection repaired it. The same focused command then produced:

```text
.                                                                        [100%]
1 passed in 0.06s
```

## Final verification

Final restoration command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests
```

Final output:

```text
............                                                             [100%]
12 passed in 0.45s
```

Required combined Task 1/2 regression command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::PlanValidatorTests tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests
```

Final output:

```text
..................                                                       [100%]
18 passed in 6.64s
```

Syntax check:

```text
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from pathlib import Path
source = Path('re/cp34_current_slot_survey.py').read_text(encoding='utf-8')
compile(source, 're/cp34_current_slot_survey.py', 'exec')
print('syntax compile: OK')
PY
```

Output:

```text
syntax compile: OK
```

## Files changed

- `re/cp34_current_slot_survey.py`
- `tests/test_cp34_current_slot_survey.py`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`
- `.superpowers/sdd/CURRENT-SLOT-SURVEY-IMPLEMENTATION/task-3-report.md`

The workspace remains intentionally non-Git; no repository was initialized and
no commit was attempted.

## Stage hashes

Printed hash command:

```text
sha256sum re/cp34_current_slot_survey.py tests/test_cp34_current_slot_survey.py
```

New rows:

```text
201ae0611c9458de53084b3f6f9df095ba15fd523ea945d7f076385f1db0ccf1  re/cp34_current_slot_survey.py
4d7e40e06498566a89d19ea861bec0e2156b5ce272c165aa89972e42aa331fb5  tests/test_cp34_current_slot_survey.py
```

Manifest verification command:

```text
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
```

Output:

```text
re/cp34_current_slot_survey.py: OK
tests/test_cp34_current_slot_survey.py: OK
```

The stage manifest contains exactly these two rows.

## Self-review

- Path traversal: manifest paths must be normalized relative POSIX paths; root
  and input symlinks, parent components, absolute paths, and special files fail.
- Manifest completeness: the test covers duplicate, unsafe, absent, omitted,
  and mismatched rows in one invocation and confirms all deterministic reasons
  are returned.
- TOCTOU/hash consistency: each included input is read once with `O_NOFOLLOW`;
  file identity/size/mtime are checked before and after the read, and all later
  parsing and hashing uses the immutable byte snapshot.
- Strict JSON: `NaN`/`Infinity` inputs are rejected and all CLI serialization
  uses `allow_nan=False`.
- Positive-only semantics: null/non-specific A/B or audible evidence remains
  `INCONCLUSIVE`; only exact `SIGNATURE_PRESENT` plus two active and zero dry
  operator-attested repeats becomes positive. Model and title must be explicitly
  unresolved and are never inferred.
- Exact restoration: state scalars require both value and JSON type equality;
  the multi-fault contract proves P2 gain/main drift and failed physical
  restoration are all reported rather than short-circuited.
- Boundary scan: imports are Python standard-library only; there are no driver,
  USB, ALSA, Wine, network, device, mutation, installation, or staging calls.

No subagents or reviewers were used, as required.

## Concerns

None within Task 3. `RESTORED` is an offline evidence-gate result only. It does
not establish complete internal DSP-byte restoration and grants no authority
for USB/device access, Wine, preset/effect operations, staging, replay,
firmware, reset, install, network, or any other live action.

## Fix round 1

Status: complete and resealed. The existing twelve
`RestorationVerifierTests` methods were preserved and extended; no new test
method was added. No subagent or reviewer was used.

### JaSt raw-snapshot provenance

Covering contracts:
`test_enabled_first_restores_with_signature_present` and
`test_selected_slot_drift_fails_restoration`.

Each P0/P1/P2 summary now requires schema
`cp34-current-slot-jast-summary-v1`, a normalized safe run-relative raw path
under the same candidate, and a lowercase SHA-256 matching a distinct
snapshotted and manifested raw JaSt input. The verifier retains the existing
limitation that JaSt cannot prove every internal DSP byte.

RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_selected_slot_drift_fails_restoration
```

RED output:

```text
F                                                                        [100%]
FAILED tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_selected_slot_drift_fails_restoration
1 failed in 0.08s
```

The raw hash/missing-reference reasons were absent before the repair.

GREEN command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_selected_slot_drift_fails_restoration tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_enabled_first_restores_with_signature_present
```

GREEN output:

```text
..                                                                       [100%]
2 passed in 0.10s
```

### Candidate-2 predecessor seal

Covering contract:
`test_second_candidate_requires_a_restored_inconclusive_first_result`.

Only the four root output paths and the root evidence manifest are excluded
from manifest inputs. Nested `ch1-slot1/RESTORATION.json` is now a normal
manifested input. Candidate 2 reads only that immutable input snapshot; it no
longer rereads the filesystem or falls back to root `RESTORATION.json`. The
contract proves a semantics-valid but byte-swapped predecessor fails its
manifest hash and that a root-only result cannot authorize candidate 2.

RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_second_candidate_requires_a_restored_inconclusive_first_result
```

RED output:

```text
F                                                                        [100%]
FAILED tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_second_candidate_requires_a_restored_inconclusive_first_result
1 failed in 0.08s
```

GREEN command: the same focused command.

GREEN output:

```text
.                                                                        [100%]
1 passed in 0.12s
```

### Frozen-channel continuity

Covering contract: `test_extra_toggle_or_event_fails_restoration`.

Every M0/S1/S2/S3/S4 `audio_capture` event must now use exactly the mapped
channel 3 or 4. The extended contract sets S1 to the wrong channel while also
retaining the original extra-toggle checks.

RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_extra_toggle_or_event_fails_restoration
```

RED output:

```text
F                                                                        [100%]
FAILED tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_extra_toggle_or_event_fails_restoration
1 failed in 0.08s
```

GREEN command: the same focused command.

GREEN output:

```text
.                                                                        [100%]
1 passed in 0.06s
```

### Stable summary types

Covering contract: `test_p2_stable_field_mismatch_fails_restoration`.

Selected-slot and processing-channel values must be non-boolean integers;
enable and phantom values must be booleans; gains, headphone/main, and monitor
blend must be finite numeric scalars excluding booleans and containers. The
contract sets equal-but-invalid P0/P2 values so equality cannot conceal an
invalid representation, while preserving the original multi-reason drift and
physical-restoration checks.

RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_p2_stable_field_mismatch_fails_restoration
```

RED output:

```text
F                                                                        [100%]
FAILED tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_p2_stable_field_mismatch_fails_restoration
1 failed in 0.08s
```

GREEN command: the same focused command.

GREEN output:

```text
.                                                                        [100%]
1 passed in 0.06s
```

### Existing slot-classifier interface and derivative binding

Covering contracts:
`test_enabled_first_restores_with_signature_present`,
`test_bypassed_first_restores_with_inconclusive_outcome`, and
`test_missing_s4_fails_restoration`.

The invented A/B schema was removed. The verifier now consumes the exact
`analyze_slot` schema `cp34-slot-survey-audio-v1`, requires the fixed candidate
scope, unresolved model identity, false title/live/restoration claims, and
consistent classifier status/classification. Only
`SIGNATURE_PRESENT` plus `REPEAT_150MS_SIGNATURE` is positive; the analyzer's
two inconclusive classifications remain `INCONCLUSIVE`.

The two dry and two active metric rows must bind by normalized path and
lowercase hash to exactly four distinct manifested mono S32/48-kHz derivatives
named `S1.mixN.mono.wav` through `S4.mixN.mono.wav`. N must be the mapped frozen
channel, and dry/active membership is derived from P0 enabled state. The
failure contract independently covers wrong schema, unsafe path, hash mismatch,
wrong encoded channel, and wrong role membership.

RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_enabled_first_restores_with_signature_present tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_bypassed_first_restores_with_inconclusive_outcome tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_missing_s4_fails_restoration
```

RED output:

```text
FFF                                                                      [100%]
3 failed in 0.17s
```

GREEN command: the same three focused tests.

GREEN output:

```text
...                                                                      [100%]
3 passed in 0.14s
```

### Final suites

Restoration verifier command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests
```

Output:

```text
............                                                             [100%]
12 passed in 0.51s
```

Combined Task 1/2 regression command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::PlanValidatorTests tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests
```

Output:

```text
..................                                                       [100%]
18 passed in 6.72s
```

Syntax compilation also returned `syntax compile: OK` without creating
bytecode.

### Changed files and reseal

- `re/cp34_current_slot_survey.py`
- `tests/test_cp34_current_slot_survey.py`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`
- `.superpowers/sdd/CURRENT-SLOT-SURVEY-IMPLEMENTATION/task-3-report.md`

Printed replacement stage rows:

```text
13c67d0c5840df636bb49c8338acb2efc97f8a7478e3460469479e2549075d51  re/cp34_current_slot_survey.py
19bcfe269dd835943a75be2d9f23b0c5be24426fba0b2cb10c323cb330427535  tests/test_cp34_current_slot_survey.py
```

Manifest verification command and output:

```text
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
re/cp34_current_slot_survey.py: OK
tests/test_cp34_current_slot_survey.py: OK
```

The stage manifest still contains exactly two rows.

### Fix-round self-review and concerns

- Raw JaSt, predecessor, metric derivative, plan, state, action, mapping,
  attestation, and restoration inputs are hashed from the same immutable bytes
  subsequently parsed; no candidate-2 authorization path rereads live files.
- Manifest exclusions are exact root-relative paths, not basename-wide rules.
- JaSt and metric paths are normalized run-relative paths. JaSt paths must stay
  below the candidate directory; metric paths must equal their deterministic
  candidate/capture/frozen-channel name.
- Metric rows require four distinct snapshotted and manifested mono S32 48-kHz
  WAV files with matching lowercase SHA-256 values.
- Invalid state types, all wrong frozen-channel events, classifier scope drift,
  malformed positive claims, and all deterministic evidence defects accumulate
  explicit reasons.
- Imports remain Python standard-library only. The verifier stays offline and
  read-only with no driver, USB, ALSA, Wine, network, device, install, staging,
  firmware, reset, or run-directory mutation path.

Concerns: none within this fix round. A restored result remains bounded by the
explicit JaSt limitation and does not grant any live-device authority.

## Fix round 2

Status: complete and resealed. The existing twelve test methods remain intact;
`test_enabled_first_restores_with_signature_present` was extended with a
second malformed-analyzer invocation.

### Analyzer output completeness

The covering test removes `expected_delay_s` and representative dry/active
metric fields, supplies invalid arrival offsets and a Boolean peak, and changes
an active late delta to a nonnumeric value. Before this repair the structurally
incomplete object retained valid classifier assertions plus derivative
path/hash bindings and incorrectly returned `RESTORED`.

RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_enabled_first_restores_with_signature_present
```

RED output:

```text
F                                                                        [100%]
FAILED tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_enabled_first_restores_with_signature_present
1 failed in 0.12s
```

The exact failing assertion was `AssertionError: 0 != 2` for the malformed
second invocation.

The verifier now requires the exact `analyze_slot` top-level field set and
types: schema, status, classification, reverb flag, candidate, unresolved model
identity, false title/live/restoration flags, audible flag, exact 0.15-second
delay, two metric lists, and a list containing only string reasons. Existing
status/classification relationships and positive-only semantics remain in
force.

Dry metric rows require exactly the analyzer base fields. Active rows require
those base fields plus `echo_delta_db` and `late_delta_db`. Every row requires
exactly five impulses, five integer arrival offsets beginning at zero, and
finite non-Boolean peak, RMS, echo-ratio, and late-ratio values; both active
deltas must also be finite non-Boolean numerics. Existing safe-path, lowercase
hash, deterministic role/channel name, four-distinct-input, manifested snapshot,
and mono-WAV checks are unchanged. The verifier does not recompute the
classifier.

GREEN command: the same focused command.

GREEN output:

```text
.                                                                        [100%]
1 passed in 0.10s
```

### Final suites

Restoration verifier command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests
............                                                             [100%]
12 passed in 0.55s
```

Combined Task 1/2 regression command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::PlanValidatorTests tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests
..................                                                       [100%]
18 passed in 6.64s
```

The source-only syntax compilation also returned `syntax compile: OK`.

### Changed files and stage reseal

- `re/cp34_current_slot_survey.py`
- `tests/test_cp34_current_slot_survey.py`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`
- `.superpowers/sdd/CURRENT-SLOT-SURVEY-IMPLEMENTATION/task-3-report.md`

Printed replacement rows:

```text
12410ae2b6692cee6b2b03651f249227cdec65f7a392a7acd70cdb8839f6f73e  re/cp34_current_slot_survey.py
c88f59d17c93ac8e78138cd6745277e8aa5bc1633feac309322ccdfc4f2dc077  tests/test_cp34_current_slot_survey.py
```

Manifest verification:

```text
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
re/cp34_current_slot_survey.py: OK
tests/test_cp34_current_slot_survey.py: OK
```

The stage manifest still contains exactly two rows.

### Self-review and concerns

- Exact top-level and per-role row key sets prevent asserted classifier fields
  from substituting for missing metric evidence.
- Required scalar checks reject booleans, containers, non-finite values, short
  arrival lists, noninteger offsets, nonzero first offsets, and impulse counts
  other than five.
- The repair only validates the existing analyzer output contract. It neither
  imports nor modifies `cp34_live_matrix.py` and does not recompute classification.
- All analysis remains over immutable, manifested input snapshots; there is no
  run-directory mutation or live filesystem reread for evidence decisions.
- Imports remain standard-library-only, with no driver, USB, ALSA, Wine,
  network, device, install, staging, firmware, or reset path.

Concerns: none within Fix round 2. `RESTORED` remains an offline evidence result
bounded by the explicit JaSt limitation and grants no live authority.

## Fix round 3

Status: complete and resealed. The existing malformed-analyzer subcase in
`test_enabled_first_restores_with_signature_present` now includes a valid JSON
integer of `10 ** 1000` as an analyzer metric.

### Oversized-integer crash regression

RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_enabled_first_restores_with_signature_present
```

RED output:

```text
F                                                                        [100%]
FAILED tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_enabled_first_restores_with_signature_present
1 failed in 0.18s
```

The subprocess emitted a genuine traceback ending in:

```text
File "re/cp34_current_slot_survey.py", line 555, in _is_finite_numeric
    and math.isfinite(value))
OverflowError: int too large to convert to float
```

`_is_finite_numeric` is now total over arbitrary decoded JSON values. It first
rejects nonnumeric values and booleans, then catches numeric conversion/domain
exceptions from `math.isfinite`. Oversized integers return false and accumulate
the existing reason
`ab_metric_echo_ratio_db_must_be_finite_numeric:active:2`; the CLI returns
standard `RESTORATION_FAILED` JSON without a traceback.

GREEN command: the same focused command.

GREEN output:

```text
.                                                                        [100%]
1 passed in 0.10s
```

### Final suites

Restoration verifier command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests
............                                                             [100%]
12 passed in 0.57s
```

Combined Task 1/2 regression command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::PlanValidatorTests tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests
..................                                                       [100%]
18 passed in 6.75s
```

Source-only syntax compilation returned `syntax compile: OK`.

### Changed files and stage reseal

- `re/cp34_current_slot_survey.py`
- `tests/test_cp34_current_slot_survey.py`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`
- `.superpowers/sdd/CURRENT-SLOT-SURVEY-IMPLEMENTATION/task-3-report.md`

Printed replacement rows:

```text
1bb029a18181a85c602a84f42fbbf57602dbce321a5ae39727c14b9828a74ff3  re/cp34_current_slot_survey.py
7ee2c148553ac398f1c13bb8d9936d99206b985d980bcfc4f01887e52aec6280  tests/test_cp34_current_slot_survey.py
```

Manifest verification:

```text
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
re/cp34_current_slot_survey.py: OK
tests/test_cp34_current_slot_survey.py: OK
```

The stage manifest remains exactly two rows.

### Self-review and concerns

- The finite-number predicate returns a Boolean for every JSON type and for
  arbitrarily large JSON integers; conversion exceptions cannot escape.
- The malformed analyzer still accumulates all prior exact-shape, arrival,
  Boolean, missing-delta, and nonnumeric-delta reasons in the same invocation.
- Standard finite integers/floats preserve existing behavior; booleans,
  containers, non-finite floats, and oversized integers remain non-evidence.
- The change does not recompute classifier output or modify
  `cp34_live_matrix.py`.
- All work remains standard-library-only, offline, read-only, and free of
  driver, USB, ALSA, Wine, network, device, install, staging, firmware, reset,
  or run-directory mutation paths.

Concerns: none within Fix round 3. The result remains bounded by the explicit
JaSt limitation and grants no live authority.
