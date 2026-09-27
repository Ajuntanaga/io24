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
keeps its measured source control positions and circular knob radii, but its
live plate is recomposed to fill the common height instead of floating as a
short strip. Switching models therefore does not resize or jump the page.

Standard's list rows are state-only and remain hidden. Its faceplate provides
four large Gain knobs, four smaller logarithmic Q knobs, per-band power and
outer-band Peak/Shelf buttons, Flatten, and global power. The Q additions are
recorded in the calibration-node overlay even though they are not present in
the original illustrative bitmap.
