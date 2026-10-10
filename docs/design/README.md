# EQ rack references

These are original visual references for the Linux Host's Standard, Passive
Program, and Vintage EQ panels. They were developed from the io24 control
topology recovered from Universal Control 4.7.2 and the Host's existing rack
language. They are not copied Universal Control bitmaps.

`io24_eq_reference.py` is the shared coordinate authority. It records every
load-bearing crop, screen, plot, knob, rack ear, slot, screw, divider, and lamp
landmark. The Host, asset renderer, hit testing, and pixel-diff tooling all use
that same geometry.

Passive and Vintage use value-free production faceplates derived from their
references. Static metal, rack hardware, group headings, dividers, and display
bezels therefore stay pixel-identical to the source references. The source
knobs, illustrative scale values, response trace, and lamp are removed. GTK
draws those state-bearing regions from the decoded UC fields, so no decorative
value can contradict the actual control protocol.

Knob bodies are separate transparent PNG assets generated from
`eq-knob-reference-board.png` by `tools/render_eq_knob_assets.py`. Standard has
separate Gain and Q bodies, Passive has continuous and selector bodies, and
Vintage has one coloured body per band. GTK adds only live collars, pointers,
focus, and values, so the faceplates never bake in a control position.

- `passive-program-eq-reference.png` establishes the blue steel faceplate,
  low/high grouping, recessed response display, stepped selectors, screws and
  power lamp. The plate runs from y=123 to y=605 (482 px).
- `vintage-eq-reference.png` establishes the dark 1970s faceplate, colored
  band knobs, dividers, recessed response display, rack ears and power lamp.
  The plate runs from y=174 to y=551 (377 px).
- `standard-parametric-eq-reference.png` is the deterministic Standard EQ
  reference. Its blank production faceplate comes from the same renderer.

Each rack also has two developer-only calibration images:

- `*-calibration-underlay.png` is the exact reference crop.
- `*-calibration-nodes.png` is a transparent geometry overlay with a 100 px
  grid, control centres and radii, plot/screen bounds, rack hardware, dividers,
  and lamp coordinates.

Set `IO24_EQ_REFERENCE_CALIBRATION` to `backdrop`, `overlay`, `nodes`, or
`both` when running `tests/paint_smoke.py`. Normal Host sessions never show
these layers. See `EQ_REFERENCE_CALIBRATION.md` for the element inventory,
coordinates, regeneration command, and diff workflow.

Selecting or hovering a continuous knob shows its exact decoded value; a
stepped selector lights its current printed position instead. The response
display previews the semantic controls immediately and is replaced by UC's
exact designed sections after a successful device write. The clickable lamp
is that EQ model's independent on/off control.

All three models occupy the same full-width, 2U outer rack rectangle. Vintage
fits its cleaned source plate into that rectangle while keeping measured
control positions and circular knob bodies as independent live layers.
Switching models therefore does not resize or jump the page.

Standard's list rows are state-only and remain hidden. Its faceplate provides
four large Gain knobs, four smaller logarithmic Q knobs, per-band power and
outer-band Peak/Shelf buttons, Flatten, and global power. The Q additions are
recorded in the calibration-node overlay even though they are not present in
the original illustrative bitmap.

## Reference-rack workflow

To add a rack, commit a single populated source reference in `docs/design/`,
then declare its source size, static hardware, live regions, controls, and
generated filenames in `io24_rack_reference.py`. Keep the manifest as the
coordinate authority: runtime hit targets, focus, renderer output, and diff
allowances must all derive from it.

Compile the reference and generated assets, then use the non-writing drift
gate before committing:

```bash
python3 tools/render_rack_assets.py limiter
python3 tools/render_rack_assets.py limiter --check
```

For calibration, set `IO24_EQ_REFERENCE_CALIBRATION` to `backdrop`, `overlay`,
`nodes`, or `both` while running the paint harness. `backdrop` (also accepted
as `underlay`) shows only the generated populated reference; `overlay` adds
that reference at 46% opacity over the live rack, `nodes` adds the measured
geometry, and `both` combines those two inspection layers. Normal mode uses
the production faceplate and live controls.

Capture the same state with `backdrop` and normally. The harness writes each
limiter capture's actual allocation to a `.limiter-rack.json` sidecar. Use
that rectangle with `--rack limiter --rack-rect X,Y,W,H` in
`tools/eq_reference_diff.py`. Allowances include the source cleanup regions,
the live display, tick strokes, focus/hover halos, lamp border, and clipped
value text. Dimensions come from the manifest, including fixed logical-pixel
padding where the GTK paint uses a fixed font or halo. Native GTK regression
tests also compare actual reference/live render nodes at 600 and 1040 px,
including extreme values, power, and all focus/hover targets.

Bind a new `ReferenceRack` only to the existing authoritative widgets and
their existing callbacks; do not introduce a second state store or device
write path. The limiter retains its original switch row and sliders, mapped
inside a transparent, non-measuring GTK overlay. This preserves native
switch/slider accessibility roles, names, values, Tab navigation, and native
actions without displaying the old rows. Pointer events still reach the rack;
native focus selects the corresponding painted control. Finally, paint-capture
the selected module at desktop and minimum
width with the hardware-free harness, inspect the captures, and keep those
captures outside the release tree:

```bash
IO24_PAINT_PAGE=ch IO24_PAINT_MODULE=LIM IO24_PAINT_LIMITER_ON=1 \
IO24_PAINT_CAPTURE_DIR=/tmp/io24-limiter-desktop \
python3 tests/paint_smoke.py
IO24_PAINT_WIDTH=600 IO24_PAINT_PAGE=ch IO24_PAINT_MODULE=LIM \
IO24_PAINT_LIMITER_ON=1 IO24_PAINT_CAPTURE_DIR=/tmp/io24-limiter-minimum \
python3 tests/paint_smoke.py
```
