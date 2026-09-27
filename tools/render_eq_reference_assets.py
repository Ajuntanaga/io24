#!/usr/bin/env python3
"""Build deterministic EQ calibration layers and value-free faceplates.

The canonical full references stay untouched.  For each rack this tool emits:

* an exact cropped underlay for pixel comparison;
* a transparent landmark overlay with every load-bearing measured node; and
* for Passive/Vintage, a production faceplate with illustrative controls,
  response trace, and lamp removed so live protocol values can be drawn once.

Run from any directory:

    python3 tools/render_eq_reference_assets.py
"""

import argparse
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import io24_eq_reference as geometry  # noqa: E402

DESIGN = ROOT / "docs" / "design"
FONT_CANDIDATES = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
)


def _font(size=18):
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _crop_reference(art):
    source = Image.open(DESIGN / art["filename"]).convert("RGB")
    x, y, width, height = art["rack_crop"]
    return source.crop((x, y, x + width, y + height))


def _control_mask(model, art):
    """Mask every illustrative, parameter-bearing control inscription."""
    width, height = art["rack_crop"][2:]
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    for x, y, region_width, region_height in art["control_clear_regions"]:
        draw.rectangle((x, y, x + region_width, y + region_height), fill=255)
    lx, ly, radius = art["lamp"]
    reach = radius * 2.35
    draw.ellipse((lx - reach, ly - reach, lx + reach, ly + reach), fill=255)
    sx, sy, sw, sh = art["screen"]
    draw.rectangle((sx - 4, sy - 4, sx + sw + 4, sy + sh + 4), fill=0)
    for cx, cy, radius in art["screws"]:
        keep = radius + 8
        draw.ellipse((cx - keep, cy - keep, cx + keep, cy + keep), fill=0)
    for x1, y1, x2, y2 in art.get("dividers", ()):
        draw.line((x1, y1, x2, y2), fill=0, width=9)
    return mask


def _plate_fill(image, mask, model):
    """Replace masked controls with local plate colour and fine deterministic grain."""
    source = np.asarray(image, dtype=np.float32)
    selected = np.asarray(mask, dtype=np.uint8) > 0
    height, width = selected.shape
    art = geometry.rack(model)
    ear = art["ear"]
    screen = art["screen"]
    sx, sy, sw, sh = screen

    # A robust upper-middle percentile finds the actual plate rather than the
    # black knob shadows that dominate some rows. Exclude the screen, then
    # smooth the resulting one-pixel-wide vertical material sample.
    plate_samples = np.concatenate((
        source[:, ear:max(ear + 1, sx - 8)],
        source[:, min(width - ear, sx + sw + 8):width - ear],
    ), axis=1)
    row_colours = np.percentile(plate_samples, 64, axis=1)
    strip = Image.fromarray(
        np.clip(row_colours, 0, 255).astype(np.uint8)[:, None, :], "RGB")
    strip = strip.filter(ImageFilter.GaussianBlur(13))
    row_colours = np.asarray(strip, dtype=np.float32)[:, 0, :]

    prepared = source.copy()
    prepared[selected] = np.repeat(
        row_colours[:, None, :], width, axis=1)[selected]
    prepared_image = Image.fromarray(
        np.clip(prepared, 0, 255).astype(np.uint8), "RGB")
    smooth = np.asarray(
        prepared_image.filter(ImageFilter.GaussianBlur(7.0)),
        dtype=np.float32)

    # Fine, seeded grain prevents the cleared areas reading as flat patches.
    seed = 20260925 if model == "passive" else 20260926
    rng = np.random.default_rng(seed)
    grain = rng.normal(0.0, 1.35, source.shape[:2])[:, :, None]
    fill = np.clip(smooth + grain, 0, 255)
    alpha = np.asarray(mask.filter(ImageFilter.GaussianBlur(3.0)),
                       dtype=np.float32)[:, :, None] / 255.0
    result = source * (1.0 - alpha) + fill * alpha

    # Mask feathering must never soften static rack hardware.  Restore those
    # pixels from the canonical crop after the value-bearing regions have
    # been blended.  This keeps screws, dividers and the display surround
    # byte-identical while allowing the live controls to occupy clean plate.
    restore = Image.new("L", (width, height), 0)
    restore_draw = ImageDraw.Draw(restore)
    sx, sy, sw, sh = art["screen"]
    restore_draw.rectangle((sx - 4, sy - 4, sx + sw + 4, sy + sh + 4),
                           fill=255)
    for cx, cy, radius in art["screws"]:
        keep = radius * 2.25
        restore_draw.ellipse((cx - keep, cy - keep,
                              cx + keep, cy + keep), fill=255)
    for x1, y1, x2, y2 in art.get("dividers", ()):
        restore_draw.line((x1, y1, x2, y2), fill=255, width=13)
    restored = np.asarray(restore, dtype=np.uint8) > 0
    result[restored] = source[restored]
    return Image.fromarray(np.clip(result, 0, 255).astype(np.uint8), "RGB")


def _blank_reference_plot(image, art, model):
    """Clear state-bearing plot pixels; GTK restores the calibrated grid."""
    source = np.asarray(image, dtype=np.float32)
    x, y, width, height = art["plot"]
    plot = source[y:y + height, x:x + width]
    # The lower quartile rejects the bright cyan trace, grid, and lettering
    # while retaining the glass's exact vertical tone. A tiny seeded grain
    # prevents a synthetic flat rectangle at native resolution.
    row_colours = np.percentile(plot, 24, axis=1)
    strip = Image.fromarray(
        np.clip(row_colours, 0, 255).astype(np.uint8)[:, None, :], "RGB")
    strip = strip.filter(ImageFilter.GaussianBlur(9))
    row_colours = np.asarray(strip, dtype=np.float32)[:, 0, :]
    cleaned = np.repeat(row_colours[:, None, :], width, axis=1)
    rng = np.random.default_rng(20260930 if model == "passive" else 20261001)
    cleaned = np.clip(
        cleaned + rng.normal(0.0, .55, (height, width, 1)), 0, 255)
    result = source.copy()
    result[y:y + height, x:x + width] = cleaned
    return Image.fromarray(np.clip(result, 0, 255).astype(np.uint8), "RGB")


def _node_overlay(model, art):
    width, height = art["rack_crop"][2:]
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    font = _font(17)
    small = _font(14)

    # A low-opacity 100 px grid makes a mismatch measurable at a glance.
    for x in range(0, width, 100):
        draw.line((x, 0, x, height), fill=(125, 190, 255, 45), width=1)
        if x:
            draw.text((x + 3, 3), str(x), font=small,
                      fill=(180, 215, 255, 150))
    for y in range(0, height, 100):
        draw.line((0, y, width, y), fill=(125, 190, 255, 45), width=1)
        if y:
            draw.text((3, y + 2), str(y), font=small,
                      fill=(180, 215, 255, 150))

    for x, y, rect_width, rect_height in art["ears"]:
        draw.rectangle((x, y, x + rect_width - 1, y + rect_height - 1),
                       outline=(90, 255, 155, 220), width=3)
    for x, y, rect_width, rect_height in art["slots"]:
        draw.rectangle((x, y, x + rect_width, y + rect_height),
                       outline=(225, 130, 255, 210), width=2)
    for cx, cy, radius in art["screws"]:
        draw.ellipse((cx - radius, cy - radius,
                      cx + radius, cy + radius),
                     outline=(225, 130, 255, 220), width=2)

    for key in ("screen", "frame", "gasket", "glass", "plot"):
        if key not in art:
            continue
        x, y, rect_width, rect_height = art[key]
        colour = (0, 245, 255, 235) if key == "plot" else \
            (90, 170, 255, 190)
        draw.rectangle((x, y, x + rect_width, y + rect_height),
                       outline=colour, width=3 if key == "plot" else 2)
        draw.text((x + 5, y + 4), key.upper(), font=small,
                  fill=(225, 250, 255, 235),
                  stroke_width=2, stroke_fill=(0, 20, 28, 220))

    for field, (cx, cy, radius) in art["controls"].items():
        draw.ellipse((cx - radius, cy - radius,
                      cx + radius, cy + radius),
                     outline=(255, 205, 55, 240), width=3)
        draw.line((cx - radius - 12, cy, cx + radius + 12, cy),
                  fill=(255, 205, 55, 220), width=2)
        draw.line((cx, cy - radius - 12, cx, cy + radius + 12),
                  fill=(255, 205, 55, 220), width=2)
        label = "%s  %d,%d  r%d" % (field, cx, cy, radius)
        bbox = draw.textbbox((0, 0), label, font=font, stroke_width=1)
        label_width = bbox[2] - bbox[0]
        label_x = max(4, min(width - label_width - 8, cx - label_width / 2))
        label_y = max(4, min(height - 24, cy + radius + 8))
        draw.rounded_rectangle((label_x - 4, label_y - 2,
                                label_x + label_width + 4, label_y + 21),
                               radius=4, fill=(0, 12, 18, 205))
        draw.text((label_x, label_y), label, font=font,
                  fill=(255, 230, 100, 255))

    # Standard's live-only Q rotaries and faceplate buttons deliberately do
    # not exist in the original illustrative bitmap. They still belong in the
    # calibration overlay so the runtime additions can be aligned exactly.
    for index, (cx, cy) in enumerate(zip(
            art.get("q_knob_x", ()),
            (art.get("q_knob_y"),) * len(art.get("q_knob_x", ())))):
        radius = art["q_knob_radius"]
        draw.ellipse((cx - radius, cy - radius,
                      cx + radius, cy + radius),
                     outline=(95, 245, 255, 245), width=3)
        draw.line((cx - radius - 8, cy, cx + radius + 8, cy),
                  fill=(95, 245, 255, 220), width=2)
        draw.line((cx, cy - radius - 8, cx, cy + radius + 8),
                  fill=(95, 245, 255, 220), width=2)
        draw.text((cx - 16, cy + radius + 5), "Q%d" % (index + 1),
                  font=small, fill=(150, 250, 255, 245))
    for index, (cx, cy, radius) in enumerate(art.get("band_power", ())):
        draw.ellipse((cx - radius, cy - radius,
                      cx + radius, cy + radius),
                     outline=(255, 120, 210, 245), width=2)
        draw.text((cx - 8, cy - 25), "B%d" % (index + 1), font=small,
                  fill=(255, 175, 225, 245))
    for index, rectangle in enumerate(art.get("band_mode", ())):
        x, y, rect_width, rect_height = rectangle
        draw.rectangle((x, y, x + rect_width, y + rect_height),
                       outline=(150, 210, 255, 235), width=2)
        draw.text((x + 3, y + 3), "M%d" % (index + 1), font=small,
                  fill=(185, 225, 255, 245))
    if "flatten" in art:
        x, y, rect_width, rect_height = art["flatten"]
        draw.rectangle((x, y, x + rect_width, y + rect_height),
                       outline=(80, 255, 190, 245), width=2)
        draw.text((x + 3, y + 3), "FLAT", font=small,
                  fill=(135, 255, 210, 245))

    lx, ly, radius = art["lamp"]
    draw.ellipse((lx - radius, ly - radius, lx + radius, ly + radius),
                 outline=(255, 110, 35, 245), width=4)
    draw.line((lx - radius - 10, ly, lx + radius + 10, ly),
              fill=(255, 110, 35, 230), width=2)
    draw.line((lx, ly - radius - 10, lx, ly + radius + 10),
              fill=(255, 110, 35, 230), width=2)
    draw.text((max(4, lx - 115), max(4, ly - radius - 28)),
              "POWER %d,%d r%d" % (lx, ly, radius), font=small,
              fill=(255, 170, 95, 255), stroke_width=2,
              stroke_fill=(25, 8, 0, 230))

    for x1, y1, x2, y2 in art.get("dividers", ()):
        draw.line((x1, y1, x2, y2), fill=(120, 255, 175, 220), width=3)

    draw.rectangle((0, 0, width - 1, height - 1),
                   outline=(255, 55, 150, 235), width=3)
    draw.text((width // 2 - 100, height - 25),
              "%s  %d x %d" % (model.upper(), width, height),
              font=font, fill=(255, 255, 255, 245), stroke_width=2,
              stroke_fill=(0, 0, 0, 230))
    return overlay


def render_model(model, output_dir=DESIGN):
    art = geometry.rack(model)
    cropped = _crop_reference(art)
    underlay = output_dir / art["calibration_underlay_filename"]
    nodes = output_dir / art["calibration_nodes_filename"]
    cropped.save(underlay, optimize=True)
    _node_overlay(model, art).save(nodes, optimize=True)

    outputs = [underlay, nodes]
    if model in ("passive", "vintage"):
        faceplate = _plate_fill(cropped, _control_mask(model, art), model)
        faceplate = _blank_reference_plot(faceplate, art, model)
        faceplate_path = output_dir / art["faceplate_filename"]
        faceplate.save(faceplate_path, optimize=True)
        outputs.append(faceplate_path)
    return outputs


def render_all(output_dir=DESIGN):
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for model in ("standard", "passive", "vintage"):
        outputs.extend(render_model(model, output_dir))
    return outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, default=DESIGN)
    args = parser.parse_args(argv)
    for output in render_all(args.output_dir):
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
