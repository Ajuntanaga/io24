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

