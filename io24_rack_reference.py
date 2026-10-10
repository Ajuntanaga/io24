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

    ``design_root`` is accepted for callers that resolve asset paths; this
    validator only enforces the manifest's portable-path boundary.
    """
    del design_root  # reserved for future asset-existence validation
    if not isinstance(spec, dict):
        raise ValueError("rack specification must be a dictionary")
    required = {"rack_id", "source_size", "panel", "display", "lamp", "controls", "source", "output"}
    missing = required.difference(spec)
    if missing:
        raise ValueError("missing rack keys: %s" % ", ".join(sorted(missing)))
    try:
        source_size = tuple(float(item) for item in spec["source_size"])
    except (TypeError, ValueError):
        raise ValueError("source_size must contain two numbers")
    if len(source_size) != 2 or any(item <= 0 for item in source_size):
        raise ValueError("source_size must be positive")
    for field in ("source", "output"):
        path = Path(str(spec[field]))
        if ".." in path.parts:
            raise ValueError("%s path may not contain '..'" % field)
    for field in _RECT_KEYS:
        _rectangle(spec[field], field, source_size)
    _rectangle(spec["lamp"], "lamp", source_size, allow_circle=True)
    controls = spec["controls"]
    if not isinstance(controls, dict) or not controls:
        raise ValueError("controls must be a non-empty dictionary")
    widgets = set()
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
        if not isinstance(control["step"], (int, float)) or control["step"] <= 0:
            raise ValueError("invalid step for control %s" % name)
        if not bounds[0] <= control["default"] <= bounds[1]:
            raise ValueError("default outside range for control %s" % name)
        sweep = control["sweep"]
        if (not isinstance(sweep, (tuple, list)) or len(sweep) != 2 or
                sweep[0] >= sweep[1]):
            raise ValueError("invalid sweep for control %s" % name)
        _rectangle(control["geometry"], "control %s" % name, source_size, allow_circle=True)
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


def fraction_value(control, fraction):
    lower, upper = control["range"]
    raw = lower + max(0.0, min(1.0, float(fraction))) * (upper - lower)
    step = control["step"]
    return max(lower, min(upper, round(raw / step) * step))


def pointer_angle(control, value):
    start, end = control["sweep"]
    return start + value_fraction(control, value) * (end - start)
