# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow", "matplotlib"]
# ///
"""Palette audit: contrast, grayscale separation, and colourblind simulation.

A palette is not accessible because it has a name like "colourblind safe". This
tool measures what actually matters for a printed figure:

1. **Contrast against the background** — WCAG relative-luminance ratio. Text needs
   >= 4.5, graphical objects >= 3.0.
2. **Grayscale separation** — CIE L* distance. Series that collapse to the same
   grey cannot be told apart in a B&W print.
3. **Colourblind separation** — pairwise distance after simulating deuteranopia,
   protanopia, and tritanopia. Two series that merge for a deuteranope are one
   series for ~6% of male readers.

Thresholds here are screening heuristics with stated origins, not standards.

Usage:
    uv run sf_palette.py --list
    uv run sf_palette.py --audit wong
    uv run sf_palette.py --audit "#0072B2,#D55E00,#009E73"
    uv run sf_palette.py --audit wong --background "#FFFFFF" --strict
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any

PALETTES_JSON = Path(__file__).resolve().parents[1] / "palettes" / "palettes.json"

WCAG_TEXT_MIN = 4.5
WCAG_GRAPHICS_MIN = 3.0
# Below this a colour is effectively invisible on the background, whatever its role.
CONTRAST_INVISIBLE = 1.5
GRAYSCALE_DELTA_L_MIN = 10.0
CVD_DELTA_E_MIN = 10.0

# Machado, Oliveira & Fernandes (2009) severity-1.0 matrices, applied in linear RGB.
CVD_MATRICES = {
    "deuteranopia": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "protanopia": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "tritanopia": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}


def parse_hex(value: str) -> tuple[int, int, int]:
    text = value.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        raise ValueError(f"expected a 3- or 6-digit hex colour, got {value!r}")
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError as exc:
        raise ValueError(f"invalid hex colour: {value!r}") from exc


def to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, int(round(c)))):02X}" for c in rgb)


def _srgb_to_linear(channel: float) -> float:
    value = channel / 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(value: float) -> float:
    value = max(0.0, min(1.0, value))
    encoded = value * 12.92 if value <= 0.0031308 else 1.055 * (value ** (1 / 2.4)) - 0.055
    return encoded * 255.0


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def cie_lstar(rgb: tuple[int, int, int]) -> float:
    """CIE L* from sRGB, used as the grayscale proxy."""
    y = relative_luminance(rgb)
    delta = 6 / 29
    return 116 * _f(y) - 16 if y > delta**3 else (y / (3 * delta**2)) * 100


def _f(t: float) -> float:
    delta = 6 / 29
    return t ** (1 / 3) if t > delta**3 else t / (3 * delta**2) + 4 / 29


def rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """sRGB to CIELAB (D65). Used for perceptual distance, not for display."""
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    xn, yn, zn = 0.95047, 1.0, 1.08883
    fx, fy, fz = _f(x / xn), _f(y / yn), _f(z / zn)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))


def simulate(rgb: tuple[int, int, int], kind: str) -> tuple[int, int, int]:
    matrix = CVD_MATRICES[kind]
    linear = [_srgb_to_linear(c) for c in rgb]
    out = [sum(matrix[i][j] * linear[j] for j in range(3)) for i in range(3)]
    return tuple(_linear_to_srgb(v) for v in out)  # type: ignore[return-value]


def load_palettes() -> dict[str, Any]:
    if not PALETTES_JSON.exists():
        raise SystemExit(json.dumps({"ok": False, "error": f"missing {PALETTES_JSON}"}))
    return json.loads(PALETTES_JSON.read_text(encoding="utf-8"))


def audit(colors: list[str], background: str = "#FFFFFF", strict: bool = False) -> dict[str, Any]:
    rgb_list = [parse_hex(c) for c in colors]
    bg = parse_hex(background)
    findings: list[dict[str, Any]] = []

    contrasts = []
    for label, rgb in zip(colors, rgb_list):
        ratio = contrast_ratio(rgb, bg)
        contrasts.append({"color": label, "ratio": round(ratio, 2), "lstar": round(cie_lstar(rgb), 1)})
        # A light colour in a published palette (Wong yellow sits at 1.3:1 on white) is
        # not a defect of the palette — it is a usage constraint: fills only, never thin
        # lines, small markers, or text. Only a colour that is unusable for *any* mark
        # is a hard failure, which here means effectively the same as the background.
        if ratio < CONTRAST_INVISIBLE:
            findings.append(
                {
                    "severity": "warn",
                    "check": "contrast",
                    "color": label,
                    "message": (
                        f"contrast {ratio:.2f}:1 against {background} — usable only as a large fill, "
                        "invisible as a line, marker, or text"
                    ),
                    "fix": "pair it with a dark outline, or reserve it for filled areas",
                }
            )
        elif ratio < WCAG_GRAPHICS_MIN:
            findings.append(
                {
                    "severity": "warn",
                    "check": "contrast",
                    "color": label,
                    "message": f"contrast {ratio:.2f}:1 is below the {WCAG_GRAPHICS_MIN}:1 graphics minimum",
                    "fix": "acceptable for large fills; avoid thin lines, small markers, and text in this colour",
                }
            )
        elif ratio < WCAG_TEXT_MIN:
            findings.append(
                {
                    "severity": "info",
                    "check": "contrast",
                    "color": label,
                    "message": f"contrast {ratio:.2f}:1 is below the {WCAG_TEXT_MIN}:1 text minimum",
                    "fix": "acceptable for thick lines and fills, not for text in this colour",
                }
            )

    grayscale = []
    for (i, a), (j, b) in itertools.combinations(list(enumerate(colors)), 2):
        dl = abs(cie_lstar(rgb_list[i]) - cie_lstar(rgb_list[j]))
        grayscale.append({"pair": [a, b], "delta_lstar": round(dl, 1)})
        if dl < GRAYSCALE_DELTA_L_MIN:
            findings.append(
                {
                    "severity": "warn",
                    "check": "grayscale",
                    "pair": [a, b],
                    "message": f"L* difference {dl:.1f} is below {GRAYSCALE_DELTA_L_MIN}: these series merge in a B&W print",
                    "fix": "add a distinct marker or linestyle so shape carries the series, not shade",
                }
            )

    cvd_report: dict[str, Any] = {}
    for kind in CVD_MATRICES:
        simulated = [simulate(rgb, kind) for rgb in rgb_list]
        pairs = []
        for (i, a), (j, b) in itertools.combinations(list(enumerate(colors)), 2):
            distance = delta_e(rgb_to_lab(simulated[i]), rgb_to_lab(simulated[j]))
            pairs.append({"pair": [a, b], "delta_e": round(distance, 1)})
            if distance < CVD_DELTA_E_MIN:
                findings.append(
                    {
                        "severity": "warn",
                        "check": kind,
                        "pair": [a, b],
                        "message": f"ΔE {distance:.1f} under {kind} simulation is below {CVD_DELTA_E_MIN}: these series become indistinguishable",
                        "fix": "reorder the palette or add marker/linestyle encoding",
                    }
                )
        cvd_report[kind] = {
            "simulated": [to_hex(s) for s in simulated],
            "min_delta_e": round(min((p["delta_e"] for p in pairs), default=0.0), 1),
            "pairs": sorted(pairs, key=lambda p: p["delta_e"])[:3],
        }

    errors = [f for f in findings if f["severity"] == "error"]
    warns = [f for f in findings if f["severity"] == "warn"]
    ok = not errors and (not warns if strict else True)
    return {
        "ok": ok,
        "strict": strict,
        "background": background,
        "count": len(colors),
        "colors": colors,
        "contrast": contrasts,
        "grayscale": grayscale,
        "colorblind": cvd_report,
        "findings": findings,
        "summary": {"errors": len(errors), "warnings": len(warns)},
    }


def cmd_list() -> int:
    data = load_palettes()
    rows = []
    for key, entry in data["palettes"].items():
        result = audit(entry["colors"])
        rows.append(
            {
                "key": key,
                "label": entry["label"],
                "count": len(entry["colors"]),
                "colors": entry["colors"],
                "use": entry["use"],
                "min_contrast": round(min(c["ratio"] for c in result["contrast"]), 2),
                "min_grayscale_delta_l": round(min(g["delta_lstar"] for g in result["grayscale"]), 1),
                "worst_colorblind_delta_e": round(
                    min(v["min_delta_e"] for v in result["colorblind"].values()), 1
                ),
                "warnings": result["summary"]["warnings"],
            }
        )
    print(json.dumps({"ok": True, "palettes": rows, "colormaps": data["colormaps"]}, ensure_ascii=False, indent=2))
    return 0


def resolve(name: str) -> list[str]:
    if "," in name:
        return [part.strip() for part in name.split(",") if part.strip()]
    data = load_palettes()
    entry = data["palettes"].get(name)
    if entry is None:
        known = ", ".join(sorted(data["palettes"]))
        raise SystemExit(json.dumps({"ok": False, "error": f"unknown palette '{name}'; known: {known}"}))
    return list(entry["colors"])


def print_human(result: dict[str, Any]) -> None:
    print(f"palette audit — {result['count']} colours on {result['background']}", file=sys.stderr)
    print(f"{'colour':10s} {'contrast':>9s} {'L*':>6s}", file=sys.stderr)
    for row in result["contrast"]:
        print(f"{row['color']:10s} {row['ratio']:8.2f} {row['lstar']:6.1f}", file=sys.stderr)
    for kind, block in result["colorblind"].items():
        print(f"{kind:14s} min ΔE {block['min_delta_e']:.1f}", file=sys.stderr)
    for finding in result["findings"]:
        print(f"[{finding['severity']:5s}] {finding['message']}", file=sys.stderr)
    print(
        f"summary: {result['summary']['errors']} error(s), {result['summary']['warnings']} warning(s)",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="audit every bundled palette")
    group.add_argument("--audit", metavar="PALETTE|HEX,HEX,...", help="audit one palette name or an explicit list")
    parser.add_argument("--background", default="#FFFFFF", help="background colour (default white)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--json", action="store_true", help="JSON only")
    args = parser.parse_args(argv)

    if args.list:
        return cmd_list()

    colors = resolve(args.audit)
    try:
        result = audit(colors, args.background, args.strict)
    except ValueError as exc:
        raise SystemExit(json.dumps({"ok": False, "error": str(exc)}))
    if not args.json:
        print_human(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
