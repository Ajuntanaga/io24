# Host Bus Source and Balance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the retired physical-input monitor with truthful, passive Mix A and Mix B PipeWire sources and aligned Host-side bus balance controls while leaving Main visibly unavailable.

**Architecture:** Keep the Host snapshot key `pan`, migrate it from version 1 input positions to version 2 bus balances, and publish Mix A and Mix B through two independent filter-chain child processes. GTK owns the presentation and slow reconciliation loop; `io24_mbc.py` owns strict state, signal graphs, PipeWire configuration, and process lifecycle; `io24.py` validates and migrates Host files before any device setter runs.

**Tech Stack:** Python 3.8+, GTK4/libadwaita, PipeWire filter-chain, `pw-cli`, `unittest`/pytest, SHA-256 task-local recovery records.

**Spec:** `docs/superpowers/specs/2026-09-09-host-bus-source-balance-design.md`

## Global Constraints

- Linux Host only; do not access Wine or `/home/ajuntanaga/.wine-io24`.
- No Host launch, PipeWire graph launch, USB/device/audio action, installation, publication, firmware action, network use, or Obsidian write during offline implementation.
- Main is not a capturable source: USB capture 1-2 are physical Inputs, 3-4 are Mix A, and 5-6 are Mix B.
- Publish only passive `io24 Host Mix A` and `io24 Host Mix B` `Audio/Source` endpoints; never route them automatically to io24 playback.
- Preserve `stream.dont-remix = true` on both sides of each source graph.
- Main remains visible and insensitive; routine discovery and balance moves never toast.
- Keep Mix A and Mix B in independent child processes so one survives failure of the other.
- The exact 53-file Claude disclosure boundary must not expand without separate approval.
- This workspace has no usable Git metadata. Replace commit steps with task-local before/after SHA-256 inventories and never imply a commit exists.
- Run all tests with `PYTHONDONTWRITEBYTECODE=1`, disable pytest's cache provider, and elevate `ResourceWarning` to an error for affected-suite closure.

---

### Task 1: Establish recovery identity and migrate Host pan state

**Files:**
- Create: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260909T103619-0700-host-bus-source-balance/SCOPE.md`
- Create: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260909T103619-0700-host-bus-source-balance/PRE-EDIT.sha256`
- Modify: `io24_mbc.py:42-43,79,183-221`
- Modify: `io24.py:1952-2032,2692-2711`
- Test: `tests/test_io24_host_parameter_repairs.py:416-523`

**Interfaces:**
- Produces: `PAN_SNAPSHOT_VERSION = 2`
- Produces: `default_pan_snapshot() -> dict`
- Produces: `validate_pan_snapshot(state: dict) -> dict`
- Produces: `normalise_pan_snapshot(state)` returning the normalized dictionary
  and a list of migration messages.
- Produces: `_normalise_host_features(features)` returning the normalized
  dictionary and a list of migration messages.
- Consumes: existing `_finite_number()` and atomic `Io24.save_preset()` / `Io24.load_preset()` flow.

- [ ] **Step 1: Create the task-local scope and pre-edit identity**

Write `SCOPE.md` with the approved offline boundary, the two source names, the permanently unavailable Main control, the exact excluded actions, and the peer agreement timestamp `2026-09-09T10:33:34-07:00`. Compute SHA-256 values for:

```text
io24.py
io24_mbc.py
io24gtk.py
tests/test_io24_host_parameter_repairs.py
README.md
GUIDE.md
docs/superpowers/specs/2026-09-09-host-bus-source-balance-design.md
docs/superpowers/plans/2026-09-09-host-bus-source-balance.md
```

Add the exact output to `PRE-EDIT.sha256` with `apply_patch`, then run:

```bash
sha256sum -c .superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260909T103619-0700-host-bus-source-balance/PRE-EDIT.sha256
```

Expected: every entry reports `OK`.

- [ ] **Step 2: Write RED tests for the version 2 state and version 1 migration**

Replace the retired input-pan assertions with tests equivalent to:

```python
def test_bus_balance_state_is_strict_and_defaults_centered(self):
    expected = {"version": 2,
                "balances": {"mixa": 0.5, "mixb": 0.5}}
    self.assertEqual(io24_mbc.default_pan_snapshot(), expected)
    self.assertEqual(io24_mbc.validate_pan_snapshot(expected), expected)
    for invalid in (
        {"version": 2, "balances": {"mixa": 0.5}},
        {"version": 2,
         "balances": {"mixa": True, "mixb": 0.5}},
        {"version": 2,
         "balances": {"mixa": 0.5, "mixb": 1.1}},
        {"version": 2,
         "balances": {"mixa": 0.5, "mixb": float("nan")}},
    ):
        with self.assertRaises(ValueError):
            io24_mbc.validate_pan_snapshot(invalid)

def test_legacy_input_pan_migrates_to_neutral_bus_balance(self):
    legacy = {"version": 1, "enabled": True,
              "positions": [0.2, 0.85]}
    state, notices = io24_mbc.normalise_pan_snapshot(legacy)
    self.assertEqual(state, io24_mbc.default_pan_snapshot())
    self.assertEqual(notices, [
        "legacy input pan was not applied; Mix A/B balances centered"])
```

Add a malformed-version-1 case proving migration validates the old object
before discarding its positions.

- [ ] **Step 3: Run the focused tests and confirm RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_io24_host_parameter_repairs.py \
  -k 'bus_balance_state or legacy_input_pan' -p no:cacheprovider
```

Expected: failures because version 2 state and `normalise_pan_snapshot` do not
exist yet.

- [ ] **Step 4: Implement strict version 2 state and explicit migration**

In `io24_mbc.py`, replace the version 1 functions with this interface:

```python
PAN_SNAPSHOT_VERSION = 2
BUS_SOURCE_KEYS = ("mixa", "mixb")

def default_pan_snapshot():
    return {"version": PAN_SNAPSHOT_VERSION,
            "balances": {bus: 0.5 for bus in BUS_SOURCE_KEYS}}

def validate_pan_snapshot(state):
    if not isinstance(state, dict) or set(state) != {"version", "balances"}:
        raise ValueError("pan state fields must be balances, version")
    if state["version"] != PAN_SNAPSHOT_VERSION:
        raise ValueError("pan snapshot version must be 2")
    raw = state["balances"]
    if not isinstance(raw, dict) or set(raw) != set(BUS_SOURCE_KEYS):
        raise ValueError("pan balances must contain mixa and mixb")
    return {"version": PAN_SNAPSHOT_VERSION,
            "balances": {bus: _finite_number(
                raw[bus], "%s balance" % bus, 0.0, 1.0)
                for bus in BUS_SOURCE_KEYS}}

def normalise_pan_snapshot(state):
    if isinstance(state, dict) and state.get("version") == 1:
        if set(state) != {"version", "enabled", "positions"}:
            raise ValueError("legacy pan fields must be enabled, positions, version")
        if not isinstance(state["enabled"], bool):
            raise ValueError("legacy pan enabled must be Boolean")
        positions = state["positions"]
        if not isinstance(positions, list) or len(positions) != 2:
            raise ValueError("legacy pan positions must contain two values")
        for value in positions:
            _finite_number(value, "legacy pan position", 0.0, 1.0)
        return default_pan_snapshot(), [
            "legacy input pan was not applied; Mix A/B balances centered"]
    return validate_pan_snapshot(state), []
```

Remove `pan_coefficients()` and `pan_controls()` in this task; their replacement
belongs to Task 2.

- [ ] **Step 5: Make Host-file normalization return migration notices**

Change `_normalise_host_features()` in `io24.py` to return `(normalized,
migrations)`. Normalize multiband unchanged; normalize `pan` through
`normalise_pan_snapshot()` and extend the migration list.

Update the two callers:

```python
host_features, _migrations = _normalise_host_features(host_features)
```

for save, and:

```python
host_features, migrations = _normalise_host_features(
    snap.get("host_features"))
```

for load. Add `"host_feature_migrations": migrations` to
`_last_preset_load_report`. Saving a legacy object must emit version 2, while
loading reports the migration.

- [ ] **Step 6: Add Host-file atomicity and round-trip regressions**

Update the existing Host-feature test to save version 2 and assert exact
round-trip. Add a legacy file test asserting centered state and the exact
migration notice. Add an invalid current state test whose fake device records
setter calls and assert `device.applied == []` after `load_preset()` raises.

- [ ] **Step 7: Run Task 1 tests GREEN**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_io24_host_parameter_repairs.py \
  -k 'pan or bus_balance or host_feature or multiband_state_round_trips' \
  -p no:cacheprovider
```

Expected: all selected tests pass.

- [ ] **Step 8: Record the Task 1 recovery identity**

Compute current hashes for `io24.py`, `io24_mbc.py`, and the focused test file.
Add them to `TASK1.sha256` via `apply_patch`, verify with `sha256sum -c`, and
append the RED/GREEN commands and counts to the run's `PROGRESS.md`.

---

### Task 2: Build independent passive Mix A and Mix B sources

**Files:**
- Modify: `io24_mbc.py:393-456,459-628`
- Test: `tests/test_io24_host_parameter_repairs.py:461-523,1142-1250`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260909T103619-0700-host-bus-source-balance/PROGRESS.md`

**Interfaces:**
- Consumes: `BUS_SOURCE_KEYS`, `validate_pan_snapshot()`, `_finite_number()`,
  `_lin()`, `Chain._launch()`, `Chain.node_id()`, and `Chain.set_controls()`.
- Produces: `balance_coefficients(position)` returning `(left, right)` floats.
- Produces: `balance_controls(position)` returning the two named gain controls.
- Produces: `build_bus_source_graph(bus, balance)` returning a graph dictionary.
- Produces: `build_bus_source_conf(bus, capture_target, balance)` returning text.
- Produces: `BusSourceChain(bus)`.
- Produces: `BusSourceManager.reconcile(capture_target, balances, now=None)`
  returning a mapping from bus key to status string.
- Produces: `BusSourceManager.set_balance(bus, position) -> bool`
- Produces: `BusSourceManager.stop() -> None`

- [ ] **Step 1: Write RED balance-law and channel-selection tests**

Add tests with these exact invariants:

```python
def test_bus_balance_is_center_unity_without_crossfeed(self):
    self.assertEqual(io24_mbc.balance_coefficients(0.0), (1.0, 0.0))
    self.assertEqual(io24_mbc.balance_coefficients(0.5), (1.0, 1.0))
    self.assertEqual(io24_mbc.balance_coefficients(1.0), (0.0, 1.0))
    quarter = io24_mbc.balance_coefficients(0.25)
    three_quarter = io24_mbc.balance_coefficients(0.75)
    self.assertEqual(quarter[0], 1.0)
    self.assertEqual(three_quarter[1], 1.0)
    self.assertAlmostEqual(quarter[1], three_quarter[0])

def test_bus_graph_selects_only_its_exact_capture_pair(self):
    mixa = io24_mbc.build_bus_source_graph("mixa", 0.5)
    mixb = io24_mbc.build_bus_source_graph("mixb", 0.5)
    self.assertEqual(len(mixa["inputs"]), 6)
    self.assertEqual(len(mixb["inputs"]), 6)
    self.assertEqual(mixa["selected_capture_indices"], [2, 3])
    self.assertEqual(mixb["selected_capture_indices"], [4, 5])
    self.assertNotIn(0, mixa["selected_capture_indices"])
    self.assertNotIn(1, mixb["selected_capture_indices"])
```

The production graph need not retain `selected_capture_indices`; if it does
not, assert the exact links from `src2/src3` and `src4/src5` instead.

- [ ] **Step 2: Run the new tests and confirm RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_io24_host_parameter_repairs.py \
  -k 'bus_balance_is or bus_graph_selects' -p no:cacheprovider
```

Expected: failures because the bus graph and balance functions are undefined.

- [ ] **Step 3: Implement the stereo balance law**

Use a center-unity, no-crossfeed sine taper:

```python
def balance_coefficients(position):
    position = _finite_number(position, "bus balance", 0.0, 1.0)
    if position <= 0.5:
        return 1.0, math.sin(math.pi * position)
    return math.sin(math.pi * (1.0 - position)), 1.0

def balance_controls(position):
    left, right = balance_coefficients(position)
    return {"balance_l:Mult": left, "balance_r:Mult": right}
```

Do not reuse the retired equal-power mono-pan law.

- [ ] **Step 4: Implement exact six-input graphs and source configurations**

Add constants:

```python
BUS_CAPTURE_PAIRS = {"mixa": (2, 3), "mixb": (4, 5)}
BUS_SOURCE_NAMES = {"mixa": "io24-host-mixa", "mixb": "io24-host-mixb"}
BUS_SOURCE_DESCRIPTIONS = {
    "mixa": "io24 Host Mix A", "mixb": "io24 Host Mix B"}
CAPTURE_POSITIONS = ("FL", "FR", "FC", "LFE", "RL", "RR")
```

`build_bus_source_graph()` must expose six input ports, connect only the chosen
pair through `balance_l` and `balance_r`, expose exactly two output ports, and
never use mixer or crossfeed nodes.

`build_bus_source_conf()` must encode this shape:

```python
"capture.props": {
    "media.class": "Stream/Input/Audio",
    "target.object": capture_target,
    "node.passive": True,
    "stream.dont-remix": True,
    "audio.channels": 6,
    "audio.position": list(CAPTURE_POSITIONS),
},
"playback.props": {
    "node.name": BUS_SOURCE_NAMES[bus],
    "node.description": BUS_SOURCE_DESCRIPTIONS[bus],
    "media.class": "Audio/Source",
    "node.passive": True,
    "stream.dont-remix": True,
    "audio.channels": 2,
    "audio.position": ["FL", "FR"],
},
```

There must be no playback `target.object` and no `Audio/Sink` identity.

- [ ] **Step 5: Add RED configuration and lifecycle tests**

Test both exact descriptions, both `stream.dont-remix` fields, passive flags,
absence of a playback target, and unique node names. Add fake-chain tests for:

```text
both ready
Mix A failed while Mix B remains ready
spawned but not yet visible reports starting
node absent past five seconds stops and reports failed
identical start does not relaunch
updating Mix A never calls Mix B
stop cleans both chains
```

- [ ] **Step 6: Implement `BusSourceChain` and `BusSourceManager`**

`BusSourceChain` stores its bus, dynamic node name, last configuration, and
start time. Its configured start is idempotent only when the process is running
and the rendered configuration is unchanged.

`BusSourceManager` owns exactly two chain instances. Use statuses
`unavailable`, `starting`, `ready`, and `failed`. A process becomes `ready` only
after `node_id()` finds its unique source. Use a five-second monotonic readiness
deadline; stop a process that never publishes its node. `set_balance()` must
return false unless the selected chain is ready and `set_controls()` succeeds.

- [ ] **Step 7: Run Task 2 tests GREEN**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_io24_host_parameter_repairs.py \
  -k 'balance or bus_source or repeated_identical' -p no:cacheprovider
```

Expected: all selected tests pass without launching PipeWire.

- [ ] **Step 8: Record the Task 2 recovery identity**

Add exact hashes for `io24_mbc.py` and the focused test file to `TASK2.sha256`,
verify it, and append the RED/GREEN evidence to `PROGRESS.md`.

---

### Task 3: Replace the GTK input monitor with aligned bus controls

**Files:**
- Modify: `io24gtk.py:2495-2589,2890-3081,5711-5957,6238-6249`
- Test: `tests/test_io24_host_parameter_repairs.py:504-523,620-700,900-1085`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260909T103619-0700-host-bus-source-balance/PROGRESS.md`

**Interfaces:**
- Consumes: `default_pan_snapshot()`, `BusSourceManager`,
  `find_io24_capture_source()`, and version 2 `host_features.pan`.
- Produces: `Win._bus_balance_moved(bus: str, value: float) -> None`
- Produces: `Win._bus_source_watchdog() -> bool`
- Produces: `Win._pan_snapshot_state() -> dict`
- Produces: `Win._adopt_pan_state(state: dict) -> str | None`

- [ ] **Step 1: Write RED GTK structure tests**

Parse `_input_strip`, `_bus_strip`, `_bus_balance_moved`, and
`_bus_source_watchdog` with `ast` and assert:

```text
no per-channel pan knob is created in _input_strip
no Host input pan toggle or status paragraph exists
the Buses grid creates Main, Mix A, and Mix B knobs
Main is insensitive and says Main is not exposed by USB capture
Mix A/B begin insensitive until their source is ready
routine _bus_balance_moved contains no self.say call
```

Add a fake manager test proving a Mix A move updates only `mixa` state and
manager controls.

- [ ] **Step 2: Run GTK tests and confirm RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_io24_host_parameter_repairs.py \
  -k 'bus_knob or removes_input_pan or bus_balance_move' \
  -p no:cacheprovider
```

Expected: failures against the current per-input monitor UI.

- [ ] **Step 3: Replace GTK state and widgets**

In `Win.__init__`, replace `pan_chain` with:

```python
self.pan_state = io24_mbc.default_pan_snapshot()
self.bus_sources = io24_mbc.BusSourceManager()
self._pan_mute = False
self._bus_source_status = {bus: "unavailable"
                           for bus in io24_mbc.BUS_SOURCE_KEYS}
```

Remove the entire per-input pan row from `_input_strip`.

In `_bus_strip`, attach one `Knob` and one compact value label under each meter
pair. Main stays centered and insensitive with tooltip/value text
`Main is not exposed by USB capture`. Mix A/B use their saved values and begin
insensitive. Store widgets in `self.bus_balance_knobs` and
`self.bus_balance_labels` keyed by `main`, `mixa`, and `mixb`.

- [ ] **Step 4: Add silent balance updates and slow source reconciliation**

`_bus_balance_moved()` must clamp the value, update only the chosen saved
balance and label, and call `bus_sources.set_balance()`. A false update result
transitions only that endpoint to failed, disables its knob, stops its chain,
and emits one fault notification for the transition.

Register:

```python
GLib.timeout_add(2000, self._bus_source_watchdog)
```

The watchdog locates only the capture source, calls `reconcile()` with the
current balances, sets sensitivity from exact `ready` states, and toasts only a
new `failed` transition. Missing nodes and ordinary start/stop remain silent.
Remove pan work from `_watch_attach`; the manager responds to capture discovery
rather than coupling source availability to the USB control connection.

- [ ] **Step 5: Update Host snapshot save/load and legacy disclosure**

Keep the key `host_features["pan"]`, but make `_pan_snapshot_state()` read the
two bus knobs and validate version 2. `_adopt_pan_state()` updates the two knobs
without notifying and leaves process lifecycle to the watchdog.

Pass `_last_preset_load_report["host_feature_migrations"]` from the worker into
`_after_load`. Append the exact legacy notice to the discrete load completion
message. Do not create a standing banner or toast outside that completed file
load.

- [ ] **Step 6: Update shutdown cleanup and write lifecycle tests**

Replace every `pan_chain.stop()` with `bus_sources.stop()`. Add fakes proving:

```text
shutdown stops both endpoints
node absence disables both bus knobs without a toast
one failed endpoint disables only its knob and toasts once
a later ready state re-enables only the corresponding knob
snapshot adoption does not launch or touch PipeWire
legacy notice appears only on completed Host-file load
```

- [ ] **Step 7: Run Task 3 tests GREEN**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_io24_host_parameter_repairs.py -p no:cacheprovider
```

Expected: the entire focused module passes without Host or audio launch.

- [ ] **Step 8: Record the Task 3 recovery identity**

Add exact hashes for `io24gtk.py` and the focused test file to `TASK3.sha256`,
verify it, and append the RED/GREEN evidence to `PROGRESS.md`.

---

### Task 4: Correct documentation and run affected offline gates

**Files:**
- Modify: `README.md:52-54,304-347,703-706`
- Modify: `GUIDE.md:12-31,272-293,353-355`
- Modify: `runs/20260906T165749-0700-host-live-routing-repair/PARAMETER-VERIFICATION-MATRIX.json`
- Modify: `.superpowers/sdd/FULL-PARAMETER-VERIFICATION-PLAN/task-5-report.md`
- Modify: `.superpowers/sdd/FULL-PARAMETER-VERIFICATION-PLAN/progress.md`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260909T103619-0700-host-bus-source-balance/PROGRESS.md`
- Test: `tests/test_io24_release_package.py`
- Test: `tests/test_io24_host_parameter_repairs.py`
- Test: `tests/test_io24_host_state_repair.py`
- Test: `tests/test_io24_host_hotkey.py`
- Test: `tests/test_io24_preset_persistence.py`
- Test: `tests/test_io24_full_parameter_inventory.py`
- Test: `tests/test_uc472_standard_highshelf.py`
- Test: `tests/test_io24_voicefx_preset_apply.py`

**Interfaces:**
- Consumes: completed Tasks 1-3.
- Produces: truthful user documentation, regenerated deterministic matrix,
  affected-suite evidence, and current task-local recovery records.

- [ ] **Step 1: Replace stale product claims**

README and GUIDE must state:

```text
Mix A is USB capture 3-4 and appears as passive source io24 Host Mix A.
Mix B is USB capture 5-6 and appears as passive source io24 Host Mix B.
Main has no complete USB capture pair and remains unavailable in this Host.
The sources are computer-side, disappear with the Host, and route nowhere by default.
Balance settings live only in version 2 host_features.pan snapshot data.
Legacy per-input pan settings are not semantically reused.
```

Remove every claim about Channel 1/2 Host pan, the activation button, a
capture-to-playback monitor, Monitoring Blend warnings for that retired graph,
and automatically audible routing.

- [ ] **Step 2: Add source-level documentation regression assertions**

Extend the focused test to require both new endpoint names and the unavailable
Main statement in README/GUIDE, while rejecting `Host input pan`,
`capture→playback`, and `host_features.pan` version 1 claims.

- [ ] **Step 3: Run focused source and persistence gates**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_io24_host_parameter_repairs.py \
  tests/test_io24_host_state_repair.py \
  tests/test_io24_preset_persistence.py \
  -W error::ResourceWarning -p no:cacheprovider
```

Expected: all tests pass.

- [ ] **Step 4: Regenerate the parameter matrix twice**

Run the existing builder into two independent temporary paths and compare both
outputs to the checked-in matrix. This Host-only source feature does not add a
device parameter row: row count must remain 748 and the checked-in matrix must
remain byte-identical. Any difference is a failure to diagnose; do not update
the checked-in artifact to make the gate pass.

Use a task-specific temporary directory from `mktemp -d`; do not delete any
pre-existing project or user directory.

- [ ] **Step 5: Run the complete affected Host suite**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_io24_release_package.py \
  tests/test_io24_host_parameter_repairs.py \
  tests/test_io24_host_state_repair.py \
  tests/test_io24_host_hotkey.py \
  tests/test_io24_preset_persistence.py \
  tests/test_io24_full_parameter_inventory.py \
  tests/test_uc472_standard_highshelf.py \
  tests/test_io24_voicefx_preset_apply.py \
  -W error::ResourceWarning -p no:cacheprovider
```

Expected: exit 0 with no ResourceWarning.

- [ ] **Step 6: Run release-package verification without installation**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_io24_release_package.py -p no:cacheprovider
```

Expected: the wheel still includes all 15 modules and seven entry points,
imports every module from its own bytes in an empty directory, and executes the
hardware-free `python -m io24_scene` path. Do not install the wheel.

- [ ] **Step 7: Update task reports and recovery text**

Append one new controlling section to Task 5 report/progress and CP34
`RESUME.md`. Record exact test counts, matrix hash, source boundaries, peer
agreement, and the still-unproved live PipeWire/visual/audio gates. Do not
rewrite historical evidence or claim Main availability.

- [ ] **Step 8: Build and verify the final checkpoint**

Create `CHECKPOINT.sha256` in the new run covering:

```text
SCOPE.md
PROGRESS.md
io24.py
io24_mbc.py
io24gtk.py
tests/test_io24_host_parameter_repairs.py
README.md
GUIDE.md
PARAMETER-VERIFICATION-MATRIX.json
task-5-report.md
FULL-PARAMETER-VERIFICATION-PLAN/progress.md
CP34 RESUME.md
the approved design spec
this implementation plan
```

Add exact hashes via `apply_patch`, run `sha256sum -c`, and require every entry
to report `OK`.

---

### Task 5: One bounded peer closure and final reconciliation

**Files:**
- Modify: `.claude-peer/INBOX.md`
- Modify: `.claude-peer/PEER-TURN.md`
- Generated by existing peer tooling: `.claude-peer/SNAPSHOT.md`
- Generated by existing peer tooling: `.claude-peer/EVIDENCE.sha256`
- Modify: `.claude-peer/OUTBOX.md`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260909T103619-0700-host-bus-source-balance/PROGRESS.md`
- Modify: `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/20260909T103619-0700-host-bus-source-balance/CHECKPOINT.sha256`

**Interfaces:**
- Consumes: final verified source, docs, tests, matrix, and exact 53-file peer boundary.
- Produces: one independent Claude closure result or one concrete correction.

- [ ] **Step 1: Append the implementation evidence to the peer inbox**

Include exact test counts and hashes, the two passive source names, the final
state/migration behavior, absence of Main capture, and every deferred live gate.
Ask for one substantive defect review, not a ceremonial confirmation.

- [ ] **Step 2: Obtain exact external-disclosure authorization**

Before running `./claude-io24-peer-turn`, obtain the user's explicit approval
to send the refreshed exact 53-file snapshot to Anthropic Claude for this one
read-only closure review. Do not infer this new transmission from the earlier
architecture-review approval.

- [ ] **Step 3: Run one serialized peer closure turn**

```bash
./claude-io24-peer-turn
```

Require a successful response envelope with nonzero token usage, zero permission
denials, the same dedicated UUID, and a 53-entry snapshot whose manifest
verifies from `.claude-peer/`.

- [ ] **Step 4: Reconcile once**

If Claude agrees, append the agreement to `PROGRESS.md` and proceed immediately.
If Claude identifies a concrete defect, reproduce it RED, correct it, rerun the
affected gates, and request exactly one correction review. Do not repeat a clean
review or reopen settled design choices.

- [ ] **Step 5: Rebuild the final checkpoint after peer evidence**

Update the new run's `PROGRESS.md` and `CHECKPOINT.sha256`, then verify all
entries. Final status must remain offline-only until separately authorized live
PipeWire and visual acceptance passes.
