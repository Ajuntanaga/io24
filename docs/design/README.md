# Alternate EQ rack references

These are original visual references for the Linux Host's Passive Program EQ
and Vintage EQ panels. They were developed from the io24 control topology
recovered from Universal Control 4.7.2 and the Host's existing rack language.
They are not copied Universal Control bitmaps.

The Host draws both faceplates as vectors, using control positions, knob
radii, scale arcs, plot rectangles and lamp positions measured from these
images (`ALTERNATE_EQ_REFERENCE_ART` / `ALTERNATE_EQ_REFERENCE_GEOMETRY` in
`io24gtk.py`). It does not composite the bitmaps: their engraved scale values
are illustrative (for example a -10..+10 boost and a 20..400 Hz low
selector) and contradict the retained UC contract, so painting over them left
doubled numbers. Every printed value on the rack now comes from
`ALTERNATE_EQ_RACK_SPECS`, which mirrors
`re/uc_component_model/fatchannelxt_alternate_eq_contract.xml`.

- `passive-program-eq-reference.png` establishes the blue steel faceplate,
  low/high grouping, recessed response display, stepped selectors, screws and
  power lamp. The plate runs from y=123 to y=605 (482 px).
- `vintage-eq-reference.png` establishes the dark 1970s faceplate, colored
  band knobs, dividers, recessed response display, rack ears and power lamp.
  The plate runs from y=174 to y=551 (377 px).

Selecting or hovering a continuous knob shows its exact decoded value; a
stepped selector lights its current printed position instead. The response
display previews the semantic controls immediately and is replaced by UC's
exact designed sections after a successful device write. The clickable lamp
is that EQ model's independent on/off control.

Both models occupy the same outer rack bay. Passive keeps its taller 2U
faceplate, while Vintage keeps its slimmer 1U aspect centred in that bay.
Switching models therefore does not resize or jump the page and does not
distort either reference.
