#!/usr/bin/env python3
"""Split the approved transparent EQ knob board into runtime knob assets."""

from pathlib import Path
from collections import deque

from PIL import Image, ImageEnhance, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs" / "design"
BOARD = DESIGN / "eq-knob-reference-board.png"

CELLS = (
    ("standard-gain-knob.png", 0, 0, True),
    ("standard-q-knob.png", 1, 0, True),
    ("passive-continuous-knob.png", 2, 0, False),
    ("passive-selector-knob.png", 3, 0, False),
    ("vintage-low-knob.png", 0, 1, False),
    ("vintage-lowmid-knob.png", 1, 1, False),
    ("vintage-himid-knob.png", 2, 1, False),
    ("vintage-high-knob.png", 3, 1, False),
)


def extract(image, column, row, neutral=False):
    cell_w, cell_h = image.width // 4, image.height // 2
    cell = image.crop((column * cell_w, row * cell_h,
                       (column + 1) * cell_w, (row + 1) * cell_h))
    alpha = cell.getchannel("A")
    pixels = alpha.load()
    seen = set()
    components = []
    for y in range(alpha.height):
        for x in range(alpha.width):
            if pixels[x, y] <= 8 or (x, y) in seen:
                continue
            queue = deque(((x, y),))
            seen.add((x, y))
            component = []
            while queue:
                px, py = queue.popleft()
                component.append((px, py))
                for nx, ny in ((px - 1, py), (px + 1, py),
                               (px, py - 1), (px, py + 1)):
                    if 0 <= nx < alpha.width and 0 <= ny < alpha.height and \
                            pixels[nx, ny] > 8 and (nx, ny) not in seen:
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            components.append(component)
    keep = set(max(components, key=len))
    cleaned = Image.new("L", alpha.size)
    cleaned_pixels = cleaned.load()
    for x, y in keep:
        cleaned_pixels[x, y] = pixels[x, y]
    cell.putalpha(cleaned)
    alpha = cleaned
    bounds = alpha.getbbox()
    if bounds is None:
        raise ValueError(f"empty knob cell {column},{row}")
    cell = cell.crop(bounds)
    if neutral:
        alpha = cell.getchannel("A")
        grey = ImageOps.grayscale(cell.convert("RGB"))
        grey = ImageEnhance.Contrast(grey).enhance(1.08)
        cell = Image.merge("RGBA", (grey, grey, grey, alpha))
    side = max(cell.size)
    pad = max(8, round(side * .035))
    square = Image.new("RGBA", (side + pad * 2, side + pad * 2))
    square.alpha_composite(cell, ((square.width - cell.width) // 2,
                                  (square.height - cell.height) // 2))
    return square


def main():
    image = Image.open(BOARD).convert("RGBA")
    for filename, column, row, neutral in CELLS:
        output = DESIGN / filename
        extract(image, column, row, neutral).save(output, optimize=True)
        print(output)


if __name__ == "__main__":
    main()
