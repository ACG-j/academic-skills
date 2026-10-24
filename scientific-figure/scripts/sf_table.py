# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Turn tabular data into a booktabs LaTeX table.

The value here is the parts that are tedious and easy to get wrong: escaping LaTeX special
characters, choosing a numeric format per column, bolding the best value, and emitting a
complete float with caption and label.

Usage:
    uv run sf_table.py results.csv --caption "Results by strategy." --label tab:results
    uv run sf_table.py results.csv --best-max accuracy --best-min time_ms
    uv run sf_table.py results.csv --style siunitx --notes "N=30 per condition."
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

# Characters that break a LaTeX compile when they appear unescaped in text.
LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex(value: str) -> str:
    return "".join(LATEX_ESCAPES.get(ch, ch) for ch in value)


def is_number(value: str) -> bool:
    if value is None:
        return False
    text = value.strip().replace(",", "").replace("%", "")
    if text in ("", "-", "--", "nan", "NaN", "None"):
        return False
    try:
        float(text)
    except ValueError:
        return False
    return True


def numeric_value(value: str) -> float | None:
    if not is_number(value):
        return None
    try:
        return float(value.strip().replace(",", "").replace("%", ""))
    except ValueError:
        return None


def decimals_of(value: str) -> int:
    text = value.strip().replace("%", "")
    if "." not in text:
        return 0
    return len(text.split(".", 1)[1])


def table_format(column: list[str]) -> str:
    """Build a siunitx table-format from the observed values."""
    numbers = [v for v in column if is_number(v)]
    if not numbers:
        return ""
    int_digits = 1
    dec_digits = 0
    negative = False
    for value in numbers:
        numeric = numeric_value(value)
        if numeric is None:
            continue
        if numeric < 0:
            negative = True
        text = value.strip().replace("%", "").lstrip("+-")
        parts = text.split(".")
        int_digits = max(int_digits, len(parts[0].lstrip("0")) or 1)
        if len(parts) > 1:
            dec_digits = max(dec_digits, len(parts[1]))
    sign = "-" if negative else ""
    if dec_digits:
        return f"{sign}{int_digits}.{dec_digits}"
    return f"{sign}{int_digits}"


def load_table(path: Path) -> tuple[list[str], list[list[str]]]:
    suffix = path.suffix.lower()
    if suffix in (".csv", ".tsv", ".txt"):
        delimiter = "\t" if suffix == ".tsv" else ","
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            rows = [row for row in reader if any(cell.strip() for cell in row)]
        if not rows:
            raise ValueError("empty table")
        header, body = rows[0], rows[1:]
        return [h.strip() for h in header], body
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "columns" in data and "rows" in data:
            return list(data["columns"]), [[str(v) for v in row] for row in data["rows"]]
        if isinstance(data, list) and data and isinstance(data[0], dict):
            columns = list(data[0].keys())
            return columns, [[str(row.get(c, "")) for c in columns] for row in data]
        raise ValueError("JSON must be a list of objects or {columns, rows}")
    raise ValueError(f"unsupported table format: {suffix} (use .csv, .tsv, or .json)")


def build_latex(
    header: list[str],
    body: list[list[str]],
    caption: str,
    label: str,
    style: str,
    best_max: set[str],
    best_min: set[str],
    notes: str,
    align_center: bool,
    decimals: int | None,
) -> tuple[str, dict[str, Any]]:
    width = len(header)
    normalized = [(row + [""] * width)[:width] for row in body]

    numeric_columns = [all(not row[i].strip() or is_number(row[i]) for row in normalized) for i in range(width)]
    formats = [table_format([row[i] for row in normalized]) if numeric_columns[i] else "" for i in range(width)]

    # Best-value detection per column.
    best_cells: set[tuple[int, int]] = set()
    for index, name in enumerate(header):
        if name in best_max or name in best_min:
            values = [(row_index, numeric_value(row[index])) for row_index, row in enumerate(normalized)]
            values = [(r, v) for r, v in values if v is not None]
            if not values:
                continue
            pick = max(values, key=lambda p: p[1]) if name in best_max else min(values, key=lambda p: p[1])
            best_cells.add((pick[0], index))

    def render(value: str, column: int, row_index: int) -> str:
        text = value.strip()
        if not text:
            # An S column tries to parse every cell as a number, so a bare "--"
            # raises "Invalid number". Wrapping it in \multicolumn makes siunitx
            # treat the cell as text.
            return r"\multicolumn{1}{c}{--}" if style == "siunitx" else "--"
        if numeric_columns[column] and is_number(text):
            numeric = numeric_value(text)
            if numeric is not None and decimals is not None:
                text = f"{numeric:.{decimals}f}"
            text = escape_latex(text)
        else:
            text = escape_latex(text)
        if (row_index, column) in best_cells:
            return f"\\textbf{{{text}}}"
        return text

    if style == "siunitx":
        column_spec = "l" + "".join(
            f" S[table-format={formats[i]}]" if numeric_columns[i] and formats[i] else " l"
            for i in range(1, width)
        )
        header_cells = " & ".join(f"{{{escape_latex(h)}}}" for h in header)
        preamble_packages = "\\usepackage{booktabs}\n\\usepackage{siunitx}\n\\sisetup{detect-weight=true, detect-family=true}"
    else:
        align = "c" if align_center else "l"
        column_spec = "l" + align * (width - 1)
        header_cells = " & ".join(escape_latex(h) for h in header)
        preamble_packages = "\\usepackage{booktabs}"

    lines = [
        "% Generated by sf_table.py",
        f"% preamble: {preamble_packages.replace(chr(10), ' ')}",
        "\\begin{table}[tbp]",
        "  \\centering",
        f"  \\caption{{{escape_latex(caption)}}}",
        f"  \\label{{{label}}}",
        f"  \\begin{{tabular}}{{{column_spec}}}",
        "    \\toprule",
        f"    {header_cells} \\\\",
        "    \\midrule",
    ]
    for row_index, row in enumerate(normalized):
        cells = " & ".join(render(row[i], i, row_index) for i in range(width))
        lines.append(f"    {cells} \\\\")
    lines += [
        "    \\bottomrule",
        "  \\end{tabular}",
    ]
    if notes:
        lines += ["  \\par\\smallskip", f"  {{\\footnotesize {escape_latex(notes)}}}"]
    lines.append("\\end{table}")

    facts = {
        "rows": len(normalized),
        "columns": width,
        "numeric_columns": [header[i] for i in range(width) if numeric_columns[i]],
        "formats": {header[i]: formats[i] for i in range(width) if formats[i]},
        "bold_cells": len(best_cells),
        "style": style,
    }
    return "\n".join(lines) + "\n", facts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data", help="CSV, TSV, or JSON table")
    parser.add_argument("-o", "--out", default=None, help="output .tex path (default: stdout)")
    parser.add_argument("--caption", default="", help="table caption")
    parser.add_argument("--label", default="tab:results", help="LaTeX label")
    parser.add_argument("--style", default="booktabs", choices=["booktabs", "siunitx"], help="column style")
    parser.add_argument("--best-max", action="append", default=[], help="bold the largest value in this column")
    parser.add_argument("--best-min", action="append", default=[], help="bold the smallest value in this column")
    parser.add_argument("--notes", default="", help="footnote line under the table")
    parser.add_argument("--align-center", action="store_true", help="center non-first columns")
    parser.add_argument("--decimals", type=int, default=None, help="force this many decimals")
    parser.add_argument("--json", action="store_true", help="JSON metadata only (table still written)")
    args = parser.parse_args(argv)

    path = Path(args.data).resolve()
    if not path.exists():
        print(json.dumps({"ok": False, "error": f"missing {path}"}))
        return 2
    try:
        header, body = load_table(path)
    except (ValueError, csv.Error) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2

    unknown = (set(args.best_max) | set(args.best_min)) - set(header)
    if unknown:
        print(json.dumps({"ok": False, "error": f"unknown column(s): {', '.join(sorted(unknown))}", "columns": header}))
        return 2

    latex, facts = build_latex(
        header,
        body,
        args.caption,
        args.label,
        args.style,
        set(args.best_max),
        set(args.best_min),
        args.notes,
        args.align_center,
        args.decimals,
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(latex, encoding="utf-8")
        target = str(out_path)
    else:
        target = "stdout"
        if not args.json:
            sys.stdout.write(latex)

    payload = {"ok": True, "source": str(path), "output": target, **facts}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
