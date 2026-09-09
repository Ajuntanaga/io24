# Verification

Timestamp: 2026-09-06T14:22:50-07:00

## Physical-channel correction verification

The original results below predate discovery that VoiceFX assignment does not
renumber the physical preset APIs. The corrected focused command is:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_io24_voicefx_preset_apply \
  tests.test_cp34_channel2_reverb_slot_stage \
  tests.test_cp34_channel2_voicefx_materialization_stage \
  tests.test_cp34_uc472_hotkey_voicefx_route
```

Result: 28 tests, 0 failures, 0 errors. It covers the exact
`processingChannel == 0` ownership branch, assignment before model/state, and
physical Channel-2-only preset calls.

The stale Slap Echo wrapper was rebound to the corrected base runner and now
asserts physical Channel 2 for every preset call: 4/4 passed. The wider suite
excluding only the unchanged, slow current-slot-survey module passed 254 tests
with one expected skip and 44 subtests in 76.83 seconds on the final rerun.

The excluded survey module was then run separately and passed 41 tests and 11
subtests in 564.54 seconds. Because the two commands are disjoint and together
cover every `test*.py` module, the complete current total is 295 passed, one
expected skip, and 55 subtests.

The corrected dry plan matches checked-in `PLAN.json` byte-for-byte and returns
`OFFLINE_READY`. It pins the factory-derived 100%-wet record and exact changed
record/frame/model-state hashes. No USB, audio, Wine, or device operation was
performed.

## Focused contracts

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_cp34_channel2_voicefx_materialization_stage \
  tests.test_io24_voicefx_preset_apply \
  tests.test_cp34_uc472_hotkey_voicefx_route
```

Result: 13 tests, 0 failures, 0 errors, exit 0, 0.248 seconds.

The contracts cover:

- exact source hashes, Hot Key dispatch, persistence, and VoiceFX selector;
- all six class-ID to builder-field translations;
- strict rejection of missing, non-finite, or unknown selected state;
- model selector before selected-model payloads;
- failure before any Fat Channel mutation for an invalid opt-in record;
- inherited battery, identity, overwrite, link, slot-family, and Channel-1
  preservation gates;
- no slot write after a failed model/state apply;
- checked-in `PLAN.json` equality and explicit post-publication firmware
  deferral.

After the final GUI deferral and documentation pass, the same three modules
plus `tests.test_io24_preset_persistence` were run together. Result: 38 tests,
0 failures, 0 errors, exit 0, 0.430 seconds.

## Complete hardware-free suite

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test*.py' -v
```

Result: 293 tests, 0 failures, 0 errors, 1 expected skip, exit 0, 185.344
seconds.

The skip is the already-recorded unavailable historical truncated firmware
extraction. One pre-existing `ResourceWarning` reports an unclosed WAV fixture
in `cp34_current_slot_survey.py`; it is not a test failure and is unrelated to
this change.

## Syntax

Python `ast.parse` succeeded for:

- `io24.py`
- `io24_fx.py`
- `io24_presets.py`
- `io24_scene.py`
- `io24gtk.py`
- `re/cp34_channel2_voicefx_materialization_stage.py`
- `re/cp34_uc472_hotkey_voicefx_route.py`
- `tests/test_io24_voicefx_preset_apply.py`
- `tests/test_cp34_channel2_voicefx_materialization_stage.py`
- `tests/test_cp34_uc472_hotkey_voicefx_route.py`

## Hardware boundary

No device, USB, audio, Wine, network, firmware, or GitHub operation occurred.
The live stage remains separately authorization-gated.
