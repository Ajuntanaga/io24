# Reference-to-Rack Compiler Design

Date: 2026-10-09

## Goal

Turn an approved rack reference and an existing Host parameter contract into a
finished, interactive rack without repeating the EQ project's manual geometry,
asset-cleanup, hit-testing, calibration, and regression work. The limiter is
the pilot. The compiler is repository tooling, not a Codex skill and not a new
runtime framework.

Success means a new rack requires one declarative manifest, its approved visual
reference, and model-specific live visualization code. Shared mechanics are
generated or provided by one reusable runtime component.

## Scope

The first production slice supports:

- one full-width 2U rack;
- continuous knobs, a two-state power control, labels, and live values;
- a recessed live display whose drawing callback remains model-specific;
- reference-derived faceplate and transparent knob assets;
- geometry shared by rendering, GTK interaction, and tests;
- calibration overlays and screenshot-diff allowances;
- keyboard, pointer, scroll, hover, focus, and reduced-motion behavior.

The pilot limiter exposes the existing controls exactly as they already exist:

- power;
- threshold from -40 to 0 dBFS;
- release from 50 to 1500 ms;
- live gain reduction from the existing telemetry snapshot.

This work does not change DSP formulas, protocol writes, parameter ranges,
preset behavior, USB access, firmware, or the interface's fixed chain order.
It does not attempt computer-vision inference of an arbitrary photograph.

## Architecture

### Rack manifest

`io24_rack_reference.py` becomes the single coordinate and visual-contract
authority for generated racks. Each rack entry contains:

- reference filename and crop;
- faceplate, calibration, and knob-asset filenames;
- rack ears, slots, screws, display, lamp, and control geometry;
- per-control semantic binding, type, range, step, default, display formatter,
  pointer sweep, and asset role;
- regions that are state-bearing and may differ in pixel comparisons;
- material sampling regions and cleanup regions.

The manifest never duplicates device state. Semantic values still live in the
existing Host widgets and DSP code.

### Asset compiler

`tools/render_rack_assets.py` accepts a rack ID and emits deterministic assets:

1. an exact cropped calibration underlay;
2. a transparent measured-node overlay;
3. a value-free production faceplate with controls, lamp state, and display
   content removed only inside declared regions;
4. transparent knob bodies extracted from declared source regions;
5. a JSON build receipt containing input and output SHA-256 hashes.

The compiler rejects missing files, out-of-bounds geometry, overlapping control
IDs, empty knob masks, and cleanup pixels outside declared regions. Seeded
texture synthesis keeps repeated builds byte-stable.

### Runtime rack

`ReferenceRack` in `io24gtk.py` provides shared interaction and painting:

- manifest-scaled geometry;
- hit testing from the same control circles used by the asset compiler;
- drag, wheel, keyboard, double-click reset, focus, and hover;
- faceplate/knob texture loading and caching;
- live pointer, label, value, lamp, and focus drawing;
- a model callback for the dynamic display;
- direct binding to existing GTK value widgets and switches.

The limiter supplies only bindings and its live display renderer. It does not
receive a new state store or write path. Existing `lth`, `lrel`, and `lim_on`
widgets remain authoritative but become hidden when the generated limiter rack
is visible.

### Visual regression

The existing EQ pixel-diff mechanism becomes rack-generic. Dynamic allowances
come from the manifest rather than test-local rectangles. A generated rack must
pass:

- exact underlay/reference crop equality;
- production-faceplate changes confined to declared cleanup regions;
- asset hash determinism;
- reference overlay alignment;
- desktop and minimum-width hardware-free screenshots;
- no unexpected static pixels outside the display, controls, lamp, and focus
  regions.

## Limiter pilot appearance

The approved spike establishes the starting composition: warm dark faceplate,
reference-derived vintage knobs, Threshold on the left, Release on the right,
a central recessed gain-reduction display, and a local power lamp. Production
work uses the selected approved reference image rather than hard-coded spike
colors.

The display maps 0 to 20 dB reduction vertically, shows the current numerical
reduction, and remains visually quiet at zero. Threshold and Release update
immediately while dragging. No decorative meter value may be baked into the
faceplate.

## Data flow

1. The manifest binds `threshold`, `release`, and `power` to existing Host
   widgets.
2. User interaction changes the backing widget through `ReferenceRack`.
3. Existing callbacks call `_dyn_push("lim", channel)` or `_dyn_toggle`.
4. Existing device-write code computes the limiter coefficients at the active
   sample rate.
5. Existing gain-reduction telemetry updates the display on the Host paint
   cadence.

No compiler or generated asset participates in device communication.

## Generated versus maintained files

Maintained:

- `io24_rack_reference.py`;
- `tools/render_rack_assets.py`;
- one source reference per rack;
- the small limiter display callback and binding declaration;
- rack compiler/runtime tests.

Generated:

- value-free faceplate PNG;
- calibration underlay and node overlay PNGs;
- transparent knob PNGs;
- build receipt JSON.

Generated files are committed because the installed Host must not require
Pillow or NumPy at runtime. CI regenerates them and fails on drift.

## Error handling and fallback

Compilation fails closed and leaves existing generated files untouched by
writing to a temporary directory before atomic replacement. Runtime asset-load
failure falls back to the existing vector miniature and exposes an actionable
diagnostic; it never changes limiter state. Invalid manifests fail unit tests
before GTK starts.

## Testing

Hardware-free tests cover:

- schema and geometry validation at 600, 680, and 1040 pixel widths;
- exact value-to-angle and angle-to-value round trips;
- pointer, scroll, keyboard, reset, and power interaction;
- limiter bindings using fake widgets and a stub controller;
- gain-reduction display mapping at 0, threshold crossings, and 20 dB;
- deterministic asset regeneration and declared-region pixel diffs;
- paint-smoke rendering with synthetic gain-reduction history;
- hidden legacy rows retaining their current callback behavior.

The existing full hardware-free CI suite remains the release gate. No live
device test is required for this visual and interaction refactor because the
write path and DSP contract are unchanged.

## Acceptance criteria

- One command regenerates every limiter visual asset and calibration layer.
- Changing one manifest coordinate moves the asset, hit target, focus ring, and
  test overlay together.
- The limiter rack controls the existing limiter state without duplicate rows.
- The gain-reduction display reflects synthetic telemetry in the paint harness.
- Static pixels outside declared live regions match the generated faceplate.
- The rack remains usable at the Host's minimum supported width.
- The full hardware-free suite passes.
- No USB, firmware, Wine, or live audio-interface operation occurs.

## Deliberate exclusions

- automatic semantic understanding of arbitrary reference images;
- a general UI builder unrelated to audio racks;
- changes to compressor, gate, HPF, reverb, or Voice FX during the limiter
  pilot;
- device-side limiter release persistence, which the current preset format does
  not provide.
