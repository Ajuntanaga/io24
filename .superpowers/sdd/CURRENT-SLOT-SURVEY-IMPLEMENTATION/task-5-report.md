# Task 5: CP34 integration, self-audit, and offline seal

Status: CP34 records integrated and offline-sealed; independent review is the
next gate. No live run is authorized.

## Safety preflight

Before either pinned inventory, I inspected the exact command text in
`LINUX-MANIFEST.md`. Each command invokes the task-local offline PE analyzer on
the explicitly pinned local DLL input. Neither command references Wine or the
protected prefix, USB or device nodes, ALSA, network, firmware, reset/DFU,
installation, staging, or any live action. Both were therefore eligible to run.

No live acquisition, USB/device access, interface claim/detach, ALSA stream,
Wine/prefix access, front-panel action, preset/effect operation, mapped write,
firmware/reset/DFU, install, external staging, network action, audio playback,
capture, or monitoring occurred.

## Complete hardware-free regression

Exact command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_host_queue_inventory.py \
  tests/test_cp34_live_matrix.py \
  tests/test_cp34_current_slot_survey.py \
  tests/test_io24_preset_persistence.py \
  tests/test_normalize_io24_capture.py \
  tests/test_io24_capture_decode.py
```

Fresh post-record-edit output:

```text
........................................................................ [ 76%]
......................                        [100%]
94 passed, 27 subtests passed in 11.34s
```

The result is the existing 63 contracts plus 31 current-slot contracts.

## Pinned host inventories

Exact direct-caller command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_host_queue_inventory.py \
  '/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll' \
  --target 0x1800546b0 --context-before 384
```

Output:

```json
{
  "call_kind": "direct",
  "call_sites": [
    {"address": "0x180035abe", "function_end": "0x180035c0b", "function_start": "0x180035a50", "nearby_ascii_immediates": ["FRst", "Appl"]},
    {"address": "0x180049f2f", "function_end": "0x180049fe0", "function_start": "0x1800499f0", "nearby_ascii_immediates": ["JICC", "JDvC", "VoFx"]},
    {"address": "0x18005238e", "function_end": "0x1800523c3", "function_start": "0x1800522ff", "nearby_ascii_immediates": ["MemP"]},
    {"address": "0x1800542a9", "function_end": "0x1800542c6", "function_start": "0x180054250", "nearby_ascii_immediates": ["Pari"]},
    {"address": "0x18005432a", "function_end": "0x180054347", "function_start": "0x1800542d0", "nearby_ascii_immediates": ["Pari", "Para"]},
    {"address": "0x1800555ae", "function_end": "0x1800555c3", "function_start": "0x180055570", "nearby_ascii_immediates": ["GetP", "SetP"]}
  ],
  "image_base": "0x180000000",
  "queue_target": "0x1800546b0",
  "sha256": "567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b"
}
```

Exact RIP-indirect inventory command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_host_queue_inventory.py \
  '/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll' \
  --target 0x1800e53f0 --call-kind rip-indirect --context-before 384
```

Output:

```json
{
  "call_kind": "rip-indirect",
  "call_sites": [
    {"address": "0x1800780db", "function_end": "0x180078189", "function_start": "0x180077fa0", "nearby_ascii_immediates": []},
    {"address": "0x18007867d", "function_end": "0x18007876b", "function_start": "0x1800783b0", "nearby_ascii_immediates": []},
    {"address": "0x180084ac8", "function_end": "0x180084b41", "function_start": "0x1800849e0", "nearby_ascii_immediates": []}
  ],
  "image_base": "0x180000000",
  "queue_target": "0x1800e53f0",
  "sha256": "567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b"
}
```

Summary: six direct callers of `0x1800546b0`, three RIP-relative consumers of
`0x1800e53f0`, and the exact pinned DLL SHA-256 reproduced.

## Integrated contracts and limitations

- `validate-plan` produces schema
  `cp34-current-slot-survey-plan-validation-v1`; exit 0 is reserved for
  `VALID`. Exact authorization, source provenance, serial, candidate order,
  action shape, capture shape, evidence path, battery floor, and prohibitions
  are mandatory. The checked-in template stays `NOT_AUTHORIZED` and contains
  `UNRECORDED` source fields, so it is intentionally rejected.
- `map-channel` produces `cp34-current-slot-map-v1`; exit 0 is reserved for
  `MAPPED`. It binds `raw_sha256`, accepts only six-channel 48 kHz S32_LE,
  scores only Mix A channels 3 and 4, and freezes the selection before effect
  analysis.
- `analyze-slot` actually produces `cp34-slot-survey-audio-v1`. `AB.json`
  retains candidate, dry/active metric rows, derivative path/hash bindings,
  `model_identity: "UNRESOLVED"`, `title_verified: false`, `live_ready: false`,
  and `restoration_verified: false`.
- `verify-restoration` produces `cp34-current-slot-restoration-v1`; exit 0 is
  reserved for `RESTORED`. It snapshots each input, returns `input_hashes`,
  verifies the exact input manifest, and retains `JaSt cannot prove every
  internal DSP byte.`
- `P0.json`, `P1.json`, and `P2.json` use
  `cp34-current-slot-jast-summary-v1` and bind immutable raw JaSt snapshots by
  safe relative `raw_snapshot_path` and exact `raw_snapshot_sha256`.
- `MAP.json.raw_sha256` binds `MAP.raw.wav`. `AB.json` binds the exact two dry
  and two active deterministic `S1.mixN.mono.wav` through `S4.mixN.mono.wav`
  derivative paths and SHA-256 values. `N` is the already frozen Mix A channel;
  dry/active roles come from `P0.enabled`, not filenames.
- `SIGNATURE_PRESENT` is positive only with `RESTORED`. A null signal or
  non-specific late tail is `INCONCLUSIVE`, never a negative. No result proves
  title, model, custom device-resident storage, device source, or complete
  internal-DSP restoration.
- Channel 2 is eligible only after channel 1 is exactly `RESTORED` plus
  `INCONCLUSIVE`. `UNAVAILABLE` or `RESTORATION_FAILED` stops.

## Manifest strategy and verification

`CURRENT-SLOT-SURVEY-STAGE.sha256` remains the exact six-row Task 1-4 artifact
stage. None of those six tracked files changed during Task 5, so its rows did
not require refresh. Its manifest SHA-256 is:

```text
25fbebbed34be6b11809f58e563a68844b675dfb3604805a51281b3d06c97f28  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
```

`LINUX-OFFLINE-SHA256SUMS` was refreshed from printed hashes for the modified
CP34 records and extended to cover all six current-slot artifacts plus the
six-row stage manifest itself. It now has 23 rows. Its SHA-256 is:

```text
11a7c3b99fa28467b15d37722a023cb123d6a00ebb2eb3a1c730d6d9d7417aba  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-OFFLINE-SHA256SUMS
```

Exact stage verification command and output:

```text
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
re/cp34_current_slot_survey.py: OK
tests/test_cp34_current_slot_survey.py: OK
.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-DESIGN.md: OK
.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md: OK
.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-PLAN.template.json: OK
.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-IMPLEMENTATION.md: OK
```

Exact offline-manifest verification command:

```text
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-OFFLINE-SHA256SUMS
```

Output: every one of the 23 rows reported `OK`, including the six current-slot
artifacts, `CURRENT-SLOT-SURVEY-STAGE.sha256`, and pinned DLL.

## Rejection self-audit

1. Can any checked-in command touch USB or ALSA? **No.** The procedure's
   runnable commands validate/analyze retained local files or hash a run tree.
   The template names an ALSA identity but is invalid and is not a command; no
   acquisition command is checked in.
2. Can a template validate without exact authorization and source provenance?
   **No.** Exact authorization is mandatory, every `UNRECORDED` string fails,
   and the checked-in template rejection is an executable contract.
3. Can a short press, slot drift, mapped write, extra toggle, or missing
   inverse pass? **No.** Exact event fields/order, two long toggles, P1 inverse,
   P2 equality, mapped-write rejection, and restoration tests fail closed.
4. Can the analysis channel be selected after seeing the effect result? **No.**
   `MAP.json` binds the raw map and freezes channel 3 or 4; every capture event,
   derivative, A/B metric, S4, and attestation must use that frozen channel.
5. Can a null result become a negative? **No.** It is `INCONCLUSIVE`; the
   current-slot survey is positive-only.
6. Can a signal signature become a title or model claim? **No.** The analyzer
   and verifier require `model_identity: "UNRESOLVED"` and title verification
   false; the records preserve that limitation.
7. Can channel 2 run after a failed restoration or unavailable channel 1?
   **No.** It requires the manifested channel-1 `RESTORATION.json` to be exactly
   `RESTORED` plus `INCONCLUSIVE`.
8. Can a missing evidence file escape the hash seal? **No.** Required inputs
   are checked explicitly, the input manifest must exactly match every actual
   pre-verification input, and the final NUL-safe no-clobber seal enumerates
   every retained file except itself.

Audit result: all answers are No; no `REQUEST CHANGES` condition was found. No
reviewer was dispatched.

## Battery

Exact sysfs-only command:

```text
for supply in /sys/class/power_supply/*; do if [ -r "$supply/capacity" ]; then printf '%s capacity=' "$(basename "$supply")"; tr -d '\n' < "$supply/capacity"; printf '%% status='; if [ -r "$supply/status" ]; then tr -d '\n' < "$supply/status"; else printf 'UNKNOWN'; fi; printf '\n'; fi; done
```

Output:

```text
BAT0 capacity=100% status=Full
```

## Files changed

- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/PLAN.md`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/EVIDENCE.md`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-MANIFEST.md`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-LIVE-MATRIX.md`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-OFFLINE-SHA256SUMS`
- `.superpowers/sdd/CURRENT-SLOT-SURVEY-IMPLEMENTATION/task-5-report.md`

`CURRENT-SLOT-SURVEY-STAGE.sha256` was verified but not modified because all
six tracked artifact rows were already exact. No production code, test, design,
procedure, template, implementation plan, or unrelated file was modified.

## Self-review and concerns

Self-review checked path/hash transcription against the live files, exact
analyzer and restoration schemas against the implementation, JaSt/raw and
derivative bindings, positive-only semantics, channel-2 gating, absence of
runnable live acquisition commands, and the review-before-authorization order
in `RESUME.md`.

Remaining limitations are intentional and material: title and effect-model
identity remain unresolved; JaSt cannot prove every internal DSP byte; the
offline stage contains no live evidence; and an independent review is still
required before a separately exact named-run authorization may even be
considered. Passing validators, templates, tests, inventories, or checksums
does not authorize hardware.

## Fix round 1

Status: four independent-review findings repaired with offline RED/GREEN
cycles. The corrected stage is sealed for independent re-review, not live use.
The deferred monotonic-timestamp minor was not changed.

### 1. Canonical mapping RED/GREEN

Existing method extended:
`RestorationVerifierTests.test_enabled_first_restores_with_signature_present`.
The fixture now contains a real deterministic five-impulse, six-channel
S32_LE/48 kHz map. A structurally valid forged `MAP.json` changes both scores
and the implied winner while retaining its matching raw hash.

RED command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_enabled_first_restores_with_signature_present
F                                                                        [100%]
AssertionError: 0 != 2
1 failed in 0.57s
```

The old verifier accepted the forged report. `analyze_map_bytes` now contains
the pure mapping algorithm, while the path CLI reads once and delegates to it.
Restoration recomputes from the immutable `MAP.raw.wav` buffer plus the plan's
physical input and requires type-preserving equality of the full report.

GREEN output from the same command:

```text
.                                                                        [100%]
1 passed in 2.63s
```

### 2. Canonical immutable-byte A/B RED/GREEN

Existing methods extended:
`SlotSurveyAnalyzerTests.test_analyze_slot_scopes_repeat_signature_without_claiming_title_or_live_readiness`
and
`RestorationVerifierTests.test_bypassed_first_restores_with_inconclusive_outcome`.
The restoration fixture now uses real deterministic five-impulse mono dry and
active WAVs instead of one-sample silence. A structurally valid forged A/B
report changes the signature and metric values without changing source bytes.

Immutable-seam RED:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_live_matrix.py::SlotSurveyAnalyzerTests::test_analyze_slot_scopes_repeat_signature_without_claiming_title_or_live_readiness
F                                                                        [100%]
AssertionError: False is not true
1 failed in 0.13s
```

Immutable-seam GREEN:

```text
.                                                                        [100%]
1 passed in 0.39s
```

Forgery RED:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_bypassed_first_restores_with_inconclusive_outcome
F                                                                        [100%]
AssertionError: 0 != 2
1 failed in 0.50s
```

Forgery GREEN:

```text
.                                                                        [100%]
1 passed in 2.10s
```

`re/cp34_live_matrix.py::analyze_slot_bytes` is the minimal seam. It accepts
exactly two dry and two active `(path_label, bytes)` pairs, hashes and analyzes
those same immutable bytes, and preserves the supplied labels. The existing
path CLI reads each file once and calls the seam. The restoration verifier
loads that exact local module with the standard library, passes the four
snapshotted derivative buffers and run-relative labels, derives audible status
from the post-restoration attestation, and compares the complete canonical
`cp34-slot-survey-audio-v1` result. It creates no temporary file, duplicates no
algorithm, imports no driver, and opens no ALSA, USB, or hardware path.

### 3. Complete required-capture set RED/GREEN

Existing method extended:
`RestorationVerifierTests.test_missing_s4_fails_restoration`. It now deletes
`S1.raw.wav`, `S2.raw.wav`, `S3.raw.wav`, and `S4.raw.wav`, regenerates an exact
manifest, and requires an explicit missing-input reason for each.

RED command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_missing_s4_fails_restoration
F                                                                        [100%]
AssertionError: 'required_input_missing:ch1-slot1/S1.raw.wav' not found
1 failed in 0.45s
```

GREEN output from the same command:

```text
.                                                                        [100%]
1 passed in 1.14s
```

The verifier now independently requires and parses `MAP.raw.wav` and
`S1.raw.wav` through `S4.raw.wav` as exact six-channel S32_LE/48 kHz WAVs.
Plan, three JaSt summaries and their distinct raw snapshots, action log,
`MAP.json`, four deterministic frozen-channel mono derivatives, `AB.json`,
audible attestation, physical restoration, and manifest inputs remain explicit
requirements. Manifest exactness is an additional gate, never a substitute.

### 4. Candidate-2 predecessor replay RED/GREEN

Existing method extended:
`RestorationVerifierTests.test_second_candidate_requires_a_restored_inconclusive_first_result`.
The fixture now contains complete channel-1 evidence and a full saved
restoration result. One branch newly manifests a fabricated/contradictory
result; another newly manifests invalid underlying P2 state.

RED command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_second_candidate_requires_a_restored_inconclusive_first_result
F                                                                        [100%]
AssertionError: 0 != 2
1 failed in 0.89s
```

GREEN output from the same command:

```text
.                                                                        [100%]
1 passed in 6.48s
```

Candidate-scoped `input_hashes` include `PLAN.json` and the candidate's exact
inputs while excluding its result file, avoiding self-reference. Before
channel 2 is eligible, the verifier re-evaluates channel 1 from the same
immutable snapshot and requires `RESTORED`, `INCONCLUSIVE`, and empty reasons.
The saved result must exactly match the recomputation, including schema,
slot/channel/frozen scope, JaSt limitation, input hashes, and reasons. Neither a
newly manifested result JSON nor its hash is trusted as proof.

### Full regression and inventories

Exact complete command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_host_queue_inventory.py \
  tests/test_cp34_live_matrix.py \
  tests/test_cp34_current_slot_survey.py \
  tests/test_io24_preset_persistence.py \
  tests/test_normalize_io24_capture.py \
  tests/test_io24_capture_decode.py
```

Output:

```text
........................................................................ [ 76%]
......................                        [100%]
94 passed, 27 subtests passed in 50.76s
```

The existing method totals remain 37 live-matrix plus 31 current-slot methods;
the complete combined count remains 94 tests and 27 subtests.

The two pinned inventory command texts were rechecked before execution. Each
uses only the task-local offline analyzer and the pinned local DLL; neither
references Wine/prefix, USB, ALSA, network, or a live input.

Direct inventory command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_host_queue_inventory.py \
  '/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll' \
  --target 0x1800546b0 --context-before 384
{
  "call_kind": "direct",
  "call_sites": [
    {"address": "0x180035abe", "function_end": "0x180035c0b", "function_start": "0x180035a50", "nearby_ascii_immediates": ["FRst", "Appl"]},
    {"address": "0x180049f2f", "function_end": "0x180049fe0", "function_start": "0x1800499f0", "nearby_ascii_immediates": ["JICC", "JDvC", "VoFx"]},
    {"address": "0x18005238e", "function_end": "0x1800523c3", "function_start": "0x1800522ff", "nearby_ascii_immediates": ["MemP"]},
    {"address": "0x1800542a9", "function_end": "0x1800542c6", "function_start": "0x180054250", "nearby_ascii_immediates": ["Pari"]},
    {"address": "0x18005432a", "function_end": "0x180054347", "function_start": "0x1800542d0", "nearby_ascii_immediates": ["Pari", "Para"]},
    {"address": "0x1800555ae", "function_end": "0x1800555c3", "function_start": "0x180055570", "nearby_ascii_immediates": ["GetP", "SetP"]}
  ],
  "image_base": "0x180000000",
  "queue_target": "0x1800546b0",
  "sha256": "567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b"
}
```

RIP-indirect inventory command and output:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_host_queue_inventory.py \
  '/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll' \
  --target 0x1800e53f0 --call-kind rip-indirect --context-before 384
{
  "call_kind": "rip-indirect",
  "call_sites": [
    {"address": "0x1800780db", "function_end": "0x180078189", "function_start": "0x180077fa0", "nearby_ascii_immediates": []},
    {"address": "0x18007867d", "function_end": "0x18007876b", "function_start": "0x1800783b0", "nearby_ascii_immediates": []},
    {"address": "0x180084ac8", "function_end": "0x180084b41", "function_start": "0x1800849e0", "nearby_ascii_immediates": []}
  ],
  "image_base": "0x180000000",
  "queue_target": "0x1800e53f0",
  "sha256": "567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b"
}
```

### Refreshed hashes and manifests

Changed tracked hashes:

```text
ad694447f07b2999d67c12c614f14e726fc3dc4623efd5040a0bd73cc8768d08  re/cp34_current_slot_survey.py
2c315c79a68e477807d4ae34e33a50dc93b60b5374186310998256f2b60499a4  tests/test_cp34_current_slot_survey.py
aac2a39a49284cc42c01247fca53fbaf6b0af1a04dd3182b82aa7358c5db95c8  re/cp34_live_matrix.py
0f27703b9ba94b4af9807ca6bc1f9389f81deb31d12d8d14f435055d1d4b7b8f  tests/test_cp34_live_matrix.py
5bb402f6b0e98f83f2ab082d738d7fd9a071356c07ae64cf0119ea7886f116f8  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md
645fbe169ed13830edd7a3e2d893a1bbfad9d45d091a80cc57a2989c140403d6  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
```

Stage verification command output: all six rows reported `OK`.

```text
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
re/cp34_current_slot_survey.py: OK
tests/test_cp34_current_slot_survey.py: OK
.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-DESIGN.md: OK
.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md: OK
.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-PLAN.template.json: OK
.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-IMPLEMENTATION.md: OK
```

Offline manifest verification command output: all 23 rows reported `OK`,
including the corrected current-slot and live-matrix code/tests, CP34 records,
six-row stage, and pinned DLL.

```text
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-OFFLINE-SHA256SUMS
```

Manifest hashes:

```text
645fbe169ed13830edd7a3e2d893a1bbfad9d45d091a80cc57a2989c140403d6  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
de2c9382beb3750a97198f44031ef479822c1c217464e2acd6b6b52d3e76726b  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-OFFLINE-SHA256SUMS
```

### Fix-round rejection self-audit

1. Can any checked-in command touch USB or ALSA? **No.** The corrected
   analyzer and verifier accept local paths or immutable bytes only; the
   procedure command is run-directory-relative retained-file analysis.
2. Can a template validate without exact authorization and provenance?
   **No.** Unchanged fail-closed validation and template rejection remain
   covered.
3. Can a short press, slot drift, mapped write, extra toggle, or missing inverse
   pass? **No.** Existing exact event and restoration contracts remain green.
4. Can the analysis channel be selected after seeing the effect result?
   **No.** Canonical map recomputation fixes the winner from raw bytes; all raw,
   derivative, event, analyzer, and attestation bindings reuse it.
5. Can a null result become a negative? **No.** Canonical A/B recomputation
   retains the positive-only `INCONCLUSIVE` semantics.
6. Can a signal signature become a title or model claim? **No.** The canonical
   report itself fixes model unresolved and title/live/restoration flags false.
7. Can channel 2 run after failed/unavailable/fabricated channel 1? **No.** Full
   channel-1 evidence is recomputed and its exact saved result is compared.
8. Can a missing evidence file escape the hash seal? **No.** All required
   inputs and all five raw captures are explicit gates in addition to exact
   manifest coverage.

All eight answers are No. Independent re-review remains the next gate; no
reviewer was dispatched in this fix round.

### Battery, files changed, and concerns

Exact sysfs-only battery command is unchanged from the initial report. Output:

```text
BAT0 capacity=100% status=Full
```

Files changed in fix round 1:

- `re/cp34_current_slot_survey.py`
- `tests/test_cp34_current_slot_survey.py`
- `re/cp34_live_matrix.py`
- `tests/test_cp34_live_matrix.py`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/PLAN.md`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/EVIDENCE.md`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-MANIFEST.md`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-LIVE-MATRIX.md`
- `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-OFFLINE-SHA256SUMS`
- this report.

No other production surface, design, template, implementation plan, or
unrelated file was modified. No live acquisition, device access, interface
claim, ALSA stream, Wine/prefix access, front-panel action, preset/effect
operation, mapped write, firmware/reset/DFU, install, external staging,
network, playback, capture, or monitoring occurred.

Remaining concerns are the intended scope limits: preset title and model
identity remain unresolved; JaSt cannot prove every internal DSP byte; no live
evidence exists; and a clean independent re-review must precede any separately
exact named-run authorization. Passing the corrected tools, fixtures, tests,
inventories, or manifests is not live authority.
## Final fix wave — focused RED

Command (offline, hardware-free):

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::PlanValidatorTests::test_rejects_wrong_audio_shape_or_effect_channels tests/test_cp34_current_slot_survey.py::PlanValidatorTests::test_rejects_wrong_toggle_count_short_press_or_mapped_action tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests::test_no_usable_mix_a_channel_is_unavailable tests/test_cp34_current_slot_survey.py::MappingAnalyzerTests::test_changed_impulse_cadence_is_unavailable tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_enabled_first_restores_with_signature_present tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_bypassed_first_restores_with_inconclusive_outcome tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_selected_slot_drift_fails_restoration tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_missing_s4_fails_restoration tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_incomplete_or_mismatched_evidence_manifest_fails tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_second_candidate_requires_a_restored_inconclusive_first_result
```

Exact summary: `9 failed, 1 passed in 11.70s`. The recursive plan-field cases
returned 0 instead of 2, the four-of-five map returned 0 instead of 2, and the
restoration cases raised `TypeError: verify_restoration() got an unexpected
keyword argument 'project_root'`, proving the deterministic run-root seam and
the candidate-scoped/raw/JaSt contracts were not yet implemented. The +96
sample cadence boundary passed. No USB, ALSA, Wine, network, device, driver, or
live interface was accessed.

## Final fix wave — GREEN, seal, and self-audit

Status: `READY FOR SCOPED RE-REVIEW`. This is not a clean review or final
approval, and it grants no live authority.

Implemented contracts:

- S1-S4 mono derivatives must equal the decoded frozen channel of their raw
  six-channel WAVs sample-for-sample; M0 is bound by canonical map replay.
- Canonical newline-terminated `cp34-current-slot-jast-raw-v1` JSON is parsed
  from immutable bytes and every supported summary field/path/hash is derived.
- Candidate-scoped no-clobber manifests/results make channel 2 reachable while
  delaying the root final seal. Channel 2 seals and reports the channel-1
  interim manifest/result and independently re-evaluates its underlying input.
- Plan fields are recursively exact and the normalized non-symlink actual run
  path must equal the project-root-resolved `plan.evidence_dir`.
- Mapping requires all five expected arrivals at one consistent lag and the
  inclusive 96-sample cadence tolerance.
- Restored-state replay/listening and attestation precede A/B analysis;
  `--audible-attested` follows only a positive human attestation, and restored
  but unheard remains `INCONCLUSIVE` rather than `RESTORATION_FAILED`.
- `monotonic_ns` is a nonnegative exact integer, `_load` uses a context manager,
  and the procedure no longer uses “source control” terminology.

### TDD evidence

The initial focused RED and exact `9 failed, 1 passed in 11.70s` output are
recorded immediately above. A later predecessor-input-hash regression used:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_current_slot_survey.py::RestorationVerifierTests::test_second_candidate_requires_a_restored_inconclusive_first_result
```

RED: `1 failed in 6.06s`; channel-2 `input_hashes` lacked
`ch1-slot1/EVIDENCE-SHA256SUMS`. GREEN after the minimal fix:
`1 passed in 20.00s`.

Current-survey module GREEN:

```text
31 passed, 4 subtests passed in 87.75s (0:01:27)
```

Final exact complete hardware-free command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_cp34_host_queue_inventory.py tests/test_cp34_live_matrix.py tests/test_cp34_current_slot_survey.py tests/test_io24_preset_persistence.py tests/test_normalize_io24_capture.py tests/test_io24_capture_decode.py
```

Exact output: `94 passed, 31 subtests passed in 103.54s (0:01:43)`.

### Pinned offline inventories

Before execution, both strings were checked: their only inputs were the local
repository analyzer, fixed local DLL path, numeric targets, and context length.
Neither references Wine/prefix contents, USB/device nodes, ALSA, network,
firmware, or a live interface.

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_host_queue_inventory.py '/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll' --target 0x1800546b0 --context-before 384
```

Output: direct callers `0x180035abe`, `0x180049f2f`, `0x18005238e`,
`0x1800542a9`, `0x18005432a`, `0x1800555ae`; image base `0x180000000`;
target `0x1800546b0`; DLL SHA-256
`567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`.

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_host_queue_inventory.py '/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll' --target 0x1800e53f0 --call-kind rip-indirect --context-before 384
```

Output: RIP-indirect callers `0x1800780db`, `0x18007867d`, `0x180084ac8`;
image base `0x180000000`; target `0x1800e53f0`; same DLL SHA-256.

### Manifest strategy and verification

The six-row current-survey manifest is the core stage. The broader 23-row
offline manifest separately pins the unchanged live-matrix immutable-byte seam
and tests. This keeps both scopes exact without calling six rows every
dependency.

```text
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-OFFLINE-SHA256SUMS
```

Output: all 6 stage rows `OK`; all 23 offline rows `OK`, including the pinned
DLL. Manifest hashes:

```text
d713a3b880a226ad8f76876ef6f2bb9c458827bb6db6b332d955fb4efdce173b  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
0bd57590076873ca497c506483e3c8d99c372a8eefbee52009e651daf19f2d2c  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-OFFLINE-SHA256SUMS
```

Current touched-file hashes:

```text
bf7484eb9257075259b77177d8f0ff00a1d281a97f0927bff0a3db6f897c753b  re/cp34_current_slot_survey.py
93df2c3f108575e14c404814f6cc4cf29f5209bc8279e6a4e6eadcaa5116e590  tests/test_cp34_current_slot_survey.py
c96d0e8adec4274feb7c21ec06a2c994b45a32318f823e19b17fc3f91db04e01  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY.md
7115b815a708832b62eda06c69fd0c4d060904207f8f6dee1b40521c2bd52342  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/PLAN.md
e753b54c346041e9e93265bc8a534df053de7b0357efb02e752b49867f1f2dd5  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/EVIDENCE.md
89f426aa2ed34a2386ba09c05094e132c8fe51270c8b709c1e378847b950536a  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md
a0faf1d74ce94a02433513ebc92ccc5ebbf0152bbe357a915109004c0940c457  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-MANIFEST.md
84bb525ddca044bec3fbd3608e6e62b07c3b0fdde93f4e00dc3e9520c1e53684  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-LIVE-MATRIX.md
d713a3b880a226ad8f76876ef6f2bb9c458827bb6db6b332d955fb4efdce173b  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/CURRENT-SLOT-SURVEY-STAGE.sha256
0bd57590076873ca497c506483e3c8d99c372a8eefbee52009e651daf19f2d2c  .superpowers/sdd/2026-08-28-cp34-preset-effect-control/LINUX-OFFLINE-SHA256SUMS
```

Unchanged dependency hashes: `re/cp34_live_matrix.py`
`aac2a39a49284cc42c01247fca53fbaf6b0af1a04dd3182b82aa7358c5db95c8`;
`tests/test_cp34_live_matrix.py`
`0f27703b9ba94b4af9807ca6bc1f9389f81deb31d12d8d14f435055d1d4b7b8f`.
The report's own hash is computed after this append and supplied in handoff.

### Eight-question rejection self-audit

1. Can any checked-in offline validation command touch USB or ALSA? **No.**
2. Can a template validate without exact authorization/source provenance?
   **No.**
3. Can a short press, slot drift, mapped write, extra toggle, or missing inverse
   pass? **No.**
4. Can the analysis channel be selected after seeing the effect result? **No.**
5. Can a null result become a negative? **No.**
6. Can a signal signature become a title/model claim? **No.**
7. Can channel 2 run after failed restoration or unavailable channel 1? **No.**
8. Can a missing evidence file escape the hash seal? **No.**

All seven final reviewer findings now have focused executable or procedure
coverage: M0/S1-S4 raw binding; canonical JaSt derivation; reachable append-only
channel 2; recursive plan exactness; actual-path/symlink binding; five arrivals
at one lag plus cadence boundaries; and audible attestation before A/B with
restored-unheard semantics.

Battery command (sysfs only):

```text
for battery in /sys/class/power_supply/BAT*; do if [ -d "$battery" ]; then printf '%s capacity=' "$(basename "$battery")"; tr -d '\n' < "$battery/capacity"; printf '%% status='; tr -d '\n' < "$battery/status"; printf '\n'; fi; done
```

Final output: `BAT0 capacity=99% status=Discharging` (an earlier read during the
same wave reported `99%`, `Not charging`).

Files changed: `re/cp34_current_slot_survey.py`,
`tests/test_cp34_current_slot_survey.py`, `CURRENT-SLOT-SURVEY.md`, `PLAN.md`,
`EVIDENCE.md`, `RESUME.md`, `LINUX-MANIFEST.md`, `LINUX-LIVE-MATRIX.md`,
`CURRENT-SLOT-SURVEY-STAGE.sha256`, `LINUX-OFFLINE-SHA256SUMS`, and this report.
No approved design, implementation plan, template, progress ledger, review
package, live-matrix source/test, driver, or other production surface changed.

No USB/device node, ALSA device, Wine/prefix content, network, firmware,
reset/DFU, install, external stage/replay, physical preset/effect control, or
live audio action occurred. Remaining concerns are the intentional limits:
title/model identity remains unresolved, no live run is authorized, and scoped
independent re-review is still pending.
