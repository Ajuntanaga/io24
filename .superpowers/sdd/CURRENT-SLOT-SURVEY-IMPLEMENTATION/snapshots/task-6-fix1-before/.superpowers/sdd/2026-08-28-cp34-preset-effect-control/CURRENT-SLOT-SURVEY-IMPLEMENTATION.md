# CP34 Current-Slot Survey Implementation Plan v2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build hardware-free validators and analyzers that make a future current-slot-only, no-write Voice FX survey reproducible and restorable without granting live authority.

**Architecture:** Add one focused standard-library CLI, `re/cp34_current_slot_survey.py`, for pre-run plan validation, six-channel Mix A mapping, and post-run restoration verification. Keep the existing mono A/B classifier in `re/cp34_live_matrix.py`; the new verifier consumes its JSON output and never imports `io24.py`, opens ALSA/USB, or performs an action. A task-local operator procedure and intentionally invalid template define the later authorization boundary.

**Tech Stack:** Python 3 standard library (`argparse`, `hashlib`, `json`, `math`, `pathlib`, `struct`, `wave`), `unittest` contracts executed by pytest, Markdown and JSON task-local records, SHA-256 manifests.

**Spec:** `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-DESIGN.md`

**Revision 2 amendment:** Tasks 1-5 below are retained as execution history.
Task 6 is the binding correction plan and supersedes any conflicting revision-1
schema, root-manifest, restoration-result, or audible-attestation instruction.
Revision 2 remains hardware-free and grants no live authority.

## Global Constraints

- Target only serial `AB7C22200355`.
- Candidate order is exactly channel 1 numeric slot 0, then channel 2 numeric slot 2 only after a restored inconclusive first result.
- Stop after the first restored `SIGNATURE_PRESENT` result.
- Never authorize or implement slot selection, mapped writes, device-output playback, io24 monitoring, Wine/prefix access, network access, firmware/reset/DFU, installation, staging, USB detach, or guessed packets.
- The only modeled mutation is exactly two `manual_preset_toggle` long presses per attempted candidate.
- Audio is six-channel S32_LE at 48 kHz from `hw:CARD=R24,DEV=0`; only Mix A capture channels 3 and 4 may be selected for effect analysis.
- Interface-5 state reads are discrete `P0`, `P1`, and `P2` checkpoints; continuous claims and overlap with ALSA streaming are invalid.
- `P2` must restore the selected slot, enable flag, processing map, phantom, gains, headphone/main volume, and monitor blend from `P0`.
- A null signal result is `INCONCLUSIVE`, never a negative.
- Stop at or below 10 percent battery.
- This intentionally non-Git workspace must not be initialized as a repository. Replace commit steps with task-local SHA-256 stage records.
- The current plan schema is `cp34-current-slot-survey-plan-v2`, the evidence
  protocol is `cp34-current-slot-evidence-v2`, and restoration results use
  `cp34-current-slot-restoration-v2`; revision-1 plans and results fail closed.
- Candidate input manifests and restoration results are immutable and scoped to
  their candidate. Root `SHA256SUMS` is created only after the terminal result;
  protocol v2 has no root `EVIDENCE-SHA256SUMS` or root `RESTORATION.json`.

---

## File Map

- Create `re/cp34_current_slot_survey.py`: offline CLI and pure validation/analysis functions only.
- Create `tests/test_cp34_current_slot_survey.py`: real subprocess contracts and deterministic WAV/JSON fixtures.
- Create `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md`: exact future operator procedure and authority boundary.
- Create `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-PLAN.template.json`: deliberately invalid, fail-closed plan template with `UNRECORDED` sentinels.
- Create `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`: durable per-task hashes.
- Modify `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/{PLAN.md,EVIDENCE.md,RESUME.md,LINUX-MANIFEST.md,LINUX-LIVE-MATRIX.md,LINUX-OFFLINE-SHA256SUMS}` only after executable gates pass.

### Task 1: Fail-closed survey plan validator

**Files:**
- Create: `re/cp34_current_slot_survey.py`
- Create: `tests/test_cp34_current_slot_survey.py`
- Create: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`

**Interfaces:**
- Produces: `validate_plan(path: str) -> dict`, returning schema `cp34-current-slot-survey-plan-validation-v1`, status `VALID` or `INVALID`, plan SHA-256, and ordered reasons.
- Produces CLI: `python3 re/cp34_current_slot_survey.py validate-plan PLAN.json`; exit 0 only for `VALID`, otherwise exit 2 without a traceback.
- Consumes no project driver or hardware API.

- [ ] **Step 1: Write the valid-plan fixture and first failing contract**

Add `_valid_plan()` with these literal boundaries:

```python
def _valid_plan():
    return {
        "schema": "cp34-current-slot-survey-plan-v1",
        "run_id": "20260829T120000-0700-current-slot-survey",
        "device_serial": "AB7C22200355",
        "authorization_status": "EXACT_AUTHORIZATION_RECORDED",
        "stop_on_first_positive": True,
        "battery_stop_percent": 10,
        "evidence_dir": (
            ".superpowers/sdd/2026-08-28-cp34-preset-effect-control/"
            "runs/20260829T120000-0700-current-slot-survey"
        ),
        "source": {
            "kind": "external_line_level",
            "device": "offline-fixture-player",
            "power": "isolated-battery",
            "stimulus_path": "/offline/slap-impulses.wav",
            "stimulus_sha256": "a" * 64,
            "cable": "balanced-line-fixture",
            "volume": "fixed-mark-4",
        },
        "audio": {
            "device": "hw:CARD=R24,DEV=0",
            "format": "S32_LE",
            "rate": 48000,
            "channels": 6,
            "effect_candidates": [3, 4],
        },
        "state_reads": ["P0", "P1", "P2"],
        "continuous_interface_claim": False,
        "candidates": [
            {
                "label": "ch1-slot1", "channel": 1, "numeric_slot": 0,
                "physical_input": 1,
                "connection": "player line out to io24 input 1",
                "restore_connection": "remove cable from io24 input 1",
                "actions": [
                    {"id": "T1", "kind": "manual_preset_toggle", "press": "long"},
                    {"id": "T2", "kind": "manual_preset_toggle", "press": "long"},
                ],
            },
            {
                "label": "ch2-slot1", "channel": 2, "numeric_slot": 2,
                "physical_input": 2,
                "connection": "player line out to io24 input 2",
                "restore_connection": "remove cable from io24 input 2",
                "actions": [
                    {"id": "T1", "kind": "manual_preset_toggle", "press": "long"},
                    {"id": "T2", "kind": "manual_preset_toggle", "press": "long"},
                ],
            },
        ],
        "prohibited_actions": [
            "slot_selection", "mapped_write", "device_output_playback",
            "io24_monitoring", "wine", "network", "firmware", "reset",
            "dfu", "install", "stage", "usb_detach", "guessed_packet",
        ],
    }
```

Test `validate-plan` returns exit 0, status `VALID`, no reasons, and the literal candidate order.

- [ ] **Step 2: Run the contract and verify RED**

Run:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_current_slot_survey.py::PlanValidatorTests::test_accepts_exact_current_slot_plan
```

Expected: FAIL because `re/cp34_current_slot_survey.py` does not exist.

- [ ] **Step 3: Implement the minimal validator and CLI**

Define exact constants and helpers:

```python
EXPECTED_SERIAL = "AB7C22200355"
EXPECTED_CANDIDATES = (
    {"label": "ch1-slot1", "channel": 1, "numeric_slot": 0, "physical_input": 1},
    {"label": "ch2-slot1", "channel": 2, "numeric_slot": 2, "physical_input": 2},
)
EXPECTED_PROHIBITED = frozenset({
    "slot_selection", "mapped_write", "device_output_playback",
    "io24_monitoring", "wine", "network", "firmware", "reset", "dfu",
    "install", "stage", "usb_detach", "guessed_packet",
})

def validate_plan(path):
    # Load one JSON object, append deterministic reasons for every violated
    # literal above, hash the input, and return VALID only when reasons is empty.
```

The validator must reject any string containing `UNRECORDED`, an evidence path outside the active task's `runs/` directory, a run-directory basename inconsistent with `run_id`, and a stimulus hash that is not 64 lowercase hexadecimal characters.

- [ ] **Step 4: Verify GREEN**

Run the single test from Step 2. Expected: 1 passed.

- [ ] **Step 5: Add the remaining fail-closed plan contracts one at a time**

For each test, mutate exactly one copy of `_valid_plan()`, run it to observe a failure against the current validator branch, then add the smallest check:

```text
test_rejects_non_object_plan
test_rejects_wrong_serial_or_authorization_status
test_rejects_reordered_or_changed_candidates
test_rejects_false_stop_on_first_positive
test_rejects_device_output_or_unrecorded_source
test_rejects_wrong_audio_shape_or_effect_channels
test_rejects_continuous_or_missing_state_reads
test_rejects_wrong_toggle_count_short_press_or_mapped_action
test_rejects_unsafe_path_battery_floor_or_missing_prohibitions
```

Each invalid invocation must exit 2, emit one JSON object, contain the expected reason, and omit a traceback.

- [ ] **Step 6: Run Task 1 tests**

Run:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_current_slot_survey.py::PlanValidatorTests
```

Expected: 10 passed.

- [ ] **Step 7: Record the non-Git stage**

Print SHA-256 for the new CLI and test, then create `CURRENT-SLOT-SURVEY-STAGE.sha256` with those exact two rows using `apply_patch`. Verify it with `sha256sum -c`.

### Task 2: Six-channel Mix A mapping analyzer

**Files:**
- Modify: `re/cp34_current_slot_survey.py`
- Modify: `tests/test_cp34_current_slot_survey.py`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`

**Interfaces:**
- Consumes: six-channel S32_LE 48 kHz WAV and `input_channel` 1 or 2.
- Produces: `analyze_map(path: str, input_channel: int) -> dict` with schema `cp34-current-slot-map-v1`, status `MAPPED` or `UNAVAILABLE`, raw SHA-256, input metrics, scores for channels 3 and 4, and `frozen_mix_channel`.
- Produces CLI: `map-channel MAP.raw.wav --input-channel 1`; exit 0 only for `MAPPED`, otherwise exit 2.

- [ ] **Step 1: Write the channel-3 RED contract**

Add a test helper that writes a literal six-channel 48 kHz S32_LE WAV containing five impulses on input channel 1 and correlated responses on Mix A channel 3. Keep channels 2, 4, 5, and 6 at deterministic low-level noise. Assert `MAPPED`, `frozen_mix_channel == 3`, five arrivals, and both scores are reported.

- [ ] **Step 2: Run and verify RED**

Run the new test alone. Expected: FAIL because `map-channel` is not registered.

- [ ] **Step 3: Implement WAV validation and deterministic scoring**

Add:

```python
RATE = 48000
CHANNELS = 6
MIN_INPUT_PEAK_DB = -36.0
MAX_INPUT_PEAK_DB = -12.0
MAX_ANY_PEAK_DB = -3.0
MIN_MAP_CORRELATION = 0.80
MAX_LAG_SAMPLES = 12000
MIX_CHANNELS = (3, 4)

def _read_six_channel_wav(path):
    # Reject non-PCM, non-S32_LE, non-48-kHz, non-six-channel files.

def _normalized_impulse_correlation(raw_input, candidate, arrivals, lag):
    # Use 17-sample windows centered on all five arrivals. Return the absolute
    # normalized dot product, or 0.0 when either norm is zero.

def analyze_map(path, input_channel):
    # Validate exactly five pinned-cadence arrivals, input/all-channel level
    # bounds, scan lags 0..12000 for channels 3 and 4, require score >= 0.80,
    # choose the higher score, and break a six-decimal tie toward channel 3.
```

Arrival offsets must match the deterministic stimulus offsets `(0, 33600, 67200, 100800, 134400)` within 96 samples after removing the first arrival.

- [ ] **Step 4: Verify GREEN for channel 3**

Run the channel-3 test. Expected: 1 passed.

- [ ] **Step 5: Add seven independent RED/GREEN mapping contracts**

Add and implement in this order:

```text
test_selects_channel_4_when_its_score_is_higher
test_equal_six_decimal_scores_choose_channel_3
test_no_usable_mix_a_channel_is_unavailable
test_changed_impulse_cadence_is_unavailable
test_any_channel_above_minus_3_dbfs_is_unavailable
test_input_peak_outside_safe_window_is_unavailable
test_wrong_wav_format_is_unavailable_without_traceback
```

The production mutation each test catches is respectively: wrong comparison, nondeterministic tie, missing threshold, missing cadence gate, missing clip gate, missing source-level gate, and accepting converted audio.

- [ ] **Step 6: Run Task 2 tests**

Run:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests
```

Expected: 8 passed.

- [ ] **Step 7: Refresh and verify the stage hashes**

Replace the CLI/test rows in `CURRENT-SLOT-SURVEY-STAGE.sha256` with the new printed hashes using `apply_patch`, then run `sha256sum -c`.

### Task 3: Post-run restoration verifier

**Files:**
- Modify: `re/cp34_current_slot_survey.py`
- Modify: `tests/test_cp34_current_slot_survey.py`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`

**Interfaces:**
- Consumes: validated `PLAN.json`, candidate directory, three JaSt summaries, exact action log, map/A-B/attestation JSON, `S4.raw.wav`, physical-restoration JSON, and `EVIDENCE-SHA256SUMS`.
- Produces: `verify_restoration(run_dir: str, candidate: str) -> dict` with schema `cp34-current-slot-restoration-v1`, status `RESTORED` or `RESTORATION_FAILED`, `survey_outcome` of `SIGNATURE_PRESENT` or `INCONCLUSIVE`, frozen channel, input hashes, and explicit JaSt limitation.
- Produces CLI: `verify-restoration RUN_DIR --candidate ch1-slot1`; exit 0 only for `RESTORED`.

- [ ] **Step 1: Write the enabled-first restored-positive RED contract**

Build a real temporary run directory. Use `P0.enabled=true`, `P1.enabled=false`, and `P2.enabled=true`; keep all stable fields identical between P0 and P2. Use the exact event order:

```python
EXPECTED_EVENTS = (
    ("P0", "state_read"), ("M0", "audio_capture"),
    ("S1", "audio_capture"), ("T1", "manual_preset_toggle"),
    ("P1", "state_read"), ("S2", "audio_capture"),
    ("S3", "audio_capture"), ("T2", "manual_preset_toggle"),
    ("P2", "state_read"), ("S4", "audio_capture"),
)
```

Make monotonic timestamps strictly increasing. Supply map status `MAPPED`, frozen channel 3, A/B status `SIGNATURE_PRESENT` with model/title unresolved, a post-restoration audible attestation with two active repeats heard and zero dry repeats heard, physical restoration true, and an exact `EVIDENCE-SHA256SUMS`. Assert `RESTORED`, `SIGNATURE_PRESENT`, and the JaSt limitation string.

- [ ] **Step 2: Run and verify RED**

Run the new test alone. Expected: FAIL because `verify-restoration` is not registered.

- [ ] **Step 3: Implement exact evidence and state validation**

Define:

```python
STABLE_STATE_KEYS = (
    "selected_slot", "processing_channel_1", "processing_channel_2",
    "phantom_1", "phantom_2", "gain_1", "gain_2", "headphone",
    "main", "monitor_blend",
)

def _verify_input_manifest(run_dir):
    # Reject absolute/parent paths, duplicate rows, missing files, extra rows,
    # hash mismatches, and any actual pre-verification input omitted from the
    # manifest. Exclude only EVIDENCE-SHA256SUMS, RESTORATION.json, REPORT.md,
    # and final SHA256SUMS.

def verify_restoration(run_dir, candidate):
    # Revalidate PLAN.json; verify exact candidate/slot/channel, P1 inverse,
    # P2 stable equality, event order/kinds/timestamps, two long presses only,
    # MAPPED/frozen channel, S4 presence, physical restoration, attestation,
    # A/B scope fields, and all input hashes.
```

Return `RESTORATION_FAILED` with every deterministic reason rather than stopping at the first mismatch. Never infer title or model.

- [ ] **Step 4: Verify GREEN for enabled-first positive**

Run the test from Step 2. Expected: 1 passed.

- [ ] **Step 5: Add eleven independent RED/GREEN restoration contracts**

```text
test_bypassed_first_restores_with_inconclusive_outcome
test_selected_slot_drift_fails_restoration
test_p1_must_invert_the_initial_enable_state
test_p2_stable_field_mismatch_fails_restoration
test_extra_toggle_or_event_fails_restoration
test_short_press_is_rejected
test_mapped_write_is_rejected
test_missing_s4_fails_restoration
test_incomplete_or_mismatched_evidence_manifest_fails
test_missing_physical_restoration_attestation_fails
test_second_candidate_requires_a_restored_inconclusive_first_result
```

The last test creates both candidate directories and a first-candidate restoration result; channel 2 is valid only when channel 1 is `RESTORED` plus `INCONCLUSIVE`.

- [ ] **Step 6: Run Task 3 tests**

Run:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_current_slot_survey.py::RestorationVerifierTests
```

Expected: 12 passed.

- [ ] **Step 7: Refresh and verify stage hashes**

Update the CLI/test rows in `CURRENT-SLOT-SURVEY-STAGE.sha256` using printed `sha256sum` output and `apply_patch`, then verify all rows.

### Task 4: Fail-closed operator procedure and template

**Files:**
- Create: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md`
- Create: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-PLAN.template.json`
- Modify: `tests/test_cp34_current_slot_survey.py`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`

**Interfaces:**
- Consumes the exact CLI commands from Tasks 1-3.
- Produces a human procedure that stops before any live command until exact authorization is recorded.
- Produces an intentionally invalid template rejected because `authorization_status` and physical source fields are `UNRECORDED`.

- [ ] **Step 1: Write the template-rejection RED contract**

Invoke `validate-plan` on the checked-in template. Assert exit 2 and reasons containing `authorization_status` and `UNRECORDED`. This catches accidental shipment of a live-ready template.

- [ ] **Step 2: Create the invalid template and verify GREEN**

Copy the full literal shape of `_valid_plan()` but set:

```json
"authorization_status": "NOT_AUTHORIZED",
"device": "UNRECORDED",
"power": "UNRECORDED",
"stimulus_path": "UNRECORDED",
"stimulus_sha256": "UNRECORDED",
"cable": "UNRECORDED",
"volume": "UNRECORDED"
```

Keep the exact serial, candidates, action count, prohibitions, and battery floor visible. Run the template test; expected: 1 passed.

- [ ] **Step 3: Write the operator procedure**

`CURRENT-SLOT-SURVEY.md` must contain, in order:

1. scope and prohibited actions;
2. explicit statement that the file is not authority;
3. plan population and `validate-plan` gate;
4. battery, external-source, phantom, level, and physical-connection preflight;
5. discrete P0/M0/S1/T1/P1/S2/S3/T2/P2/S4 sequence;
6. rule that ALSA and interface-5 claims never overlap;
7. exact map-channel and existing analyze-slot commands;
8. restoration-verifier and final SHA-256 seal commands;
9. stop-on-first-positive and channel-2 eligibility rules;
10. `UNAVAILABLE`, `INCONCLUSIVE`, `SIGNATURE_PRESENT`, and `RESTORATION_FAILED` semantics;
11. no-negative and no-title/model claims; and
12. exact authorization fields a future request must name.

Do not include a runnable live acquisition command or populated authorization value.

- [ ] **Step 4: Run all new contracts**

Run:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_current_slot_survey.py
```

Expected: 31 passed: 10 plan, 8 mapping, 12 restoration, and 1 template contract.

- [ ] **Step 5: Record the documentation stage**

Add CLI, test, design, procedure, template, and implementation-plan hashes to `CURRENT-SLOT-SURVEY-STAGE.sha256` using `apply_patch`; verify every row.

### Task 5: CP34 integration, review, and offline seal

**Files:**
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/PLAN.md`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/EVIDENCE.md`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-MANIFEST.md`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-LIVE-MATRIX.md`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-OFFLINE-SHA256SUMS`

**Interfaces:**
- Consumes all Task 1-4 artifacts and verification output.
- Produces a hash-pinned offline stage that is eligible for review, not live execution.

- [ ] **Step 1: Run the complete hardware-free regression set**

Run:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_host_queue_inventory.py \
  tests/test_cp34_live_matrix.py \
  tests/test_cp34_current_slot_survey.py \
  tests/test_io24_preset_persistence.py \
  tests/test_normalize_io24_capture.py \
  tests/test_io24_capture_decode.py
```

Expected: 94 passed and 27 subtests passed (the existing 63 plus 31 new contracts).

- [ ] **Step 2: Reproduce both pinned host inventories**

Run the two commands in `LINUX-MANIFEST.md`. Expected: six direct callers of `0x1800546b0`, three RIP-relative consumers of `0x1800e53f0`, and DLL SHA-256 `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`.

- [ ] **Step 3: Update CP34 records without widening authority**

Record exact paths, hashes, test counts, validator semantics, remaining title/model limitation, positive-only interpretation, and the fact that no live action occurred. `RESUME.md` must make the next gate an independent offline review followed by a separately authorized run; it must not say the template or passing validators authorize hardware.

- [ ] **Step 4: Refresh and verify both manifests**

Update `CURRENT-SLOT-SURVEY-STAGE.sha256` and `LINUX-OFFLINE-SHA256SUMS` from printed hashes using `apply_patch`. Run `sha256sum -c` on each; every row must report `OK`.

- [ ] **Step 5: Perform the review gate**

Review the design, operator procedure, CLI, tests, and manifests against these rejection questions:

```text
Can any checked-in command touch USB or ALSA?
Can a template validate without exact authorization and source provenance?
Can a short press, slot drift, mapped write, extra toggle, or missing inverse pass?
Can the analysis channel be selected after seeing the effect result?
Can a null result become a negative?
Can a signal signature become a title or model claim?
Can channel 2 run after a failed restoration or unavailable channel 1?
Can a missing evidence file escape the hash seal?
```

Any `yes` is REQUEST CHANGES. Preserve the working tree and fix with a new RED/GREEN cycle.

- [ ] **Step 6: Final verification**

Re-run Step 1 and both checksum verifications after the last documentation edit. Record battery state using sysfs only. Do not access the device.

### Task 6: Revision-2 evidence-protocol correction

**Files:**
- Modify: `re/cp34_current_slot_survey.py`
- Modify: `tests/test_cp34_current_slot_survey.py`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-DESIGN.md`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-IMPLEMENTATION.md`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-PLAN.template.json`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`
- Modify the Task-5 CP34 integration records and offline manifest only after the
  focused correction contracts pass.

**Interfaces:**
- `validate_plan` accepts only `cp34-current-slot-survey-plan-v2` with exact
  `evidence_protocol: cp34-current-slot-evidence-v2`; revision-1 plans fail
  closed. The validation result schema becomes
  `cp34-current-slot-survey-plan-validation-v2`.
- `verify_restoration` produces and accepts predecessor results only with schema
  `cp34-current-slot-restoration-v2`.
- JaSt raw and summary schemas remain v1, but all numeric validation is total:
  every JSON number either validates as a supported finite value or produces a
  deterministic reason. No valid JSON number may escape as `OverflowError` or
  `ValueError`.
- Candidate-scoped manifests/results and the terminal root seal implement
  evidence protocol v2 exactly as defined by the revised design.
- Audible attestation is earned only by post-restoration replay of all four
  preserved mono derivatives through a separate non-io24 path.

- [ ] **Step 1: Add fail-closed numeric RED contracts**

Add focused restoration and CLI cases for a summary field containing a valid
JSON integer larger than binary floating-point range, a raw JaSt field with the
same oversized integer, and raw JaSt exponent overflow such as `1e10000`.
Assert a deterministic `RESTORATION_FAILED` result and CLI exit 2 with no
traceback. The raw evidence must be rejected before canonical serialization.

- [ ] **Step 2: Make JaSt numeric validation total**

Route summary and raw numeric checks through one safe finite-number predicate.
Reject booleans as numbers, catch integer-to-float overflow, reject parsed
non-finite floats before `json.dumps(..., allow_nan=False)`, and aggregate
deterministic reasons rather than throwing.

- [ ] **Step 3: Add revision-2 schema RED contracts**

Require the exact plan-v2 schema and evidence-protocol field, reject a complete
revision-1 plan, emit validation-v2, emit restoration-v2, and reject a
revision-1 channel-1 predecessor result for channel 2. Update the deliberately
invalid checked-in template to the complete v2 shape while retaining
`NOT_AUTHORIZED` and every `UNRECORDED` sentinel.

- [ ] **Step 4: Add procedure/seal RED contracts**

Pin this order after `S4`: verify restored readable state, restore and attest
the physical connection, replay `S1` through `S4` frozen-channel mono
derivatives individually through a separate non-io24 playback/monitoring path,
record observations for both active and both dry files, write the audible
attestation, then run A/B analysis. A single replay of the external stimulus on
the controlled io24 path is forbidden as audible-attestation evidence.

Assert that both candidate-manifest subshells and the terminal root-seal
subshell enable `set -o pipefail` before their first pipeline, enumerate files
NUL-safely, publish with no-clobber semantics, and verify only after successful
publication. Distinguish all three commands in the test so one correct root
seal cannot mask unsafe interim seals.

- [ ] **Step 5: Implement and document evidence protocol v2**

Apply the schema bumps, correct the audible sequence, and make both interim
seals fail atomically on any upstream pipeline error. Preserve the already
reviewed raw-to-derivative binding, JaSt semantic derivation, run-path binding,
five-arrival mapping, positive-only semantics, unresolved title/model fields,
and lack of live commands. Update integration records to identify revision 1
as rejected/superseded and revision 2 as pending independent review.

- [ ] **Step 6: Focused and complete offline verification**

Run the new correction cases, then all current-slot tests, then the complete
hardware-free regression command from Task 5. Record exact tests/subtests
rather than preserving a stale expected count. Reproduce the two pinned static
inventories only if their tracked inputs changed.

- [ ] **Step 7: Refresh seals and perform a fresh review**

Refresh all six stage rows and all affected offline-manifest rows from printed
SHA-256 output, then verify both manifests completely. Record battery through
sysfs only and state explicitly that no live action occurred. Package the exact
revision-2 diff for a fresh independent specification-and-quality review; any
Critical or Important finding leaves the stage unsealed.

## Execution Handoff

The user selected recommended choices globally. Tasks 1-5 are historical;
execute Task 6 as one fresh bounded correction task with
`superpowers:subagent-driven-development`, followed by one fresh independent
specification-and-quality review. Workers share this non-Git workspace, must
own only their assigned task files, must preserve unrelated edits, and must
never run hardware-facing commands.
