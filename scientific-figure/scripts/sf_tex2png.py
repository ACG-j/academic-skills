# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Compile a TikZ figure and rasterize it for review.

A TikZ figure that compiles can still be wrong: overlapping labels, a legend over data,
text too small for the target column. None of that is visible in the .tex source, so the
figure needs the same rasterize-then-look treatment as a matplotlib render.

The chain is xelatex -> pdfcrop -> pdftoppm. xelatex rather than pdflatex because CJK text
in a figure requires it; pdfcrop because a standalone figure has a tight bounding box but a
non-standalone one does not.

Usage:
    uv run sf_tex2png.py fig.tex -o qa/ --dpi 300
    uv run sf_tex2png.py fig.tex --engine pdflatex --keep-aux
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_DPI = 300


def run(cmd: list[str], cwd: Path, timeout: float = 180.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def extract_errors(log_text: str, limit: int = 6) -> list[str]:
    """Pull the lines a LaTeX user actually needs out of a very noisy log."""
    errors: list[str] = []
    lines = log_text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("!") or "Error" in line and "error" not in line.lower()[:6]:
            context = " | ".join(part.strip() for part in lines[index : index + 3] if part.strip())
            if context and context not in errors:
                errors.append(context[:300])
            if len(errors) >= limit:
                break
    for pattern in (r"Missing character:.*", r"LaTeX Warning:.*undefined.*"):
        for match in list(re.finditer(pattern, log_text))[:3]:
            message = match.group(0).strip()[:200]
            if message not in errors:
                errors.append(message)
    return errors[:limit]


def pdf_page_size(pdf: Path) -> list[float] | None:
    """Read the page size in points, via pdfinfo or a raw MediaBox scan.

    A regex over the PDF bytes looks simpler but fails on the compressed object streams
    modern TeX engines emit, so pdfinfo is tried first and the scan is only a fallback.
    """
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        code, out = run([pdfinfo, str(pdf)], pdf.parent, timeout=30)
        if code == 0:
            match = re.search(r"Page size:\s+([\d.]+)\s+x\s+([\d.]+)\s+pts", out)
            if match:
                return [round(float(match.group(1)), 2), round(float(match.group(2)), 2)]
    try:
        data = pdf.read_bytes()
    except OSError:
        return None
    for raw in re.findall(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", data):
        try:
            x0, y0, x1, y1 = (float(value) for value in raw)
        except ValueError:
            continue
        if x1 > x0 and y1 > y0:
            return [round(x1 - x0, 2), round(y1 - y0, 2)]
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tex", help="the .tex file to compile")
    parser.add_argument("-o", "--outdir", default="qa", help="where to write the PNG and PDF")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="rasterization dpi")
    parser.add_argument("--engine", default="xelatex", help="latex engine (xelatex handles CJK)")
    parser.add_argument("--no-crop", action="store_true", help="skip pdfcrop")
    parser.add_argument("--keep-aux", action="store_true", help="keep .aux/.log in the output directory")
    parser.add_argument("--json", action="store_true", help="JSON only")
    args = parser.parse_args(argv)

    tex_path = Path(args.tex).resolve()
    if not tex_path.exists():
        print(json.dumps({"ok": False, "error": f"missing {tex_path}"}))
        return 2

    engine = shutil.which(args.engine)
    if engine is None:
        print(json.dumps({"ok": False, "error": f"{args.engine} not found on PATH", "fix": "install TeX Live"}))
        return 2

    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    stem = tex_path.stem

    workdir = Path(tempfile.mkdtemp(prefix="sf_tex_"))
    # Compile in a scratch copy so the source directory stays clean, but keep relative
    # includes working by copying the whole source directory.
    source_dir = tex_path.parent
    for item in source_dir.iterdir():
        if item.is_file() and item.suffix in {".tex", ".dat", ".csv", ".pgf", ".tikz", ".sty", ".cls"}:
            shutil.copy2(item, workdir / item.name)

    code, output = run(
        [engine, "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={workdir}", str(workdir / tex_path.name)],
        workdir,
    )
    log_path = workdir / f"{stem}.log"
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else output

    if code != 0 or not (workdir / f"{stem}.pdf").exists():
        errors = extract_errors(log_text)
        payload: dict[str, Any] = {
            "ok": False,
            "stage": "compile",
            "engine": args.engine,
            "tex": str(tex_path),
            "exit_code": code,
            "errors": errors or [output[-600:]],
            "hint": "common causes: missing \\usepackage{pgfplots}, CJK text with pdflatex, dimension too large",
        }
        if not args.json:
            print(f"compile FAILED: {tex_path.name}", file=sys.stderr)
            for error in payload["errors"]:
                print(f"  {error}", file=sys.stderr)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    compiled = workdir / f"{stem}.pdf"
    cropped = workdir / f"{stem}-crop.pdf"
    final_pdf = outdir / f"{stem}.pdf"

    pdfcrop = shutil.which("pdfcrop")
    if pdfcrop and not args.no_crop:
        crop_code, crop_out = run([pdfcrop, "--margins", "2 2 2 2", str(compiled), str(cropped)], workdir)
        if crop_code == 0 and cropped.exists():
            shutil.copy2(cropped, final_pdf)
        else:
            shutil.copy2(compiled, final_pdf)
    else:
        shutil.copy2(compiled, final_pdf)

    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        payload = {
            "ok": False,
            "stage": "rasterize",
            "error": "pdftoppm not found",
            "pdf": str(final_pdf),
            "fix": "install poppler-utils",
        }
        if not args.json:
            print(json.dumps(payload, indent=2), file=sys.stderr)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    png_prefix = outdir / stem
    raster_code, raster_out = run(
        [pdftoppm, "-png", "-r", str(args.dpi), "-singlefile", str(final_pdf), str(png_prefix)],
        workdir,
    )
    png_path = outdir / f"{stem}.png"
    if raster_code != 0 or not png_path.exists():
        payload = {
            "ok": False,
            "stage": "rasterize",
            "error": raster_out.strip()[:300],
            "pdf": str(final_pdf),
        }
        if not args.json:
            print(json.dumps(payload, indent=2), file=sys.stderr)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    size_px: list[int] | None = None
    try:
        from PIL import Image

        with Image.open(png_path) as image:
            size_px = list(image.size)
    except Exception:
        pass

    size_pt = pdf_page_size(final_pdf)
    size_mm = [round(v / 72 * 25.4, 1) for v in size_pt] if size_pt else None

    if args.keep_aux:
        for suffix in (".log", ".aux"):
            source = workdir / f"{stem}{suffix}"
            if source.exists():
                shutil.copy2(source, outdir / source.name)

    warnings = extract_errors(log_text)
    missing_glyphs = [w for w in warnings if w.startswith("Missing character")]

    payload = {
        "ok": not missing_glyphs,
        "stage": "done",
        "tex": str(tex_path),
        "engine": args.engine,
        "pdf": str(final_pdf),
        "png": str(png_path),
        "png_size_px": size_px,
        "figure_size_pt": size_pt,
        "figure_size_mm": size_mm,
        "dpi": args.dpi,
        "warnings": warnings,
        "missing_glyphs": missing_glyphs,
        "next": f"uv run sf_crop.py --image {png_path} --overlay -o {outdir}",
    }
    if not args.json:
        print(f"compiled {tex_path.name} -> {final_pdf.name}", file=sys.stderr)
        if size_mm:
            print(f"  figure size: {size_mm[0]} x {size_mm[1]} mm", file=sys.stderr)
        if size_px:
            print(f"  review PNG: {size_px[0]}x{size_px[1]} px @ {args.dpi} dpi", file=sys.stderr)
        for warning in warnings:
            print(f"  [warn] {warning}", file=sys.stderr)
        print(f"  next: {payload['next']}", file=sys.stderr)
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    shutil.rmtree(workdir, ignore_errors=True)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
