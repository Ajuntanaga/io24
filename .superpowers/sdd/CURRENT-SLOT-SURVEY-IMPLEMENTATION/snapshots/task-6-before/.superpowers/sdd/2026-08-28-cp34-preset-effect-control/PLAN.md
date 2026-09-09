# CP34 execution plan

Status: active, Linux-only; current-slot survey final fix wave integrated and
awaiting scoped independent re-review

The project runs on Linux. A Windows or macOS Universal Control host is not an
available dependency. Wine and the protected io24 prefix remain outside this
workstream unless the user separately reopens them.

## Phase A: reproduce the evidence

- Hash the vendor host module and extract the io24 firmware into a temporary,
  non-project directory.
- Record image version, size, extraction offsets, and tool versions.
- Reproduce the known preset-component and Voice FX-gate instruction windows.
- Audit current comments and tests against the newest protocol conclusions.

Exit: every CP34 premise is tied to bytes, instructions, a native artifact, or
an executable fixture.

## Phase B: derive the control sequences

- Trace host-side builders for user-preset store, library-to-slot assignment,
  Voice FX model selection, and Voice FX activation.
- Compare that trace to the device resolver and internal component boundaries.
- Inventory every direct caller of the host module's central operation queue and
  every `WinUsb_WritePipe` consumer from the pinned DLL.
- Treat the combination of the host-operation inventory and closed firmware
  ingress map as the Linux-native capability boundary. Do not preserve a
  supported-host capture as a prerequisite when no such host exists.

Exit: each candidate field and ordering rule has source-bound provenance. No
candidate is allowed to depend on a guessed tag or successful reply alone.

## Phase C: implement test-first

- Keep the PE queue/writer inventory executable and hash-pinned on Linux.
- Keep the Linux live-matrix generator, audio analyzer, and restoration-ledger
  validator hardware-free and contract-tested.
- Keep title-free capture classification source/model-neutral and offline-only
  until a separate live procedure and executable restoration contract exist.
- Add complete fixtures for baseline, Voice FX activation, parameter change,
  preset store, slot assignment, hardware recall, and restoration.
- Make the decoder preserve coherent novel commands and reject malformed or
  contradictory frames.
- Implement only the smallest observed sequence needed by the two outcomes.
- Keep host JSON persistence working as a fallback and retained regression.

Exit: hardware-free tests fail before the implementation and pass after it,
including wrong-slot, partial-sequence, and restoration failures.

## Phase D: validate and seal

- Record Linux PRESTATE and immutable native captures only after a separately
  authorized, source-bound live matrix exists.
- Prove audible Voice FX with an observable A/B result and a working positive
  control in the same run.
- Prove the custom preset survives editor-independent hardware recall.
- Restore every PRESTATE value, original slot assignment, and preset library.
- Hash the evidence and obtain an independent review.

Exit: both CP34 outcomes pass and restoration is complete. Otherwise CP34 stays
active with the exact failed gate recorded.

## Current-slot survey offline stage

The positive-only current-slot survey is implemented as a review-eligible
offline stage. Its six-row core-stage manifest tracks:

- `re/cp34_current_slot_survey.py` —
  `bf7484eb9257075259b77177d8f0ff00a1d281a97f0927bff0a3db6f897c753b`;
- `tests/test_cp34_current_slot_survey.py` —
  `93df2c3f108575e14c404814f6cc4cf29f5209bc8279e6a4e6eadcaa5116e590`;
- `CURRENT-SLOT-SURVEY-DESIGN.md` —
  `8e5beb5b13da09cfa66b15908adf0189053c2861908822912e2d3ca860e52b28`;
- `CURRENT-SLOT-SURVEY.md` —
  `c96d0e8adec4274feb7c21ec06a2c994b45a32318f823e19b17fc3f91db04e01`;
- `CURRENT-SLOT-SURVEY-PLAN.template.json` —
  `3288d3be80f125e2a66f9be71e18fc213a5c6070fe1e99150d3e87cc80b72ac3`;
- `CURRENT-SLOT-SURVEY-IMPLEMENTATION.md` —
  `7d24b3d3e6de5f0fc519768c9732cfdd08e49268cbb6024e4b43a299cc9f8e49`.

The broader offline manifest additionally pins the immutable-byte analyzer seam
in `re/cp34_live_matrix.py` and its tests; those are dependencies, not two more
rows in the current-survey core-stage manifest.

The complete hardware-free regression passed with 94 tests and 31 subtests.
The stage does not run a survey and does not authorize hardware. Its next gate
is an independent offline review. Only after a clean review may a separately
exact authorization be considered for a named run; validator, analyzer,
restoration-verifier, template, test, or manifest success is never live
authority.

The final fix wave additionally binds each S1-S4 derivative sample-for-sample
to the frozen channel in its raw capture; derives every JaSt summary field from
canonical `cp34-current-slot-jast-raw-v1` bytes; uses no-clobber
candidate-scoped interim manifests/results so channel 2 is reachable without
invalidating channel 1; rejects undeclared plan fields and run-path ambiguity;
requires all five map arrivals at one consistent lag; and treats a restored but
unheard result as `INCONCLUSIVE`. These are offline verification guarantees
only. This wave has not been independently re-reviewed. The next gate remains
a scoped independent re-review, followed only after a clean result by a
separately exact authorization.
