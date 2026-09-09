# Task 2 report: six-channel Mix A mapping analyzer

## Scope and implementation

Implemented the offline-only `map-channel MAP.raw.wav --input-channel 1`
interface in `re/cp34_current_slot_survey.py`.  `analyze_map(path,
input_channel)` now returns `cp34-current-slot-map-v1` records with a raw
SHA-256, input metrics, channel-3/channel-4 scores, a frozen selection, and
either `MAPPED` or `UNAVAILABLE`.  The CLI returns zero only for `MAPPED` and
two otherwise.

The analyzer accepts only six-channel, 48-kHz, uncompressed S32_LE WAV input.
It requires exactly five source impulses at the pinned cadence, checks the
source safe window and every-channel clipping ceiling, scores only planned Mix
A channels 3 and 4 across lags zero through 12000, applies the 0.80 threshold,
and resolves six-decimal score ties toward channel 3.  It does not inspect or
use effect results to alter the frozen mapping.

`MappingAnalyzerTests` adds literal, deterministic six-channel S32_LE WAV
fixtures: input impulses, candidate response placement, and low-level noise
are all generated locally with the Python standard library.  No driver code,
ALSA, USB, Wine, network, or hardware is used.

## RED/GREEN evidence

Initial RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests::test_selects_channel_3_for_correlated_five_impulse_fixture
```

Initial RED result before registering `map-channel`:

```text
FAILED ...test_selects_channel_3_for_correlated_five_impulse_fixture
AssertionError: 2 != 0
1 failed in 0.27s
```

GREEN command after the WAV reader, scoring, analyzer, and CLI registration:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests::test_selects_channel_3_for_correlated_five_impulse_fixture
```

GREEN result:

```text
1 passed in 0.82s
```

The remaining independent contracts cover higher channel-4 score,
six-decimal tie selection, unavailable low correlation, cadence rejection,
all-channel clipping, source level bounds, and invalid WAV rejection without a
traceback.  Their focused command and result:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests
8 passed in 4.56s
```

Task 1 regression command and result:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::PlanValidatorTests
10 passed in 0.59s
```

## Changed files

- `re/cp34_current_slot_survey.py`
- `tests/test_cp34_current_slot_survey.py`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`
- `.superpowers/sdd/CURRENT-SLOT-SURVEY-IMPLEMENTATION/task-2-report.md`

## Stage hashes

New stage rows:

```text
7feb313c5ddc39bdb326b5ede1d1ec78d221a60df306fd0d55eb36583ed7ee2c  re/cp34_current_slot_survey.py
4fc9947c6bcab6d4dccc8b0d7963ba35f703ee14d399538d7ec3edd9159e2239  tests/test_cp34_current_slot_survey.py
```

Manifest verification command:

```text
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
```

Verification result:

```text
re/cp34_current_slot_survey.py: OK
tests/test_cp34_current_slot_survey.py: OK
```

## Self-review and concerns

Self-review confirmed that both selections are constrained to channels 3 and 4,
the tie rule is deterministic, failures preserve the output schema and exit
two without a traceback, and the established Task 1 CLI behavior remains
unchanged.  Syntax compilation completed successfully; the temporary bytecode
file it created was removed.

Concern: this is intentionally fixture-only analysis.  It establishes no live
device mapping or effect behavior, and the current result must remain frozen
rather than reused as authorization for a device action.

## Fix round 1

This round preserves the eight `MappingAnalyzerTests` methods and Task 1's
plan-validator behavior.  All test fixtures and the mutable-path regression
are local standard-library work only; they do not access hardware, Wine,
network, ALSA, or driver code.

### Exact S32_LE semantics

Covering test: `test_wrong_wav_format_is_unavailable_without_traceback`,
extended with a deterministic six-channel `WAVE_FORMAT_EXTENSIBLE` fixture
having a 32-bit container but only 24 declared valid bits.

RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests::test_wrong_wav_format_is_unavailable_without_traceback
```

RED result:

```text
AssertionError: 'wav_must_be_six_channel_s32_le_48khz_pcm' not found in ['input_peak_outside_safe_window']
1 failed in 0.08s
```

GREEN command: the same command.

GREEN result:

```text
1 passed in 0.07s
```

The reader now inspects the RIFF `fmt ` declaration.  Conventional PCM must
declare 32 bits, while extensible PCM must additionally declare 32 valid bits
and the PCM subtype GUID.

### Hash and analyzed bytes are identical

Covering test: `test_selects_channel_3_for_correlated_five_impulse_fixture`,
extended with a deterministic path-open swap.  The first read is a channel-3
fixture and later opens expose a distinguishable channel-4 fixture.  The
result must retain the channel-3 selection and the first fixture's SHA-256.

RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests::test_selects_channel_3_for_correlated_five_impulse_fixture
```

RED result before eliminating the second parse read:

```text
AssertionError: 'ef7fe7501a87600ebc38c29a0038d7e486e005b55b21ea7ace6e0d4ceceea9b6' != 'f53b802c9c2014e6a1f2289ea2db9fc4d32f25802250d6d4ae3bea2c52645de7'
1 failed in 1.83s
```

GREEN command: the same command.

GREEN result:

```text
1 passed in 1.82s
```

`analyze_map` now hashes one byte buffer and passes that same immutable buffer
through `BytesIO` to the WAV parser and `fmt ` validator; it does not reopen
the path after hashing.

### Standard JSON for null input

Covering test: `test_input_peak_outside_safe_window_is_unavailable`, extended
with a zero-valued six-channel WAV.  It requires exit 2, `UNAVAILABLE`, no
`Infinity` token, and a JSON `null` input peak.

RED command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests::test_input_peak_outside_safe_window_is_unavailable
```

RED result:

```text
AssertionError: 'Infinity' unexpectedly found in '{... "peak_dbfs": -Infinity, ...}'
1 failed in 0.80s
```

GREEN command: the same command.

GREEN result:

```text
1 passed in 0.81s
```

Zero peak now maps to `None`/JSON `null`, and each CLI JSON serialization uses
`allow_nan=False` to prevent non-standard numeric tokens.

### Final verification

Amended focused contracts:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests::test_wrong_wav_format_is_unavailable_without_traceback tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests::test_selects_channel_3_for_correlated_five_impulse_fixture tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests::test_input_peak_outside_safe_window_is_unavailable
3 passed in 2.67s
```

Complete mapping and Task 1 suites:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests
8 passed in 5.99s

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::PlanValidatorTests
10 passed in 0.60s
```

Changed files: `re/cp34_current_slot_survey.py`,
`tests/test_cp34_current_slot_survey.py`, and
`.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`;
this report was appended with the evidence.

New stage rows:

```text
dd26812453ea923e38c3b4853e0098571b2a8184575906b6b82ca3a5247059a7  re/cp34_current_slot_survey.py
7fd9b7d3107c5a5cc5156e13bc92d3923ed88ad80ab86d1d36770a17d030aa22  tests/test_cp34_current_slot_survey.py
```

Manifest verification:

```text
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
re/cp34_current_slot_survey.py: OK
tests/test_cp34_current_slot_survey.py: OK
```

Concern: this remains fixture-only offline analysis.  It does not establish a
live mapping or authorize any device, preset, effect, firmware, staging, or
other live action.
