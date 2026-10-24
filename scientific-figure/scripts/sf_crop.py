# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy"]
# ///
"""Crop figures for visual review, with the model deciding where to look.

The model sees the figure and decides which regions matter; this tool only executes
coordinates. Nothing here assumes the image came from matplotlib — a TikZ render, an
Origin export, a screenshot of someone else's paper all work the same way.

Two-step protocol:

1. ``--overlay`` renders a reference copy with a labelled coordinate grid. The model
   reads that image and writes down the normalized ``[x0, y0, x1, y1]`` of each region
   it wants to inspect (a legend, an axis label, a dense cluster, a suspicious gap).
2. ``--spec`` executes those boxes at a readable scale.

``--auto`` exists for coverage when no judgement has been made yet: it tiles the whole
image mechanically. It is a starting point, not a review strategy — mechanical tiling
spends equal attention everywhere, while defects concentrate in text and dense regions.

Coordinates are normalized to the image: ``[0, 0]`` is the top-left, ``[1, 1]`` the
bottom-right, matching what the overlay prints.

Usage:
    uv run sf_crop.py --image fig.png --overlay -o qa/
    uv run sf_crop.py --image fig.png --spec qa/crops.json -o qa/tiles/
    uv run sf_crop.py --image fig.png --box 0.6,0.05,0.95,0.3 --name legend -o qa/
    uv run sf_crop.py --image fig.png --auto full,grid -o qa/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_TARGET_WIDTH = 1400
MAX_TARGET_WIDTH = 1600
MIN_TARGET_WIDTH = 800
# Beyond this the short side becomes too thin to read even when the long side fits.
MAX_ASPECT = 8.0
# Enlarging past this turns pixels into mush without adding information.
MAX_UPSCALE = 4.0


def parse_box(value: Any, width: int, height: int) -> tuple[int, int, int, int]:
    """Accept ``[x0, y0, x1, y1]`` as normalized fractions or absolute pixels."""
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"box must be 4 numbers, got {value!r}")
    parts = [float(v) for v in value]
    if all(0.0 <= p <= 1.0 for p in parts):
        x0, y0, x1, y1 = parts
        box = (int(x0 * width), int(y0 * height), int(x1 * width), int(y1 * height))
    else:
        box = (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"box has no area: {value!r}")
    return (max(0, x0), max(0, y0), min(width, x1), min(height, y1))


def save_tile(
    image: Any,
    box: tuple[int, int, int, int],
    out_path: Path,
    target_width: int,
    zoom: float = 1.0,
    allow_upscale: bool = True,
) -> dict[str, Any]:
    """Crop, then fit the result into a size an image model can actually read.

    The goal is legibility, not a fixed width. Enlarging cannot add information, so a
    crop already wide enough stays at native resolution; only genuinely small crops are
    upscaled, and never past ``MAX_UPSCALE``. A tall thin strip is unreadable at any
    width, so extreme aspect ratios are capped.
    """
    from PIL import Image

    cropped = image.crop(box)
    crop_w, crop_h = cropped.size
    if crop_w <= 0 or crop_h <= 0:
        raise ValueError("empty crop box")

    long_side = max(crop_w, crop_h)
    if long_side <= target_width:
        base = min(target_width / long_side, MAX_UPSCALE) if allow_upscale else 1.0
    else:
        base = min(1.0, target_width / long_side)
    scale = base * max(zoom, 1.0) if allow_upscale else base

    new_w = max(1, int(round(crop_w * scale)))
    new_h = max(1, int(round(crop_h * scale)))

    aspect = max(new_w, new_h) / max(1, min(new_w, new_h))
    if aspect > MAX_ASPECT:
        limit = max(8, int(min(new_w, new_h) * MAX_ASPECT))
        if new_w > new_h:
            new_w = limit
        else:
            new_h = limit

    if max(new_w, new_h) > MAX_TARGET_WIDTH:
        shrink = MAX_TARGET_WIDTH / max(new_w, new_h)
        new_w = max(1, int(round(new_w * shrink)))
        new_h = max(1, int(round(new_h * shrink)))

    if (new_w, new_h) != (crop_w, crop_h):
        cropped = cropped.resize((new_w, new_h), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(out_path)
    return {
        "path": str(out_path),
        "source_box_px": list(box),
        "source_size": [crop_w, crop_h],
        "size": [new_w, new_h],
        "scale": round(new_w / crop_w, 3) if crop_w else 1.0,
    }


def render_overlay(image: Any, out_path: Path, steps: int = 10, label_every: int = 1) -> dict[str, Any]:
    """Draw a labelled normalized coordinate grid so the model can read off boxes.

    Without this the model has to estimate positions from a bare image, and estimates
    drift by several percent — enough to cut a label in half. The grid turns "about a
    third from the left" into a number it can copy.
    """
    from PIL import ImageDraw, ImageFont

    width, height = image.size
    canvas = image.copy()
    draw = ImageDraw.Draw(canvas, "RGBA")
    try:
        font = ImageFont.load_default(size=max(12, min(width, height) // 60))
    except Exception:
        font = ImageFont.load_default()

    faint = (255, 0, 0, 90)
    strong = (255, 0, 0, 180)
    label_bg = (255, 255, 255, 215)

    for index in range(steps + 1):
        frac = index / steps
        x = int(frac * (width - 1))
        y = int(frac * (height - 1))
        draw.line([(x, 0), (x, height)], fill=strong if index % 5 == 0 else faint, width=1)
        draw.line([(0, y), (width, y)], fill=strong if index % 5 == 0 else faint, width=1)

    if label_every > 0:
        for index in range(0, steps + 1, label_every):
            frac = index / steps
            x = min(int(frac * (width - 1)), width - 1)
            y = min(int(frac * (height - 1)), height - 1)
            for text, tx, ty in ((f"{frac:.1f}", x + 2, 2), (f"{frac:.1f}", 2, y + 1)):
                try:
                    bbox = draw.textbbox((tx, ty), text, font=font)
                    draw.rectangle([bbox[0] - 1, bbox[1] - 1, bbox[2] + 1, bbox[3] + 1], fill=label_bg)
                except Exception:
                    pass
                draw.text((tx, ty), text, fill=(170, 0, 0), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    return {
        "overlay": str(out_path),
        "image_size": [width, height],
        "grid_steps": steps,
        "note": (
            'Read normalized coordinates off this image, then write a crop spec: '
            '{"crops": [{"name": "...", "why": "...", "box": [x0, y0, x1, y1]}]} with values in 0..1'
        ),
    }


def auto_tiles(size: tuple[int, int], families: set[str], rows: int, cols: int, overlap: float) -> list[dict[str, Any]]:
    """Mechanical coverage tiles. Blind to content by design — a fallback, not a strategy."""
    width, height = size
    tiles: list[dict[str, Any]] = []

    def add(name: str, box: tuple[int, int, int, int], why: str) -> None:
        if box[2] - box[0] < 8 or box[3] - box[1] < 8:
            return
        tiles.append({"name": name, "why": why, "box_px": box, "zoom": 1.0, "upscale": False})

    if "full" in families:
        add("full", (0, 0, width, height), "whole figure — composition, balance, first impression")

    if "grid" in families:
        for r in range(rows):
            for c in range(cols):
                x0 = int(c * width / cols - (overlap * width / cols if c else 0))
                x1 = int((c + 1) * width / cols + (overlap * width / cols if c < cols - 1 else 0))
                y0 = int(r * height / rows - (overlap * height / rows if r else 0))
                y1 = int((r + 1) * height / rows + (overlap * height / rows if r < rows - 1 else 0))
                add(
                    f"grid-r{r + 1}c{c + 1}",
                    (max(0, x0), max(0, y0), min(width, x1), min(height, y1)),
                    f"grid row {r + 1} col {c + 1}",
                )

    if "edges" in families:
        band_w = max(48, int(width * 0.07))
        band_h = max(48, int(height * 0.09))
        for index in range(3):
            y0, y1 = int(index * height / 3), int((index + 1) * height / 3)
            add(f"edge-left-{index + 1}", (0, y0, band_w, y1), "left border — clipping, y-axis truncation")
            add(f"edge-right-{index + 1}", (width - band_w, y0, width, y1), "right border — clipping, legend truncation")
        for index in range(3):
            x0, x1 = int(index * width / 3), int((index + 1) * width / 3)
            add(f"edge-top-{index + 1}", (x0, 0, x1, band_h), "top border — title clipping")
            add(f"edge-bottom-{index + 1}", (x0, height - band_h, x1, height), "bottom border — axis label clipping")

    return tiles


def load_spec(path: Path, width: int, height: int) -> list[dict[str, Any]]:
    """Read a model-authored crop plan."""
    data = json.loads(path.read_text(encoding="utf-8"))
    crops = data.get("crops") if isinstance(data, dict) else data
    if not isinstance(crops, list):
        raise ValueError('spec must be {"crops": [...]} or a bare list')
    tiles: list[dict[str, Any]] = []
    for index, entry in enumerate(crops):
        if not isinstance(entry, dict):
            raise ValueError(f"crop #{index + 1} is not an object")
        tiles.append(
            {
                "name": str(entry.get("name") or f"crop-{index + 1}"),
                "why": str(entry.get("why") or ""),
                "box_px": parse_box(entry.get("box"), width, height),
                "zoom": float(entry.get("zoom") or 1.0),
                "upscale": bool(entry.get("upscale", True)),
            }
        )
    return tiles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image", required=True, help="figure to crop (PNG/JPEG/WebP)")
    parser.add_argument("-o", "--outdir", default="qa/crops", help="output directory")
    parser.add_argument("--overlay", action="store_true", help="render a labelled coordinate grid and exit")
    parser.add_argument("--spec", metavar="JSON", help="model-authored crop plan")
    parser.add_argument("--box", action="append", default=[], help="one-off crop: x0,y0,x1,y1 (0..1 or px)")
    parser.add_argument("--name", default="manual", help="name for a --box crop")
    parser.add_argument("--zoom", type=float, default=1.0, help="extra magnification for --box crops")
    parser.add_argument("--auto", default="", help="mechanical coverage: full,grid,edges (comma separated)")
    parser.add_argument("--rows", type=int, default=3, help="--auto grid rows")
    parser.add_argument("--cols", type=int, default=3, help="--auto grid cols")
    parser.add_argument("--overlap", type=float, default=0.12, help="--auto grid overlap")
    parser.add_argument("--target-width", type=int, default=DEFAULT_TARGET_WIDTH, help="tile long edge in px")
    parser.add_argument("--steps", type=int, default=10, help="--overlay grid divisions")
    parser.add_argument("--json", action="store_true", help="JSON only")
    args = parser.parse_args(argv)

    from PIL import Image

    image_path = Path(args.image).resolve()
    if not image_path.exists():
        print(json.dumps({"ok": False, "error": f"missing image {image_path}"}))
        return 2

    outdir = Path(args.outdir).resolve()
    target = max(MIN_TARGET_WIDTH, min(MAX_TARGET_WIDTH, args.target_width))

    with Image.open(image_path) as opened:
        image = opened.convert("RGB")
        width, height = image.size

        if args.overlay:
            payload = render_overlay(image, outdir / f"{image_path.stem}-grid.png", steps=max(2, args.steps))
            payload["ok"] = True
            payload["source"] = str(image_path)
            if not args.json:
                print(f"coordinate overlay -> {payload['overlay']}", file=sys.stderr)
                print(f"image is {width}x{height} px; grid divisions: {payload['grid_steps']}", file=sys.stderr)
                print(payload["note"], file=sys.stderr)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        tiles: list[dict[str, Any]] = []
        if args.spec:
            spec_path = Path(args.spec)
            if not spec_path.exists():
                print(json.dumps({"ok": False, "error": f"missing spec {spec_path}"}))
                return 2
            try:
                tiles.extend(load_spec(spec_path, width, height))
            except (ValueError, json.JSONDecodeError) as exc:
                print(json.dumps({"ok": False, "error": f"bad spec: {exc}"}))
                return 2
        for text in args.box:
            parts = [float(p) for p in text.split(",")]
            tiles.append(
                {
                    "name": args.name,
                    "why": "explicitly requested crop",
                    "box_px": parse_box(parts, width, height),
                    "zoom": args.zoom,
                    "upscale": True,
                }
            )
        if args.auto:
            families = {part.strip() for part in args.auto.split(",") if part.strip()}
            if "all" in families:
                families = {"full", "grid", "edges"}
            tiles.extend(auto_tiles((width, height), families, args.rows, args.cols, args.overlap))

        if not tiles:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "no crops requested",
                        "hint": "use --overlay first to get coordinates, then --spec; or --auto for mechanical coverage",
                    }
                )
            )
            return 2

        results = []
        for index, tile in enumerate(tiles):
            safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in tile["name"])[:60]
            out_path = outdir / f"{index + 1:02d}-{safe}.png"
            try:
                info = save_tile(
                    image,
                    tile["box_px"],
                    out_path,
                    target,
                    zoom=tile.get("zoom", 1.0),
                    allow_upscale=bool(tile.get("upscale", True)),
                )
            except Exception as exc:
                results.append({"name": tile["name"], "error": str(exc)})
                continue
            info.update({"name": tile["name"], "why": tile.get("why", "")})
            results.append(info)

    payload = {
        "ok": all("error" not in r for r in results),
        "source": str(image_path),
        "image_size": [width, height],
        "outdir": str(outdir),
        "target_width": target,
        "crop_count": len(results),
        "crops": results,
    }
    if not args.json:
        print(f"crops for {image_path.name} ({width}x{height}) -> {outdir}", file=sys.stderr)
        for crop in results:
            if "error" in crop:
                print(f"  [skip] {crop['name']}: {crop['error']}", file=sys.stderr)
                continue
            print(
                f"  {Path(crop['path']).name:44s} {crop['size'][0]:5d}x{crop['size'][1]:<5d} "
                f"x{crop['scale']:<5} {crop['why'][:40]}",
                file=sys.stderr,
            )
        print(f"{len(results)} crop(s) at target long edge {target}px", file=sys.stderr)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
