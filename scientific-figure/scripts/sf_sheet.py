# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy"]
# ///
"""Contact sheet: many figures (or many review tiles) on one page.

Reviewing figures one file at a time burns attention on opening and comparing. A
sheet puts every panel on a single image so inconsistencies surface immediately:
different font sizes between panels, a colour that drifts, one figure visibly
lighter than its neighbours, an axis label present in three panels and missing in
the fourth.

Each cell is labelled so a finding can name its target.

Usage:
    uv run sf_sheet.py --images figs/*.png --out qa/sheet.png --cols 2
    uv run sf_sheet.py --dir qa/round-1 --out qa/sheet.png --cell 520
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_SHEET_WIDTH = 1600


def collect(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    for pattern in args.images or []:
        candidate = Path(pattern)
        if candidate.is_dir():
            paths.extend(sorted(p for p in candidate.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES))
        elif candidate.exists():
            paths.append(candidate)
        else:
            # Allow shell globs that did not expand.
            paths.extend(sorted(Path().glob(pattern)))
    if args.dir:
        directory = Path(args.dir)
        if directory.is_dir():
            paths.extend(sorted(p for p in directory.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen or resolved.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def build_sheet(paths: list[Path], cols: int, cell: int, pad: int, label_height: int, out: Path) -> dict[str, Any]:
    from PIL import Image, ImageDraw, ImageFont

    if not paths:
        raise ValueError("no images to place on the sheet")

    try:
        font = ImageFont.load_default(size=max(11, cell // 40))
    except Exception:  # older Pillow without the size argument
        font = ImageFont.load_default()

    rows = (len(paths) + cols - 1) // cols
    cell_h = cell + label_height
    sheet_w = cols * cell + (cols + 1) * pad
    sheet_h = rows * cell_h + (rows + 1) * pad
    scale = 1.0
    if sheet_w > MAX_SHEET_WIDTH:
        scale = MAX_SHEET_WIDTH / sheet_w
        sheet_w = MAX_SHEET_WIDTH
        sheet_h = int(sheet_h * scale)

    sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
    draw = ImageDraw.Draw(sheet)
    placed: list[dict[str, Any]] = []

    for index, path in enumerate(paths):
        row, col = divmod(index, cols)
        x = pad + col * (cell + pad)
        y = pad + row * (cell_h + pad)
        cell_w = cell if scale == 1.0 else int(cell * scale)
        cell_hh = cell if scale == 1.0 else int(cell * scale)

        with Image.open(path) as opened:
            image = opened.convert("RGB")
            original = image.size
            image.thumbnail((cell_w, cell_hh), Image.LANCZOS)
            placed_size = image.size
            offset_x = x + (cell_w - placed_size[0]) // 2
            offset_y = y + (cell_hh - placed_size[1]) // 2
            sheet.paste(image, (offset_x, offset_y))

        # Frame the cell so an empty or white figure is still visible as a cell.
        draw.rectangle([x, y, x + cell_w, y + cell_hh], outline=(200, 200, 200), width=1)
        caption = path.name
        if len(caption) > 46:
            caption = caption[:43] + "…"
        draw.text((x + 3, y + cell_hh + 2), caption, fill=(30, 30, 30), font=font)
        placed.append(
            {
                "path": str(path),
                "cell": [row + 1, col + 1],
                "original_size": list(original),
                "placed_size": list(placed_size),
            }
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return {
        "ok": True,
        "sheet": str(out),
        "size": list(sheet.size),
        "cols": cols,
        "rows": rows,
        "count": len(placed),
        "cells": placed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images", nargs="*", default=[], help="image files, directories, or globs")
    parser.add_argument("--dir", help="directory of images to include")
    parser.add_argument("--out", default="qa/sheet.png", help="output sheet path")
    parser.add_argument("--cols", type=int, default=2, help="columns")
    parser.add_argument("--cell", type=int, default=620, help="cell edge in px")
    parser.add_argument("--pad", type=int, default=10, help="padding between cells")
    parser.add_argument("--json", action="store_true", help="JSON only")
    args = parser.parse_args(argv)

    paths = collect(args)
    if not paths:
        print(json.dumps({"ok": False, "error": "no images found"}))
        return 2

    try:
        payload = build_sheet(paths, max(1, args.cols), max(80, args.cell), max(0, args.pad), 18, Path(args.out).resolve())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    if not args.json:
        print(f"contact sheet: {payload['count']} image(s) -> {payload['sheet']}", file=sys.stderr)
        for cell in payload["cells"]:
            print(f"  cell {cell['cell'][0]},{cell['cell'][1]}  {Path(cell['path']).name}", file=sys.stderr)
        print(f"sheet size {payload['size'][0]}x{payload['size'][1]} px", file=sys.stderr)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
