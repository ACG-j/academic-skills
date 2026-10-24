# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy", "pillow"]
# ///
"""Export figures to several formats and verify what actually landed on disk.

Saving a file is not exporting it. A PDF can carry unembedded fonts, an SVG can
have its text converted to paths (no longer editable), a PNG can be 72 dpi, and a
figure can be the wrong physical width for the journal. This tool runs a plotting
script, then inspects every artifact it produced and reports the gaps.

Usage:
    uv run sf_export.py --script plot.py --outdir out --target-mm 89
    uv run sf_export.py --inspect out/fig1.pdf
    uv run sf_export.py --inspect out/            # every supported file in a directory

The script runs in its own directory; whatever it writes is discovered by extension.
Exit code 0 when no blocking issue was found, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import runpy
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SUPPORTED = {".png", ".svg", ".pdf", ".pgf", ".eps", ".tif", ".tiff"}
MM_PER_INCH = 25.4
MIN_DPI = 300
# PNG dpi is stored as a rational, so 300 dpi round-trips as 299.9994.
DPI_TOLERANCE = 1.0
WIDTH_TOLERANCE_MM = 1.5


@dataclass
class Finding:
    severity: str
    check: str
    message: str
    fix: str = ""


@dataclass
class Artifact:
    path: str
    kind: str
    bytes: int
    facts: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)


def _run(cmd: list[str], timeout: float = 60.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def inspect_png(path: Path, target_mm: float | None) -> tuple[dict[str, Any], list[Finding]]:
    from PIL import Image

    findings: list[Finding] = []
    with Image.open(path) as image:
        width, height = image.size
        dpi = image.info.get("dpi")
        mode = image.mode
        dpi_x = float(dpi[0]) if dpi else 0.0
    facts: dict[str, Any] = {"width_px": width, "height_px": height, "dpi": dpi_x, "mode": mode}
    if dpi_x:
        facts["physical_mm"] = [round(width / dpi_x * MM_PER_INCH, 1), round(height / dpi_x * MM_PER_INCH, 1)]
    if dpi_x and dpi_x < MIN_DPI - DPI_TOLERANCE:
        findings.append(
            Finding("warn", "dpi", f"{dpi_x:.0f} dpi is below the {MIN_DPI} dpi print minimum", "pass dpi=300 or 600 to savefig")
        )
    if not dpi:
        findings.append(Finding("info", "dpi", "PNG carries no dpi metadata", "savefig(dpi=...) writes it; LaTeX then sizes it correctly"))
    if mode not in ("RGB", "RGBA", "L"):
        findings.append(Finding("warn", "mode", f"unexpected PNG colour mode {mode}", "save as RGB"))
    if width < 600:
        findings.append(Finding("warn", "resolution", f"only {width} px wide — too coarse for visual review", "render the review PNG at dpi>=200"))
    if target_mm and "physical_mm" in facts:
        delta = abs(facts["physical_mm"][0] - target_mm)
        facts["width_delta_mm"] = round(delta, 2)
        if delta > WIDTH_TOLERANCE_MM:
            # savefig(bbox_inches='tight') crops to the artists, so the saved PNG is
            # narrower than figsize by the trimmed margin. That is a real signal: the
            # PDF/SVG are the size-bearing artifacts, and a PNG narrower than the
            # target means the figure will be scaled up (blurred) in the layout.
            findings.append(
                Finding(
                    "warn",
                    "width",
                    f"PNG is {facts['physical_mm'][0]} mm wide but the target column is {target_mm} mm "
                    f"({delta:.1f} mm narrower) — tight bbox trimmed the margins",
                    "size the PDF/SVG by figsize; for the PNG either accept the crop or set bbox_inches=None",
                )
            )
    return facts, findings


def inspect_svg(path: Path) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    n_text = len(re.findall(r"<text\b", text))
    n_tspan = len(re.findall(r"<tspan\b", text))
    n_path = len(re.findall(r"<path\b", text))
    has_font_face = "font-face" in text or "@font-face" in text
    facts = {
        "text_elements": n_text,
        "tspan_elements": n_tspan,
        "path_elements": n_path,
        "embeds_fonts": has_font_face,
        "editable_text": n_text > 0,
    }
    if n_text == 0 and n_path > 0:
        findings.append(
            Finding(
                "warn",
                "svg-text",
                "no <text> elements: all glyphs were converted to paths, so labels are not editable",
                "set svg.fonttype='none' to keep text as text (default in the base style)",
            )
        )
    if n_text > 0 and not has_font_face:
        findings.append(
            Finding(
                "info",
                "svg-fonts",
                "text kept as text without embedded fonts — the file depends on fonts installed on the viewing machine",
                "fine for LaTeX/Inkscape on the same machine; convert to PDF for submission",
            )
        )
    return facts, findings


def inspect_pdf(path: Path) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    facts: dict[str, Any] = {"bytes": path.stat().st_size}
    pdffonts = shutil.which("pdffonts")
    if pdffonts is None:
        findings.append(
            Finding("info", "pdf-fonts", "pdffonts not installed — font embedding could not be verified", "install poppler-utils")
        )
        return facts, findings
    code, out = _run([pdffonts, str(path)])
    if code != 0:
        findings.append(Finding("warn", "pdf-fonts", f"pdffonts failed: {out.strip()[:160]}", ""))
        return facts, findings
    lines = [line for line in out.splitlines()[2:] if line.strip()]
    fonts = []
    for line in lines:
        # Columns: name, type, encoding, emb, sub, uni, object id
        parts = line.split()
        if len(parts) < 4:
            continue
        name = parts[0]
        emb = None
        for token in parts[1:]:
            if token in ("yes", "no"):
                emb = token == "yes"
                break
        fonts.append({"name": name, "embedded": emb, "raw": line.strip()[:120]})
    facts["fonts"] = fonts
    unembedded = [f["name"] for f in fonts if f["embedded"] is False]
    if unembedded:
        findings.append(
            Finding(
                "error",
                "pdf-fonts",
                f"unembedded fonts: {', '.join(unembedded[:4])}",
                "set pdf.fonttype=42 and pdf.use14corefonts=False, then re-export",
            )
        )
    type3 = [f["name"] for f in fonts if "Type 3" in f.get("raw", "")]
    if type3:
        findings.append(
            Finding("error", "pdf-type3", f"Type 3 fonts: {', '.join(type3[:3])}", "Type 3 renders poorly; use pdf.fonttype=42")
        )
    if not fonts:
        findings.append(Finding("info", "pdf-fonts", "no fonts listed — figure may be pure vector paths", ""))
    return facts, findings


def inspect_pgf(path: Path) -> tuple[dict[str, Any], list[Finding]]:
    """Inspect a .pgf file.

    Two different things produce this extension and they are not interchangeable:
    matplotlib's PGF backend emits raw PGF drawing commands (``\\pgfpath``,
    ``\\pgfusepath``) wrapped in a ``pgfpicture``, while matplot2tikz/tikzplotlib
    emit a pgfplots ``axis`` environment with ``\\addplot``. Only the latter is
    editable as data; the former is a vector snapshot that still renders text with
    the document's fonts.
    """
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    n_addplot = len(re.findall(r"\\addplot", text))
    n_axis = len(re.findall(r"\\begin\{axis\}", text))
    n_pgfpath = len(re.findall(r"\\pgfpath", text))
    n_pgfusepath = len(re.findall(r"\\pgfusepath", text))
    n_begin_picture = len(re.findall(r"\\begin\{pgfpicture\}", text))
    if n_axis and n_addplot:
        flavour = "pgfplots"
    elif n_begin_picture or n_pgfpath:
        flavour = "raw-pgf"
    else:
        flavour = "unknown"
    facts = {
        "flavour": flavour,
        "addplot_calls": n_addplot,
        "axis_environments": n_axis,
        "pgfpath_calls": n_pgfpath,
        "pgfusepath_calls": n_pgfusepath,
        "kb": round(path.stat().st_size / 1024, 1),
    }
    if flavour == "unknown":
        findings.append(
            Finding("warn", "pgf-content", "neither a pgfpicture nor a pgfplots axis was found", "check that the export finished")
        )
    if flavour == "raw-pgf":
        findings.append(
            Finding(
                "info",
                "pgf-flavour",
                "raw PGF from matplotlib's pgf backend: renders with the document's fonts but is not editable as plot data",
                "for an editable pgfplots axis, export with matplot2tikz.save(...) instead",
            )
        )
    if path.stat().st_size > 5 * 1024 * 1024:
        findings.append(
            Finding(
                "warn",
                "pgf-size",
                f"{facts['kb']} kB of TikZ — LaTeX compilation may be slow",
                "export PDF instead, or reduce the point count / use a coarser sampling",
            )
        )
    if n_pgfusepath > 5000:
        findings.append(
            Finding(
                "warn",
                "pgf-paths",
                f"{n_pgfusepath} filled paths — a scatter plot this dense makes LaTeX crawl",
                "switch to a raster image for dense scatters, or downsample",
            )
        )
    return facts, findings


def inspect_eps(path: Path) -> tuple[dict[str, Any], list[Finding]]:
    head = path.read_text(encoding="latin-1", errors="replace")[:400]
    facts = {"is_eps": head.startswith("%!PS-Adobe")}
    findings = [] if facts["is_eps"] else [Finding("warn", "eps", "file does not start with an EPS magic comment", "")]
    return facts, findings


def inspect_file(path: Path, target_mm: float | None) -> Artifact:
    suffix = path.suffix.lower()
    kind = suffix.lstrip(".")
    artifact = Artifact(path=str(path), kind=kind, bytes=path.stat().st_size)
    try:
        if suffix == ".png":
            artifact.facts, artifact.findings = inspect_png(path, target_mm)
        elif suffix == ".svg":
            artifact.facts, artifact.findings = inspect_svg(path)
        elif suffix == ".pdf":
            artifact.facts, artifact.findings = inspect_pdf(path)
        elif suffix == ".pgf":
            artifact.facts, artifact.findings = inspect_pgf(path)
        elif suffix == ".eps":
            artifact.facts, artifact.findings = inspect_eps(path)
        elif suffix in (".tif", ".tiff"):
            from PIL import Image

            with Image.open(path) as image:
                artifact.facts = {"width_px": image.size[0], "height_px": image.size[1], "mode": image.mode}
        else:
            artifact.findings = [Finding("info", "format", f"no inspector for {suffix}", "")]
    except Exception as exc:  # a corrupt artifact is itself a finding
        artifact.findings = [Finding("error", "read", f"could not inspect: {exc}", "")]
    return artifact


def discover(outdir: Path) -> list[Path]:
    if not outdir.exists():
        return []
    return sorted(p for p in outdir.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED)


def run_script(script: Path) -> dict[str, Any]:
    """Execute the plotting script in its own directory, capturing its chatter.

    The script prints things like "saved fig1.*". That would interleave with this tool's
    JSON on stdout, so the child's stdout is redirected to stderr while it runs.
    """
    cwd = script.parent
    previous = Path.cwd()
    real_stdout = sys.stdout
    sys.path.insert(0, str(cwd))
    try:
        import os

        os.chdir(cwd)
        sys.stdout = sys.stderr
        runpy.run_path(str(script), run_name="__main__")
        return {"ok": True}
    except SystemExit as exc:
        return {"ok": exc.code in (0, None), "exit": exc.code}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        sys.stdout = real_stdout
        os.chdir(previous)
        if str(cwd) in sys.path:
            sys.path.remove(str(cwd))


def latex_snippet(path: Path, label: str, caption: str) -> str:
    suffix = path.suffix.lower()
    stem = path.stem
    if suffix == ".pgf":
        return (
            "\\begin{figure}[tbp]\n"
            "  \\centering\n"
            f"  \\input{{{path.name}}}\n"
            f"  \\caption{{{caption}}}\n"
            f"  \\label{{fig:{label or stem}}}\n"
            "\\end{figure}"
        )
    if suffix == ".pdf":
        return (
            "\\begin{figure}[tbp]\n"
            "  \\centering\n"
            f"  \\includegraphics[width=\\linewidth]{{{stem}.pdf}}\n"
            f"  \\caption{{{caption}}}\n"
            f"  \\label{{fig:{label or stem}}}\n"
            "\\end{figure}"
        )
    return ""


def build_report(
    artifacts: list[Artifact], target_mm: float | None, snippet_for: str | None, caption: str
) -> dict[str, Any]:
    blocking = [f for a in artifacts for f in a.findings if f.severity == "error"]
    warnings = [f for a in artifacts for f in a.findings if f.severity == "warn"]
    infos = [f for a in artifacts for f in a.findings if f.severity == "info"]
    payload: dict[str, Any] = {
        "ok": not blocking,
        "target_mm": target_mm,
        "artifacts": [
            {
                "path": a.path,
                "kind": a.kind,
                "bytes": a.bytes,
                "facts": a.facts,
                "findings": [f.__dict__ for f in a.findings],
            }
            for a in artifacts
        ],
        "summary": {"errors": len(blocking), "warnings": len(warnings), "info": len(infos)},
        "formats_present": sorted({a.kind for a in artifacts}),
    }
    if snippet_for:
        match = next((a for a in artifacts if Path(a.path).stem == snippet_for or a.path.endswith(snippet_for)), None)
        if match:
            payload["latex"] = latex_snippet(Path(match.path), snippet_for, caption)
    return payload


def print_human(payload: dict[str, Any]) -> None:
    print(f"export check — {len(payload['artifacts'])} artifact(s)", file=sys.stderr)
    for artifact in payload["artifacts"]:
        name = Path(artifact["path"]).name
        print(f"  {name:32s} {artifact['kind']:4s} {artifact['bytes'] / 1024:8.1f} kB", file=sys.stderr)
        for finding in artifact["findings"]:
            print(f"    [{finding['severity']:5s}] {finding['message']}", file=sys.stderr)
    print(f"formats: {', '.join(payload['formats_present']) or 'none'}", file=sys.stderr)
    summary = payload["summary"]
    verdict = "PASS" if payload["ok"] else "BLOCKED"
    print(f"{verdict} — {summary['errors']} error(s), {summary['warnings']} warning(s)", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--script", metavar="PY", help="plotting script to run before inspecting")
    source.add_argument("--inspect", metavar="PATH", help="file or directory to inspect")
    parser.add_argument("--outdir", default=None, help="where the script writes (default: script directory)")
    parser.add_argument("--target-mm", type=float, default=None, help="expected physical width in mm")
    parser.add_argument("--snippet", metavar="NAME", help="emit a LaTeX figure block for this artifact")
    parser.add_argument("--caption", default="", help="caption text used by --snippet")
    parser.add_argument("--json", action="store_true", help="JSON only")
    args = parser.parse_args(argv)

    script_result: dict[str, Any] | None = None
    if args.script:
        script = Path(args.script).resolve()
        if not script.exists():
            print(json.dumps({"ok": False, "error": f"missing script {script}"}))
            return 2
        script_result = run_script(script)
        outdir = Path(args.outdir).resolve() if args.outdir else script.parent
        if not script_result["ok"]:
            payload = {"ok": False, "script": script_result, "artifacts": [], "summary": {"errors": 1, "warnings": 0, "info": 0}}
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1
    else:
        target = Path(args.inspect)
        outdir = target if target.is_dir() else target.parent

    files = discover(outdir)
    if args.inspect and not Path(args.inspect).is_dir():
        files = [Path(args.inspect)]

    artifacts = [inspect_file(path, args.target_mm) for path in files]
    payload = build_report(artifacts, args.target_mm, args.snippet, args.caption)
    if script_result is not None:
        payload["script"] = script_result
    if not artifacts:
        payload["ok"] = False
        payload["note"] = f"no figure artifacts found under {outdir}"
    if not args.json:
        print_human(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
