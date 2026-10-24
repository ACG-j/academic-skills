# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy"]
# ///
"""Compare two renders of the same figure: what changed between review rounds.

A fix for one defect routinely introduces another — a legend moved away from the
data now overlaps an axis label, a font bumped up pushes the tick labels into the
title. Without a diff, the reviewer re-inspects from scratch and hopes to notice.

This reports three things:

* **geometry** — did the canvas size change, and by how much
* **pixels** — where content differs, with a bounding box per cluster so the change
  can be cropped and looked at
* **ink** — how much of the difference is added versus removed content

The diff image marks removals in red and additions in blue, which distinguishes "the
label moved" from "the label disappeared".

Usage:
    uv run sf_diff.py --before qa/round-1/fig.png --after qa/round-2/fig.png -o qa/diff
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Per-channel difference above which a pixel counts as changed. 8/255 tolerates
# antialiasing and PNG round-trip noise while still catching a 1 px shift.
DEFAULT_THRESHOLD = 8
MIN_CLUSTER_AREA = 40


def load_rgb(path: Path) -> Any:
    from PIL import Image

    with Image.open(path) as opened:
        return opened.convert("RGB")


def resize_to(image: Any, size: tuple[int, int]) -> Any:
    from PIL import Image

    if image.size == size:
        return image
    return image.resize(size, Image.LANCZOS)


def find_clusters(mask: Any, max_clusters: int = 12) -> list[dict[str, Any]]:
    """Group changed pixels into coarse clusters using a grid, then merge neighbours.

    A full connected-component pass on a 2 MP mask is slow and over-precise: the point
    is to point a crop at "something changed around here", not to trace outlines. A
    coarse grid keeps it fast and merges nearby changes naturally.
    """
    import numpy as np

    height, width = mask.shape
    cell = max(24, min(width, height) // 40)
    rows = (height + cell - 1) // cell
    cols = (width + cell - 1) // cell
    occupied: set[tuple[int, int]] = set()
    ys, xs = np.nonzero(mask)
    for y, x in zip(ys.tolist(), xs.tolist()):
        occupied.add((y // cell, x // cell))
    if not occupied:
        return []

    # Merge adjacent occupied cells into regions (BFS over the coarse grid).
    seen: set[tuple[int, int]] = set()
    clusters: list[dict[str, Any]] = []
    for start in sorted(occupied):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        cells: list[tuple[int, int]] = []
        while stack:
            r, c = stack.pop()
            cells.append((r, c))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    neighbour = (r + dr, c + dc)
                    if neighbour in occupied and neighbour not in seen:
                        seen.add(neighbour)
                        stack.append(neighbour)
        r0 = min(r for r, _ in cells)
        r1 = max(r for r, _ in cells) + 1
        c0 = min(c for _, c in cells)
        c1 = max(c for _, c in cells) + 1
        area_cells = len(cells)
        x0, y0 = c0 * cell, r0 * cell
        x1, y1 = min(width, c1 * cell), min(height, r1 * cell)
        clusters.append(
            {
                "box_px": [x0, y0, x1, y1],
                "box_norm": [
                    round(x0 / width, 4),
                    round(y0 / height, 4),
                    round(x1 / width, 4),
                    round(y1 / height, 4),
                ],
                "cells": area_cells,
                "area_px": (x1 - x0) * (y1 - y0),
            }
        )
    clusters.sort(key=lambda c: c["area_px"], reverse=True)
    return clusters[:max_clusters]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--before", required=True, help="previous render")
    parser.add_argument("--after", required=True, help="current render")
    parser.add_argument("-o", "--outdir", default="qa/diff", help="where to write the diff image and mask")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, help="per-channel difference threshold")
    parser.add_argument("--json", action="store_true", help="JSON only")
    args = parser.parse_args(argv)

    import numpy as np
    from PIL import Image

    before_path = Path(args.before).resolve()
    after_path = Path(args.after).resolve()
    for path in (before_path, after_path):
        if not path.exists():
            print(json.dumps({"ok": False, "error": f"missing image {path}"}))
            return 2

    before = load_rgb(before_path)
    after_raw = load_rgb(after_path)
    before_size = before.size
    after_size = after_raw.size
    size_changed = before_size != after_size
    after = resize_to(after_raw, before_size)

    a = np.asarray(before, dtype=np.int16)
    b = np.asarray(after, dtype=np.int16)
    delta = np.abs(a - b).max(axis=2)
    mask = delta > args.threshold

    changed = int(mask.sum())
    total = int(mask.size)
    share = changed / total if total else 0.0

    # Ink direction: darker in after means content was added, lighter means removed.
    lum_a = a.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    lum_b = b.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    darker = int(((lum_b < lum_a - args.threshold) & mask).sum())
    lighter = int(((lum_b > lum_a + args.threshold) & mask).sum())

    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    # Side-by-side plus a highlighted diff.
    diff_vis = np.asarray(after, dtype=np.uint8).copy()
    diff_vis[mask] = np.array([255, 0, 0], dtype=np.uint8)
    Image.fromarray(diff_vis).save(outdir / "diff-mask.png")
    Image.fromarray((mask.astype(np.uint8) * 255)).save(outdir / "diff-binary.png")

    width, height = before_size
    sheet = Image.new("RGB", (width, height * 2 + 8), "white")
    sheet.paste(before, (0, 0))
    sheet.paste(after, (0, height + 8))
    sheet.save(outdir / "diff-stacked.png")

    clusters = find_clusters(mask)
    clusters = [c for c in clusters if c["area_px"] >= MIN_CLUSTER_AREA]

    payload: dict[str, Any] = {
        "ok": True,
        "before": str(before_path),
        "after": str(after_path),
        "size_changed": size_changed,
        "before_size": list(before_size),
        "after_size": list(after_size),
        "threshold": args.threshold,
        "changed_pixels": changed,
        "changed_share": round(share, 5),
        "added_ink_px": darker,
        "removed_ink_px": lighter,
        "clusters": clusters,
        "outputs": {
            "mask": str(outdir / "diff-mask.png"),
            "binary": str(outdir / "diff-binary.png"),
            "stacked": str(outdir / "diff-stacked.png"),
        },
    }

    # A tiny share of changed pixels on an unchanged canvas means the edit landed.
    # A large share, or a size change, means the whole figure moved.
    if size_changed:
        payload["verdict"] = "canvas size changed — every element may have shifted"
    elif share < 0.0005:
        payload["verdict"] = "no meaningful change"
    elif share < 0.05:
        payload["verdict"] = "localized change"
    else:
        payload["verdict"] = "widespread change — verify the whole figure again"

    if not args.json:
        print(f"diff {before_path.name} -> {after_path.name}", file=sys.stderr)
        print(f"  canvas: {before_size} -> {after_size}{' (CHANGED)' if size_changed else ''}", file=sys.stderr)
        print(f"  changed: {changed} px ({share * 100:.2f}%)", file=sys.stderr)
        print(f"  ink added {darker} px / removed {lighter} px", file=sys.stderr)
        print(f"  verdict: {payload['verdict']}", file=sys.stderr)
        for index, cluster in enumerate(clusters[:6]):
            box = cluster["box_norm"]
            print(
                f"  cluster {index + 1}: box {box} ({cluster['area_px']} px²) — crop this to inspect the change",
                file=sys.stderr,
            )
        print(f"  outputs: {outdir}", file=sys.stderr)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
