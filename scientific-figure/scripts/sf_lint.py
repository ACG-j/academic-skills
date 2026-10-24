# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy", "pillow"]
# ///
"""Three-layer figure lint: static source analysis, runtime layout, rendered-image checks.

The layers answer different questions and deliberately do not overlap:

* **L1 static** (`--static`) parses the plotting script without running it. It checks
  the things a machine can read from source: reproducibility, axis labels and units,
  uncertainty, sample size, forbidden colormaps, equal grids, export format. Fast,
  CI-safe, and blind to anything that depends on the data.
* **L2 runtime** (`--run`) executes the script with matplotlib on Agg, hooks
  `savefig`, and measures real text boxes from the renderer: collisions, legend
  overlap, panel overlap, tiny fonts, crowded ticks, content outside the canvas.
  This catches what source analysis cannot — the layout that actually came out.
* **L3 image** (`--image`) inspects a rendered PNG: blank margins, clipped edges,
  near-white content, effective ink density. It cannot judge aesthetics; that is
  the visual review's job (`sf_crop.py` + an image-capable model).

Usage:
    uv run sf_lint.py --static plot.py
    uv run sf_lint.py --run plot.py
    uv run sf_lint.py --image review.png
    uv run sf_lint.py --all plot.py            # static + run

Every mode prints JSON on stdout. Exit code 1 when a finding is blocking.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
import runpy
import sys
import traceback
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SEVERITY_ORDER = {"info": 0, "warn": 1, "error": 2}

BAD_CMAPS = (
    "jet",
    "rainbow",
    "hsv",
    "gist_rainbow",
    "gist_ncar",
    "nipy_spectral",
    "flag",
    "prism",
    "gist_stern",
)
DATA_READERS = (
    "read_csv",
    "read_table",
    "read_excel",
    "read_parquet",
    "read_json",
    "load",
    "loadtxt",
    "genfromtxt",
    "load_npz",
    "read_hdf",
)
SAVE_CALLS = ("savefig", "save", "savez", "export")
UNCERTAINTY_CALLS = ("fill_between", "fill_betweenx", "errorbar", "boxplot", "violinplot")
MIN_FONT_PT = 6.0
MAX_FONT_PT = 14.0
OVERLAP_FRAC = 0.08
TICK_OVERLAP_FRAC = 0.12
# Largest gutter between two matrix cells that still counts as a shared seam.
SEAM_GAP = 0.04
# Share of a text box's area that may be crossed by a plotted line before the label
# counts as sitting on top of the data.
TEXT_OVER_LINE_FRAC = 0.10
# LaTeX escapes that only render correctly inside mathtext. Outside it, matplotlib
# prints the backslash literally.
LATEX_ESCAPES = ("\\_", "\\%", "\\&", "\\#", "\\$", "\\{", "\\}")
MIN_REVIEW_PX = 800


@dataclass
class Finding:
    layer: str
    check: str
    severity: str
    message: str
    location: str = ""
    fix: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "check": self.check,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
            "fix": self.fix,
        }


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)

    def add(self, layer: str, check: str, severity: str, message: str, location: str = "", fix: str = "") -> None:
        self.findings.append(Finding(layer, check, severity, message, location, fix))

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    def summary(self) -> dict[str, int]:
        counts = {"error": 0, "warn": 0, "info": 0}
        for finding in self.findings:
            counts[finding.severity] += 1
        return counts


# --------------------------------------------------------------------------- #
# L1 — static source analysis
# --------------------------------------------------------------------------- #
def _call_tail(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _str_args(node: ast.Call) -> list[str]:
    return [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]


def _has_unit(label: str) -> bool:
    """A label carries a unit when it has (...) / [...] / $math$ / a slash unit."""
    return bool(re.search(r"\(.+?\)|\[.+?\]|\$[^$]+\$|/[A-Za-z]", label))


def _inline_literal_size(tree: ast.AST) -> int:
    biggest = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            if len(node.elts) <= 20:
                continue
            if all(
                isinstance(e, ast.Constant) and isinstance(e.value, (int, float))
                or isinstance(e, ast.UnaryOp) and isinstance(e.operand, ast.Constant)
                for e in node.elts
            ):
                biggest = max(biggest, len(node.elts))
    return biggest


def analyse_static(path: Path, report: Report) -> None:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.add("L1", "read", "error", f"cannot read script: {exc}", str(path))
        return
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        report.add("L1", "parse", "error", f"script does not parse: {exc}", f"line {exc.lineno}")
        return

    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    tails = [_call_tail(c) for c in calls]
    tail_set = set(tails)

    # --- reproducibility ---
    reads_data = bool(tail_set & set(DATA_READERS))
    uses_rng = bool(re.search(r"np\.random|default_rng|\brandom\.", source))
    seeded = bool(re.search(r"default_rng\(\s*\d|np\.random\.seed\(|\brandom\.seed\(|seed\s*=\s*\d", source))
    if reads_data:
        report.add("L1", "data-source", "info", "reads data from a file", str(path))
    elif uses_rng and seeded:
        report.add(
            "L1",
            "data-source",
            "warn",
            "no file read; uses seeded synthetic data",
            str(path),
            "acceptable for a demo, but a paper figure should read real data from a file",
        )
    else:
        report.add(
            "L1",
            "data-source",
            "error",
            "no data file read and no seeded RNG — the figure is not reproducible",
            str(path),
            "read from a path (pd.read_csv(...)) or seed the RNG (np.random.default_rng(0))",
        )

    big = _inline_literal_size(tree)
    if big:
        report.add(
            "L1",
            "inline-data",
            "error",
            f"inline literal with {big} numeric elements",
            str(path),
            "move the data to a file and read it; inline arrays are not reviewable",
        )

    if uses_rng and not seeded:
        report.add("L1", "seed", "warn", "randomness without a fixed seed", str(path), "seed it so reruns match")

    # --- style application ---
    style_calls = tails.count("use") + tails.count("paper_style") + tails.count("apply_style")
    style_in_source = bool(re.search(r"\.mplstyle|style\.use|rcParams\.update", source))
    if style_in_source:
        report.add("L1", "style", "info", "a style sheet or rcParams block is applied", str(path))
    else:
        report.add(
            "L1",
            "style",
            "warn",
            "no style sheet applied — this renders with matplotlib defaults",
            str(path),
            "apply styles/base.mplstyle plus a journal sheet via plt.style.use([...])",
        )

    # --- export ---
    savefig_calls = [c for c in calls if _call_tail(c) in ("savefig", "save")]
    formats: set[str] = set()
    unresolved: list[str] = []
    for call in savefig_calls:
        literal_args = _str_args(call)
        for arg in literal_args:
            match = re.search(r"\.([A-Za-z0-9]+)$", arg)
            if match:
                formats.add(match.group(1).lower())
        for keyword in call.keywords:
            if keyword.arg == "format" and isinstance(keyword.value, ast.Constant):
                formats.add(str(keyword.value.value).lower())
        # A dynamically built filename such as f"fig.{ext}" still names its
        # extensions elsewhere in the source; look for a literal format list.
        if not literal_args:
            for inner in ast.walk(call):
                if isinstance(inner, ast.JoinedStr):
                    unresolved.append(ast.unparse(inner)[:60])
    # A loop over extensions (``for ext in ("png", "pdf")``) writes every listed format.
    for match in re.finditer(r"for\s+\w+\s+in\s*[\(\[]([^\)\]]*)[\)\]]", source):
        for ext in re.findall(r"['\"]([a-z]{2,5})['\"]", match.group(1)):
            formats.add(ext.lower())
    for match in re.finditer(r"formats\s*=\s*[\(\[]([^\)\]]+)[\)\]]", source):
        for ext in re.findall(r"['\"]([a-z]{2,5})['\"]", match.group(1)):
            formats.add(ext.lower())

    if not savefig_calls:
        report.add("L1", "export", "error", "no savefig/save call — nothing is written to disk", str(path))
    elif not formats:
        report.add(
            "L1",
            "export",
            "warn",
            "savefig called but the output format could not be resolved",
            str(path),
            "use literal filenames such as savefig('fig1.pdf') so the format is reviewable",
        )
    else:
        report.facts["formats"] = sorted(formats)
        has_vector = bool(formats & {"pdf", "svg", "eps", "pgf"})
        if not has_vector:
            report.add(
                "L1",
                "export",
                "error",
                f"only raster output ({', '.join(sorted(formats))}) — no vector format",
                str(path),
                "also save PDF or SVG; journals require vector line art",
            )
        if "png" not in formats and "tif" not in formats and "tiff" not in formats:
            report.add(
                "L1",
                "export",
                "info",
                "no raster output — a PNG is convenient for visual review",
                str(path),
                "also save a PNG at dpi>=200 for the review pass",
            )

    # --- labels and units ---
    xlabels = re.findall(r"set_xlabel\(\s*[rf]?['\"](.*?)['\"]", source)
    ylabels = re.findall(r"set_ylabel\(\s*[rf]?['\"](.*?)['\"]", source)
    report.facts["x_labels"] = xlabels
    report.facts["y_labels"] = ylabels
    if xlabels and ylabels:
        report.add("L1", "labels", "info", "both axes are labelled", str(path))
    elif xlabels or ylabels:
        report.add(
            "L1",
            "labels",
            "warn",
            "only one axis is labelled",
            str(path),
            "label both axes; every quantitative axis carries a label",
        )
    else:
        report.add(
            "L1",
            "labels",
            "error",
            "no axis labels found",
            str(path),
            "set_xlabel/set_ylabel with the quantity and its unit",
        )
    labels = xlabels + ylabels
    if labels and not any(_has_unit(label) for label in labels):
        # A number on a quantitative axis is meaningless without its unit: this is a
        # defect, not a style preference. The one exception is a genuinely
        # dimensionless quantity, which a symbol in the label already signals.
        report.add(
            "L1",
            "units",
            "error",
            "no axis label carries a unit or symbol — the plotted numbers have no meaning",
            str(path),
            'write "Time $t$ (s)", or name the dimensionless quantity ("Score (a.u.)")',
        )
    elif labels:
        report.add("L1", "units", "info", "at least one axis label carries a unit or symbol", str(path))

    # --- uncertainty and sample size ---
    has_uncertainty = bool(tail_set & set(UNCERTAINTY_CALLS)) or bool(
        re.search(r"\byerr\b|\bxerr\b|axhspan|axvspan|\bCI\b|confidence", source)
    )
    if has_uncertainty:
        report.add("L1", "uncertainty", "info", "uncertainty is drawn (band, bars, or distribution)", str(path))
    else:
        report.add(
            "L1",
            "uncertainty",
            "warn",
            "no uncertainty drawn on the figure",
            str(path),
            "add a CI band or error bars, or state on the figure why none applies",
        )
    if re.search(r"[Nn]\s*=\s*\{?\d|\$[Nn]\$\s*=|n\s*=\s*len|N_\w+\s*=", source):
        report.add("L1", "sample-size", "info", "sample size appears in the source", str(path))
    else:
        report.add(
            "L1",
            "sample-size",
            "info",
            "N is not annotated",
            str(path),
            "a reader asks 'N=?'; annotate the sample size per series when it varies",
        )

    # --- colormaps ---
    for cmap in BAD_CMAPS:
        if re.search(rf"cmap\s*=\s*['\"]{cmap}['\"]|set_cmap\(\s*['\"]{cmap}", source):
            report.add(
                "L1",
                "colormap",
                "error",
                f"perceptually non-uniform colormap '{cmap}'",
                str(path),
                "use viridis/cividis for magnitude, RdBu_r for signed values",
            )
            break

    # --- subplot geometry ---
    for call in calls:
        if _call_tail(call) == "subplots":
            ints = [a.value for a in call.args if isinstance(a, ast.Constant) and isinstance(a.value, int)]
            keywords = {k.arg for k in call.keywords}
            has_ratio = "gridspec_kw" in keywords or "width_ratios" in source or "height_ratios" in source
            if len(ints) >= 2 and ints[0] >= 2 and ints[1] >= 2 and not has_ratio:
                report.add(
                    "L1",
                    "layout",
                    "warn",
                    f"equal {ints[0]}x{ints[1]} grid with no size ratios",
                    str(path),
                    "choose one hero panel and shrink the rest, e.g. gridspec_kw={'width_ratios':[2,1]}",
                )
            break

    # --- honesty checks a source can reveal ---
    if re.search(r"set_ylim\(\s*[^0)]", source) and re.search(r"\.bar\(", source):
        report.add(
            "L1",
            "truncated-axis",
            "warn",
            "bar chart with an explicit ylim — bars must start at zero",
            str(path),
            "remove the nonzero bottom, or switch to a dot/lollipop plot that encodes position",
        )
    if re.search(r"twiny|secondary_yaxis|twinx", source):
        report.add(
            "L1",
            "dual-axis",
            "warn",
            "dual y-axis in use",
            str(path),
            "only justified when the two quantities are physically linked; label both axes' colours",
        )
    if re.search(r"set_(x|y)scale\(\s*['\"]log", source) and not re.search(r"log|对数", source[:400]):
        report.add(
            "L1",
            "log-axis",
            "info",
            "log scale applied — make sure the axis label says so",
            str(path),
            "state the transform in the axis label or caption, and define the policy for zero/negative values",
        )


# --------------------------------------------------------------------------- #
# L2 — runtime layout analysis
# --------------------------------------------------------------------------- #
def _overlap_fraction(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Overlap area divided by the smaller box area."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    width = min(ax1, bx1) - max(ax0, bx0)
    height = min(ay1, by1) - max(ay0, by0)
    if width <= 0 or height <= 0:
        return 0.0
    inter = width * height
    area_a = max((ax1 - ax0) * (ay1 - ay0), 1e-9)
    area_b = max((bx1 - bx0) * (by1 - by0), 1e-9)
    return inter / min(area_a, area_b)


def _bbox(text: Any, renderer: Any) -> tuple[float, float, float, float] | None:
    try:
        box = text.get_window_extent(renderer)
    except Exception:
        return None
    if box.width <= 0 or box.height <= 0:
        return None
    return (box.x0, box.y0, box.x1, box.y1)


def _canvas_margins(fig: Any, renderer: Any) -> tuple[float, float, float, float]:
    """Extra space `bbox_inches='tight'` would add around the figure.

    A figure saved with a tight bbox grows to contain its artists, so text that
    extends past `fig.bbox` is not clipped — it widens the saved canvas. Checking
    against the raw canvas therefore reports false clipping on every figure whose
    labels reach the edge, which is most correct figures. These margins describe
    how far content legitimately extends beyond the nominal canvas.
    """
    left = top = 0.0
    right, bottom = float(fig.bbox.width), float(fig.bbox.height)
    for text in _collect_texts(fig)[:]:
        box = _bbox(text[0], renderer)
        if box is None:
            continue
        left = min(left, box[0])
        top = min(top, box[1])
        right = max(right, box[2])
        bottom = max(bottom, box[3])
    return (left, top, right, bottom)


def _savefig_bbox_mode(path: Path) -> str | None:
    """Best-effort read of the savefig bbox mode from the script source."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"bbox_inches\s*=\s*['\"]([a-z_]+)['\"]", source)
    if match:
        return match.group(1)
    if "savefig.bbox" in source:
        return "tight" if "tight" in source else None
    return None


# Roles that are expected to sit next to each other. An x-tick label and a y-tick
# label sharing a corner is how matplotlib draws axes, not a defect; the same pair of
# texts overlapping in the middle of the plot is a defect.
ADJACENT_ROLES = {("xtick", "ytick")}


def _collect_texts(fig: Any) -> list[tuple[Any, Any, str]]:
    """Every visible Text object with non-empty content, its owner axes, and its role."""
    out: list[tuple[Any, Any, str]] = []
    for ax in fig.axes:
        for text in (ax.title,):
            if text.get_visible() and text.get_text().strip():
                out.append((text, ax, "title"))
        for text in (ax.xaxis.label, ax.yaxis.label):
            if text.get_visible() and text.get_text().strip():
                out.append((text, ax, "axis-label"))
        for text in ax.texts:
            if text.get_visible() and text.get_text().strip():
                out.append((text, ax, "annotation"))
        for axis, role in ((ax.xaxis, "xtick"), (ax.yaxis, "ytick")):
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                for label in (tick.label1, tick.label2):
                    if label.get_visible() and label.get_text().strip():
                        out.append((label, ax, role))
        legend = ax.get_legend()
        if legend is not None and legend.get_visible():
            for text in legend.get_texts():
                if text.get_text().strip():
                    out.append((text, ax, "legend"))
    for text in fig.texts:
        if text.get_visible() and text.get_text().strip():
            out.append((text, None, "figure-text"))
    return out


def _font_size(text: Any) -> float:
    try:
        return float(text.get_fontsize())
    except Exception:
        return 0.0


def _data_points(ax: Any) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for line in ax.get_lines():
        data = line.get_xydata()
        if data is None or len(data) == 0:
            continue
        try:
            display = ax.transData.transform(data)
        except Exception:
            continue
        points.extend((float(x), float(y)) for x, y in display)
        if len(points) > 4000:
            break
    for collection in ax.collections:
        try:
            offsets = collection.get_offsets()
        except Exception:
            continue
        if offsets is None or len(offsets) == 0:
            continue
        try:
            display = ax.transData.transform(offsets)
        except Exception:
            continue
        points.extend((float(x), float(y)) for x, y in display)
        if len(points) > 4000:
            break
    return points


def _line_segments(ax: Any) -> list[tuple[float, float, float, float]]:
    """Every plotted line segment in display coordinates.

    Sampling the data points is enough for "does a legend cover a marker", but a label
    sitting on a curve is crossed *between* samples, so the segments themselves are
    what the text-over-line check needs.
    """
    segments: list[tuple[float, float, float, float]] = []
    for line in ax.get_lines():
        data = line.get_xydata()
        if data is None or len(data) < 2:
            continue
        try:
            display = ax.transData.transform(data)
        except Exception:
            continue
        for index in range(len(display) - 1):
            x0, y0 = float(display[index][0]), float(display[index][1])
            x1, y1 = float(display[index + 1][0]), float(display[index + 1][1])
            segments.append((x0, y0, x1, y1))
        if len(segments) > 3000:
            break
    for patch in ax.patches:
        # Curved edges (network overlays, FancyArrowPatch) are drawn as paths; sampling
        # their vertices is enough to detect a label sitting on them.
        try:
            path = patch.get_path()
            transform = patch.get_transform()
        except Exception:
            continue
        try:
            vertices = transform.transform(path.vertices)
        except Exception:
            continue
        for index in range(len(vertices) - 1):
            x0, y0 = float(vertices[index][0]), float(vertices[index][1])
            x1, y1 = float(vertices[index + 1][0]), float(vertices[index + 1][1])
            segments.append((x0, y0, x1, y1))
    return segments


def _segment_crosses_box(
    segment: tuple[float, float, float, float],
    box: tuple[float, float, float, float],
    samples: int = 24,
) -> int:
    """Count how many sample points of the segment fall inside the box."""
    x0, y0, x1, y1 = segment
    bx0, by0, bx1, by1 = box
    # Cheap rejection: the segment's own bounds cannot reach the box.
    if max(x0, x1) < bx0 or min(x0, x1) > bx1 or max(y0, y1) < by0 or min(y0, y1) > by1:
        return 0
    inside = 0
    for step in range(samples + 1):
        t = step / samples
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        if bx0 <= x <= bx1 and by0 <= y <= by1:
            inside += 1
    return inside


def _check_matrix_seams(fig: Any, label: str, report: Report) -> None:
    """Report a grid of cells where drawn and undrawn neighbours meet.

    A matrix layout often leaves the upper triangle as ``ax.axis("off")`` cells. If the
    drawn cells keep their frames, every seam against an undrawn neighbour terminates in
    mid-air: the reader sees a border that stops halfway and a corner that does not
    close. Either every cell in the block is drawn, or none is.
    """
    cells: list[tuple[int, Any, Any]] = []
    for index, ax in enumerate(fig.axes):
        if not ax.get_frame_on():
            continue
        try:
            cells.append((index, ax, ax.get_position()))
        except Exception:
            continue
    if len(cells) < 4:
        return

    drawn = [c for c in cells if c[1].axison]
    undrawn = [c for c in cells if not c[1].axison]
    if not drawn or not undrawn:
        return

    # A seam exists when two cell boxes touch (within a few pixels) and their facing
    # edges overlap substantially.
    touching = 0
    for _, _axa, ba in drawn:
        for _, _axb, bb in undrawn:
            horizontal = abs(ba.x1 - bb.x0) <= SEAM_GAP or abs(bb.x1 - ba.x0) <= SEAM_GAP
            vertical = abs(ba.y1 - bb.y0) <= SEAM_GAP or abs(bb.y1 - ba.y0) <= SEAM_GAP
            overlap_y = min(ba.y1, bb.y1) - max(ba.y0, bb.y0)
            overlap_x = min(ba.x1, bb.x1) - max(ba.x0, bb.x0)
            if (horizontal and overlap_y > 0.02) or (vertical and overlap_x > 0.02):
                touching += 1
    if touching:
        report.add(
            "L2",
            "open-seam",
            "warn",
            f"{touching} seam(s) where a framed cell meets an undrawn neighbour — borders stop mid-air",
            label,
            'draw every cell in the block (leave the reserved ones empty but framed), '
            'or drop the frames entirely',
        )


def _check_text_over_line(fig: Any, label: str, report: Report) -> None:
    """Report annotations that sit on top of a plotted line.

    A label crossed by the very curve it annotates is unreadable, and the collision
    check cannot see it: the text overlaps a *line*, not another text. This is what
    makes a network overlay's node labels run through the arcs.
    """
    renderer = fig.canvas.get_renderer()
    # Both the text boxes and the line segments must live in the same pixel space.
    # fig.dpi and the canvas dpi can differ (a figure drawn at 150 dpi and saved at 300
    # is the common case), so the ratio is applied to the text box.
    ratio = 1.0
    try:
        if fig.dpi:
            ratio = float(fig.canvas.get_renderer().points_to_pixels(1)) / float(
                fig.dpi / 72.0
            )
    except Exception:
        ratio = 1.0
    for ax in fig.axes:
        segments = _line_segments(ax)
        if not segments:
            continue
        for text, owner, role in _collect_texts(fig):
            if owner is not ax or role not in ("annotation", "figure-text"):
                continue
            content = text.get_text().strip()
            if not content:
                continue
            box = _bbox(text, renderer)
            if box is None:
                continue
            crossings = sum(_segment_crosses_box(segment, box) for segment in segments)
            # 24 samples per segment, so a crossing line contributes a handful; a label
            # merely near a line contributes none.
            if crossings >= 3:
                report.add(
                    "L2",
                    "text-over-line",
                    "warn",
                    f"annotation '{_short(content)}' is crossed by a plotted line",
                    label,
                    "move the label clear of the line, or add a white bbox behind it",
                )
                break


def _check_literal_escapes(fig: Any, label: str, report: Report) -> None:
    r"""Report text that will print a backslash literally.

    A label such as ``Leaf\_type`` written outside mathtext renders with the backslash
    drawn: the reader sees ``Leaf\_type``. It is the most common copy-paste defect when
    moving a label from LaTeX into matplotlib, and static analysis cannot see it — the
    source looks exactly like a correct mathtext escape.
    """
    offenders: list[str] = []
    for text, _ax, _role in _collect_texts(fig):
        content = text.get_text()
        if "\\" not in content:
            continue
        # A mathtext span ($...$) legitimately uses backslash commands.
        stripped = re.sub(r"\$[^$]*\$", "", content)
        if "\\" in stripped:
            offenders.append(content)
    if offenders:
        sample = ", ".join(repr(item)[:32] for item in offenders[:3])
        report.add(
            "L2",
            "literal-escape",
            "error",
            f"{len(offenders)} label(s) render a backslash literally: {sample}",
            label,
            "drop the escape (use 'Leaf_type'), or wrap the label in $...$ for mathtext",
        )


def inspect_figure(fig: Any, label: str, report: Report) -> None:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    fig_box = fig.bbox
    axes_boxes = [(ax, ax.get_window_extent(renderer)) for ax in fig.axes]

    _check_literal_escapes(fig, label, report)
    _check_text_over_line(fig, label, report)
    _check_matrix_seams(fig, label, report)

    # --- tiny and oversized fonts ---
    too_small: dict[float, int] = {}
    too_large: dict[float, int] = {}
    for text, _ax, _role in _collect_texts(fig):
        size = _font_size(text)
        if size <= 0:
            continue
        if size < MIN_FONT_PT:
            too_small[size] = too_small.get(size, 0) + 1
        elif size > MAX_FONT_PT:
            too_large[size] = too_large.get(size, 0) + 1
    if too_small:
        sizes = ", ".join(f"{s:g} pt x{n}" for s, n in sorted(too_small.items()))
        report.add(
            "L2",
            "font-size",
            "error",
            f"text below {MIN_FONT_PT} pt at final size ({sizes})",
            label,
            "raise the font size; text under 6 pt is unreadable in print",
        )
    if too_large:
        sizes = ", ".join(f"{s:g} pt x{n}" for s, n in sorted(too_large.items()))
        report.add("L2", "font-size", "info", f"text above {MAX_FONT_PT} pt ({sizes})", label, "check the size hierarchy")

    # --- text collisions ---
    texts = [(t, ax, role, _bbox(t, renderer)) for t, ax, role in _collect_texts(fig)]
    texts = [(t, ax, role, box) for t, ax, role, box in texts if box is not None]
    collisions = 0
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            ta, axa, rolea, ba = texts[i]
            tb, axb, roleb, bb = texts[j]
            if _overlap_fraction(ba, bb) <= OVERLAP_FRAC:
                continue
            # The same string in the same role is the same label counted twice
            # (major and minor tick objects can both exist at one position).
            if ta.get_text().strip() == tb.get_text().strip() and rolea == roleb:
                continue
            # An x-tick label meeting a y-tick label at the origin is how axes are
            # drawn. Only treat it as a defect when the overlap is substantial, which
            # means the corner is genuinely cramped rather than merely adjacent.
            if {rolea, roleb} in ADJACENT_ROLES and axa is axb:
                if _overlap_fraction(ba, bb) < 0.35:
                    continue
            collisions += 1
            if collisions <= 6:
                where_a = _axes_index(fig, axa)
                where_b = _axes_index(fig, axb)
                if where_a == where_b:
                    location = f"axes {where_a}"
                else:
                    location = f"axes {where_a} vs {where_b}"
                report.add(
                    "L2",
                    "text-collision",
                    "error",
                    f"{rolea} '{_short(ta.get_text())}' overlaps {roleb} '{_short(tb.get_text())}'",
                    f"{label} @ {location}",
                    "increase the gap between these subplots (wspace/hspace), or thin the ticks",
                )
    if collisions > 6:
        report.add("L2", "text-collision", "error", f"{collisions} text collisions total", label, "reduce label density")

    # --- text far outside the canvas ---
    # A tight bbox grows the saved canvas to contain every artist, so modest
    # overflow is normal. Only report text that escapes the canvas by a large
    # margin, which indicates a layout error rather than ordinary label extent.
    escape = max(fig_box.width, fig_box.height) * 0.12
    for text, _ax, _role, box in texts:
        if box[0] < -escape or box[1] < -escape or box[2] > fig_box.width + escape or box[3] > fig_box.height + escape:
            report.add(
                "L2",
                "clipped-text",
                "error",
                f"'{_short(text.get_text())}' extends far outside the canvas",
                label,
                "increase the figure margins, or reposition the annotation/legend",
            )
            break

    # --- legend over data ---
    for ax, ax_box in axes_boxes:
        legend = ax.get_legend()
        if legend is None or not legend.get_visible():
            continue
        legend_box = legend.get_window_extent(renderer)
        points = _data_points(ax)
        if points:
            inside = sum(
                1
                for x, y in points
                if legend_box.x0 <= x <= legend_box.x1 and legend_box.y0 <= y <= legend_box.y1
            )
            share = inside / len(points)
            if share > 0.12:
                report.add(
                    "L2",
                    "legend-overlap",
                    "warn",
                    f"legend covers {share * 100:.0f}% of the plotted points",
                    label,
                    "move the legend outside the axes, or place it in genuinely empty space",
                )
        # Legend outside its own axes entirely
        if _overlap_fraction(
            (legend_box.x0, legend_box.y0, legend_box.x1, legend_box.y1),
            (ax_box.x0, ax_box.y0, ax_box.x1, ax_box.y1),
        ) < 0.2 and (legend_box.x0 > ax_box.x1 or legend_box.x1 < ax_box.x0):
            report.add(
                "L2",
                "legend-placement",
                "info",
                "legend sits outside the axes",
                label,
                "fine if intentional; verify the surrounding margin is large enough",
            )

    # --- panel overlap ---
    for i in range(len(axes_boxes)):
        for j in range(i + 1, len(axes_boxes)):
            axa, boxa = axes_boxes[i]
            axb, boxb = axes_boxes[j]
            frac = _overlap_fraction(
                (boxa.x0, boxa.y0, boxa.x1, boxa.y1),
                (boxb.x0, boxb.y0, boxb.x1, boxb.y1),
            )
            if frac > 0.05:
                inset = axa.get_label() == "<colorbar>" or axb.get_label() == "<colorbar>"
                # Only framed axes are panels. A frameless axes is annotation or a
                # hand-built legend, and overlapping a panel on purpose is exactly how
                # those are composed.
                framed = axa.get_frame_on() and axb.get_frame_on()
                overlay = _is_transparent_overlay(axa) or _is_transparent_overlay(axb)
                if framed and not inset and not overlay:
                    report.add(
                        "L2",
                        "panel-overlap",
                        "warn",
                        f"two axes overlap by {frac * 100:.0f}%",
                        label,
                        "check gridspec spacing; overlapping panels usually hide a label",
                    )

    # --- tick label crowding ---
    for ax, _ in axes_boxes:
        for axis, name in ((ax.xaxis, "x"), (ax.yaxis, "y")):
            boxes = []
            for tick in axis.get_major_ticks():
                tick_text = tick.label1
                if tick_text.get_visible() and tick_text.get_text().strip():
                    box = _bbox(tick_text, renderer)
                    if box:
                        boxes.append(box)
            boxes.sort(key=lambda b: b[0] if name == "x" else b[1])
            crowded = 0
            for k in range(len(boxes) - 1):
                if _overlap_fraction(boxes[k], boxes[k + 1]) > TICK_OVERLAP_FRAC:
                    crowded += 1
            if crowded:
                report.add(
                    "L2",
                    "tick-crowding",
                    "warn",
                    f"{crowded} overlapping {name}-tick labels",
                    label,
                    "thin the ticks (MaxNLocator), rotate them, or widen the figure",
                )

    # --- empty or data-less axes ---
    for ax, _ in axes_boxes:
        if ax.get_label() == "<colorbar>":
            continue
        has_data = bool(ax.get_lines() or ax.collections or ax.patches or ax.images)
        # A cell that carries only a text label is intentional in a matrix layout
        # (diagonal name boxes), so it is not an empty panel.
        has_text = any(t.get_visible() and t.get_text().strip() for t in ax.texts)
        # ax.axison is False when the axes was switched off with ax.axis("off") — an
        # upper-triangle cell reserved for an overlay, not a forgotten panel.
        drawn = getattr(ax, "axison", True) and ax.get_frame_on()
        # A reserved cell in a matrix layout keeps its frame but has had its ticks
        # cleared; a forgotten panel still shows the default ticks.
        ticks_cleared = (
            len(ax.get_xticks()) == 0
            and len(ax.get_yticks()) == 0
            and not any(
                tick.label1.get_text().strip()
                for axis in (ax.xaxis, ax.yaxis)
                for tick in axis.get_major_ticks()
            )
        )
        if not has_data and not has_text and drawn and not ticks_cleared:
            report.add("L2", "empty-axes", "warn", "an axes has no plotted data", label, "remove the empty panel")

    # --- aspect and canvas facts ---
    report.facts.setdefault("figures", []).append(
        {
            "label": label,
            "size_inches": [round(fig.get_figwidth(), 3), round(fig.get_figheight(), 3)],
            "size_mm": [round(fig.get_figwidth() * 25.4, 1), round(fig.get_figheight() * 25.4, 1)],
            "axes_count": len(fig.axes),
            "dpi": float(fig.dpi),
        }
    )


def _axes_index(fig: Any, ax: Any) -> int:
    """Position of an axes in fig.axes, so a finding can name which panel it is."""
    if ax is None:
        return -1
    for index, candidate in enumerate(fig.axes):
        if candidate is ax:
            return index
    return -1


def _is_transparent_overlay(ax: Any) -> bool:
    """An axes drawn purely for annotation, with no frame of its own.

    ``fig.add_axes(..., frameon=False)`` is how annotation layers, network overlays, and
    hand-built legends are drawn on top of a panel whose geometry they deliberately
    reuse. ``get_frame_on()`` is the only reliable signal — the patch and spine objects
    keep their default properties and are merely skipped at draw time.
    """
    try:
        return not ax.get_frame_on()
    except Exception:
        return False


def _short(value: str, limit: int = 28) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _declared_dependencies(path: Path) -> list[str]:
    """Read the PEP 723 dependency list from a script header, if it has one."""
    try:
        head = path.read_text(encoding="utf-8")[:4000]
    except OSError:
        return []
    match = re.search(r"#\s*dependencies\s*=\s*\[([^\]]*)\]", head)
    if not match:
        return []
    return [item.strip().strip("'\"") for item in match.group(1).split(",") if item.strip()]


def _missing_imports(path: Path) -> list[str]:
    """Third-party modules the script imports that this interpreter cannot import.

    The runtime layer executes the target script in *this* process, so the script's own
    dependencies must already be importable. When they are not, reporting "script failed:
    ModuleNotFoundError" is unhelpful — the script is fine, the harness is under-provisioned.
    Reading the script's PEP 723 header turns that into an actionable instruction.
    """
    import ast
    import importlib.util

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    stdlib = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()
    missing: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module.split(".")[0]]
        else:
            continue
        for name in names:
            if name in stdlib or name in missing:
                continue
            if importlib.util.find_spec(name) is None:
                missing.append(name)
    return missing


def run_runtime(path: Path, report: Report) -> None:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure

    missing = _missing_imports(path)
    if missing:
        declared = _declared_dependencies(path)
        hint = f"uv run --with {' --with '.join(missing)} <this script>"
        report.add(
            "L2",
            "harness-deps",
            "error",
            f"the runtime layer cannot import {', '.join(missing)} — the target script needs them",
            str(path),
            f"re-run with the dependencies available ({hint}), or use --static for this script",
        )
        report.facts["missing_imports"] = missing
        report.facts["declared_dependencies"] = declared
        return

    captured: list[tuple[str, Any]] = []
    original_savefig = Figure.savefig
    counter = {"n": 0}

    def hooked_savefig(self: Any, fname: Any, *args: Any, **kwargs: Any) -> Any:
        counter["n"] += 1
        label = Path(str(fname)).stem if isinstance(fname, (str, Path)) else f"figure{counter['n']}"
        captured.append((label, self))
        return original_savefig(self, fname, *args, **kwargs)

    Figure.savefig = hooked_savefig  # type: ignore[method-assign]
    cwd = path.parent
    previous = Path.cwd()
    # The script under inspection prints whatever it likes ("saved fig1.*"). That output
    # would land in the middle of this tool's JSON on stdout and break every caller that
    # parses it, so the child's stdout is redirected to stderr for the duration.
    real_stdout = sys.stdout
    try:
        import os

        os.chdir(cwd)
        sys.path.insert(0, str(cwd))
        sys.stdout = sys.stderr
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            runpy.run_path(str(path), run_name="__main__")
        sys.stdout = real_stdout
        missing = [str(w.message) for w in caught if "missing from font" in str(w.message).lower()]
        if missing:
            report.add(
                "L2",
                "missing-glyph",
                "error",
                f"missing glyphs in the rendered text: {missing[0][:120]}",
                str(path),
                "set a font that covers the characters (CJK needs an explicit CJK family)",
            )
    except Exception as exc:
        report.add(
            "L2",
            "execute",
            "error",
            f"script failed: {type(exc).__name__}: {exc}",
            str(path),
            "fix the exception; the traceback is in facts.traceback",
        )
        report.facts["traceback"] = traceback.format_exc()[-2000:]
    finally:
        sys.stdout = real_stdout
        os.chdir(previous)
        if str(cwd) in sys.path:
            sys.path.remove(str(cwd))
        Figure.savefig = original_savefig  # type: ignore[method-assign]

    if not captured:
        report.add(
            "L2",
            "no-figure",
            "warn",
            "the script never called savefig — nothing was rendered for inspection",
            str(path),
            "save the figure so the runtime layout can be checked",
        )
        return

    seen: set[int] = set()
    for label, fig in captured:
        if id(fig) in seen:
            continue
        seen.add(id(fig))
        try:
            inspect_figure(fig, label, report)
        except Exception as exc:
            # A crash here means the checks did not run at all. Reporting it as a
            # warning would let a figure pass L2 with zero findings while nothing was
            # inspected, which is worse than a noisy failure.
            report.add(
                "L2",
                "inspect-crashed",
                "error",
                f"the layout checks could not run on '{label}': {type(exc).__name__}: {exc}",
                str(path),
                "this is a bug in sf_lint, not in the figure; the L2 results are incomplete",
            )
            report.facts["inspect_error"] = traceback.format_exc()[-1500:]
    plt.close("all")



# --------------------------------------------------------------------------- #
# L3 — rendered image checks
# --------------------------------------------------------------------------- #
def analyse_image(path: Path, report: Report) -> None:
    try:
        from PIL import Image
        import numpy as np
    except Exception as exc:
        report.add("L3", "import", "warn", f"image analysis unavailable: {exc}", str(path))
        return
    try:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            array = np.asarray(rgb, dtype=np.uint8)
    except Exception as exc:
        report.add("L3", "read", "error", f"cannot read image: {exc}", str(path))
        return

    report.facts["image"] = {"width": width, "height": height, "path": str(path)}
    if width < MIN_REVIEW_PX:
        report.add(
            "L3",
            "review-resolution",
            "warn",
            f"{width} px wide — detail review will be unreliable",
            str(path),
            "render the review PNG at 200 dpi or higher",
        )

    # Ink = pixels meaningfully darker than the background.
    luminance = array.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    ink = luminance < 240
    ink_share = float(ink.mean())
    report.facts["ink_share"] = round(ink_share, 4)
    if ink_share < 0.005:
        report.add("L3", "ink", "error", "almost no visible content (under 0.5% ink)", str(path), "the figure may be blank")

    # Content touching the border suggests clipping.
    border = max(1, min(width, height) // 200)
    edges = {
        "left": ink[:, :border].any(axis=0).mean(),
        "right": ink[:, -border:].any(axis=0).mean(),
        "top": ink[:border, :].any(axis=1).mean(),
        "bottom": ink[-border:, :].any(axis=1).mean(),
    }
    clipped = [side for side, share in edges.items() if share > 0.9]
    if clipped:
        report.add(
            "L3",
            "edge-clipping",
            "warn",
            f"content reaches the {', '.join(clipped)} edge(s) — likely clipped",
            str(path),
            "increase margins or save with bbox_inches='tight'",
        )

    # Blank margin balance: a very lopsided margin usually means a misplaced legend.
    rows = np.where(ink.any(axis=1))[0]
    cols = np.where(ink.any(axis=0))[0]
    if len(rows) and len(cols):
        top, bottom = int(rows[0]), height - 1 - int(rows[-1])
        left, right = int(cols[0]), width - 1 - int(cols[-1])
        report.facts["margins_px"] = {"top": top, "bottom": bottom, "left": left, "right": right}
        horizontal = max(left, right) / max(width, 1)
        if horizontal > 0.22:
            report.add(
                "L3",
                "margin-balance",
                "info",
                f"horizontal margins are lopsided (left {left}px, right {right}px)",
                str(path),
                "often a legend or annotation placed outside the axes; verify it is intentional",
            )


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #
def build_payload(report: Report, target: str, layers: list[str]) -> dict[str, Any]:
    counts = report.summary()
    return {
        "ok": counts["error"] == 0,
        "target": target,
        "layers": layers,
        "summary": counts,
        "findings": [f.as_dict() for f in sorted(report.findings, key=lambda f: -SEVERITY_ORDER[f.severity])],
        "facts": report.facts,
    }


def print_human(payload: dict[str, Any]) -> None:
    print(f"figure lint — {payload['target']} [{', '.join(payload['layers'])}]", file=sys.stderr)
    for finding in payload["findings"]:
        mark = {"error": "FAIL", "warn": "warn", "info": "info"}[finding["severity"]]
        location = f" @ {finding['location']}" if finding["location"] else ""
        print(f"  [{mark}] {finding['layer']}/{finding['check']}: {finding['message']}{location}", file=sys.stderr)
        if finding["severity"] == "error" and finding["fix"]:
            print(f"         fix: {finding['fix']}", file=sys.stderr)
    summary = payload["summary"]
    verdict = "PASS" if payload["ok"] else "BLOCKED"
    print(
        f"{verdict} — {summary['error']} error(s), {summary['warn']} warning(s), {summary['info']} info",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--static", metavar="PY", help="static source analysis of a plotting script")
    parser.add_argument("--run", metavar="PY", help="execute the script and inspect the rendered layout")
    parser.add_argument("--image", metavar="PNG", help="inspect a rendered image")
    parser.add_argument("--all", metavar="PY", help="static + runtime in one pass")
    parser.add_argument("--json", action="store_true", help="JSON only")
    args = parser.parse_args(argv)

    report = Report()
    layers: list[str] = []
    target = ""

    if args.static or args.all:
        script = Path((args.static or args.all)).resolve()
        target = str(script)
        layers.append("L1")
        analyse_static(script, report)
    if args.run or args.all:
        script = Path((args.run or args.all)).resolve()
        target = str(script)
        layers.append("L2")
        run_runtime(script, report)
    if args.image:
        image = Path(args.image).resolve()
        target = str(image)
        layers.append("L3")
        analyse_image(image, report)

    if not layers:
        parser.error("give at least one of --static / --run / --image / --all")

    payload = build_payload(report, target, layers)
    if not args.json:
        print_human(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
