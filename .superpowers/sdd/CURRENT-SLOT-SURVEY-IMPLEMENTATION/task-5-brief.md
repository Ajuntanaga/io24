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

## Execution Handoff

The user selected recommended choices globally. Execute with `superpowers:subagent-driven-development`: one implementation worker per task, followed by specification and quality review gates. Workers share this non-Git workspace, must own only their assigned task files, must preserve unrelated edits, and must never run hardware-facing commands.
