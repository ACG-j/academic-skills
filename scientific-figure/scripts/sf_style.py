# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy", "pillow"]
# ///
"""Journal style registry for the scientific-figure skill.

The style layer has two halves: machine-readable specifications
(``styles/journals.json``) and matplotlib style sheets (``styles/base.mplstyle``
plus one file per journal). This tool reads both, merges base+journal rcParams,
renders a preview at the target physical size, and can generate a new style from
a JSON spec.

Usage:
    uv run sf_style.py --list
    uv run sf_style.py --show nature
    uv run sf_style.py --apply nature
    uv run sf_style.py --preview nature -o /tmp/figstyle
    uv run sf_style.py --from-spec spec.json [--register]

Every command prints JSON on stdout; human summaries go to stderr.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any

STYLE_DIR = Path(__file__).resolve().parents[1] / "styles"
BASE_STYLE = STYLE_DIR / "base.mplstyle"
JOURNALS_JSON = STYLE_DIR / "journals.json"
MM_PER_INCH = 25.4


def die(message: str) -> None:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    raise SystemExit(2)


def load_meta() -> dict[str, Any]:
    if not JOURNALS_JSON.exists():
        die(f"missing {JOURNALS_JSON}")
    return json.loads(JOURNALS_JSON.read_text(encoding="utf-8"))


def style_path(name: str) -> Path:
    path = STYLE_DIR / f"{name}.mplstyle"
    if not path.exists():
        known = sorted(p.stem for p in STYLE_DIR.glob("*.mplstyle") if p.stem != "base")
        die(f"unknown style '{name}'; known: {', '.join(known)}")
    return path


def load_rc(name: str) -> dict[str, Any]:
    """Merge base + journal rcParams; journal values win."""
    import matplotlib as mpl

    merged: dict[str, Any] = {}
    merged.update(mpl.rc_params_from_file(str(BASE_STYLE), use_default_template=False))
    if name != "base":
        merged.update(mpl.rc_params_from_file(str(style_path(name)), use_default_template=False))
    return merged


def describe(name: str) -> dict[str, Any]:
    meta = load_meta()
    journal = meta["journals"].get(name)
    if journal is None and name != "base":
        die(f"'{name}' has no entry in journals.json")
    rc = load_rc(name)
    figsize = rc.get("figure.figsize", [3.5, 2.6])
    width_mm = float(figsize[0]) * MM_PER_INCH
    height_mm = float(figsize[1]) * MM_PER_INCH
    return {
        "name": name,
        "label": (journal or {}).get("label", "base"),
        "figure_inches": [round(float(figsize[0]), 3), round(float(figsize[1]), 3)],
        "figure_mm": [round(width_mm, 1), round(height_mm, 1)],
        "font_pt": rc.get("font.size"),
        "tick_pt": rc.get("xtick.labelsize"),
        "legend_pt": rc.get("legend.fontsize"),
        "line_width": rc.get("lines.linewidth"),
        "font_family": rc.get("font.family"),
        "serif": rc.get("font.serif"),
        "sans": rc.get("font.sans-serif"),
        "colors": _cycle_colors(rc),
        "meta": journal or {},
    }


def _cycle_colors(rc: dict[str, Any]) -> list[str]:
    """Read the colour cycle whether rc_params_from_file yielded a Cycler or a raw dict."""
    cycle = rc.get("axes.prop_cycle")
    if cycle is None:
        return []
    by_key = getattr(cycle, "by_key", None)
    if callable(by_key):
        return list(by_key().get("color", []))
    if isinstance(cycle, dict):
        return list(cycle.get("color", []))
    return []


def cmd_list(as_json: bool) -> int:
    meta = load_meta()
    rows = [describe(name) for name in sorted(meta["journals"])]
    if as_json:
        print(json.dumps({"ok": True, "styles": rows, "warning": meta.get("warning", "")}, ensure_ascii=False, indent=2))
        return 0
    print(f"{'style':14s} {'width':>8s} {'font':>5s} {'tick':>5s} {'line':>5s}  label", file=sys.stderr)
    for row in rows:
        print(
            f"{row['name']:14s} {row['figure_mm'][0]:7.1f}mm {row['font_pt']:5} "
            f"{row['tick_pt']:5} {row['line_width']:5}  {row['label']}",
            file=sys.stderr,
        )
    print(json.dumps({"ok": True, "styles": rows}, ensure_ascii=False, indent=2))
    return 0


def cmd_show(name: str) -> int:
    payload = describe(name)
    payload["rcParams"] = {k: _jsonable(v) for k, v in load_rc(name).items()}
    payload["ok"] = True
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return str(value)


def cmd_apply(name: str) -> int:
    rc_path = style_path(name)
    snippet = (
        "import matplotlib.pyplot as plt\n"
        "from pathlib import Path\n\n"
        f"STYLE_DIR = Path({str(STYLE_DIR)!r})\n"
        f"plt.style.use([STYLE_DIR / 'base.mplstyle', STYLE_DIR / '{rc_path.name}'])\n"
        "# Apply the style ONCE at the top of the script; do not tweak rcParams per figure.\n"
    )
    print(json.dumps({"ok": True, "style": name, "snippet": snippet, "style_file": str(rc_path)}, ensure_ascii=False, indent=2))
    print(snippet, file=sys.stderr)
    return 0


def cmd_preview(name: str, outdir: Path, scale: float) -> int:
    """Render a diagnostic figure at the style's real physical size."""
    import matplotlib as mpl

    mpl.use("Agg", force=True)
    import matplotlib.pyplot as plt
    import numpy as np

    rc = load_rc(name)
    outdir.mkdir(parents=True, exist_ok=True)
    figsize = rc.get("figure.figsize", [3.5, 2.6])
    figsize = [float(figsize[0]) * scale, float(figsize[1]) * scale]
    issues: list[str] = []

    with mpl.rc_context(rc), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig = plt.figure(figsize=figsize)
        gs = fig.add_gridspec(2, 1, height_ratios=[2.2, 1.0], hspace=0.55)

        ax = fig.add_subplot(gs[0])
        x = np.linspace(0, 10, 12)
        colors = mpl.rcParams["axes.prop_cycle"].by_key()["color"]
        for index in range(3):
            y = np.sin(x / (index + 1.2)) + index * 0.35
            ax.errorbar(
                x,
                y,
                yerr=0.12,
                marker="os^"[index],
                linestyle=["-", "--", "-."][index],
                color=colors[index % len(colors)],
                label=f"方法 {index + 1}" if name.endswith("-cn") else f"Method {index + 1}",
                linewidth=mpl.rcParams["lines.linewidth"],
                markersize=mpl.rcParams["lines.markersize"],
                capsize=mpl.rcParams["errorbar.capsize"],
            )
        ax.set_xlabel("时间 $t$ (s)" if name.endswith("-cn") else "Time $t$ (s)")
        ax.set_ylabel("误差 (%)" if name.endswith("-cn") else "Error (%)")
        ax.set_title("风格预览" if name.endswith("-cn") else "Style preview")
        ax.legend(loc="upper right", ncol=1, framealpha=0.9)
        # Annotate into empty space above the curves: the preview must itself obey
        # the rule that annotation never covers data.
        peak = int(np.argmax(np.sin(x / 1.2) + 0.7))
        ax.set_ylim(top=float(ax.get_ylim()[1]) + 0.55)
        ax.annotate(
            "标注示例" if name.endswith("-cn") else "annotation",
            xy=(x[peak], np.sin(x[peak] / 1.2) + 0.7),
            xytext=(x[peak] + 1.6, np.sin(x[peak] / 1.2) + 1.05),
            arrowprops={"arrowstyle": "->", "linewidth": 0.7},
            fontsize=mpl.rcParams["xtick.labelsize"],
            ha="left",
            va="center",
        )

        ax2 = fig.add_subplot(gs[1])
        categories = ["A", "B", "C", "D"]
        values = [0.62, 0.81, 0.74, 0.55]
        ax2.bar(categories, values, color=colors[0], width=0.6, edgecolor="black", linewidth=0.4)
        ax2.set_ylim(0, 1.0)
        ax2.set_ylabel("Score")
        ax2.set_xlabel("Group")
        fig.savefig(outdir / f"preview_{name}.png")
        fig.savefig(outdir / f"preview_{name}.pdf")
        png_path = outdir / f"preview_{name}.png"
        plt.close(fig)

    missing = [str(w.message) for w in caught if "missing from font" in str(w.message).lower()]
    if missing:
        issues.append(f"missing glyphs: {missing[0][:120]}")
    if float(rc.get("font.size", 8)) < 5:
        issues.append("base font below 5 pt")
    width_mm = float(figsize[0]) * MM_PER_INCH
    if width_mm > 200:
        issues.append(f"figure width {width_mm:.0f} mm exceeds a typical journal text block")

    dpi = _numeric_dpi(rc.get("savefig.dpi"), rc.get("figure.dpi"))
    payload = {
        "ok": not issues,
        "style": name,
        "png": str(png_path),
        "pdf": str(outdir / f"preview_{name}.pdf"),
        "figure_mm": [round(width_mm, 1), round(float(figsize[1]) * MM_PER_INCH, 1)],
        "pixels_at_savefig_dpi": [int(round(figsize[0] * dpi)), int(round(figsize[1] * dpi))],
        "issues": issues,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


def _numeric_dpi(savefig_dpi: Any, figure_dpi: Any) -> float:
    """Resolve savefig.dpi, which matplotlib may store as the literal string 'figure'."""
    if isinstance(savefig_dpi, (int, float)):
        return float(savefig_dpi)
    if isinstance(figure_dpi, (int, float)):
        return float(figure_dpi)
    return 100.0


def cmd_from_spec(spec_path: Path, register: bool) -> int:
    """Generate a journal .mplstyle from a JSON spec."""
    if not spec_path.exists():
        die(f"missing spec file {spec_path}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    name = spec.get("name")
    if not name or not isinstance(name, str):
        die("spec requires a string 'name'")
    single_mm = float(spec.get("single_column_mm", 90))
    base_pt = float(spec.get("base_font_pt", 8))
    fonts = spec.get("fonts") or ["Arial", "Helvetica", "DejaVu Sans"]
    font_kind = spec.get("font_kind", "sans")
    aspect = float(spec.get("aspect", 0.74))
    width_in = single_mm / MM_PER_INCH
    height_in = round(width_in * aspect, 3)

    lines = [
        f"# Generated from {spec_path.name} on demand; verify against the live journal guide.",
        f"figure.figsize: {width_in:.3f}, {height_in:.3f}",
        f"font.size: {base_pt:g}",
        f"axes.titlesize: {base_pt:g}",
        f"axes.labelsize: {base_pt:g}",
        f"xtick.labelsize: {max(base_pt - 1, 5):g}",
        f"ytick.labelsize: {max(base_pt - 1, 5):g}",
        f"legend.fontsize: {max(base_pt - 1, 5):g}",
        f"figure.titlesize: {base_pt + 1:g}",
        f"lines.linewidth: {float(spec.get('line_width', 1.0)):g}",
        f"lines.markersize: {float(spec.get('marker_size', 3.2)):g}",
        f"axes.linewidth: {float(spec.get('axes_linewidth', 0.7)):g}",
    ]
    if font_kind == "serif":
        lines += ["font.family: serif", f"font.serif: {', '.join(fonts)}", "mathtext.fontset: stix"]
    else:
        lines += ["font.family: sans-serif", f"font.sans-serif: {', '.join(fonts)}"]
    for key, value in (spec.get("extra_rc") or {}).items():
        lines.append(f"{key}: {value}")

    target = STYLE_DIR / f"{name}.mplstyle"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")

    registered = False
    if register:
        meta = load_meta()
        meta["journals"][name] = {
            "label": spec.get("label", name),
            "single_column_mm": single_mm,
            "double_column_mm": float(spec.get("double_column_mm", single_mm * 2)),
            "base_font_pt": base_pt,
            "min_font_pt": float(spec.get("min_font_pt", max(base_pt - 2, 5))),
            "fonts": fonts,
            "font_kind": font_kind,
            "vector_formats": spec.get("vector_formats", ["pdf", "eps"]),
            "raster_formats": spec.get("raster_formats", ["tiff"]),
            "source": spec.get("source", "user spec"),
            "notes": spec.get("notes", ""),
        }
        JOURNALS_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        registered = True

    print(
        json.dumps(
            {"ok": True, "style_file": str(target), "registered": registered, "journal_entry": spec.get("label", name)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="list every journal style with its specs")
    group.add_argument("--show", metavar="STYLE", help="dump merged rcParams for one style")
    group.add_argument("--apply", metavar="STYLE", help="print the snippet that applies a style")
    group.add_argument("--preview", metavar="STYLE", help="render a diagnostic preview at target size")
    group.add_argument("--from-spec", metavar="JSON", help="generate a style from a JSON spec")
    parser.add_argument("-o", "--outdir", default="style_preview", help="preview output directory")
    parser.add_argument("--scale", type=float, default=1.0, help="preview canvas scale (does not change font sizes)")
    parser.add_argument("--register", action="store_true", help="with --from-spec, also add the entry to journals.json")
    parser.add_argument("--json", action="store_true", help="JSON only (list)")
    args = parser.parse_args(argv)

    if args.list:
        return cmd_list(args.json)
    if args.show:
        return cmd_show(args.show)
    if args.apply:
        return cmd_apply(args.apply)
    if args.preview:
        return cmd_preview(args.preview, Path(args.outdir), args.scale)
    if args.from_spec:
        return cmd_from_spec(Path(args.from_spec), args.register)
    parser.error("no command given")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
