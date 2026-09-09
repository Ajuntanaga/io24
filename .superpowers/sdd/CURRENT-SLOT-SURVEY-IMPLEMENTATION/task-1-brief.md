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

