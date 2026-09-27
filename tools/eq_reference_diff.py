#!/usr/bin/env python3
"""Exact pixel-diff gate for the three EQ reference calibrations.

Render the same midpoint state once with
``IO24_EQ_REFERENCE_CALIBRATION=backdrop`` and once normally. Scope the check
to the fitted rack. ``--model`` derives every allowed live region from the
same measured manifest as GTK; manual rectangles/circles remain available for
one-off checks. Any other change is a static faceplate or rack-bay regression.
"""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import io24_eq_reference  # noqa: E402


def rectangle(text):
    values = tuple(int(part) for part in text.split(","))
    if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
        raise argparse.ArgumentTypeError("expected x,y,width,height")
    return values


def circle(text):
    values = tuple(int(part) for part in text.split(","))
    if len(values) != 3 or values[2] <= 0:
        raise argparse.ArgumentTypeError("expected center_x,center_y,radius")
    return values


def diff_images(baseline_path, actual_path, allowed_rectangles=(),
                allowed_circles=(), scope_rectangle=None,
                max_channel_delta=0):
    baseline = np.asarray(Image.open(baseline_path).convert("RGBA"),
                          dtype=np.int16)
    actual = np.asarray(Image.open(actual_path).convert("RGBA"),
                        dtype=np.int16)
    if baseline.shape != actual.shape:
        raise ValueError("capture dimensions differ: %r != %r" % (
            baseline.shape, actual.shape))

    delta = np.max(np.abs(actual - baseline), axis=2)
    source_changed = delta > int(max_channel_delta)
    scope = np.ones(source_changed.shape, dtype=bool)
    if scope_rectangle is not None:
        scope[:] = False
        x, y, scope_width, scope_height = scope_rectangle
        left, top = max(0, x), max(0, y)
        right = min(source_changed.shape[1], x + scope_width)
        bottom = min(source_changed.shape[0], y + scope_height)
        if left < right and top < bottom:
            scope[top:bottom, left:right] = True
    changed = source_changed & scope
    allowed = np.zeros(changed.shape, dtype=bool)
    height, width = changed.shape
    for x, y, rect_width, rect_height in allowed_rectangles:
        left, top = max(0, x), max(0, y)
        right = min(width, x + rect_width)
        bottom = min(height, y + rect_height)
        if left < right and top < bottom:
            allowed[top:bottom, left:right] = True
    yy, xx = np.ogrid[:height, :width]
    for center_x, center_y, radius in allowed_circles:
        allowed |= ((xx - center_x) ** 2 + (yy - center_y) ** 2 <=
                    radius ** 2)
    unexpected = changed & ~allowed
    coordinates = np.argwhere(unexpected)
    unexpected_bbox = None
    if coordinates.size:
        top, left = coordinates.min(axis=0)
        bottom, right = coordinates.max(axis=0)
        unexpected_bbox = [int(left), int(top),
                           int(right + 1), int(bottom + 1)]
    return {
        "width": width,
        "height": height,
        "source_changed_pixels": int(source_changed.sum()),
        "changed_pixels": int(changed.sum()),
        "allowed_changed_pixels": int((changed & allowed).sum()),
        "unexpected_pixels": int(unexpected.sum()),
        "unexpected_bbox": unexpected_bbox,
        "max_channel_delta": int(delta.max()),
    }, changed, allowed, unexpected


def model_regions(model, rack_rectangle):
    """Translate one measured rack manifest into screenshot coordinates."""
    art = io24_eq_reference.rack(model)
    rack_x, rack_y, rack_width, rack_height = rack_rectangle
    _source_x, _source_y, source_width, source_height = art["rack_crop"]

    def scale_rect(rect, padding=0):
        x, y, width, height = rect
        x = max(0, x - padding)
        y = max(0, y - padding)
        width = min(source_width - x, width + padding * 2)
        height = min(source_height - y, height + padding * 2)
        return (round(rack_x + x / source_width * rack_width),
                round(rack_y + y / source_height * rack_height),
                round(width / source_width * rack_width),
                round(height / source_height * rack_height))

    dynamic_plot = art.get("glass", art["plot"]) \
        if model == "standard" else art["plot"]
    # The production layers intentionally feather cleared artwork and glow
    # live curves.  Twelve source pixels is the measured maximum reach of
    # those effects; it is dynamic allowance, not static-faceplate tolerance.
    dynamic_padding = 12
    rectangles = [scale_rect(dynamic_plot, dynamic_padding)]
    rectangles.extend(scale_rect(region, dynamic_padding)
                      for region in art["control_clear_regions"])
    lamp_x, lamp_y, lamp_radius = art["lamp"]
    radius_scale = min(rack_width / source_width,
                       rack_height / source_height)
    circles = [(
        round(rack_x + lamp_x / source_width * rack_width),
        round(rack_y + lamp_y / source_height * rack_height),
        max(1, round(lamp_radius * 2.75 * radius_scale)),
    )]
    return rectangles, circles


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline")
    parser.add_argument("actual")
    parser.add_argument(
        "--scope-rect", type=rectangle, metavar="X,Y,W,H",
        help="compare only this rack rectangle")
    parser.add_argument(
        "--model", choices=("standard", "passive", "vintage"),
        help="derive dynamic allowances from the measured rack manifest")
    parser.add_argument(
        "--rack-rect", type=rectangle, metavar="X,Y,W,H",
        help="fitted rack bounds in both captures; required with --model")
    parser.add_argument(
        "--allow-rect", action="append", default=[], type=rectangle,
        metavar="X,Y,W,H", help="dynamic plot/lamp rectangle; repeatable")
    parser.add_argument(
        "--allow-circle", action="append", default=[], type=circle,
        metavar="CX,CY,R", help="dynamic knob circle; repeatable")
    parser.add_argument(
        "--heatmap", help="optional output: cyan allowed, magenta unexpected")
    parser.add_argument(
        "--tolerance", type=int, default=0, metavar="0..255",
        help="ignore per-channel render noise up to this value")
    args = parser.parse_args(argv)

    if bool(args.model) != bool(args.rack_rect):
        parser.error("--model and --rack-rect must be used together")
    allowed_rectangles = list(args.allow_rect)
    allowed_circles = list(args.allow_circle)
    scope_rectangle = args.scope_rect
    if args.model:
        model_rectangles, model_circles = model_regions(
            args.model, args.rack_rect)
        allowed_rectangles.extend(model_rectangles)
        allowed_circles.extend(model_circles)
        if scope_rectangle is None:
            scope_rectangle = args.rack_rect

    result, changed, allowed, unexpected = diff_images(
        args.baseline, args.actual, allowed_rectangles, allowed_circles,
        scope_rectangle, args.tolerance)
    if args.heatmap:
        heatmap = np.zeros((*changed.shape, 3), dtype=np.uint8)
        heatmap[changed & allowed] = (20, 235, 255)
        heatmap[unexpected] = (255, 35, 115)
        Image.fromarray(heatmap, "RGB").save(args.heatmap)
    print(json.dumps(result, sort_keys=True))
    return 1 if result["unexpected_pixels"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
