# CP34 Autonomous Voice FX Gate-Transition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine without a human listener whether linked Channel-2 slot-3 recall produces the factory Slap Echo signal path when the existing Input-2 noise is deliberately passed through a temporary channel-strip gate transition with a byte-exact restoration write.

**Architecture:** Add a narrow host action that reuses the proven linked recall, sends byte-pinned factory gate blobs with only `on` changing, and restores gate-on before clearing stereo link in nested cleanup. A dedicated runner owns one fixed-duration passive ALSA capture, while a hardware-free analyzer validates capture format, event windows, gate observability, and 150 ms transfer coefficients. Every live result remains conditional on a downstream gate-observable capture tap.

**Tech Stack:** Python 3 standard library, NumPy for offline WAV analysis, PyUSB through the existing `io24.Io24` transport, ALSA `arecord`, `unittest`, SHA-256 checkpoint manifests.

**Spec:** `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260904T022636-0700-linked-channel2-slot3-audio/SCOPE.md` and `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260904T022636-0700-linked-channel2-slot3-audio/RESULT.md`

## Global Constraints

- Target only Revelator io24 serial `AB7C22200355`; abort before mutation on identity mismatch or battery at/below 10 percent.
- Treat the user's 2026-09-04 “make extended plan, then proceed -authorized” as authority only for this plan's one bounded live trial.
- Permitted live writes are exactly: Channel-2 slot `3 -> 2`, stereo link on, Channel-2 slot `2 -> 3`, two Channel-2 factory-gate instances off, those same two instances restored on, and stereo link off.
- Factory gate fields are fixed at threshold `-47.5` dBFS, range `-60.0` dB, attack `0.025` s, release `0.7` s, key filter `730.000244` Hz, expander on, key listen off, 48 kHz.
- Emit no playback and make no gain, phantom, mute, high-pass, routing, output, mixer, preset-record, Voice-FX-parameter, firmware, reset, DFU, install, Wine, or network change.
- Start only from flags `0x1a1`: link off, Channel 1 disabled on slot 0, Channel 2 enabled on slot 3. Preserve the readable Channel-1 guard.
- Gate state has no live readback. Restoration means byte-exact re-emission of the factory gate-on blobs, not a claim of read-back verification.
- Stop on preflight mismatch, unavailable capture, unexpected state, input meter above the probe ceiling, write failure, cleanup failure, or postflight mismatch. Do not retry a live write automatically.
- The workspace is not a Git repository. Replace plan commit steps with task-local SHA-256 checkpoints; do not initialize Git.

## File Structure

- Modify `io24.py`: factory gate constants, byte-pinned gate-kwargs helper, and nested-cleanup live action.
- Modify `tests/test_io24_linked_recall_action.py`: exact sequencing, blob arguments, input-level stop, and cleanup-failure contracts.
- Create `re/cp34_gate_transition_audio.py`: pure capture/event validation and transfer analysis.
- Create `tests/test_cp34_gate_transition_audio.py`: synthetic six-channel positive, negative, and invalid-tap fixtures.
- Create `re/cp34_gate_transition_trial.py`: `--execute`-gated serial/battery/capture orchestration and durable JSON report.
- Create `tests/test_cp34_gate_transition_trial.py`: dry-run, battery, identity, capture-start, and single-action orchestration contracts.
- Create `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260904T025429-0700-gate-transition-probe/`: scope, pre/post state, raw capture, reports, commands, verification, result, progress, dashboard mirror, and manifest.
- Modify `README.md`, `PROTOCOL.md`, task-local `RESUME.md`, and task-local `EVIDENCE.md` only after the result is classified.

---

### Task 1: Freeze the Gate Bytes and Trial Scope

**Files:**
- Create: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260904T025429-0700-gate-transition-probe/SCOPE.md`
- Create: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260904T025429-0700-gate-transition-probe/GATE-BLOBS.json`

**Interfaces:**
- Consumes: factory record 4 from `re/uc_factory_presets.json` and `io24_dsp.gate_blob(index, ...)`.
- Produces: four immutable 72-byte gate-blob hashes and the exact live action allowlist.

- [x] **Step 1: Record the exact authorization interpretation and stop rules**

Write `SCOPE.md` with the serial, starting state, exact permitted operation set, forbidden operations, no-retry rule, and the fact that gate restoration is write-confirmed but not readable.

- [x] **Step 2: Derive and record the four gate blobs**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import hashlib, io24_dsp
kw = dict(threshold_db=-47.5, range_db=-60.0, attack_s=0.025,
          release_s=0.7, keyfilter_hz=730.000244, expander=True,
          keylisten=False, fs=48000.0)
for on in (False, True):
    for index in (0, 1):
        blob = io24_dsp.gate_blob(index, on=on, **kw)
        print(on, index, len(blob), hashlib.sha256(blob).hexdigest())
PY
```

Expected literal hashes:

```text
off instance 0  4c4231f9a63267d6b42a7723099b538f53bdcb786ca72de2e9034705b1d2200c
off instance 1  028d515d874947adebc745078ea6f83b7b03764dc1013da588952ffe98bcdbac
on  instance 0  e6efb8cf74415621a6160091ff06b1e0ef07a465eb03c2dc2863b053b83f73ee
on  instance 1  ed052c4ac25cc0edb837d0a0c68c245869980e66a9a6a347888afc674f67c31a
```

- [x] **Step 3: Checkpoint the immutable scope**

Run `sha256sum SCOPE.md GATE-BLOBS.json > SCOPE.sha256` from the run directory and verify it immediately with `sha256sum -c SCOPE.sha256`.

### Task 2: Add the Fail-Closed Gate-Transition Action

**Files:**
- Modify: `tests/test_io24_linked_recall_action.py`
- Modify: `io24.py:225-348`

**Interfaces:**
- Consumes: `dev.read_params()`, `dev.set_preset_slot(channel, slot)`, `dev.set_channel_link(on)`, and `dev.set_gate(channel, **kwargs)`.
- Produces: `probe_channel2_slot3_with_gate_transition(dev, sleep_fn=time.sleep, event_fn=..., input_ceiling=0.01) -> dict`.

- [x] **Step 1: Write failing success-path and exact-arguments tests**

Extend the stateful fake with `input1Level`, `input2Level`, and:

```python
def set_gate(self, channel, **kwargs):
    self.calls.append(("set_gate", channel, copy.deepcopy(kwargs)))
```

Assert the exact order `read -> slot2 -> read -> link on -> read -> slot3 -> read -> gate on -> gate off -> gate on restore -> link off -> read`, Channel 2 only, two gate instances through `instance=None`, exact factory kwargs, and the event sequence:

```python
[
    "baseline_confirmed", "channel2_slot2_confirmed", "link_on_confirmed",
    "channel2_slot3_confirmed", "factory_gate_on_sent",
    "factory_gate_off_sent", "factory_gate_restored", "link_off_confirmed",
]
```

- [x] **Step 2: Run the tests and verify RED**

Run `python3 -m unittest tests.test_io24_linked_recall_action`. Expected: failures stating `probe_channel2_slot3_with_gate_transition` is missing.

- [x] **Step 3: Write the minimum action and factory helper**

Add:

```python
FACTORY_SLAP_GATE = {
    "threshold_db": -47.5, "range_db": -60.0, "attack_s": 0.025,
    "release_s": 0.7, "keyfilter_hz": 730.000244, "expander": True,
    "keylisten": False, "instance": None, "fs": 48000.0,
}

def _set_factory_slap_gate(dev, on):
    return dev.set_gate(2, on=on, **FACTORY_SLAP_GATE)
```

Implement the existing linked selector sequence, require `input2Level <= 0.01` before gate-off, send factory gate-on, wait 1.5 seconds, send factory gate-off, wait 3.0 seconds, and restore gate-on before clearing link. Use nested cleanup so link-off is attempted even if gate restoration raises. Return exact event names, final readable state, `gate_restoration="WRITE_SENT_NOT_READABLE"`, and Channel-1 guard equality.

- [x] **Step 4: Add failing safety-path tests**

Cover: input level over `0.01` blocks before gate-off; slot-3 failure still clears link; gate-off failure still emits factory gate-on and link-off; factory gate restore failure still emits link-off and returns a cleanup failure.

- [x] **Step 5: Run focused GREEN**

Run `python3 -m unittest tests.test_io24_linked_recall_action`. Expected: all old and new tests pass with no warning.

- [x] **Step 6: Pin generated gate bytes**

Add assertions that the four blobs generated from `FACTORY_SLAP_GATE` match the Task-1 literal SHA-256 values. This catches a changed field, instance, sample rate, or `on` bit.

### Task 3: Build a Reproducible Gate/Delay Analyzer

**Files:**
- Create: `tests/test_cp34_gate_transition_audio.py`
- Create: `re/cp34_gate_transition_audio.py`

**Interfaces:**
- Consumes: a six-channel 32-bit PCM/48 kHz WAV and the event array from the live report.
- Produces: `analyze_capture(wav_path, events) -> dict` with `capture_tap`, `repeat_result`, per-window levels, direct/150/300 ms coefficients, and a bounded `effect_conclusion`.

- [x] **Step 1: Write a synthetic positive test**

Generate deterministic Input-2 noise with seed `240904`, put it in raw channel 2, and place `0.5*x[n] + 0.25*x[n-7200] + 0.0625*x[n-14400]` in channels 3-6 only during the gate-off window. Assert `capture_tap="DOWNSTREAM_GATE_OBSERVABLE"` and `repeat_result="REPEAT_150MS_SIGNATURE"`.

- [x] **Step 2: Run the positive test and verify RED**

Run `python3 -m unittest tests.test_cp34_gate_transition_audio`. Expected: failure because the analyzer module is absent.

- [x] **Step 3: Implement strict WAV and event validation**

Require exactly six channels, four-byte samples, 48 kHz, monotonically ordered required events, at least 0.5 seconds per clean window, and no clipping above -0.1 dBFS. Return `INVALID_CAPTURE` with literal reasons rather than guessing windows.

- [x] **Step 4: Implement gate observability and transfer fitting**

Use NumPy least squares against current, 7200-sample delayed, and 14400-sample delayed Input 2. Require a gate-on/off monitor RMS delta of at least 12 dB for `DOWNSTREAM_GATE_OBSERVABLE`; otherwise return `CAPTURE_TAP_NOT_GATE_OBSERVABLE`. Require correlation above `0.95` and `abs(lag150/direct) >= 0.05` on every monitor channel for a repeat signature.

- [x] **Step 5: Add negative and invalid tests**

Test a direct-only gate-off path, a pre-gate tap with no on/off delta, wrong channel count, wrong rate, missing events, reversed events, clipping, and a cadence-shifted 173 ms echo. The 173 ms fixture must not pass the 150 ms classifier.

- [x] **Step 6: Run analyzer GREEN**

Run `python3 -m unittest tests.test_cp34_gate_transition_audio`. Expected: all fixtures pass and no device module opens hardware at import.

### Task 4: Add an Execute-Gated Live Runner

**Files:**
- Create: `tests/test_cp34_gate_transition_trial.py`
- Create: `re/cp34_gate_transition_trial.py`

**Interfaces:**
- Consumes: expected serial, battery path, capture endpoint, duration, report path, injected device/recorder factories for tests.
- Produces: one JSON report with identity, battery, event offsets, action result, capture metadata/hash, cleanup status, and no audibility claim.

- [x] **Step 1: Write runner RED tests**

Assert that default invocation returns `DRY_RUN_ONLY`; battery `<=10` opens
neither device nor capture; a wrong serial opens no capture; an early recorder
exit calls no action; `--execute` calls the action exactly once; and any action
exception still waits for capture cleanup and records `LIVE_TRIAL_FAILED`.

- [x] **Step 2: Run runner tests and verify RED**

Run `python3 -m unittest tests.test_cp34_gate_transition_trial`. Expected: failure because the runner module is absent.

- [x] **Step 3: Implement the runner**

Use `arecord -q -D hw:CARD=R24,DEV=0 -t wav -f S32_LE -r 48000 -c 6 -d 14`. Read battery before enumerating USB, verify `device.dev.serial_number` before calling the action, set `shadow=False`, reject an existing capture path, record monotonic event offsets, close the device in `finally`, and never retry.

- [x] **Step 4: Run runner GREEN and syntax checks**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cp34_gate_transition_trial
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  io24.py re/cp34_gate_transition_audio.py re/cp34_gate_transition_trial.py
```

Expected: all tests pass and compilation exits 0.

### Task 5: Verify Offline Gates Before Hardware

**Files:**
- Create: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260904T025429-0700-gate-transition-probe/OFFLINE-VERIFICATION.md`

**Interfaces:**
- Consumes: Tasks 1-4.
- Produces: an explicit `LIVE_ELIGIBLE` or `LIVE_BLOCKED` decision.

- [x] **Step 1: Run focused suites**

Run the three new test modules plus `tests.test_io24_factory_slap_action`, `tests.test_io24_host_delay_action`, and `tests.test_cp34_readonly_preflight`.

- [x] **Step 2: Run the runner without `--execute`**

Require JSON status `DRY_RUN_ONLY` and confirm no `arecord`, io24 host, or Python device-control process was opened.

- [x] **Step 3: Reconcile current source hashes and prior checkpoint**

Run `sha256sum -c` on the 20-row preceding checkpoint. Record any source drift introduced by Tasks 2-4 as intentional new-plan drift, not predecessor corruption.

- [x] **Step 4: Decide eligibility**

Mark `LIVE_ELIGIBLE` only if every test passes, gate hashes match, the dry run is non-mutating, battery is above 10 percent, and no process owns vendor interface 5 or the ALSA capture endpoint.

### Task 6: Execute One Live Gate-Transition Capture

**Files:**
- Create: run-local `PRESTATE.json`, `LIVE-TRIAL.json`, `gate-transition.wav`, and `POSTSTATE.json`.

**Interfaces:**
- Consumes: Task-5 `LIVE_ELIGIBLE` and the user's bounded authorization.
- Produces: exactly one live capture with cleanup evidence.

- [x] **Step 1: Run the dedicated read-only preflight**

Run `python3 re/cp34_readonly_preflight.py --serial AB7C22200355` and stop unless both hashes match and the exact starting state is present.

- [x] **Step 2: Execute once**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_gate_transition_trial.py \
  --serial AB7C22200355 \
  --capture-endpoint hw:CARD=R24,DEV=0 \
  --capture-path .superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260904T025429-0700-gate-transition-probe/gate-transition.wav \
  --report .superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260904T025429-0700-gate-transition-probe/LIVE-TRIAL.json \
  --execute
```

Do not rerun after any nonzero exit.

- [x] **Step 3: Run one independent postflight**

Require link off, Channel 1 disabled on slot 0, Channel 2 enabled on slot 3, and two identical `JaSt` hashes. Record gate restoration only as exact writes sent.

### Task 7: Classify the Capture and Choose the Offline Branch

**Files:**
- Create: run-local `AUDIO-ANALYSIS.json` and `RESULT.md`.

**Interfaces:**
- Consumes: Task-6 raw immutable capture and event report.
- Produces: one of `REPEAT_150MS_SIGNATURE`, `NO_REPEAT_DOWNSTREAM_GATE_OFF`, `CAPTURE_TAP_NOT_GATE_OBSERVABLE`, or `INVALID_CAPTURE`.

- [x] **Step 1: Hash the raw capture before analysis**

Record its SHA-256 and WAV metadata; all derivatives must cite that source hash.

- [x] **Step 2: Run the analyzer**

Run `python3 re/cp34_gate_transition_audio.py LIVE-TRIAL.json gate-transition.wav > AUDIO-ANALYSIS.json`.

- [x] **Step 3: Apply the branch rule**

If `REPEAT_150MS_SIGNATURE`, treat it as audible-path waveform evidence but keep model identity and physical storage separate. If `NO_REPEAT_DOWNSTREAM_GATE_OFF`, retain a strong linked-path negative without claiming slot storage failure. If the tap is not gate-observable or invalid, stop live work and continue only with a bounded static trace of the USB capture tap relative to block 201; do not increase gain or add playback.

### Task 8: Regress, Document, and Seal

**Files:**
- Modify: `README.md`, `PROTOCOL.md`, task-local `RESUME.md`, task-local `EVIDENCE.md`
- Create: run-local `COMMANDS.md`, `TESTS.md`, `PROGRESS.md`, `OBSIDIAN.md`, `CHECKPOINT.sha256`
- Modify: `/home/ajuntanaga/Documents/Obsidian/ResearchOS/Projects/PreSonus Revelator io24 — CP34 custom-firmware recovery.md`

**Interfaces:**
- Consumes: classified Task-7 result.
- Produces: the newest authoritative crash-recovery checkpoint and dashboard index.

- [x] **Step 1: Run focused and complete regression**

Run all new focused modules, then `python3 -m unittest discover -s tests` with a 900-second outer timeout. Record incomplete timeouts as incomplete, never PASS.

- [x] **Step 2: Update controlling documentation**

Put the new result at the top of `RESUME.md` and `EVIDENCE.md`; update README/PROTOCOL only to the evidence level the analyzer supports. Preserve prior historical sections as provenance.

- [x] **Step 3: Refresh the dashboard by direct Markdown and read it back**

Keep task-local `RESUME.md` authoritative. The vault file is an index and grants no live authority.

- [x] **Step 4: Seal and verify the checkpoint**

Hash all changed sources, tests, raw capture, JSON reports, docs, and run-local evidence into `CHECKPOINT.sha256`; run `sha256sum -c CHECKPOINT.sha256` from the project root and require every row `OK`.

## Self-Review

- Spec coverage: the plan covers the missing above-gate stimulus, exact inverse, serial/battery/prestate gates, no-human capture, objective classification, cleanup, regression, and recovery documentation.
- Placeholder scan: the plan contains no deferred implementation placeholders; every branch has a concrete result and next action.
- Type consistency: the action, runner, and analyzer signatures match across Tasks 2-7; event names and file paths are fixed once and reused verbatim.
- Safety review: the only new live DSP writes are byte-pinned Channel-2 gate blobs; no gain or playback is used, and link-off remains the outer cleanup action.
