# EQ reference calibration

The three rack references use one source canvas, 2172 x 724 pixels. All
runtime geometry is rack-local: `(0, 0)` is the upper-left corner of the
cropped metal unit, not the surrounding reference background.

The landmark source is `io24_eq_reference.py`. Do not hand-copy new positions
into the GTK painter. Change the measured landmark once, regenerate the
assets, then run the focused visual tests.

## Layer contract

Every rack is divided into three visual layers.

1. The cached procedural chassis owns the black or porcelain finish, edge
   highlights, rack ears, mounting slots, screws and recessed display bezel.
   It follows the measured screen and rack geometry; dividers are live strokes.
2. Cached procedural hardware owns each knob's flat ivory cap, rotating fluted
   black grip and pointer, plus chrome power switches and orange pilot lamps,
   rendered at the actual display resolution.
3. GTK owns live headings and axis inscriptions as well as the response curve,
   textured fill, Standard nodes, spectrum trace, protocol-correct values and
   scale marks, per-band controls, selection/hover focus, error badge, and the
   independent EQ power control. Text is separate from the metal and knob caches.

The Passive and Vintage source references contain illustrative control values.
Those areas are deliberately cleared from their historical blank faceplates. A
literal reference composite would show two pointers and, more importantly,
incorrect UC ranges. Normal rendering now uses `io24_retro_rack.py` instead of
those blank bitmaps. The original images remain geometry/calibration references.

## Measured landmarks

### Standard EQ

| Element | Rack-local measurement |
| --- | --- |
| Rack crop | `2156 x 482`, source origin `(8, 121)` |
| Rack ears | `x=0..80`, `x=2076..2156` |
| Screen cut | `(612, 65, 932, 384)` |
| Frame / gasket / glass | `(618, 71, 920, 372)` / `(632, 85, 892, 358)` / `(638, 91, 880, 332)` |
| Live plot | `(654, 103, 848, 308)` |
| Knob centres | Low `(224,205)`, Low Mid `(474,205)`, High Mid `(1682,205)`, High `(1932,205)` |
| Knob radius | `88` |
| Q centres / radius | same four x centres at `y=376`, radius `29` |
| Faceplate actions | four band lamps at `y=448`, four mode buttons, and Flatten `(1450,72,58,24)` |
| Power lamp | `(2032,441)`, radius `20` |

The Standard reference and blank faceplate are rendered by
`tools/render_standard_eq_reference.py`. The four live bands retain the exact
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

In the historical blank asset, the cleared control fields are `(86,58,478,424)` and
`(1290,58,786,424)`. Separate heading clears remove baked lettering. The
material region `(80,8,1996,460)` bounds that asset's finish transformation while
protecting its photographed screen bezel and screw heads. Production instead
draws a porcelain chassis and fresh hardware at the same control landmarks.

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
are fitted into the common-height bay, with a procedural porcelain chassis. The
material region `(80,8,1996,355)` applies only to the historical blank asset. Knob bodies
are separate circular renders and use the smaller scale, so the controls and
their hit regions are never vertically stretched with the plate.

## Calibration modes

`IO24_EQ_REFERENCE_CALIBRATION` is read only by the painter:

- `backdrop` or `underlay`: show the exact cropped reference instead of the
  production rack. This is a geometry reference, not a production pixel baseline.
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

Regenerate the historical reference faceplates and calibration layers with:

```bash
python3 tools/render_standard_eq_reference.py --faceplate
python3 tools/render_eq_reference_assets.py
```

`tools/eq_reference_diff.py` compares captures while allowing measured live
regions to differ. For control-state regression checks, compare two production
captures at the same size. The source backdrop intentionally has the original
material and baked lettering, so it is a geometry reference rather than a
pixel-identical production baseline. `tests/test_eq_reference_diff.py` checks
that generated faceplate changes stay inside the declared finish/cleanup areas
and that photographed screw heads and screen sides remain intact.
