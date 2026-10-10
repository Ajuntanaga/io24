"""Pure-data reference geometry and value transforms for the io24 racks.

This module deliberately has no GTK, audio, or device dependencies.  The
manifest is the single coordinate authority shared by the offline compiler
and the runtime rack.
"""

import copy
import math
from pathlib import Path


_LIMITER = {
    "rack_id": "limiter",
    "source_size": (1400, 420),
    "panel": (38, 12, 1324, 396),
    "display": (485, 104, 430, 241),
    "lamp": (1309, 336, 14),
    "source": "limiter-reference.png",
    "output": "limiter-faceplate.png",
    "material_source": "vintage-eq-reference.png",
    "material_crop": (590, 480, 160, 50),
    "knob_source": "vintage-lowmid-knob.png",
    "calibration_underlay": "limiter-calibration-underlay.png",
    "calibration_nodes": "limiter-calibration-nodes.png",
    "knob_output": "limiter-knob.png",
    "receipt": "limiter-rack-assets.json",
    "generated": (
        "limiter-faceplate.png",
        "limiter-calibration-underlay.png",
        "limiter-calibration-nodes.png",
        "limiter-knob.png",
        "limiter-rack-assets.json",
    ),
    "ears": ((0, 0, 38, 420), (1362, 0, 38, 420)),
    "slots": ((9, 34, 20, 52), (9, 334, 20, 52),
              (1371, 34, 20, 52), (1371, 334, 20, 52)),
    "screws": ((63, 37, 9), (1337, 37, 9),
                (63, 383, 9), (1337, 383, 9)),
    # Reference-only control positions, display content, live values, and
    # lamp state are removed inside these regions to make the faceplate.
    "cleanup_regions": ((170, 112, 220, 264),
                        (1010, 112, 220, 264),
                        (500, 119, 400, 211),
                        (1295, 322, 28, 28)),
    # Radius multipliers scale with the knob; *_px dimensions stay in GTK
    # logical pixels, as do the value font and focus halos. The same contract
    # bounds runtime paint and reference/runtime screenshot comparisons.
    "live_style": {
        "tick_inner": 1.21,
        "tick_major_outer": 1.46,
        "tick_minor_outer": 1.38,
        "tick_major_width": .043,
        "tick_minor_width": .032,
        "knob_focus_px": 7.0,
        "lamp_focus_px": 5.0,
        "lamp_border_px": 2.0,
        "value_offset_px": 13.0,
        "value_width_px": 96.0,
        "value_height_px": 20.0,
        "value_font_pt": 8.0,
        "antialias_px": 2.0,
    },
    "controls": {
        "threshold": {
            "range": (-40.0, 0.0),
            "step": 0.01,
            "default": -28.0,
            "sweep": (135.0, 405.0),
            "asset": "limiter-knob.png",
            "format": "threshold_db",
            "format_string": "{:.2f} dB",
            "widget": "limiter.threshold",
            "geometry": (280, 223, 78),
        },
        "release": {
            "range": (0.05, 1.5),
            "step": 0.01,
            "default": 0.4,
            "sweep": (135.0, 405.0),
            "asset": "limiter-knob.png",
            "format": "release_seconds",
            "format_string": "{:.2f} s",
            "widget": "limiter.release",
            "geometry": (1120, 223, 78),
        },
    },
}

_RACKS = {"limiter": _LIMITER}
_RECT_KEYS = ("panel", "display")


def rack(rack_id):
    """Return a defensive copy of the named rack manifest."""
    try:
        return copy.deepcopy(_RACKS[rack_id])
    except KeyError:
        raise ValueError("unknown rack: %s" % rack_id)


def _rectangle(value, name, source_size, allow_circle=False):
    if not isinstance(value, (tuple, list)) or len(value) != (3 if allow_circle else 4):
        raise ValueError("%s must have %d values" % (name, 3 if allow_circle else 4))
    try:
        numbers = tuple(float(item) for item in value)
    except (TypeError, ValueError):
        raise ValueError("%s must contain numbers" % name)
    if not all(math.isfinite(item) for item in numbers):
        raise ValueError("%s must contain finite numbers" % name)
    dimensions = numbers[2:]
    if any(item <= 0 for item in dimensions):
        raise ValueError("%s dimensions must be positive" % name)
    width, height = source_size
    if allow_circle:
        if numbers[0] - numbers[2] < 0 or numbers[1] - numbers[2] < 0:
            raise ValueError("%s circle exceeds left/top source bounds" % name)
        right = numbers[0] + numbers[2]
        bottom = numbers[1] + numbers[2]
    else:
        if numbers[0] < 0 or numbers[1] < 0:
            raise ValueError("%s origin must be nonnegative" % name)
        right = numbers[0] + numbers[2]
        bottom = numbers[1] + numbers[3]
    if right > width or bottom > height:
        raise ValueError("%s must fit within source bounds" % name)
    return numbers


def validate_rack(spec, design_root=None):
    """Validate and return a defensive copy of a rack manifest.

    When ``design_root`` is supplied, maintained compiler inputs must also
    exist beneath it.
    """
    if not isinstance(spec, dict):
        raise ValueError("rack specification must be a dictionary")
    required = {
        "rack_id", "source_size", "panel", "display", "lamp", "controls",
        "source", "output", "material_source", "material_crop",
        "knob_source", "calibration_underlay", "calibration_nodes",
        "knob_output", "receipt", "generated", "cleanup_regions",
        "ears", "slots", "screws", "live_style",
    }
    missing = required.difference(spec)
    if missing:
        raise ValueError("missing rack keys: %s" % ", ".join(sorted(missing)))
    try:
        source_size = tuple(float(item) for item in spec["source_size"])
    except (TypeError, ValueError):
        raise ValueError("source_size must contain two numbers")
    if len(source_size) != 2 or any(item <= 0 for item in source_size):
        raise ValueError("source_size must be positive")
    path_fields = (
        "source", "output", "material_source", "knob_source",
        "calibration_underlay", "calibration_nodes", "knob_output", "receipt",
    )
    for field in path_fields:
        path = Path(str(spec[field]))
        if path.is_absolute() or ".." in path.parts or path.name != str(path):
            raise ValueError("%s must be a portable filename" % field)
        if design_root is not None and field in ("material_source", "knob_source"):
            if not (Path(design_root) / path).is_file():
                raise ValueError("missing %s: %s" % (field, path))
    generated = spec["generated"]
    expected_generated = (
        spec["output"], spec["calibration_underlay"],
        spec["calibration_nodes"], spec["knob_output"], spec["receipt"],
    )
    if tuple(generated) != expected_generated or len(set(generated)) != len(generated):
        raise ValueError("generated files do not match declared outputs")
    for field in _RECT_KEYS:
        _rectangle(spec[field], field, source_size)
    for field in ("ears", "slots"):
        values = spec[field]
        if not isinstance(values, (tuple, list)) or not values:
            raise ValueError("%s must be a non-empty sequence" % field)
        for index, value in enumerate(values):
            _rectangle(value, "%s %d" % (field, index), source_size)
    screws = spec["screws"]
    if not isinstance(screws, (tuple, list)) or not screws:
        raise ValueError("screws must be a non-empty sequence")
    for index, screw in enumerate(screws):
        _rectangle(screw, "screw %d" % index, source_size, allow_circle=True)
    _rectangle(spec["material_crop"], "material_crop", (2172, 724))
    _rectangle(spec["lamp"], "lamp", source_size, allow_circle=True)
    for index, region in enumerate(spec["cleanup_regions"]):
        _rectangle(region, "cleanup region %d" % index, source_size)
    style = spec["live_style"]
    for key in _LIMITER["live_style"]:
        value = style.get(key) if isinstance(style, dict) else None
        if (not isinstance(value, (int, float)) or
                not math.isfinite(value) or value <= 0):
            raise ValueError("invalid live_style %s" % key)
    controls = spec["controls"]
    if not isinstance(controls, dict) or not controls:
        raise ValueError("controls must be a non-empty dictionary")
    widgets = set()
    geometries = []
    for name, control in controls.items():
        if not isinstance(control, dict):
            raise ValueError("control %s must be a dictionary" % name)
        for key in ("range", "step", "default", "sweep", "asset", "format", "widget", "geometry"):
            if key not in control:
                raise ValueError("control %s missing %s" % (name, key))
        widget = control["widget"]
        if widget in widgets:
            raise ValueError("duplicate widget binding: %s" % widget)
        widgets.add(widget)
        bounds = control["range"]
        if (not isinstance(bounds, (tuple, list)) or len(bounds) != 2 or
                not all(isinstance(item, (int, float)) and math.isfinite(item) for item in bounds) or
                bounds[0] >= bounds[1]):
            raise ValueError("invalid range for control %s" % name)
        if (not isinstance(control["step"], (int, float)) or
                not math.isfinite(control["step"]) or control["step"] <= 0):
            raise ValueError("invalid step for control %s" % name)
        if not bounds[0] <= control["default"] <= bounds[1]:
            raise ValueError("default outside range for control %s" % name)
        sweep = control["sweep"]
        if (not isinstance(sweep, (tuple, list)) or len(sweep) != 2 or
                not all(isinstance(item, (int, float)) and math.isfinite(item)
                        for item in sweep) or sweep[0] >= sweep[1]):
            raise ValueError("invalid sweep for control %s" % name)
        geometry = _rectangle(
            control["geometry"], "control %s" % name, source_size,
            allow_circle=True)
        for other_name, other in geometries:
            distance = math.hypot(geometry[0] - other[0], geometry[1] - other[1])
            if distance < geometry[2] + other[2]:
                raise ValueError("overlapping controls: %s and %s" % (other_name, name))
        geometries.append((name, geometry))
    return copy.deepcopy(spec)


def scaled_rect(rect, width, height, rack_id):
    source_width, source_height = rack(rack_id)["source_size"]
    x, y, rect_width, rect_height = rect
    return (x * float(width) / source_width,
            y * float(height) / source_height,
            rect_width * float(width) / source_width,
            rect_height * float(height) / source_height)


def control_layout(rack_id, width, height):
    spec = rack(rack_id)
    source_width, source_height = spec["source_size"]
    scale_x = float(width) / source_width
    scale_y = float(height) / source_height
    radius_scale = min(scale_x, scale_y)
    return {
        name: (control["geometry"][0] * scale_x,
               control["geometry"][1] * scale_y,
               control["geometry"][2] * radius_scale)
        for name, control in spec["controls"].items()
    }


def value_fraction(control, value):
    lower, upper = control["range"]
    return max(0.0, min(1.0, (float(value) - lower) / (upper - lower)))


def control_live_regions(geometry, style):
    """Return a knob's painted circle and clipped value box in GTK pixels."""
    cx, cy, radius = geometry
    reach = max(radius * style["tick_major_outer"] +
                max(1.0, radius * style["tick_major_width"]) / 2.0,
                radius * style["tick_minor_outer"] +
                max(1.0, radius * style["tick_minor_width"]) / 2.0,
                radius + style["knob_focus_px"])
    value_width = style["value_width_px"]
    return ((cx, cy, reach + style["antialias_px"]),
            (cx - value_width / 2.0,
             cy + radius + style["value_offset_px"],
             value_width, style["value_height_px"]))


def fraction_value(control, fraction):
    lower, upper = control["range"]
    raw = lower + max(0.0, min(1.0, float(fraction))) * (upper - lower)
    step = control["step"]
    return max(lower, min(upper, round(raw / step) * step))


def pointer_angle(control, value):
    start, end = control["sweep"]
    return start + value_fraction(control, value) * (end - start)
