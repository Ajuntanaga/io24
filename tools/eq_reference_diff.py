#!/usr/bin/env python3
"""Exact pixel-diff gate for the alternate-EQ reference compositor.

Render the same midpoint state once with
``IO24_EQ_REFERENCE_CALIBRATION=backdrop`` and once normally. Scope the check
to the rack, then pass the plot and lamp rectangles plus only the moving knob
cores as allowed dynamic regions. Any scoped change outside those regions is
a stationary faceplate, engraved scale, or rack-bay regression.
"""

import argparse
import json

import numpy as np
from PIL import Image


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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline")
    parser.add_argument("actual")
    parser.add_argument(
        "--scope-rect", type=rectangle, metavar="X,Y,W,H",
        help="compare only this rack rectangle")
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

    result, changed, allowed, unexpected = diff_images(
        args.baseline, args.actual, args.allow_rect, args.allow_circle,
        args.scope_rect, args.tolerance)
    if args.heatmap:
        heatmap = np.zeros((*changed.shape, 3), dtype=np.uint8)
        heatmap[changed & allowed] = (20, 235, 255)
        heatmap[unexpected] = (255, 35, 115)
        Image.fromarray(heatmap, "RGB").save(args.heatmap)
    print(json.dumps(result, sort_keys=True))
    return 1 if result["unexpected_pixels"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
