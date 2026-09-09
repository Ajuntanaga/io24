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

