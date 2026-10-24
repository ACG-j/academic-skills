# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy", "pillow"]
# ///
"""Environment self-check for the scientific-figure skill.

Reports what the current machine can and cannot do before a figure task starts,
so failures surface here instead of halfway through a render. Every probe is
independent: one missing tool never aborts the rest.

Usage:
    uv run sf_doctor.py             # human summary + JSON on stdout
    uv run sf_doctor.py --json      # JSON only
    uv run sf_doctor.py --fix       # also print copy-paste repair commands

Exit code 0 when every *required* capability is present, 1 otherwise.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import warnings
from dataclasses import dataclass, field
from typing import Any

REQUIRED_PACKAGES = ("matplotlib", "numpy", "PIL")
OPTIONAL_PACKAGES = ("pandas", "scienceplots", "matplot2tikz", "seaborn")
REQUIRED_COMMANDS = ("uv",)
LATEX_COMMANDS = ("xelatex", "pdflatex")
POPPLER_COMMANDS = ("pdfcrop", "pdftoppm", "pdffonts")
IMAGE_COMMANDS = ("inkscape", "magick")
LATEX_PACKAGES = (
    "pgfplots.sty",
    "tikz.sty",
    "standalone.cls",
    "booktabs.sty",
    "siunitx.sty",
    "subcaption.sty",
    "threeparttable.sty",
    "xcolor.sty",
)
CJK_PACKAGES = ("ctex.sty", "xeCJK.sty")
FONT_CANDIDATES = {
    "serif": ("Times New Roman", "Nimbus Roman", "DejaVu Serif"),
    "sans": ("Arial", "Helvetica", "Nimbus Sans", "DejaVu Sans"),
    "cjk": ("Noto Sans CJK SC", "SimSun", "Microsoft YaHei", "WenQuanYi Zen Hei"),
}


@dataclass
class Probe:
    """One capability probe result."""

    name: str
    ok: bool
    required: bool
    detail: str = ""
    version: str = ""
    fix: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "required": self.required,
            "detail": self.detail,
            "version": self.version,
            "fix": self.fix,
        }


@dataclass
class Report:
    """Collected probes plus grouped extras (fonts, packages, packages)."""

    probes: list[Probe] = field(default_factory=list)
    fonts: dict[str, list[str]] = field(default_factory=dict)
    packages: dict[str, str] = field(default_factory=dict)
    latex_packages: dict[str, str] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=dict)

    def add(self, probe: Probe) -> None:
        self.probes.append(probe)

    @property
    def required_missing(self) -> list[str]:
        return [p.name for p in self.probes if p.required and not p.ok]

    @property
    def optional_missing(self) -> list[str]:
        return [p.name for p in self.probes if not p.required and not p.ok]

    @property
    def ok(self) -> bool:
        return not self.required_missing

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "required_missing": self.required_missing,
            "optional_missing": self.optional_missing,
            "environment": self.environment,
            "probes": [p.as_dict() for p in self.probes],
            "packages": self.packages,
            "latex_packages": self.latex_packages,
            "fonts": self.fonts,
        }


def _run(cmd: list[str], timeout: float = 15.0) -> tuple[int, str]:
    """Run a command, returning (exit code, combined output). Never raises."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _first_line(text: str, limit: int = 160) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:limit]
    return ""


def probe_python(report: Report) -> None:
    version = ".".join(str(v) for v in sys.version_info[:3])
    ok = sys.version_info >= (3, 11)
    report.add(
        Probe(
            "python>=3.11",
            ok,
            True,
            f"Python {version}",
            version,
            "install Python 3.11 or newer (uv python install 3.12)",
        )
    )


def probe_command(report: Report, command: str, required: bool, fix: str) -> str:
    path = shutil.which(command)
    version = ""
    if path:
        _, out = _run([command, "--version"])
        version = _first_line(out)
    report.add(
        Probe(
            command,
            path is not None,
            required,
            path or "not found on PATH",
            version,
            fix,
        )
    )
    return path or ""


def probe_packages(report: Report) -> None:
    for module in REQUIRED_PACKAGES + OPTIONAL_PACKAGES:
        required = module in REQUIRED_PACKAGES
        display = "pillow" if module == "PIL" else module
        spec = importlib.util.find_spec(module)
        if spec is None:
            report.packages[display] = ""
            report.add(
                Probe(
                    display,
                    False,
                    required,
                    "not importable",
                    "",
                    f"uv add {display}  (or declare it in the script's PEP 723 block)",
                )
            )
            continue
        try:
            mod = importlib.import_module(module)
            version = str(getattr(mod, "__version__", "?"))
        except Exception as exc:  # a broken install is a real finding
            report.packages[display] = ""
            report.add(Probe(display, False, required, f"import failed: {exc}", ""))
            continue
        report.packages[display] = version
        report.add(Probe(display, True, required, "importable", version))


def probe_latex(report: Report) -> None:
    found = {name: shutil.which(name) for name in LATEX_COMMANDS}
    has_engine = any(found.values())
    report.add(
        Probe(
            "latex-engine",
            has_engine,
            False,
            ", ".join(f"{k}={v}" for k, v in found.items() if v) or "no TeX engine",
            "",
            "install TeX Live (texlive-xetex, texlive-pictures, texlive-latex-extra, texlive-lang-chinese)",
        )
    )
    if not has_engine:
        return
    kpsewhich = shutil.which("kpsewhich")
    if kpsewhich is None:
        report.add(Probe("kpsewhich", False, False, "not found", "", "install kpathsea (part of TeX Live)"))
        return
    for package in LATEX_PACKAGES + CJK_PACKAGES:
        code, out = _run([kpsewhich, package])
        path = out.strip() if code == 0 else ""
        report.latex_packages[package] = path
        required = package in ("pgfplots.sty", "tikz.sty", "standalone.cls")
        report.add(
            Probe(
                f"tex:{package}",
                bool(path),
                False,
                path or "missing",
                "",
                f"install the TeX Live package providing {package}",
            )
        )


def probe_poppler(report: Report) -> None:
    for command in POPPLER_COMMANDS:
        probe_command(report, command, False, "install poppler-utils (pdfcrop, pdftoppm, pdffonts)")


def probe_image_tools(report: Report) -> None:
    for command in IMAGE_COMMANDS:
        probe_command(report, command, False, "optional: install inkscape / imagemagick")


def probe_fonts(report: Report) -> None:
    try:
        from matplotlib import font_manager
    except Exception as exc:
        report.add(Probe("font-manager", False, True, f"matplotlib unavailable: {exc}", ""))
        return
    available = {entry.name for entry in font_manager.fontManager.ttflist}
    for role, candidates in FONT_CANDIDATES.items():
        matched = [name for name in candidates if name in available]
        report.fonts[role] = matched
        report.add(
            Probe(
                f"font:{role}",
                bool(matched),
                role == "serif",
                f"available: {', '.join(matched)}" if matched else f"none of {', '.join(candidates)}",
                "",
                "install Times New Roman / Noto Sans CJK (or accept the DejaVu fallback)",
            )
        )


def probe_cjk_rendering(report: Report) -> None:
    """Render Chinese with the discovered CJK family; a missing-glyph warning is a failure.

    matplotlib's defaults never carry CJK glyphs, so the probe configures the family
    first — it answers "can this machine render Chinese once a style is applied",
    which is the question a figure task actually depends on.
    """
    try:
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
    except Exception as exc:
        report.add(Probe("cjk-render", False, True, f"matplotlib unavailable: {exc}", ""))
        return
    families = report.fonts.get("cjk") or []
    if not families:
        report.add(Probe("cjk-render", False, True, "no CJK font family found", "", "install Noto Sans CJK SC"))
        return
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            with matplotlib.rc_context(
                {
                    "font.family": "sans-serif",
                    "font.sans-serif": [*families, "DejaVu Sans"],
                    "axes.unicode_minus": False,
                }
            ):
                fig, ax = plt.subplots(figsize=(2, 1))
                ax.set_xlabel("时间 t (s)")
                ax.set_ylabel("误差 (%)")
                ax.plot([0, 1], [0, 1])
                fig.canvas.draw()
                plt.close(fig)
        except Exception as exc:
            report.add(Probe("cjk-render", False, True, f"render failed: {exc}", ""))
            return
    missing = [str(w.message) for w in caught if "missing from font" in str(w.message).lower()]
    ok = not missing
    report.add(
        Probe(
            "cjk-render",
            ok,
            True,
            f"glyphs ok via {families[0]}" if ok else (missing[0][:160] if missing else "unknown warning"),
            "",
            "set font.sans-serif to a CJK family, e.g. 'Noto Sans CJK SC'",
        )
    )


def probe_matplotlib_backend(report: Report) -> None:
    try:
        import matplotlib

        backend = matplotlib.get_backend()
        report.environment["matplotlib_backend"] = backend
        report.add(Probe("matplotlib-backend", True, False, backend, ""))
    except Exception as exc:
        report.add(Probe("matplotlib-backend", False, False, str(exc), ""))


def probe_context(report: Report) -> None:
    from pathlib import Path

    report.environment["uv_run"] = os.environ.get("UV_RUN_RECURSION_DEPTH", "0")
    report.environment["cwd"] = os.getcwd()
    report.environment["skill_root"] = str(Path(__file__).resolve().parents[1])


def build_report() -> Report:
    report = Report()
    probe_python(report)
    for command in REQUIRED_COMMANDS:
        probe_command(report, command, True, "install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
    probe_packages(report)
    probe_latex(report)
    probe_poppler(report)
    probe_image_tools(report)
    probe_fonts(report)
    probe_cjk_rendering(report)
    probe_matplotlib_backend(report)
    probe_context(report)
    return report


def print_human(report: Report, show_fix: bool) -> None:
    print("scientific-figure environment check", file=sys.stderr)
    print("=" * 40, file=sys.stderr)
    for probe in report.probes:
        mark = "ok  " if probe.ok else ("FAIL" if probe.required else "warn")
        detail = f"  [{probe.detail}]" if probe.detail else ""
        print(f"{mark} {probe.name}{detail}", file=sys.stderr)
        if not probe.ok and show_fix and probe.fix:
            print(f"      fix: {probe.fix}", file=sys.stderr)
    print("-" * 40, file=sys.stderr)
    if report.required_missing:
        print(f"BLOCKED — required missing: {', '.join(report.required_missing)}", file=sys.stderr)
    else:
        print("READY — required capabilities present", file=sys.stderr)
    if report.optional_missing:
        print(f"optional missing: {', '.join(report.optional_missing)}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="print JSON only")
    parser.add_argument("--fix", action="store_true", help="print repair commands for missing probes")
    args = parser.parse_args(argv)

    report = build_report()
    payload = report.as_dict()
    if not args.json:
        print_human(report, args.fix)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
