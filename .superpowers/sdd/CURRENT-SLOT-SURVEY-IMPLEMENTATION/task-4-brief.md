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

