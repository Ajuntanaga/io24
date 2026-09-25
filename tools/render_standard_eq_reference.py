#!/usr/bin/env python3
"""Deterministic renderer for the Standard parametric EQ reference image.

The PNG in ``docs/design`` is the canonical reference; this script only
reproduces it.  It shares the 2172x724 frame and the 2156x482 two-unit plate
of ``passive-program-eq-reference.png`` so all three EQ references sit at one
scale.  Every printed value is taken from the Host's exact Standard EQ
contract: four bands, a -15..+15 dB gain knob per band, and a response screen
with the Host's +/-18 dB, 20 Hz..24 kHz plot.  No bitmap is read.

    python3 tools/render_standard_eq_reference.py [output.png]
"""

import argparse
import math
from pathlib import Path
import random
import sys

import cairo
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import io24  # noqa: E402  (pure biquad designers; no device is opened)

OUTPUT = ROOT / "docs" / "design" / "standard-parametric-eq-reference.png"
FACEPLATE_OUTPUT = ROOT / "docs" / "design" / \
    "standard-parametric-eq-faceplate.png"
FONT = "Nimbus Sans Narrow"

WIDTH, HEIGHT = 2172, 724
RACK = (8, 121, 2156, 482)
EAR = 80
SCREEN_CUT = (620, 186, 932, 384)
FRAME_INSET = 6
GASKET_INSET = 20
GLASS_INSET = 26
PLOT_INSET = (16, 12)
KNOB_Y = 350
KNOB_X = (232, 482, 1690, 1940)
KNOB_RADIUS = 88
HEADING_Y = 158
SCREWS = ((128, 152), (2044, 152), (128, 572))
LAMP = (2040, 562, 20)
SLOT_ROWS = (150, 574)

GAIN_RANGE = (-15.0, 15.0)
KNOB_DEGREES = (-225.0, 45.0)
DISPLAY_DB = 18.0
SAMPLE_RATE = 48000.0
LIGHT = math.radians(-125.0)

BANDS = (
    {"name": "LOW", "tone": (0.91, 0.45, 0.39), "shape": "lowshelf",
     "freq": 80.0, "gain": 5.0, "q": 0.6},
    {"name": "LOW MID", "tone": (0.95, 0.70, 0.32), "shape": "peaking",
     "freq": 350.0, "gain": -4.0, "q": 1.0},
    {"name": "HIGH MID", "tone": (0.42, 0.83, 0.60), "shape": "peaking",
     "freq": 2400.0, "gain": 4.5, "q": 1.2},
    {"name": "HIGH", "tone": (0.50, 0.62, 0.98), "shape": "highshelf",
     "freq": 9000.0, "gain": 3.0, "q": 0.6},
)
SELECTED = 2
MODE_TEXT = {"lowshelf": "SHELF", "highshelf": "SHELF",
             "peaking": "PEAK", "off": "OFF"}


def inset(rect, amount):
    x, y, w, h = rect
    return (x + amount, y + amount, w - amount * 2, h - amount * 2)


def glass_rect():
    return inset(SCREEN_CUT, GLASS_INSET)


def plot_rect():
    x, y, w, h = glass_rect()
    ix, iy = PLOT_INSET
    return (x + ix, y + iy, w - ix * 2, h - iy * 2)


def rounded(ctx, x, y, w, h, r):
    r = min(r, w / 2.0, h / 2.0)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def vgradient(y0, y1, stops):
    gradient = cairo.LinearGradient(0, y0, 0, y1)
    for offset, colour in stops:
        gradient.add_color_stop_rgba(offset, *colour)
    return gradient


def blurred(draw, radius):
    """Draw one layer, then blur its premultiplied channels independently."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    draw(cairo.Context(surface))
    surface.flush()
    stride = surface.get_stride()
    data = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape(
        HEIGHT, stride)[:, :WIDTH * 4].reshape(HEIGHT, WIDTH, 4)
    channels = [Image.fromarray(np.ascontiguousarray(data[:, :, index]))
                .filter(ImageFilter.GaussianBlur(radius))
                for index in range(4)]
    result = np.stack([np.asarray(channel) for channel in channels], axis=2)
    buffer = bytearray(np.ascontiguousarray(result).tobytes())
    # pycairo holds a reference to ``buffer`` for the surface's lifetime.
    return cairo.ImageSurface.create_for_data(
        buffer, cairo.FORMAT_ARGB32, WIDTH, HEIGHT, WIDTH * 4)


def paint_layer(ctx, layer, alpha=1.0):
    ctx.save()
    ctx.set_source_surface(layer, 0, 0)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def font(ctx, size, bold=True):
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if bold else
                         cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    options = cairo.FontOptions()
    options.set_hint_metrics(cairo.HINT_METRICS_OFF)
    options.set_hint_style(cairo.HINT_STYLE_NONE)
    options.set_antialias(cairo.ANTIALIAS_GRAY)
    ctx.set_font_options(options)


def text_width(ctx, text, spacing):
    width = 0.0
    for index, character in enumerate(text):
        width += ctx.text_extents(character).x_advance
        if index < len(text) - 1:
            width += spacing
    return width


def label(ctx, text, cx, cy, size, colour, bold=True, spacing=0.0,
          align="center", engraved=True):
    """Print faceplate text vertically centred on its cap height."""
    font(ctx, size, bold)
    cap = ctx.text_extents("H").height
    width = text_width(ctx, text, spacing)
    x = cx - width / 2.0 if align == "center" else (
        cx - width if align == "right" else cx)
    baseline = cy + cap / 2.0

    def run(dx, dy, rgba):
        ctx.set_source_rgba(*rgba)
        pen = x + dx
        for character in text:
            ctx.move_to(pen, baseline + dy)
            ctx.show_text(character)
            pen += ctx.text_extents(character).x_advance + spacing

    if engraved:
        run(0.0, 1.4, (0.0, 0.0, 0.0, 0.55 * colour[3]))
    run(0.0, 0.0, colour)
    return x, width


def line(ctx, points, rgba, width, cap=cairo.LINE_CAP_ROUND):
    ctx.set_source_rgba(*rgba)
    ctx.set_line_width(width)
    ctx.set_line_cap(cap)
    ctx.move_to(*points[0])
    for point in points[1:]:
        ctx.line_to(*point)
    ctx.stroke()


def circle(ctx, x, y, r, source):
    ctx.new_path()
    ctx.arc(x, y, r, 0, math.tau)
    if isinstance(source, tuple):
        ctx.set_source_rgba(*source)
    else:
        ctx.set_source(source)
    ctx.fill()


def radial(cx, cy, r, stops, focus=(-0.28, -0.34)):
    gradient = cairo.RadialGradient(cx + focus[0] * r, cy + focus[1] * r, 0,
                                    cx, cy, r * 1.35)
    for offset, colour in stops:
        gradient.add_color_stop_rgba(offset, *colour)
    return gradient


# -- Response ---------------------------------------------------------------

def band_sections():
    designers = {"peaking": io24.biquad_peaking,
                 "lowshelf": io24.biquad_lowshelf,
                 "highshelf": io24.biquad_highshelf}
    sections = []
    for band in BANDS:
        wire = designers[band["shape"]](
            band["freq"], band["gain"], SAMPLE_RATE, band["q"])
        sections.append((wire[0], wire[2], wire[4], -wire[1], -wire[3]))
    return sections


def response_db(sections, frequency):
    omega = 2 * math.pi * frequency / SAMPLE_RATE
    z1 = complex(math.cos(-omega), math.sin(-omega))
    z2 = z1 * z1
    total = 1.0 + 0.0j
    for b0, b1, b2, a1, a2 in sections:
        total *= (b0 + b1 * z1 + b2 * z2) / (1 + a1 * z1 + a2 * z2)
    return 20 * math.log10(max(abs(total), 1e-6))


def plot_x(frequency):
    x, _y, w, _h = plot_rect()
    return x + math.log10(max(frequency, 20.0) / 20.0) / \
        math.log10(24000.0 / 20.0) * w


def plot_y(db):
    _x, y, _w, h = plot_rect()
    return y + h / 2.0 - db / DISPLAY_DB * (h / 2.0)


# -- Hardware ----------------------------------------------------------------

def draw_background(ctx):
    ctx.set_source(vgradient(0, HEIGHT, (
        (0.0, (0.150, 0.180, 0.215, 1)),
        (0.55, (0.118, 0.142, 0.172, 1)),
        (1.0, (0.090, 0.108, 0.132, 1)))))
    ctx.paint()
    vignette = cairo.RadialGradient(WIDTH / 2, HEIGHT * 0.45, 200,
                                    WIDTH / 2, HEIGHT * 0.45, WIDTH * 0.62)
    vignette.add_color_stop_rgba(0, 0, 0, 0, 0)
    vignette.add_color_stop_rgba(1, 0, 0, 0, 0.30)
    ctx.set_source(vignette)
    ctx.paint()


def draw_rack_shadow(ctx):
    x, y, w, h = RACK

    def shadow(layer):
        rounded(layer, x + 10, y + 16, w - 20, h, 10)
        layer.set_source_rgba(0, 0, 0, 0.78)
        layer.fill()

    paint_layer(ctx, blurred(shadow, 16))


def brushed_texture(ctx, x, y, w, h, rng, streaks):
    """Fine horizontal brushing: long faint streaks over short dense grain."""
    ctx.save()
    rounded(ctx, x, y, w, h, 6)
    ctx.clip()
    for _ in range(streaks):
        sy = y + rng.random() * h
        sx = x + rng.random() * w
        length = 14 + rng.random() ** 2 * 380
        bright = rng.random() < 0.55
        alpha = 0.012 + rng.random() * 0.035
        colour = (0.82, 0.88, 0.95, alpha) if bright else \
            (0.0, 0.01, 0.02, alpha * 1.4)
        line(ctx, [(sx, sy), (sx + length, sy + rng.uniform(-.3, .3))],
             colour, 0.5 + rng.random() * 0.7, cairo.LINE_CAP_BUTT)
    ctx.restore()


def draw_plate(ctx, rng):
    x, y, w, h = RACK
    # Plate body: deep navy graphite with a real vertical fall-off.
    rounded(ctx, x, y, w, h, 8)
    ctx.set_source(vgradient(y, y + h, (
        (0.0, (0.200, 0.238, 0.296, 1)),
        (0.05, (0.160, 0.194, 0.246, 1)),
        (0.45, (0.118, 0.146, 0.190, 1)),
        (0.88, (0.080, 0.100, 0.134, 1)),
        (1.0, (0.060, 0.075, 0.102, 1)))))
    ctx.fill()
    # A broad, cool sheen across the upper third reads as anodized metal.
    sheen = cairo.RadialGradient(WIDTH * 0.5, y - 260, 80,
                                 WIDTH * 0.5, y - 260, 900)
    sheen.add_color_stop_rgba(0, 0.55, 0.70, 0.85, 0.10)
    sheen.add_color_stop_rgba(1, 0.55, 0.70, 0.85, 0.0)
    rounded(ctx, x, y, w, h, 8)
    ctx.set_source(sheen)
    ctx.fill()
    brushed_texture(ctx, x, y, w, h, rng, 5200)

    # Rack ears are separate folded pieces, one shade darker.
    for ex in (x, x + w - EAR):
        rounded(ctx, ex, y, EAR, h, 8)
        ctx.set_source(vgradient(y, y + h, (
            (0.0, (0.170, 0.204, 0.252, 1)),
            (0.5, (0.100, 0.124, 0.160, 1)),
            (1.0, (0.052, 0.066, 0.090, 1)))))
        ctx.fill()
        brushed_texture(ctx, ex, y, EAR, h, rng, 380)
        seam = ex + EAR if ex == x else ex
        line(ctx, [(seam, y + 3), (seam, y + h - 3)],
             (0.0, 0.0, 0.0, 0.70), 2.4, cairo.LINE_CAP_BUTT)
        line(ctx, [(seam + 1.8, y + 3), (seam + 1.8, y + h - 3)],
             (0.70, 0.80, 0.90, 0.10), 1.0, cairo.LINE_CAP_BUTT)
        for sy in SLOT_ROWS:
            cx = ex + EAR / 2.0
            rounded(ctx, cx - 23, sy - 10, 46, 20, 10)
            ctx.set_source(vgradient(sy - 10, sy + 10, (
                (0.0, (0.010, 0.012, 0.016, 1)),
                (1.0, (0.060, 0.070, 0.085, 1)))))
            ctx.fill()
            rounded(ctx, cx - 23, sy - 10, 46, 20, 10)
            ctx.set_source(vgradient(sy - 10, sy + 10, (
                (0.0, (0.0, 0.0, 0.0, 0.8)),
                (0.6, (0.3, 0.36, 0.42, 0.25)),
                (1.0, (0.75, 0.82, 0.90, 0.45)))))
            ctx.set_line_width(1.4)
            ctx.stroke()

    # Machined edges: bright upper chamfer, shadowed lower lip.
    line(ctx, [(x + 8, y + 1.2), (x + w - 8, y + 1.2)],
         (0.85, 0.92, 1.0, 0.34), 1.4, cairo.LINE_CAP_BUTT)
    line(ctx, [(x + 8, y + 3.2), (x + w - 8, y + 3.2)],
         (0.85, 0.92, 1.0, 0.07), 1.6, cairo.LINE_CAP_BUTT)
    line(ctx, [(x + 8, y + h - 1.2), (x + w - 8, y + h - 1.2)],
         (0.0, 0.0, 0.0, 0.65), 1.8, cairo.LINE_CAP_BUTT)
    rounded(ctx, x + 0.5, y + 0.5, w - 1, h - 1, 8)
    ctx.set_source_rgba(0.0, 0.0, 0.0, 0.55)
    ctx.set_line_width(1.0)
    ctx.stroke()


def pixel_grain(image, rng_seed):
    """Add fine, deterministic luminance grain to the plate only."""
    array = np.asarray(image).astype(np.int16)
    generator = np.random.default_rng(rng_seed)
    noise = generator.normal(0.0, 2.3, size=array.shape[:2])
    streak = generator.normal(0.0, 1.4, size=(array.shape[0], 1))
    x, y, w, h = RACK
    mask = np.zeros(array.shape[:2], dtype=bool)
    mask[y + 2:y + h - 2, x + 2:x + w - 2] = True
    delta = (noise + streak)[..., None]
    array[mask] = np.clip(array[mask] + delta[mask], 0, 255)
    return Image.fromarray(array.astype(np.uint8), "RGB")


def draw_screw(ctx, sx, sy):
    circle(ctx, sx + 1.2, sy + 2.2, 14, (0, 0, 0, 0.55))
    circle(ctx, sx, sy, 13.5, (0.020, 0.025, 0.032, 1))
    circle(ctx, sx, sy, 11.5, radial(sx, sy, 11.5, (
        (0.0, (0.72, 0.76, 0.80, 1)),
        (0.55, (0.36, 0.40, 0.45, 1)),
        (1.0, (0.12, 0.14, 0.17, 1)))))
    for angle in (math.radians(22), math.radians(112)):
        dx, dy = 7.2 * math.cos(angle), 7.2 * math.sin(angle)
        line(ctx, [(sx - dx, sy - dy), (sx + dx, sy + dy)],
             (0.04, 0.045, 0.05, 0.95), 2.8)
        line(ctx, [(sx - dx + .8, sy - dy + 1), (sx + dx + .8, sy + dy + 1)],
             (0.85, 0.88, 0.92, 0.18), 0.8)


def draw_heading(ctx, selected=SELECTED):
    x, _y, _w, _h = SCREEN_CUT
    title_x, title_w = label(
        ctx, "STANDARD  EQ", WIDTH / 2.0, HEADING_Y, 29,
        (0.90, 0.92, 0.90, 0.94), spacing=9.5)
    right = SCREEN_CUT[0] + SCREEN_CUT[2]
    for start, end in ((x + 40, title_x - 30),
                       (title_x + title_w + 30, right - 40)):
        line(ctx, [(start, HEADING_Y), (end, HEADING_Y)],
             (0.0, 0.0, 0.0, 0.55), 1.6, cairo.LINE_CAP_BUTT)
        line(ctx, [(start, HEADING_Y + 1.4), (end, HEADING_Y + 1.4)],
             (0.78, 0.85, 0.92, 0.26), 1.0, cairo.LINE_CAP_BUTT)
    for index, (cx, band) in enumerate(zip(KNOB_X, BANDS)):
        tone = band["tone"]
        is_selected = index == selected
        label(ctx, band["name"], cx, HEADING_Y, 23,
              (tone[0], tone[1], tone[2], 0.98 if is_selected else 0.80),
              spacing=4.0)


def draw_screen(ctx, rng, dynamic=True):
    cx, cy, cw, ch = SCREEN_CUT
    # Recess into the plate: dark floor, lit lower lip.
    rounded(ctx, cx, cy, cw, ch, 18)
    ctx.set_source(vgradient(cy, cy + ch, (
        (0.0, (0.010, 0.013, 0.018, 1)),
        (1.0, (0.040, 0.050, 0.064, 1)))))
    ctx.fill()
    rounded(ctx, cx - 1, cy - 1, cw + 2, ch + 2, 19)
    ctx.set_source(vgradient(cy, cy + ch, (
        (0.0, (0.0, 0.0, 0.0, 0.70)),
        (0.85, (0.5, 0.6, 0.7, 0.05)),
        (1.0, (0.80, 0.88, 0.96, 0.32)))))
    ctx.set_line_width(2.0)
    ctx.stroke()

    fx, fy, fw, fh = inset(SCREEN_CUT, FRAME_INSET)

    def frame_shadow(layer):
        rounded(layer, fx + 2, fy + 7, fw - 4, fh, 14)
        layer.set_source_rgba(0, 0, 0, 0.85)
        layer.fill()

    paint_layer(ctx, blurred(frame_shadow, 6))
    # Machined gunmetal frame.
    rounded(ctx, fx, fy, fw, fh, 14)
    ctx.set_source(vgradient(fy, fy + fh, (
        (0.0, (0.380, 0.430, 0.500, 1)),
        (0.045, (0.235, 0.270, 0.325, 1)),
        (0.50, (0.140, 0.165, 0.205, 1)),
        (0.955, (0.085, 0.100, 0.128, 1)),
        (1.0, (0.200, 0.230, 0.270, 1)))))
    ctx.fill()
    brushed_texture(ctx, fx, fy, fw, fh, rng, 700)
    rounded(ctx, fx + 0.8, fy + 0.8, fw - 1.6, fh - 1.6, 13.5)
    ctx.set_source(vgradient(fy, fy + fh, (
        (0.0, (0.90, 0.95, 1.0, 0.45)),
        (0.12, (0.90, 0.95, 1.0, 0.06)),
        (0.9, (0.0, 0.0, 0.0, 0.2)),
        (1.0, (0.0, 0.0, 0.0, 0.6)))))
    ctx.set_line_width(1.5)
    ctx.stroke()

    # Gasket and glass.
    gx, gy, gw, gh = inset(SCREEN_CUT, GASKET_INSET)
    rounded(ctx, gx, gy, gw, gh, 9)
    ctx.set_source_rgba(0.006, 0.009, 0.012, 1)
    ctx.fill()
    rounded(ctx, gx - 1, gy - 1, gw + 2, gh + 2, 10)
    ctx.set_source(vgradient(gy, gy + gh, (
        (0.0, (0.0, 0.0, 0.0, 0.9)),
        (1.0, (0.60, 0.70, 0.80, 0.30)))))
    ctx.set_line_width(1.2)
    ctx.stroke()

    x, y, w, h = glass_rect()
    ctx.save()
    rounded(ctx, x, y, w, h, 6)
    ctx.clip()
    ctx.set_source(vgradient(y, y + h, (
        (0.0, (0.024, 0.098, 0.118, 1)),
        (0.55, (0.013, 0.064, 0.080, 1)),
        (1.0, (0.008, 0.040, 0.053, 1)))))
    ctx.paint()
    bloom = cairo.RadialGradient(x + w / 2, y + h * 0.55, 20,
                                 x + w / 2, y + h * 0.55, w * 0.6)
    bloom.add_color_stop_rgba(0, 0.10, 0.45, 0.50, 0.16)
    bloom.add_color_stop_rgba(1, 0.10, 0.45, 0.50, 0.0)
    ctx.set_source(bloom)
    ctx.paint()
    draw_plot(ctx, dynamic=dynamic)
    # Faint raster, a top inner shadow and a restrained glass reflection.
    for row in range(int(y), int(y + h), 3):
        line(ctx, [(x, row + 0.5), (x + w, row + 0.5)],
             (0.0, 0.0, 0.0, 0.10), 1.0, cairo.LINE_CAP_BUTT)
    ctx.rectangle(x, y, w, 22)
    ctx.set_source(vgradient(y, y + 22, (
        (0.0, (0.0, 0.0, 0.0, 0.55)), (1.0, (0.0, 0.0, 0.0, 0.0)))))
    ctx.fill()
    reflection = cairo.LinearGradient(x, y, x + w * 0.45, y + h)
    reflection.add_color_stop_rgba(0.0, 0.80, 0.95, 1.0, 0.075)
    reflection.add_color_stop_rgba(0.42, 0.80, 0.95, 1.0, 0.020)
    reflection.add_color_stop_rgba(0.43, 0.80, 0.95, 1.0, 0.0)
    ctx.set_source(reflection)
    ctx.paint()
    ctx.restore()


def draw_plot(ctx, dynamic=True):
    x, y, w, h = plot_rect()
    teal = (0.36, 0.80, 0.84)
    minor = [base * decade for decade in (10, 100, 1000, 10000)
             for base in range(2, 10) if 20 <= base * decade <= 20000]
    for frequency in minor:
        px = plot_x(frequency)
        major = frequency in (50, 100, 200, 500, 1000, 2000, 5000, 10000)
        line(ctx, [(px, y), (px, y + h)],
             (*teal, 0.11 if major else 0.045), 1.0, cairo.LINE_CAP_BUTT)
    for db in (-12, -6, 0, 6, 12):
        py = plot_y(db)
        line(ctx, [(x, py), (x + w, py)],
             (*teal, 0.26 if db == 0 else 0.10), 1.2 if db == 0 else 1.0,
             cairo.LINE_CAP_BUTT)
        label(ctx, "%+d" % db if db else "0", x + 8, py - 11, 15,
              (0.52, 0.82, 0.85, 0.62), bold=False, align="left",
              engraved=False)
    for frequency, text in ((50, "50"), (100, "100"), (200, "200"),
                            (500, "500"), (1000, "1k"), (2000, "2k"),
                            (5000, "5k"), (10000, "10k")):
        label(ctx, text, plot_x(frequency), y + h - 11, 15,
              (0.52, 0.82, 0.85, 0.62), bold=False, engraved=False)
    label(ctx, "INPUT 1   PEAK -38 dB", x + w - 10, y + 13, 15,
          (0.55, 0.80, 0.84, 0.58), bold=False, align="right",
          engraved=False) if dynamic else None

    if not dynamic:
        return

    # A quiet live-spectrum silhouette behind the response.
    points = []
    for step in range(0, 241):
        frequency = 20.0 * (24000.0 / 20.0) ** (step / 240.0)
        octave = math.log2(frequency / 220.0)
        level = -50.0 - 5.0 * octave ** 2 * (0.55 if octave < 0 else 0.30)
        level += 1.6 * math.sin(step * 0.37) + 0.8 * math.sin(step * 0.83)
        level = max(-108.0, min(-6.0, level))
        points.append((plot_x(frequency),
                       y + h - (level + 108.0) / 102.0 * h))
    ctx.move_to(x, y + h)
    for point in points:
        ctx.line_to(*point)
    ctx.line_to(x + w, y + h)
    ctx.close_path()
    ctx.set_source_rgba(0.30, 0.80, 0.90, 0.06)
    ctx.fill()
    line(ctx, points, (0.35, 0.85, 0.92, 0.14), 1.2)

    sections = band_sections()
    curve = []
    for px in range(0, int(w) + 1, 2):
        frequency = 20.0 * (24000.0 / 20.0) ** (px / w)
        db = response_db(sections, frequency)
        curve.append((x + px, max(y + 1, min(y + h - 1, plot_y(db)))))
    zero = plot_y(0)
    ctx.move_to(x, zero)
    for point in curve:
        ctx.line_to(*point)
    ctx.line_to(x + w, zero)
    ctx.close_path()
    ctx.set_source_rgba(0.20, 0.78, 0.88, 0.15)
    ctx.fill()
    cyan = (0.36, 0.90, 0.96)

    def trace(layer):
        line(layer, curve, (*cyan, 1.0), 5.0)

    paint_layer(ctx, blurred(trace, 9), 0.75)
    line(ctx, curve, (*cyan, 1.0), 3.0)
    line(ctx, curve, (0.88, 1.0, 1.0, 0.55), 1.0)

    for index, band in enumerate(BANDS):
        tone = band["tone"]
        nx = plot_x(band["freq"])
        ny = max(y + 7, min(y + h - 7,
                            plot_y(response_db(sections, band["freq"]))))
        selected = index == SELECTED
        line(ctx, [(nx, y), (nx, y + h)],
             (*tone, 0.30 if selected else 0.12), 1.0, cairo.LINE_CAP_BUTT)
        radius = 12.5 if selected else 9.5

        def halo(layer, nx=nx, ny=ny, tone=tone, radius=radius):
            circle(layer, nx, ny, radius + 4, (*tone, 1.0))

        paint_layer(ctx, blurred(halo, 8), 0.75 if selected else 0.35)
        circle(ctx, nx, ny, radius + 2.5, (0.0, 0.02, 0.03, 0.75))
        circle(ctx, nx, ny, radius, radial(nx, ny, radius, (
            (0.0, tuple(min(1.0, part * 1.25 + 0.15) for part in tone)
             + (1.0,)),
            (0.6, (*tone, 1.0)),
            (1.0, tuple(part * 0.55 for part in tone) + (1.0,)))))
        circle(ctx, nx, ny, 3.2, (1.0, 1.0, 0.97, 0.95))
        if selected:
            ctx.new_path()
            ctx.arc(nx, ny, radius + 6.5, 0, math.tau)
            ctx.set_source_rgba(0.95, 0.98, 1.0, 0.85)
            ctx.set_line_width(1.6)
            ctx.stroke()
            tag = "%s   %.0f Hz   %+.1f dB   Q %.2f" % (
                band["name"], band["freq"], band["gain"], band["q"])
            font(ctx, 15, True)
            tag_w = text_width(ctx, tag, 1.0) + 26
            tx = min(x + w - tag_w - 8, nx + 22)
            ty = max(y + 8, ny - 50)
            rounded(ctx, tx, ty, tag_w, 26, 5)
            ctx.set_source_rgba(0.01, 0.05, 0.06, 0.82)
            ctx.fill_preserve()
            ctx.set_source_rgba(*tone, 0.55)
            ctx.set_line_width(1.0)
            ctx.stroke()
            line(ctx, [(tx + 7, ty + 7), (tx + 7, ty + 19)],
                 (*tone, 1.0), 3.0)
            label(ctx, tag, tx + 16, ty + 13, 15, (0.88, 0.96, 0.97, 0.96),
                  align="left", spacing=1.0, engraved=False)


def knob_angle(gain):
    low, high = GAIN_RANGE
    fraction = (gain - low) / (high - low)
    start, end = KNOB_DEGREES
    return math.radians(start + fraction * (end - start))


def draw_knob(ctx, index, band, rng, dynamic=True):
    cx, cy, R = KNOB_X[index], KNOB_Y, KNOB_RADIUS
    tone = band["tone"]
    selected = dynamic and index == SELECTED
    angle = knob_angle(band["gain"])
    zero = knob_angle(0.0)

    # Engraved scale: a tick every 2.5 dB, figures at the exact end stops.
    for step in range(13):
        tick = knob_angle(GAIN_RANGE[0] + step * 2.5)
        major = step % 2 == 0
        r0, r1 = (R * 1.115, R * 1.255) if major else (R * 1.135, R * 1.205)
        points = [(cx + r0 * math.cos(tick), cy + r0 * math.sin(tick)),
                  (cx + r1 * math.cos(tick), cy + r1 * math.sin(tick))]
        line(ctx, [(px, py + 1.2) for px, py in points],
             (0, 0, 0, 0.5), 2.6 if major else 1.6)
        line(ctx, points, (0.86, 0.89, 0.88, 0.80 if major else 0.46),
             2.2 if major else 1.3)
    for value, text in ((-15.0, "-15"), (0.0, "0"), (15.0, "+15")):
        tick = knob_angle(value)
        radius = R * (1.40 if value else 1.36)
        label(ctx, text, cx + radius * math.cos(tick),
              cy + radius * math.sin(tick), 18,
              (0.88, 0.90, 0.88, 0.86), spacing=0.5)

    # Recessed value track with the band colour lit from 0 dB to the value.
    track = R * 1.05
    ctx.new_path()
    ctx.arc(cx, cy, track, knob_angle(GAIN_RANGE[0]),
            knob_angle(GAIN_RANGE[1]))
    ctx.set_source_rgba(0.0, 0.0, 0.0, 0.55)
    ctx.set_line_width(5.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    start, end = sorted((zero, angle))

    def value_arc(layer):
        layer.new_path()
        layer.arc(cx, cy, track, start, end)
        layer.set_source_rgba(*tone, 1.0)
        layer.set_line_width(4.0)
        layer.set_line_cap(cairo.LINE_CAP_ROUND)
        layer.stroke()

    if dynamic:
        paint_layer(ctx, blurred(value_arc, 5), 0.8)
        value_arc(ctx)

    if selected:
        def ring(layer):
            layer.new_path()
            layer.arc(cx, cy, R * 1.02, 0, math.tau)
            layer.set_source_rgba(*tone, 1.0)
            layer.set_line_width(7.0)
            layer.stroke()
        paint_layer(ctx, blurred(ring, 12), 0.55)

    # Cast and contact shadows.
    def shadow(layer):
        circle(layer, cx + 7, cy + 14, R * 0.99, (0, 0, 0, 0.85))

    paint_layer(ctx, blurred(shadow, 12), 0.9)
    circle(ctx, cx + 1.5, cy + 3.5, R * 1.0, (0, 0, 0, 0.55))

    # Skirt: a dark machined flange with a lit upper rim.
    circle(ctx, cx, cy, R, vgradient(cy - R, cy + R, (
        (0.0, (0.330, 0.365, 0.415, 1)),
        (0.35, (0.165, 0.185, 0.215, 1)),
        (1.0, (0.045, 0.052, 0.064, 1)))))
    ctx.new_path()
    ctx.arc(cx, cy, R - 1.0, 0, math.tau)
    ctx.set_source(vgradient(cy - R, cy + R, (
        (0.0, (0.95, 0.97, 1.0, 0.55)),
        (0.45, (0.95, 0.97, 1.0, 0.04)),
        (1.0, (0.0, 0.0, 0.0, 0.5)))))
    ctx.set_line_width(1.6)
    ctx.stroke()

    # Fluted grip: each concave flute is shaded from its surface normal.
    flutes = 30
    outer, inner = R * 0.925, R * 0.66

    def scallop_path(radius, depth):
        ctx.new_path()
        for step in range(flutes * 12 + 1):
            theta = math.tau * step / (flutes * 12)
            r = radius - depth * (0.5 - 0.5 * math.cos(flutes * theta))
            point = (cx + r * math.cos(theta), cy + r * math.sin(theta))
            if step == 0:
                ctx.move_to(*point)
            else:
                ctx.line_to(*point)
        ctx.close_path()

    ctx.save()
    scallop_path(outer, R * 0.035)
    ctx.clip()
    for flute in range(flutes):
        base = math.tau * flute / flutes
        span = math.tau / flutes
        for part in range(6):
            a0 = base + span * part / 6.0
            a1 = base + span * (part + 1) / 6.0
            middle = (a0 + a1) / 2.0
            normal = middle + math.radians(62.0) * ((part + 0.5) / 3.0 - 1.0)
            facing = max(0.0, math.cos(normal - LIGHT))
            back = max(0.0, math.cos(normal - LIGHT - math.pi))
            value = 0.105 + 0.36 * facing ** 1.6 + 0.30 * facing ** 18 \
                - 0.05 * back
            ctx.new_path()
            ctx.move_to(cx + inner * math.cos(a0), cy + inner * math.sin(a0))
            ctx.arc(cx, cy, R, a0, a1 + 0.002)
            ctx.line_to(cx + inner * math.cos(a1), cy + inner * math.sin(a1))
            ctx.close_path()
            ctx.set_source_rgba(value * 0.94, value * 1.0, value * 1.10, 1)
            ctx.fill()
    # Chamfer: the grip falls away toward its edge.
    chamfer = cairo.RadialGradient(cx, cy, inner, cx, cy, outer)
    chamfer.add_color_stop_rgba(0.0, 1, 1, 1, 0.07)
    chamfer.add_color_stop_rgba(0.55, 0, 0, 0, 0.0)
    chamfer.add_color_stop_rgba(1.0, 0, 0, 0, 0.42)
    ctx.rectangle(cx - R, cy - R, R * 2, R * 2)
    ctx.set_source(chamfer)
    ctx.fill()
    ctx.restore()
    scallop_path(outer, R * 0.035)
    ctx.set_source_rgba(0.0, 0.0, 0.0, 0.65)
    ctx.set_line_width(1.2)
    ctx.stroke()

    # Anodized band-colour collar around the spun cap.
    collar, cap = R * 0.685, R * 0.605
    circle(ctx, cx, cy, collar + 1.5, (0, 0, 0, 0.7))
    circle(ctx, cx, cy, collar, vgradient(cy - collar, cy + collar, (
        (0.0, tuple(min(1.0, part * 1.18 + 0.10) for part in tone) + (1,)),
        (0.55, (*tone, 1.0)),
        (1.0, tuple(part * 0.45 for part in tone) + (1,)))))
    circle(ctx, cx, cy, cap + 1.2, (0, 0, 0, 0.6))

    # Spun aluminium cap: base dish, anisotropic highlights, lathe rings.
    circle(ctx, cx, cy, cap, radial(cx, cy, cap, (
        (0.0, (0.90, 0.92, 0.94, 1)),
        (0.50, (0.70, 0.73, 0.77, 1)),
        (1.0, (0.40, 0.43, 0.48, 1)))))
    ctx.save()
    ctx.new_path()
    ctx.arc(cx, cy, cap, 0, math.tau)
    ctx.clip()
    wedges = 180
    for wedge in range(wedges):
        a0 = math.tau * wedge / wedges
        a1 = a0 + math.tau / wedges + 0.004
        lobe = math.cos(2.0 * ((a0 + a1) / 2.0 - LIGHT))
        ctx.new_path()
        ctx.move_to(cx, cy)
        ctx.arc(cx, cy, cap, a0, a1)
        ctx.close_path()
        if lobe > 0:
            ctx.set_source_rgba(1, 1, 1, 0.20 * lobe ** 3)
        else:
            ctx.set_source_rgba(0.0, 0.02, 0.05, 0.16 * (-lobe) ** 2)
        ctx.fill()
    radius = 2.0
    while radius < cap:
        ctx.new_path()
        ctx.arc(cx, cy, radius, 0, math.tau)
        bright = rng.random() < 0.5
        ctx.set_source_rgba(*((1, 1, 1) if bright else (0, 0, 0)),
                            0.03 + rng.random() * 0.05)
        ctx.set_line_width(0.6)
        ctx.stroke()
        radius += 1.1 + rng.random() * 1.2
    ctx.restore()
    ctx.new_path()
    ctx.arc(cx, cy, cap - 0.8, 0, math.tau)
    ctx.set_source(vgradient(cy - cap, cy + cap, (
        (0.0, (1.0, 1.0, 1.0, 0.65)),
        (0.5, (1.0, 1.0, 1.0, 0.05)),
        (1.0, (0.0, 0.0, 0.0, 0.45)))))
    ctx.set_line_width(1.4)
    ctx.stroke()

    # Pointer: engraved line on the cap, white index across the flutes.
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    if dynamic:
        line(ctx, [(cx + cap * 0.16 * cos_a + 0.8,
                    cy + cap * 0.16 * sin_a + 1.2),
                   (cx + cap * 0.92 * cos_a + 0.8,
                    cy + cap * 0.92 * sin_a + 1.2)],
             (1.0, 1.0, 1.0, 0.50), 2.0)
        line(ctx, [(cx + cap * 0.16 * cos_a, cy + cap * 0.16 * sin_a),
                   (cx + cap * 0.92 * cos_a, cy + cap * 0.92 * sin_a)],
             (0.08, 0.09, 0.11, 0.95), 4.2)
        line(ctx, [(cx + R * 0.70 * cos_a + 1,
                    cy + R * 0.70 * sin_a + 1.5),
                   (cx + R * 0.96 * cos_a + 1,
                    cy + R * 0.96 * sin_a + 1.5)],
             (0.0, 0.0, 0.0, 0.6), 6.4)
        line(ctx, [(cx + R * 0.70 * cos_a, cy + R * 0.70 * sin_a),
                   (cx + R * 0.96 * cos_a, cy + R * 0.96 * sin_a)],
             (0.98, 0.97, 0.93, 1.0), 5.2)

    def specular(layer):
        layer.save()
        layer.translate(cx - cap * 0.30, cy - cap * 0.36)
        layer.scale(1.0, 0.62)
        layer.rotate(-0.55)
        circle(layer, 0, 0, cap * 0.42, (1, 1, 1, 0.55))
        layer.restore()

    paint_layer(ctx, blurred(specular, 7), 0.8)

    if not dynamic:
        return

    # Readout: the knob's own gain first, its band's frequency and state below.
    label(ctx, "%+.1f dB" % band["gain"], cx, cy + R + 30, 21,
          (0.94, 0.95, 0.92, 0.97 if selected else 0.90), spacing=0.8)
    detail = "%.0f Hz   %s" % (band["freq"], MODE_TEXT[band["shape"]])
    font(ctx, 16, True)
    detail_w = text_width(ctx, detail, 1.2)
    led_x = cx - (detail_w + 18) / 2.0 + 5
    led_y = cy + R + 60

    def led(layer):
        circle(layer, led_x, led_y, 6.5, (*tone, 1.0))

    paint_layer(ctx, blurred(led, 5), 0.6)
    circle(ctx, led_x, led_y, 5.8, (0, 0, 0, 0.7))
    circle(ctx, led_x, led_y, 4.6, radial(led_x, led_y, 4.6, (
        (0.0, (1, 1, 0.95, 1)), (0.4, (*tone, 1.0)),
        (1.0, tuple(part * 0.6 for part in tone) + (1,)))))
    label(ctx, detail, led_x + 13, led_y, 16, (0.66, 0.74, 0.78, 0.86),
          align="left", spacing=1.2)


def draw_lamp(ctx, active=True):
    lx, ly, r = LAMP
    label(ctx, "POWER", lx, ly - r - 20, 15, (0.80, 0.84, 0.86, 0.80),
          spacing=2.4)

    def shadow(layer):
        circle(layer, lx + 2, ly + 5, r + 1, (0, 0, 0, 0.9))

    paint_layer(ctx, blurred(shadow, 5), 0.8)
    circle(ctx, lx, ly, r, radial(lx, ly, r, (
        (0.0, (0.92, 0.94, 0.96, 1)),
        (0.55, (0.55, 0.59, 0.64, 1)),
        (1.0, (0.18, 0.20, 0.24, 1)))))
    circle(ctx, lx, ly, r * 0.76, (0.02, 0.022, 0.026, 1))

    if active:
        def halo(layer):
            circle(layer, lx, ly, r * 0.9, (1.0, 0.66, 0.18, 1.0))

        paint_layer(ctx, blurred(halo, 14), 0.9)
        circle(ctx, lx, ly, r * 0.62, radial(lx, ly, r * 0.62, (
            (0.0, (1.0, 0.95, 0.72, 1)),
            (0.45, (1.0, 0.68, 0.18, 1)),
            (1.0, (0.62, 0.30, 0.05, 1)))))
        circle(ctx, lx - r * 0.2, ly - r * 0.24, r * 0.16,
               (1, 1, 0.92, 0.85))


def render(output, faceplate=False):
    rng = random.Random(20260925)
    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, WIDTH, HEIGHT)
    ctx = cairo.Context(surface)
    draw_background(ctx)
    draw_rack_shadow(ctx)
    draw_plate(ctx, rng)
    surface.flush()
    stride = surface.get_stride()
    data = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape(
        HEIGHT, stride)[:, :WIDTH * 4].reshape(HEIGHT, WIDTH, 4)
    grained = pixel_grain(
        Image.fromarray(np.ascontiguousarray(data[:, :, 2::-1]), "RGB"),
        20260925)
    bgra = np.dstack([np.asarray(grained)[:, :, ::-1],
                      np.full((HEIGHT, WIDTH), 255, dtype=np.uint8)])
    base = bytearray(np.ascontiguousarray(bgra).tobytes())
    surface = cairo.ImageSurface.create_for_data(
        base, cairo.FORMAT_RGB24, WIDTH, HEIGHT, WIDTH * 4)
    ctx = cairo.Context(surface)
    for sx, sy in SCREWS:
        draw_screw(ctx, sx, sy)
    draw_heading(ctx, selected=None if faceplate else SELECTED)
    draw_screen(ctx, rng, dynamic=not faceplate)
    for index, band in enumerate(BANDS):
        draw_knob(ctx, index, band, rng, dynamic=not faceplate)
    draw_lamp(ctx, active=not faceplate)
    surface.flush()
    data = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape(
        HEIGHT, WIDTH, 4)
    image = Image.fromarray(np.ascontiguousarray(data[:, :, 2::-1]), "RGB")
    if faceplate:
        x, y, width, height = RACK
        image = image.crop((x, y, x + width, y + height))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, optimize=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", nargs="?", type=Path, default=OUTPUT)
    parser.add_argument(
        "--faceplate", action="store_true",
        help="render the blank runtime faceplate instead of the reference")
    args = parser.parse_args(argv)
    output = args.output
    if args.faceplate and output == OUTPUT:
        output = FACEPLATE_OUTPUT
    render(output, faceplate=args.faceplate)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
