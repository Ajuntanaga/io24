# Reference-to-Rack Compiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a manifest-driven reference-to-rack compiler and use it to replace the limiter's duplicate parameter rows with a finished interactive rack.

**Architecture:** A pure-data manifest is the single authority for reference geometry, runtime hit regions, and visual-regression allowances. A deterministic offline compiler turns the approved limiter reference into installable static assets, while a reusable GTK `ReferenceRack` owns interaction and binds directly to existing widgets; the limiter contributes only bindings and a live gain-reduction display callback.

**Tech Stack:** Python 3.8+, Pillow, NumPy, GTK 4, Libadwaita, PyGObject, pytest/unittest.

**Spec:** `docs/superpowers/specs/2026-10-09-reference-rack-compiler-design.md`

## Global Constraints

- Do not change limiter DSP formulas, protocol writes, parameter ranges, preset behavior, USB access, firmware, or fixed chain order.
- Threshold remains `-40.0..0.0 dBFS`, step `0.01`, default `-28.0`.
- Release remains `0.05..1.5 seconds`, step `0.01`, default `0.4`.
- No compiler or generated asset participates in device communication.
- Generated assets must be deterministic and committed; Pillow and NumPy remain build/test dependencies only.
- Runtime asset failure must leave limiter state untouched and fall back to the existing limiter miniature.
- Preserve keyboard, pointer, wheel, hover, focus, double-click reset, and reduced-motion behavior.
- No USB, firmware, Wine, or live interface operation is permitted during implementation or verification.

---

## File map

- Create `io24_rack_reference.py`: rack manifest schema, limiter manifest, validation, scaling, and value/angle transforms.
- Create `tools/render_rack_assets.py`: deterministic asset compiler and atomic output transaction.
- Create `docs/design/limiter-reference.png`: canonical approved limiter reference, recreated deterministically from the accepted spike composition.
- Create generated `docs/design/limiter-faceplate.png`, `docs/design/limiter-calibration-underlay.png`, `docs/design/limiter-calibration-nodes.png`, `docs/design/limiter-knob.png`, and `docs/design/limiter-rack-assets.json`.
- Create `tests/test_io24_rack_reference.py`: manifest, geometry, transform, compiler, determinism, and pixel-boundary contracts.
- Modify `tools/eq_reference_diff.py`: generalize model-region calculation to accept any validated rack manifest while preserving the EQ CLI.
- Modify `tests/test_eq_reference_diff.py`: cover generic limiter allowances without regressing EQ behavior.
- Modify `io24gtk.py`: add `ReferenceRack`, the limiter display adapter, bindings, hidden native rows, and page integration.
- Modify `tests/test_io24_host_rate_and_effects.py`: exercise limiter rack interaction and unchanged write semantics.
- Modify `tests/paint_smoke.py`: supply deterministic limiter gain-reduction telemetry and capture the limiter rack.
- Modify `docs/design/README.md`, `PUBLIC_FILES.txt`, `pyproject.toml`, and `.github/workflows/ci.yml`: document, package, and verify the new pipeline.

---

### Task 1: Manifest, Validation, and Geometry

**Files:**
- Create: `io24_rack_reference.py`
- Create: `tests/test_io24_rack_reference.py`

**Interfaces:**
- Produces: `rack(rack_id: str) -> dict`
- Produces: `validate_rack(spec: dict, design_root: pathlib.Path = None) -> dict`
- Produces: `scaled_rect(rect: tuple, width: float, height: float, rack_id: str) -> tuple`
- Produces: `control_layout(rack_id: str, width: float, height: float) -> dict`
- Produces: `value_fraction(control: dict, value: float) -> float`
- Produces: `fraction_value(control: dict, fraction: float) -> float`
- Produces: `pointer_angle(control: dict, value: float) -> float`
- Consumes: no GTK or device modules.

- [ ] **Step 1: Write failing manifest-contract tests**

```python
class RackReferenceTests(unittest.TestCase):
    def test_limiter_contract_is_exact(self):
        spec = io24_rack_reference.rack("limiter")
        self.assertEqual(tuple(spec["controls"]), ("threshold", "release"))
        self.assertEqual(spec["controls"]["threshold"]["range"], (-40.0, 0.0))
        self.assertEqual(spec["controls"]["threshold"]["step"], 0.01)
        self.assertEqual(spec["controls"]["release"]["range"], (0.05, 1.5))
        self.assertEqual(spec["controls"]["release"]["step"], 0.01)

    def test_geometry_scales_from_one_coordinate_authority(self):
        small = io24_rack_reference.control_layout("limiter", 600, 180)
        large = io24_rack_reference.control_layout("limiter", 1200, 360)
        for field in ("threshold", "release"):
            self.assertAlmostEqual(large[field][0], small[field][0] * 2)
            self.assertAlmostEqual(large[field][1], small[field][1] * 2)
            self.assertAlmostEqual(large[field][2], small[field][2] * 2)

    def test_value_angle_round_trip_clamps_at_contract_bounds(self):
        control = io24_rack_reference.rack("limiter")["controls"]["threshold"]
        for value in (-50.0, -40.0, -28.0, 0.0, 4.0):
            fraction = io24_rack_reference.value_fraction(control, value)
            restored = io24_rack_reference.fraction_value(control, fraction)
            self.assertGreaterEqual(restored, -40.0)
            self.assertLessEqual(restored, 0.0)
```

- [ ] **Step 2: Run the tests and verify the module is absent**

Run: `python3 -m pytest -q tests/test_io24_rack_reference.py`

Expected: collection fails with `ModuleNotFoundError: No module named 'io24_rack_reference'`.

- [ ] **Step 3: Implement the pure-data limiter manifest and helpers**

Use a plain dictionary compatible with Python 3.8. Define source size `(1400, 420)`, panel `(38, 12, 1324, 396)`, display `(485, 104, 430, 241)`, lamp `(1309, 336, 14)`, Threshold `(280, 223, 78)`, and Release `(1120, 223, 78)`. Each control contains `range`, `step`, `default`, `sweep=(135.0, 405.0)`, `asset="limiter-knob.png"`, and a format string identifier. `validate_rack` must reject missing required keys, nonpositive rectangles/radii, duplicate widget bindings, controls outside the source bounds, invalid ranges, and source/output paths containing `..`.

```python
def value_fraction(control, value):
    lower, upper = control["range"]
    return max(0.0, min(1.0, (float(value) - lower) / (upper - lower)))


def fraction_value(control, fraction):
    lower, upper = control["range"]
    raw = lower + max(0.0, min(1.0, float(fraction))) * (upper - lower)
    step = control["step"]
    return max(lower, min(upper, round(raw / step) * step))
```

- [ ] **Step 4: Run manifest tests**

Run: `python3 -m pytest -q tests/test_io24_rack_reference.py`

Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit the manifest boundary**

```bash
git add io24_rack_reference.py tests/test_io24_rack_reference.py
git commit -m "feat(host): define reusable rack reference manifest"
```

---

### Task 2: Deterministic Reference and Asset Compiler

**Files:**
- Create: `tools/render_rack_assets.py`
- Create: `docs/design/limiter-reference.png`
- Generate: `docs/design/limiter-faceplate.png`
- Generate: `docs/design/limiter-calibration-underlay.png`
- Generate: `docs/design/limiter-calibration-nodes.png`
- Generate: `docs/design/limiter-knob.png`
- Generate: `docs/design/limiter-rack-assets.json`
- Modify: `tests/test_io24_rack_reference.py`

**Interfaces:**
- Consumes: `io24_rack_reference.rack` and `validate_rack`.
- Produces: `compile_rack(rack_id: str, design_root: pathlib.Path, output_root: pathlib.Path = None) -> dict`
- Produces CLI: `python3 tools/render_rack_assets.py limiter [--check]`
- Produces receipt keys: `rack_id`, `source_sha256`, `outputs`, `manifest_sha256`.

- [ ] **Step 1: Add failing compiler and determinism tests**

```python
def test_compiler_outputs_every_declared_asset(self):
    with tempfile.TemporaryDirectory() as temp:
        receipt = render_rack_assets.compile_rack(
            "limiter", ROOT / "docs" / "design", Path(temp))
        self.assertEqual(receipt["rack_id"], "limiter")
        for filename in (
                "limiter-faceplate.png", "limiter-calibration-underlay.png",
                "limiter-calibration-nodes.png", "limiter-knob.png",
                "limiter-rack-assets.json"):
            self.assertTrue((Path(temp) / filename).is_file())

def test_compiler_is_byte_deterministic(self):
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        render_rack_assets.compile_rack("limiter", DESIGN, Path(first))
        render_rack_assets.compile_rack("limiter", DESIGN, Path(second))
        for filename in io24_rack_reference.rack("limiter")["generated"]:
            self.assertEqual((Path(first) / filename).read_bytes(),
                             (Path(second) / filename).read_bytes())
```

- [ ] **Step 2: Verify tests fail because the compiler is absent**

Run: `python3 -m pytest -q tests/test_io24_rack_reference.py`

Expected: import failure for `tools.render_rack_assets`.

- [ ] **Step 3: Promote the accepted spike composition into a deterministic reference renderer**

Implement a private `_render_limiter_reference(spec)` inside the compiler. It samples the approved `vintage-eq-reference.png` crop for plate material, uses the committed `vintage-lowmid-knob.png` as the knob source, and recreates the accepted 1400x420 composition. It must draw static reference values only in the source reference. Save to a temporary output and atomically replace `docs/design/limiter-reference.png` after successful validation.

- [ ] **Step 4: Implement generic compilation and atomic replacement**

Compile into `tempfile.TemporaryDirectory(dir=output_root.parent)`. Create the exact underlay, node overlay, value-free faceplate, and isolated knob. Validate dimensions and declared-change masks before `os.replace` moves each file into `output_root`. `--check` compiles into a temporary directory and compares SHA-256 hashes without writing.

```python
def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

- [ ] **Step 5: Generate assets and verify deterministic output**

Run: `python3 tools/render_rack_assets.py limiter`

Run: `python3 tools/render_rack_assets.py limiter --check`

Expected: both exit zero; `--check` prints `limiter assets match`.

- [ ] **Step 6: Run compiler tests**

Run: `python3 -m pytest -q tests/test_io24_rack_reference.py`

Expected: all manifest/compiler tests pass.

- [ ] **Step 7: Commit the compiler and generated contract**

```bash
git add io24_rack_reference.py tools/render_rack_assets.py \
  tests/test_io24_rack_reference.py docs/design/limiter-*.png \
  docs/design/limiter-rack-assets.json
git commit -m "feat(host): compile rack assets from reference manifests"
```

---

### Task 3: Generic Pixel-Diff Gate

**Files:**
- Modify: `tools/eq_reference_diff.py`
- Modify: `tests/test_eq_reference_diff.py`
- Modify: `tests/test_io24_rack_reference.py`

**Interfaces:**
- Consumes: validated manifests from `io24_rack_reference` and legacy EQ manifests from `io24_eq_reference`.
- Produces: `rack_regions(spec: dict, rack_rectangle: tuple) -> tuple[list, list]`.
- Preserves: `model_regions(model: str, rack_rectangle: tuple)` and the existing EQ CLI.

- [ ] **Step 1: Add a failing generic-region test**

```python
def test_limiter_regions_come_from_the_rack_manifest(self):
    spec = io24_rack_reference.rack("limiter")
    rectangles, circles = rack_regions(spec, (10, 20, 700, 210))
    self.assertEqual(len(rectangles), 1)
    self.assertEqual(len(circles), 3)  # two knobs and one lamp
    self.assertEqual(circles[0][:2], (150, 132))
```

- [ ] **Step 2: Run and verify the new import fails**

Run: `python3 -m pytest -q tests/test_eq_reference_diff.py::EqReferenceDiffTests::test_limiter_regions_come_from_the_rack_manifest`

Expected: failure because `rack_regions` is undefined.

- [ ] **Step 3: Extract the generic scaler and keep the EQ adapter**

Implement `rack_regions` using `source_size`, `display`, `controls`, and `lamp`. Keep `model_regions` as an adapter that transforms the existing EQ entry into the same input shape so all prior tests and command lines remain unchanged.

- [ ] **Step 4: Add the static-faceplate boundary test**

Load `limiter-reference.png` and `limiter-faceplate.png`, derive allowed rectangles/circles through `rack_regions`, and assert that every changed pixel is inside an allowed live or cleanup region. Assert at least one pixel changed so an accidentally identical populated faceplate cannot pass.

- [ ] **Step 5: Run visual-contract tests**

Run: `python3 -m pytest -q tests/test_eq_reference_diff.py tests/test_io24_rack_reference.py`

Expected: all tests pass, including the unchanged three EQ models.

- [ ] **Step 6: Commit the generic diff gate**

```bash
git add tools/eq_reference_diff.py tests/test_eq_reference_diff.py \
  tests/test_io24_rack_reference.py
git commit -m "test(host): generalize reference rack pixel gates"
```

---

### Task 4: Reusable GTK ReferenceRack

**Files:**
- Modify: `io24gtk.py`
- Modify: `tests/test_io24_host_rate_and_effects.py`

**Interfaces:**
- Consumes: `io24_rack_reference.rack`, `control_layout`, `fraction_value`, and `pointer_angle`.
- Produces: `ReferenceRack(Canvas)` with constructor `ReferenceRack(win, rack_id, bindings, display_draw)`.
- Bindings shape: `{field: {"widget": Gtk.Widget, "format": callable}}`; power binding uses `{"widget": Gtk.Switch}`.
- Display callback: `display_draw(snapshot, rect, state, active)`.

- [ ] **Step 1: Write failing interaction tests with fake widgets**

```python
def test_reference_rack_drag_changes_the_backing_widget_only(self):
    rack = io24gtk.ReferenceRack.__new__(io24gtk.ReferenceRack)
    rack.spec = io24_rack_reference.rack("limiter")
    rack.bindings = {"threshold": {"widget": _Value(-28.0)}}
    self.assertTrue(rack._set_fraction("threshold", .5))
    self.assertAlmostEqual(rack.bindings["threshold"]["widget"].get_value(), -20.0)

def test_reference_rack_double_click_restores_manifest_default(self):
    rack = make_reference_rack(threshold=-6.0)
    rack._reset("threshold")
    self.assertAlmostEqual(rack.bindings["threshold"]["widget"].get_value(), -28.0)
```

- [ ] **Step 2: Run the focused tests and verify the class is absent**

Run: `python3 -m pytest -q tests/test_io24_host_rate_and_effects.py -k ReferenceRack`

Expected: failure because `io24gtk.ReferenceRack` is undefined.

- [ ] **Step 3: Implement shared state-free interaction**

Move the proven interaction mechanics from `ReverbRack` into `ReferenceRack`: `_control_at`, `_select`, `_fraction`, `_set_fraction`, `_reset`, drag, scroll, keyboard navigation, hover, and focus. Do not move reverb drawing or state. Use manifest geometry for every hit target and pointer angle.

- [ ] **Step 4: Implement shared static painting and asset fallback**

Load the faceplate and knob textures through the existing cached texture helper. Draw focus, pointer, labels, live values, and lamp in GTK. If an asset load raises `GLib.Error`, draw the existing vector rack bay and report one diagnostic through `win.say`; do not mutate any widget.

- [ ] **Step 5: Run focused runtime tests**

Run: `python3 -m pytest -q tests/test_io24_host_rate_and_effects.py -k 'ReferenceRack or ReverbRack'`

Expected: all selected tests pass.

- [ ] **Step 6: Commit the reusable runtime**

```bash
git add io24gtk.py tests/test_io24_host_rate_and_effects.py
git commit -m "feat(host): add manifest-driven reference rack runtime"
```

---

### Task 5: Limiter Rack Integration

**Files:**
- Modify: `io24gtk.py`
- Modify: `tests/test_io24_host_rate_and_effects.py`
- Modify: `tests/paint_smoke.py`

**Interfaces:**
- Consumes: existing `W["lim_on"]`, `W["lth"]`, `W["lrel"]`, `_dyn_push`, `_dyn_toggle`, and `ctl.snap["gr"][channel]["lim"]`.
- Produces: `limiter_display_state(win, channel) -> {"reduction_db": float, "threshold_db": float, "release_s": float}`.
- Produces: one visible limiter `ReferenceRack` per channel; legacy rows stay instantiated but unparented.

- [ ] **Step 1: Add failing limiter binding/display tests**

```python
def test_limiter_display_uses_existing_gain_reduction_telemetry(self):
    window = _window()
    window.ctl.snap = {"gr": {1: {"lim": -8.4}}}
    window.w[1]["lth"] = _Value(-6.0)
    window.w[1]["lrel"] = _Value(.4)
    self.assertEqual(io24gtk.limiter_display_state(window, 1), {
        "reduction_db": 8.4, "threshold_db": -6.0, "release_s": .4})

def test_limiter_rack_reuses_existing_widgets(self):
    window = build_dynamics_page_stub()
    rack = window.limiter_racks[1]
    self.assertIs(rack.bindings["threshold"]["widget"], window.w[1]["lth"])
    self.assertIs(rack.bindings["release"]["widget"], window.w[1]["lrel"])
    self.assertIs(rack.power_binding["widget"], window.w[1]["lim_on"])
```

- [ ] **Step 2: Verify the limiter adapter is absent**

Run: `python3 -m pytest -q tests/test_io24_host_rate_and_effects.py -k LimiterRack`

Expected: failure because `limiter_display_state` and `limiter_racks` are undefined.

- [ ] **Step 3: Add the live limiter display callback**

Draw a recessed 0..20 dB gain-reduction scale. Clamp `abs(min(0.0, telemetry))` to 20.0, keep zero visually quiet, draw the current numeric reduction only from telemetry, and draw no baked value from the faceplate. Respect `gtk-enable-animations`; the display has no independent animation timer.

- [ ] **Step 4: Replace the visible limiter rows with the rack**

Construct `lim_on`, `lth`, and `lrel` exactly as today so callbacks and session restoration remain unchanged. Do not append their rows to the visible limiter group. Create `ReferenceRack` with those widgets, add it as the group's only child, and store it in `self.limiter_racks[channel]`. Keep the Fat Channel miniature and `show_module(channel, "LIM")` navigation unchanged.

- [ ] **Step 5: Extend the hardware-free paint fixture**

Set `FakeInner.read_reduction` to provide a visible limiter reduction and add one capture assertion that the Limiter module can be selected without opening ALSA, USB, or PipeWire. Keep `FakeSpectrum` and all device setters stubbed.

- [ ] **Step 6: Run limiter and rate-safety tests**

Run: `python3 -m pytest -q tests/test_io24_host_rate_and_effects.py tests/test_io24_host_resume.py`

Expected: all tests pass; the existing test asserting limiter release and sample rate are sent remains unchanged.

- [ ] **Step 7: Render and inspect desktop and minimum-width captures**

Run the hardware-stubbed paint harness for the Fat Channel with the Limiter selected at 1040x800 and at the minimum supported width. Inspect one initial pair, fix only concrete clipping/alignment/contrast defects, then capture one final pair. Confirm the legacy parameter rows are not visible.

- [ ] **Step 8: Commit the limiter pilot**

```bash
git add io24gtk.py tests/test_io24_host_rate_and_effects.py tests/paint_smoke.py
git commit -m "feat(host): add compiled interactive limiter rack"
```

---

### Task 6: Packaging, Documentation, and Release Gate

**Files:**
- Modify: `docs/design/README.md`
- Modify: `PUBLIC_FILES.txt`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/test_io24_release_package.py`
- Modify: `tests/test_publication_docs.py`

**Interfaces:**
- Consumes: generated assets and `tools/render_rack_assets.py --check`.
- Produces: installed source/assets sufficient for runtime without Pillow/NumPy.

- [ ] **Step 1: Add failing release/package assertions**

```python
def test_reference_rack_runtime_and_assets_ship(self):
    expected = {
        "io24_rack_reference.py",
        "docs/design/limiter-faceplate.png",
        "docs/design/limiter-knob.png",
        "docs/design/limiter-rack-assets.json",
    }
    self.assertTrue(expected <= set(PUBLIC_FILES))
```

Add a publication test asserting the design README documents the regeneration and `--check` commands verbatim.

- [ ] **Step 2: Verify packaging tests fail**

Run: `python3 -m pytest -q tests/test_io24_release_package.py tests/test_publication_docs.py`

Expected: failure listing the new module/assets absent from packaging/docs.

- [ ] **Step 3: Add public/package entries and CI drift check**

Add the runtime module, compiler, tests, source reference, generated images, and receipt to `PUBLIC_FILES.txt`. Add installed runtime assets to `pyproject.toml`. Add `python3 tools/render_rack_assets.py limiter --check` to the hardware-free CI job before pytest.

- [ ] **Step 4: Document the one-command workflow**

In `docs/design/README.md`, document: add reference, declare manifest, run compiler, enable calibration overlay, run diff gate, bind existing widgets, and run paint captures. Include the exact commands:

```bash
python3 tools/render_rack_assets.py limiter
python3 tools/render_rack_assets.py limiter --check
```

- [ ] **Step 5: Run the complete hardware-free release suite**

Run the exact test list in `.github/workflows/ci.yml`.

Expected: all tests pass; only pre-existing environment-dependent skips are allowed.

- [ ] **Step 6: Run final static checks**

Run: `python3 tools/render_rack_assets.py limiter --check`

Run: `git diff --check`

Expected: both exit zero and the compiler reports matching assets.

- [ ] **Step 7: Commit packaging and documentation**

```bash
git add PUBLIC_FILES.txt pyproject.toml .github/workflows/ci.yml \
  docs/design/README.md tests/test_io24_release_package.py \
  tests/test_publication_docs.py
git commit -m "build(host): ship reference rack compiler assets"
```

---

## Completion evidence

- The accepted limiter composition is reproducible from committed sources.
- `io24_rack_reference.py` controls asset, hit-target, focus, and test geometry.
- The limiter rack drives only the existing `lim_on`, `lth`, and `lrel` widgets.
- Legacy limiter rows are hidden without changing callbacks or device writes.
- Static pixel changes are confined to declared live/cleanup regions.
- Desktop and minimum-width final captures have been visually inspected once.
- The exact hardware-free CI suite passes.
- `git diff --check` and compiler `--check` pass.
- No live hardware operation has occurred.
