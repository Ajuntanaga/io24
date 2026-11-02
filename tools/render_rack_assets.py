#!/usr/bin/env python3
"""Deterministically compile reference-rack images from the rack manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import io24_rack_reference


DESIGN = ROOT / "docs" / "design"
_PNG_SAVE = {"format": "PNG", "compress_level": 9, "optimize": False}

# Five-bit-wide, seven-row glyphs keep generated PNGs independent of host
# fonts, Pillow's bundled font version, font discovery, and fallback behavior.
_BITMAP_GLYPHS = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    "-": (0, 0, 0, 31, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 12, 12),
    "0": (14, 17, 19, 21, 25, 17, 14),
    "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 2, 4, 8, 31),
    "3": (30, 1, 1, 14, 1, 1, 30),
    "4": (2, 6, 10, 18, 31, 2, 2),
    "5": (31, 16, 16, 30, 1, 1, 30),
    "6": (14, 16, 16, 30, 17, 17, 14),
    "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (14, 17, 17, 15, 1, 1, 14),
    "A": (14, 17, 17, 31, 17, 17, 17),
    "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14),
    "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15),
    "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14),
    "J": (7, 2, 2, 2, 2, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17),
    "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 21, 10),
    "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4),
    "Z": (31, 1, 2, 4, 8, 16, 31),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(draw, xy, value, *, size, fill, bold=False, anchor="mm"):
    del bold
    if anchor != "mm":
        raise ValueError("bitmap text supports only the mm anchor")
    value = str(value).upper()
    unknown = set(value).difference(_BITMAP_GLYPHS)
    if unknown:
        raise ValueError("unsupported bitmap glyphs: %s" % "".join(sorted(unknown)))
    scale = max(1, int(size) // 7)
    width = max(0, (len(value) * 6 - 1) * scale)
    height = 7 * scale
    left = int(round(xy[0] - width / 2.0))
    top = int(round(xy[1] - height / 2.0))
    for character_index, character in enumerate(value):
        for row, bits in enumerate(_BITMAP_GLYPHS[character]):
            for column in range(5):
                if bits & (1 << (4 - column)):
                    x = left + (character_index * 6 + column) * scale
                    y = top + row * scale
                    draw.rectangle(
                        (x, y, x + scale - 1, y + scale - 1), fill=fill)


def _material(spec, design_root: Path, size: Tuple[int, int]) -> Image.Image:
    source_path = design_root / spec["material_source"]
    source = Image.open(source_path).convert("RGB")
    x, y, width, height = spec["material_crop"]
    box = (int(x), int(y), int(x + width), int(y + height))
    if box[0] < 0 or box[1] < 0 or box[2] > source.width or box[3] > source.height:
        raise ValueError("material crop exceeds source bounds")
    tile = source.crop(box)
    if tile.width == 0 or tile.height == 0:
        raise ValueError("material crop is empty")

    tiled = Image.new("RGB", size)
    for row, top in enumerate(range(0, size[1], tile.height)):
        for column, left in enumerate(range(0, size[0], tile.width)):
            sample = tile
            if column % 2:
                sample = ImageOps.mirror(sample)
            if row % 2:
                sample = ImageOps.flip(sample)
            tiled.paste(sample, (left, top))

    pixels = np.asarray(tiled, dtype=np.float32)
    vertical = np.linspace(0.91, 1.03, size[1], dtype=np.float32)[:, None, None]
    pixels *= vertical
    pixels[..., 0] *= 1.08
    pixels[..., 1] *= 0.93
    pixels[..., 2] *= 0.80
    return Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8), "RGB")


def _draw_hardware(draw: ImageDraw.ImageDraw, spec: dict) -> None:
    for x, y, width, height in spec["ears"]:
        draw.rectangle((x, y, x + width - 1, y + height - 1), fill=(20, 23, 24, 255))
    for x, y, width, height in spec["slots"]:
        draw.rounded_rectangle(
            (x, y, x + width - 1, y + height - 1), radius=width // 2,
            fill=(5, 7, 8, 255), outline=(83, 76, 62, 255), width=2)
    for x, y, radius in spec["screws"]:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     fill=(15, 16, 16, 255), outline=(112, 102, 84, 255), width=2)
        draw.line((x - 5, y, x + 5, y), fill=(3, 3, 3, 255), width=2)


def _render_limiter_base(spec: dict, design_root: Path) -> Image.Image:
    width, height = spec["source_size"]
    image = Image.new("RGBA", (width, height), (13, 15, 15, 255))
    panel_x, panel_y, panel_width, panel_height = spec["panel"]
    material = _material(spec, design_root, (panel_width, panel_height)).convert("RGBA")
    image.alpha_composite(material, (panel_x, panel_y))
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_hardware(draw, spec)

    draw.rounded_rectangle(
        (panel_x, panel_y, panel_x + panel_width - 1, panel_y + panel_height - 1),
        radius=8, outline=(154, 125, 78, 190), width=2)
    _text(draw, (700, 44), "VINTAGE LIMITER", size=25,
          fill=(225, 203, 157, 255), bold=True)
    draw.line((515, 45, 550, 45), fill=(176, 143, 88, 220), width=2)
    draw.line((850, 45, 885, 45), fill=(176, 143, 88, 220), width=2)
    _text(draw, (280, 82), "THRESHOLD", size=20,
          fill=(222, 209, 177, 255), bold=True)
    _text(draw, (1120, 82), "RELEASE", size=20,
          fill=(222, 209, 177, 255), bold=True)
    _text(draw, (700, 82), "GAIN REDUCTION", size=16,
          fill=(187, 169, 132, 255), bold=True)

    x, y, display_width, display_height = spec["display"]
    draw.rounded_rectangle(
        (x, y, x + display_width, y + display_height), radius=18,
        fill=(10, 11, 11, 255), outline=(115, 96, 65, 255), width=3)
    draw.rounded_rectangle(
        (x + 15, y + 15, x + display_width - 15, y + display_height - 15),
        radius=10, fill=(6, 15, 15, 255), outline=(33, 53, 50, 255), width=2)

    lamp_x, lamp_y, lamp_radius = spec["lamp"]
    draw.ellipse(
        (lamp_x - lamp_radius, lamp_y - lamp_radius,
         lamp_x + lamp_radius, lamp_y + lamp_radius),
        fill=(12, 13, 12, 255), outline=(135, 108, 65, 255), width=3)
    _text(draw, (lamp_x, lamp_y + 31), "POWER", size=10,
          fill=(183, 167, 133, 255), bold=True)
    return image


def _isolated_knob(spec: dict, design_root: Path) -> Image.Image:
    source = Image.open(design_root / spec["knob_source"]).convert("RGBA")
    source_alpha = source.getchannel("A")
    source_extrema = source_alpha.getextrema()
    if source_extrema[0] != 0 or source_extrema[1] == 0:
        raise ValueError("knob source must contain transparent and visible pixels")
    bounds = source_alpha.getbbox()
    if bounds is None:
        raise ValueError("empty knob mask")
    source = source.crop(bounds)
    cropped_extrema = source.getchannel("A").getextrema()
    if cropped_extrema[0] != 0 or cropped_extrema[1] == 0:
        raise ValueError("cropped knob must contain transparent and visible pixels")
    diameter = int(spec["controls"]["threshold"]["geometry"][2] * 2)
    knob = source.resize((diameter, diameter), Image.Resampling.LANCZOS)
    output_extrema = knob.getchannel("A").getextrema()
    if output_extrema[0] != 0 or output_extrema[1] == 0:
        raise ValueError("compiled knob must contain transparent and visible pixels")
    return knob


def _draw_control_reference(image: Image.Image, control: dict,
                            knob: Image.Image, value: str) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    centre_x, centre_y, radius = control["geometry"]
    start, end = control["sweep"]
    for index in range(11):
        angle = math.radians(start + (end - start) * index / 10.0)
        inner = radius + 10
        outer = radius + (20 if index in (0, 5, 10) else 16)
        x1 = centre_x + math.cos(angle) * inner
        y1 = centre_y + math.sin(angle) * inner
        x2 = centre_x + math.cos(angle) * outer
        y2 = centre_y + math.sin(angle) * outer
        draw.line((x1, y1, x2, y2), fill=(211, 191, 150, 230), width=2)
    image.alpha_composite(
        knob, (int(centre_x - knob.width / 2), int(centre_y - knob.height / 2)))
    pointer_angle = math.radians(
        io24_rack_reference.pointer_angle(control, control["default"]))
    tip = radius * 0.63
    draw = ImageDraw.Draw(image, "RGBA")
    draw.line(
        (centre_x, centre_y,
         centre_x + math.cos(pointer_angle) * tip,
         centre_y + math.sin(pointer_angle) * tip),
        fill=(251, 239, 206, 255), width=5)
    _text(draw, (centre_x, 344), value, size=18,
          fill=(237, 221, 185, 255), bold=True)


def _draw_display_reference(image: Image.Image, spec: dict) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    left, top, width, height = (500, 119, 400, 211)
    for index in range(5):
        y = top + 20 + index * 39
        draw.line((left + 46, y, left + width - 22, y),
                  fill=(45, 79, 73, 170), width=1)
        _text(draw, (left + 28, y), str(index * 5), size=11,
              fill=(146, 171, 158, 255))
    for index in range(15):
        x = left + 58 + index * 20
        bar_height = max(4, 118 - index * 7)
        colour = (92, 210, 155, 235) if index < 10 else (222, 175, 82, 235)
        draw.rounded_rectangle(
            (x, top + 159 - bar_height, x + 11, top + 159),
            radius=3, fill=colour)
    _text(draw, (700, 303), "-6.2 dB", size=20,
          fill=(222, 232, 216, 255), bold=True)


def _render_limiter_reference(spec: dict, design_root: Path = DESIGN) -> Image.Image:
    """Recreate the approved 1400 x 420 limiter composition."""
    base = _render_limiter_base(spec, design_root)
    reference = base.copy()
    knob = _isolated_knob(spec, design_root)
    _draw_control_reference(
        reference, spec["controls"]["threshold"], knob, "-28.00 dB")
    _draw_control_reference(
        reference, spec["controls"]["release"], knob, "0.40 s")
    _draw_display_reference(reference, spec)
    draw = ImageDraw.Draw(reference, "RGBA")
    lamp_x, lamp_y, lamp_radius = spec["lamp"]
    draw.ellipse(
        (lamp_x - lamp_radius + 4, lamp_y - lamp_radius + 4,
         lamp_x + lamp_radius - 4, lamp_y + lamp_radius - 4),
        fill=(247, 150, 36, 255), outline=(255, 222, 130, 255), width=2)
    return reference


def _render_faceplate(reference: Image.Image, base: Image.Image,
                      spec: dict) -> Image.Image:
    faceplate = reference.copy()
    for x, y, width, height in spec["cleanup_regions"]:
        box = (int(x), int(y), int(x + width), int(y + height))
        faceplate.paste(base.crop(box), box)
    return faceplate


def _render_nodes(spec: dict) -> Image.Image:
    overlay = Image.new("RGBA", tuple(spec["source_size"]), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    width, height = spec["source_size"]
    for x in range(0, width, 100):
        draw.line((x, 0, x, height), fill=(50, 170, 210, 60), width=1)
    for y in range(0, height, 100):
        draw.line((0, y, width, y), fill=(50, 170, 210, 60), width=1)
    panel_x, panel_y, panel_width, panel_height = spec["panel"]
    draw.rectangle(
        (panel_x, panel_y, panel_x + panel_width, panel_y + panel_height),
        outline=(255, 210, 80, 230), width=2)
    display_x, display_y, display_width, display_height = spec["display"]
    draw.rectangle(
        (display_x, display_y, display_x + display_width,
         display_y + display_height), outline=(70, 225, 190, 240), width=2)
    for name, control in spec["controls"].items():
        x, y, radius = control["geometry"]
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     outline=(255, 105, 120, 245), width=2)
        draw.line((x - 8, y, x + 8, y), fill=(255, 105, 120, 245), width=1)
        draw.line((x, y - 8, x, y + 8), fill=(255, 105, 120, 245), width=1)
        _text(draw, (x, y - radius - 13), name, size=11,
              fill=(255, 165, 175, 255), bold=True)
    lamp_x, lamp_y, lamp_radius = spec["lamp"]
    draw.ellipse(
        (lamp_x - lamp_radius, lamp_y - lamp_radius,
         lamp_x + lamp_radius, lamp_y + lamp_radius),
        outline=(255, 165, 60, 255), width=2)
    return overlay


def _save_png(image: Image.Image, path: Path) -> None:
    image.save(path, **_PNG_SAVE)


def _validate_dimensions(path: Path, size: Tuple[int, int], mode=None) -> None:
    with Image.open(path) as image:
        if image.size != tuple(size):
            raise ValueError(f"{path.name} has size {image.size}, expected {tuple(size)}")
        if mode is not None and image.mode != mode:
            raise ValueError(f"{path.name} has mode {image.mode}, expected {mode}")
        image.load()


def _validate_change_mask(reference: Image.Image, faceplate: Image.Image,
                          spec: dict) -> None:
    reference_pixels = np.asarray(reference.convert("RGBA"))
    faceplate_pixels = np.asarray(faceplate.convert("RGBA"))
    changed = np.any(reference_pixels != faceplate_pixels, axis=2)
    allowed = np.zeros(changed.shape, dtype=bool)
    for x, y, width, height in spec["cleanup_regions"]:
        x, y, width, height = map(int, (x, y, width, height))
        allowed[y:y + height, x:x + width] = True
        if not changed[y:y + height, x:x + width].any():
            raise ValueError("declared cleanup region contains no changed pixels")
    if np.any(changed & ~allowed):
        raise ValueError("faceplate changed pixels outside declared cleanup regions")


def _manifest_sha256(spec: dict) -> str:
    encoded = json.dumps(
        spec, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compile_rack(rack_id: str, design_root: Path,
                 output_root: Optional[Path] = None) -> dict:
    """Compile one rack into ``output_root`` and return its build receipt."""
    design_root = Path(design_root)
    output_root = design_root if output_root is None else Path(output_root)
    spec = io24_rack_reference.validate_rack(
        io24_rack_reference.rack(rack_id), design_root)
    if rack_id != "limiter":
        raise ValueError("unsupported rack compiler: %s" % rack_id)
    if not output_root.parent.is_dir():
        raise ValueError("output parent does not exist: %s" % output_root.parent)

    with tempfile.TemporaryDirectory(
            dir=output_root.parent, prefix=f".{rack_id}-rack-assets-") as temp:
        stage = Path(temp)
        reference = _render_limiter_reference(spec, design_root)
        base = _render_limiter_base(spec, design_root)
        faceplate = _render_faceplate(reference, base, spec)
        nodes = _render_nodes(spec)
        knob = _isolated_knob(spec, design_root)

        reference_path = stage / spec["source"]
        faceplate_path = stage / spec["output"]
        underlay_path = stage / spec["calibration_underlay"]
        nodes_path = stage / spec["calibration_nodes"]
        knob_path = stage / spec["knob_output"]
        _save_png(reference, reference_path)
        _save_png(faceplate, faceplate_path)
        shutil.copyfile(reference_path, underlay_path)
        _save_png(nodes, nodes_path)
        _save_png(knob, knob_path)

        _validate_dimensions(reference_path, spec["source_size"], "RGBA")
        _validate_dimensions(faceplate_path, spec["source_size"], "RGBA")
        _validate_dimensions(underlay_path, spec["source_size"], "RGBA")
        _validate_dimensions(nodes_path, spec["source_size"], "RGBA")
        knob_size = int(spec["controls"]["threshold"]["geometry"][2] * 2)
        _validate_dimensions(knob_path, (knob_size, knob_size), "RGBA")
        if Image.open(knob_path).getchannel("A").getbbox() is None:
            raise ValueError("empty compiled knob mask")
        _validate_change_mask(reference, faceplate, spec)

        output_names = (
            spec["output"], spec["calibration_underlay"],
            spec["calibration_nodes"], spec["knob_output"],
        )
        receipt = {
            "rack_id": rack_id,
            "source_sha256": sha256(reference_path),
            "outputs": {name: sha256(stage / name) for name in output_names},
            "manifest_sha256": _manifest_sha256(spec),
        }
        receipt_path = stage / spec["receipt"]
        receipt_path.write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        output_root.mkdir(parents=False, exist_ok=True)
        filenames = (spec["source"],) + tuple(spec["generated"])
        # Save every previous target before publishing anything. On an I/O
        # failure restore replaced targets and remove targets introduced by
        # this transaction. The receipt remains the final successful replace.
        backup = stage / "previous"
        backup.mkdir()
        for filename in filenames:
            target = output_root / filename
            if target.exists():
                shutil.copy2(target, backup / filename)
        published = []
        try:
            for filename in filenames:
                os.replace(stage / filename, output_root / filename)
                published.append(filename)
        except OSError:
            for filename in reversed(published):
                target = output_root / filename
                previous = backup / filename
                if previous.exists():
                    os.replace(previous, target)
                else:
                    target.unlink()
            raise
        return receipt


def _check_rack(rack_id: str, design_root: Path) -> bool:
    spec = io24_rack_reference.rack(rack_id)
    with tempfile.TemporaryDirectory(prefix=f"{rack_id}-rack-check-") as temp:
        generated_root = Path(temp)
        compile_rack(rack_id, design_root, generated_root)
        for filename in (spec["source"],) + tuple(spec["generated"]):
            committed = design_root / filename
            if not committed.is_file() or sha256(committed) != sha256(generated_root / filename):
                print(f"{rack_id} asset mismatch: {filename}", file=sys.stderr)
                return False
    print(f"{rack_id} assets match")
    return True


def main(argv=None, design_root=DESIGN) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rack_id")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        if arguments.check:
            return 0 if _check_rack(arguments.rack_id, design_root) else 1
        receipt = compile_rack(arguments.rack_id, design_root)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
