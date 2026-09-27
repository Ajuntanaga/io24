"""Measured visual geometry for the three Linux Host EQ racks.

All coordinates below are rack-local pixels measured against the canonical
2172 x 724 reference images in ``docs/design``.  Keeping this data outside the
GTK painter gives the asset generator, pixel-diff tooling, hit testing, and the
runtime one shared coordinate authority.

The reference images contain illustrative knob values.  They are valid visual
references, not parameter schemas: production labels and pointer positions
must continue to come from ``io24_presets`` / ``io24_alt_eq``.
"""

REFERENCE_SOURCE_SIZE = (2172, 724)


EQ_REFERENCE_RACKS = {
    "standard": {
        "filename": "standard-parametric-eq-reference.png",
        "faceplate_filename": "standard-parametric-eq-faceplate.png",
        "calibration_underlay_filename":
            "standard-parametric-eq-calibration-underlay.png",
        "calibration_nodes_filename":
            "standard-parametric-eq-calibration-nodes.png",
        "rack_crop": (8, 121, 2156, 482),
        "panel": (0, 0, 2156, 482),
        "ear": 80,
        "ears": ((0, 0, 80, 482), (2076, 0, 80, 482)),
        "slots": ((15, 8, 47, 20), (15, 443, 47, 20),
                  (2094, 8, 47, 20), (2094, 443, 47, 20)),
        "slot_rows": (29, 453),
        "screws": ((120, 31, 13), (2036, 31, 13), (120, 451, 13)),
        "heading_y": 37,
        "screen": (612, 65, 932, 384),
        "frame": (618, 71, 920, 372),
        "gasket": (632, 85, 892, 358),
        "glass": (638, 91, 880, 332),
        "plot": (654, 103, 848, 308),
        "controls": {
            "low": (224, 229, 88),
            "low_mid": (474, 229, 88),
            "high_mid": (1682, 229, 88),
            "high": (1932, 229, 88),
        },
        # Diff-only allowances: populated reference versus live GTK state.
        "control_clear_regions": ((88, 72, 520, 370),
                                  (1546, 72, 510, 370)),
        "knob_y": 229,
        "knob_x": (224, 474, 1682, 1932),
        "knob_radius": 88,
        # Dedicated Q rotaries added to the production Standard rack.  They
        # sit on the same four vertical centre lines as Gain, so the band
        # relationship remains unambiguous when the legacy rows are hidden.
        "q_knob_y": 376,
        "q_knob_x": (224, 474, 1682, 1932),
        "q_knob_radius": 29,
        "band_power": ((149, 448, 7), (399, 448, 7),
                       (1757, 448, 7), (2007, 448, 7)),
        "band_mode": ((250, 435, 70, 26), (500, 435, 70, 26),
                      (1586, 435, 70, 26), (1836, 435, 70, 26)),
        "flatten": (1450, 72, 58, 24),
        "lamp": (2032, 441, 20),
        "group_centres": ((224, 37), (474, 37),
                          (1682, 37), (1932, 37)),
        "dividers": (),
    },
    "passive": {
        "filename": "passive-program-eq-reference.png",
        "faceplate_filename": "passive-program-eq-faceplate.png",
        "calibration_underlay_filename":
            "passive-program-eq-calibration-underlay.png",
        "calibration_nodes_filename":
            "passive-program-eq-calibration-nodes.png",
        "rack_crop": (8, 123, 2156, 482),
        "panel": (0, 0, 2156, 482),
        "ear": 80,
        "ears": ((0, 0, 80, 482), (2076, 0, 80, 482)),
        "slots": ((15, 7, 48, 28), (15, 420, 48, 27),
                  (2093, 7, 48, 28), (2093, 420, 48, 27)),
        # There are three mounting screws.  The lower-right assembly is the
        # illuminated power switch, not a fourth screw; treating it as one
        # preserved stale lamp pixels in the generated value-free faceplate.
        "screws": ((114, 42, 18), (2044, 42, 18),
                   (114, 450, 18)),
        "heading_y": 30,
        "screen": (593, 60, 707, 365),
        "plot": (663, 110, 591, 261),
        "controls": {
            "bboost": (243, 213, 66),
            "batten": (467, 213, 66),
            "bfreq": (360, 422, 58),
            "mboost": (1421, 213, 66),
            "bbwidth": (1607, 213, 66),
            "mfreq": (1785, 213, 66),
            "hatten": (1964, 213, 66),
            "hsfreq": (1858, 422, 58),
        },
        # Parameter-bearing artwork cleared from the production underlay.
        # Static headings, rules, rack hardware and the screen stay untouched.
        "control_clear_regions": ((86, 58, 478, 424),
                                  (1290, 58, 786, 424)),
        "lamp": (2031, 427, 18),
        "group_centres": ((356, 30), (1695, 30)),
        "dividers": (),
    },
    "vintage": {
        "filename": "vintage-eq-reference.png",
        "faceplate_filename": "vintage-eq-faceplate.png",
        "calibration_underlay_filename":
            "vintage-eq-calibration-underlay.png",
        "calibration_nodes_filename":
            "vintage-eq-calibration-nodes.png",
        "rack_crop": (8, 174, 2156, 377),
        "panel": (0, 0, 2156, 377),
        "ear": 80,
        "ears": ((0, 0, 80, 377), (2076, 0, 80, 377)),
        "slots": ((15, 7, 48, 25), (15, 316, 48, 28),
                  (2093, 7, 48, 25), (2093, 316, 48, 28)),
        "screws": ((121, 40, 17), (2036, 37, 17),
                   (121, 336, 17), (2036, 336, 17)),
        "heading_y": 31,
        "screen": (765, 47, 705, 292),
        "plot": (858, 102, 557, 175),
        "controls": {
            "lowgain": (182, 186, 55),
            "lowfreq": (342, 188, 55),
            "lowmidgain": (514, 186, 55),
            "lowmidfreq": (665, 186, 55),
            "himidgain": (1577, 186, 55),
            "himidfreq": (1737, 187, 55),
            "higain": (1939, 186, 55),
        },
        "control_clear_regions": ((82, 68, 349, 262),
                                  (432, 68, 322, 262),
                                  (1496, 68, 347, 262),
                                  (1844, 68, 232, 262)),
        "lamp": (1973, 330, 17),
        "group_centres": ((264, 42), (594, 42),
                          (1638, 42), (1939, 42)),
        "dividers": ((431, 28, 431, 326), (755, 28, 755, 326),
                     (1501, 28, 1501, 326), (1843, 28, 1843, 326)),
    },
}


EQ_REFERENCE_CALIBRATION_MODES = frozenset({
    "", "backdrop", "underlay", "overlay", "nodes", "both",
})


def rack(model):
    """Return one immutable-by-convention measured rack description."""
    try:
        return EQ_REFERENCE_RACKS[model]
    except KeyError as error:
        raise ValueError("unknown EQ reference model: %s" % model) from error


def calibration_mode(value):
    """Normalize the opt-in developer overlay without risking normal paint."""
    mode = str(value or "").strip().lower()
    return mode if mode in EQ_REFERENCE_CALIBRATION_MODES else ""


def scaled_rect(rect, width, height, model):
    """Scale one rack-local rectangle into a fitted rack rectangle."""
    _x, _y, source_width, source_height = rack(model)["rack_crop"]
    x, y, rect_width, rect_height = rect
    return (x * float(width) / source_width,
            y * float(height) / source_height,
            rect_width * float(width) / source_width,
            rect_height * float(height) / source_height)


def control_layout(model, width, height):
    """Scale the measured control circles into a fitted rack rectangle."""
    _x, _y, source_width, source_height = rack(model)["rack_crop"]
    scale_x = float(width) / source_width
    scale_y = float(height) / source_height
    radius_scale = min(scale_x, scale_y)
    return {
        field: (x * scale_x, y * scale_y, radius * radius_scale)
        for field, (x, y, radius) in rack(model)["controls"].items()
    }
