# CP34 device-slot decoded-record comparison - progress

Status: locally verified, hardware-free comparison evidence; device-readback
provenance and physical validation remain open.

## Result

- Added `compare_device_slot_records()` in `io24_preset_record.py`.
- It validates both expected and observed complete records, removes only
  extraction-only `_offset` metadata, emits canonical record hashes, and reports
  stable field paths for slot and nested-record differences.
- No observed record yields `READBACK_UNAVAILABLE`; an incomplete observed
  record yields `INVALID_READBACK`; only a complete equal record for the same
  slot yields `RECORD_EQUAL`.
- Every result preserves `physical_commit`, `front_panel_recall`, and
  `audibility` as `UNPROVED`.

## TDD evidence

- Baseline `tests.test_io24_preset_persistence`: 20 tests passed.
- Added comparison tests first; the focused suite failed at import because the
  comparator did not yet exist.
- After the minimal implementation, the related focused run passed 41 tests:
  `tests.test_io24_preset_persistence`,
  `tests.test_cp34_dual_private_reverb_slots`, and
  `tests.test_cp34_preset_recall_static`.
- The complete hardware-free suite passed 190 tests with one expected local
  artifact skip in 152.830 seconds. The only output outside ordinary test
  progress was the pre-existing temporary-WAV `ResourceWarning` in
  `re/cp34_current_slot_survey.py:260`.
- `CHECKPOINT.sha256` then verified all six tracked rows.

## Live boundary

No USB, device, audio, preset/effect, Wine, network, firmware, or other live
action occurred. A generic authorization was not treated as an exact USB scope;
there is therefore no current device identity, battery, PRESTATE, or readback
claim in this checkpoint.

## Next action

Wait for an exact live run scope. A later comparison needs an independently
captured/decoded slot record; selected-slot readback and transport
acknowledgment remain insufficient.
