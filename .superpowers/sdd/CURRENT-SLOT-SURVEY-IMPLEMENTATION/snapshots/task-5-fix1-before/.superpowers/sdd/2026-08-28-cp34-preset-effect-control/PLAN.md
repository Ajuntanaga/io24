# CP34 execution plan

Status: active, Linux-only; current-slot survey offline stage integrated and
awaiting independent review

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
offline stage. Its exact tracked artifacts are:

- `re/cp34_current_slot_survey.py` —
  `1bb029a18181a85c602a84f42fbbf57602dbce321a5ae39727c14b9828a74ff3`;
- `tests/test_cp34_current_slot_survey.py` —
  `3119b35f1710470bc246897dce001098bfe75c86152754813e5e0913c724a55c`;
- `CURRENT-SLOT-SURVEY-DESIGN.md` —
  `8e5beb5b13da09cfa66b15908adf0189053c2861908822912e2d3ca860e52b28`;
- `CURRENT-SLOT-SURVEY.md` —
  `295d6763f70a4bf095b0ad0fff1be16e85ac449aa9d6e7216a8cec8adcb87c43`;
- `CURRENT-SLOT-SURVEY-PLAN.template.json` —
  `3288d3be80f125e2a66f9be71e18fc213a5c6070fe1e99150d3e87cc80b72ac3`;
- `CURRENT-SLOT-SURVEY-IMPLEMENTATION.md` —
  `7d24b3d3e6de5f0fc519768c9732cfdd08e49268cbb6024e4b43a299cc9f8e49`.

The complete hardware-free regression passed with 94 tests and 27 subtests.
The stage does not run a survey and does not authorize hardware. Its next gate
is an independent offline review. Only after a clean review may a separately
exact authorization be considered for a named run; validator, analyzer,
restoration-verifier, template, test, or manifest success is never live
authority.
