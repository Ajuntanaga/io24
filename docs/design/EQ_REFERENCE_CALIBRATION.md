# EQ reference calibration

The three rack references use one source canvas, 2172 x 724 pixels. All
runtime geometry is rack-local: `(0, 0)` is the upper-left corner of the
cropped metal unit, not the surrounding reference background.

The landmark source is `io24_eq_reference.py`. Do not hand-copy new positions
into the GTK painter. Change the measured landmark once, regenerate the
assets, then run the focused visual tests.

## Layer contract

Every rack is divided into two visual layers.

1. The static faceplate owns the metal finish, edge highlights, rack ears,
   mounting slots, screws, group headings, divider rules, display bezel, and
   fixed axis inscriptions.
2. GTK owns anything that can change: response curve, Standard nodes,
   spectrum trace, Gain and Q knob pointers, protocol-correct values and scale
   marks, per-band controls, selection/hover focus, error badge, and the
   independent EQ power lamp.

The Passive and Vintage source references contain illustrative control values.
Those areas are deliberately cleared from their production faceplates. A
literal reference composite would show two pointers and, more importantly,
incorrect UC ranges.

## Measured landmarks

### Standard EQ

| Element | Rack-local measurement |
| --- | --- |
| Rack crop | `2156 x 482`, source origin `(8, 121)` |
| Rack ears | `x=0..80`, `x=2076..2156` |
| Screen cut | `(612, 65, 932, 384)` |
| Frame / gasket / glass | `(618, 71, 920, 372)` / `(632, 85, 892, 358)` / `(638, 91, 880, 332)` |
| Live plot | `(654, 103, 848, 308)` |
| Knob centres | Low `(224,229)`, Low Mid `(474,229)`, High Mid `(1682,229)`, High `(1932,229)` |
| Knob radius | `88` |
| Q centres / radius | same four x centres at `y=376`, radius `29` |
| Faceplate actions | four band lamps at `y=448`, four mode buttons, and Flatten `(1450,72,58,24)` |
| Power lamp | `(2032,441)`, radius `20` |

The Standard reference and blank faceplate are rendered by
`tools/render_eq_reference_assets.py`. The four live bands retain the exact
Host ranges and shapes. Q remains the existing `0.1..10.0` protocol field; its
rotary uses logarithmic travel only to make the physical control usable.

### Passive Program EQ

| Element | Rack-local measurement |
| --- | --- |
| Rack crop | `2156 x 482`, source origin `(8, 123)` |
| Rack ears | `x=0..80`, `x=2076..2156` |
| Screen / live plot | `(593,60,707,365)` / `(663,110,591,261)` |
| Low Boost / Atten | `(243,213,r66)` / `(467,213,r66)` |
| Low Frequency | `(360,422,r58)` |
| High Boost / Bandwidth | `(1421,213,r66)` / `(1607,213,r66)` |
| High Frequency / Atten | `(1785,213,r66)` / `(1964,213,r66)` |
| High Atten Select | `(1858,422,r58)` |
| Power lamp | `(2031,427)`, radius `18` |

The two cleared control fields are `(86,58,478,424)` and
`(1290,58,786,424)`. They stop at the rack-ear seams and do not touch the
photographed screen bezel or heading line.

### Vintage EQ

| Element | Rack-local measurement |
| --- | --- |
| Source rack crop | `2156 x 377`, source origin `(8, 174)` |
| Runtime outer rack | common `2156 x 482` presentation rectangle |
| Rack ears | `x=0..80`, `x=2076..2156` |
| Screen / live plot | `(765,47,705,292)` / `(858,102,557,175)` |
| Low Gain / Frequency | `(182,186,r55)` / `(342,188,r55)` |
| Low-mid Gain / Frequency | `(514,186,r55)` / `(665,186,r55)` |
| High-mid Gain / Frequency | `(1577,186,r55)` / `(1737,187,r55)` |
| High Gain | `(1939,186,r55)` |
| Dividers | `x=431`, `755`, `1501`, `1843`; `y=28..326` |
| Power lamp | `(1973,330)`, radius `17` |

The four cleared control fields follow the dividers exactly:
`(82,68,349,262)`, `(432,68,322,262)`, `(1496,68,347,262)`, and
`(1844,68,232,262)`.

The source crop remains the measurement authority. At runtime its y landmarks
are mapped into the common-height plate while knob radii use the smaller scale,
so the controls stay circular instead of being vertically stretched.

## Calibration modes

`IO24_EQ_REFERENCE_CALIBRATION` is read only by the painter:

- `backdrop` or `underlay`: show the exact cropped reference instead of the
  production rack. This is the baseline for pixel comparison.
- `overlay`: ghost the reference over the live rack at 46% opacity.
- `nodes`: show the transparent landmark grid over the live rack.
- `both`: combine the ghost and landmark grid.

Example, using the hardware-free paint harness:

```bash
IO24_EQ_REFERENCE_CALIBRATION=nodes \
IO24_PAINT_PAGE=ch IO24_PAINT_EQ_MODEL=passive \
IO24_PAINT_CAPTURE_DIR=/tmp/io24-eq-nodes \
python3 tests/paint_smoke.py
```

Regenerate every derived layer with:

```bash
python3 tools/render_eq_reference_assets.py
```

`tools/eq_reference_diff.py` compares a `backdrop` capture with a normal
capture. Scope the comparison to the fitted rack and allow only the measured
plot, control circles, and power lamp as dynamic regions. Everything else is
static reference territory.
