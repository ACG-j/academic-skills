# Tables

A table is a figure with different encoding rules: it must support lookup and comparison,
not impression. The conventions below are what makes that work.

---

## booktabs: the three-line table

The standard for scientific tables. No vertical rules, no double rules, no shading —
horizontal rules only where they separate meaning.

```latex
\begin{table}[tbp]
  \centering
  \caption{Allocation accuracy by strategy. Best per column in bold.}
  \label{tab:allocation}
  \begin{tabular}{lrrr}
    \toprule
    Strategy & Accuracy (\%) & Time (ms) & Memory (MB) \\
    \midrule
    Proportional    & 71.2 & 12.4 & 48 \\
    Greedy          & 78.9 & 15.1 & 52 \\
    \textbf{Sorted} & \textbf{86.4} & 14.8 & 51 \\
    Oracle          & 91.0 & --   & -- \\
    \bottomrule
  \end{tabular}
\end{table}
```

Rules:

- `\toprule`, `\midrule`, `\bottomrule` — nothing else between rows
- **No vertical lines.** They add ink and imply walls between columns that do not exist.
- Group rows with `\cmidrule(lr){2-4}` rather than adding another full rule
- Units in the column header, not repeated in every cell
- Align numbers on the decimal point (see siunitx below)

---

## Numeric alignment with siunitx

Numbers of different magnitudes only compare when their decimal points line up.

```latex
\usepackage{siunitx}
\sisetup{
  detect-weight=true,        % bold cells still align
  detect-family=true,
  group-separator={,},
  group-minimum-digits=4,
}

\begin{tabular}{l S[table-format=2.1] S[table-format=2.2]}
  \toprule
  {Strategy} & {Accuracy (\%)} & {Time (ms)} \\
  \midrule
  Proportional & 71.2 & 12.40 \\
  Sorted       & \bfseries 86.4 & 14.80 \\
  \bottomrule
\end{tabular}
```

`table-format=2.1` means two integer digits, one decimal. Getting this right makes the column
visually aligned without manual padding.

**Note**: the `S` column type needs `{...}` braces around the header text, otherwise siunitx
tries to parse it as a number.

---

## Generating from Python

`sf_table.py` reads a CSV/JSON and emits a booktabs table:

```bash
uv run sf_table.py results.csv --caption "Results by strategy." \
    --label tab:results --best-max accuracy --out tab.tex

uv run sf_table.py results.csv --style siunitx --align-center
```

What it does:

- Detects numeric columns and picks a `table-format`
- `--best-max COL` / `--best-min COL` bolds the best value per column
- Escapes LaTeX special characters in text cells (`_`, `%`, `&`, `#`)
- Emits the full `table` float with caption and label

For pandas:

```python
df.style.format(precision=1).highlight_max(props="textbf:--rwrap;").to_latex(
    "tab.tex", hrules=True, column_format="lrrr", escape=True,
)
```

`hrules=True` produces booktabs rules. `escape=True` matters — an underscore in a column name
otherwise breaks the compile.

---

## Significance marks

```latex
\begin{tabular}{lS[table-format=2.1]@{\hspace{2mm}}l}
  \toprule
  {Method} & {Score} & \\
  \midrule
  Baseline & 71.2 & \\
  Ours     & 86.4 & \textsuperscript{***} \\
  \bottomrule
\end{tabular}

\par\smallskip\footnotesize
\textsuperscript{***}$p<0.001$, \textsuperscript{**}$p<0.01$,
\textsuperscript{*}$p<0.05$; paired $t$-test, Holm-corrected.
```

Rules:

- **Always state the test and the correction** in the note. Stars without a test are decoration.
- **Give exact p-values** where space allows — stars lose information.
- **Do not use stars instead of uncertainty.** A significant difference can still be tiny.
- Put the note directly under the table, smaller than the body text.

---

## Multi-level headers

```latex
\begin{tabular}{l *{2}{S[table-format=2.1]}}
  \toprule
  & \multicolumn{2}{c}{Accuracy (\%)} \\
  \cmidrule(lr){2-3}
  {Strategy} & {In-dist.} & {OOD} \\
  \midrule
  ...
```

`\cmidrule(lr)` trims the ends so adjacent rules do not touch.

---

## Tables that span pages

```latex
\usepackage{longtable}
\begin{longtable}{lrr}
  \caption{Full results.}\label{tab:full} \\
  \toprule
  Item & Value & Unit \\
  \midrule
\endfirsthead
  \toprule
  Item & Value & Unit \\
  \midrule
\endhead
  \midrule
  \multicolumn{3}{r}{\footnotesize continued on next page} \\
\endfoot
  \bottomrule
\endlastfoot
  ... rows ...
\end{longtable}
```

`longtable` repeats the header on each page — a table continued without a header forces the
reader to flip back.

---

## Notes under a table

```latex
\usepackage{threeparttable}
\begin{threeparttable}
  \begin{tabular}{...} ... \end{tabular}
  \begin{tablenotes}[flushleft]\footnotesize
    \item $N=30$ per condition. Errors are 95\% CI.
    \item[\textsuperscript{*}] $p<0.05$, two-sided Wilcoxon.
  \end{tablenotes}
\end{threeparttable}
```

`threeparttable` keeps the note width tied to the table width, which manual `\parbox` hacks
get wrong.

---

## Decision: table or figure?

| Data | Format |
|---|---|
| Exact values the reader will look up | table |
| A pattern, trend, or ranking | figure |
| ≤ 7 rows, ≤ 5 columns, precise values | table |
| Many rows, comparison across categories | figure (dot plot) |
| Both patterns and precision matter | figure + supplementary table |

A 40-row table is almost always a figure waiting to happen. A 3-row table with a trend is
usually better as a small chart — but if the reader needs the exact numbers, keep the table.

---

## Typography

| Element | Size |
|---|---|
| Table body | same as or one step below body text |
| Caption | one step below body text |
| Notes | one step below caption |
| Header | same as body, bold or with a rule |

- Caption **above** the table (figures take their caption below — this asymmetry is
  conventional, follow it)
- `\centering`, not `\begin{center}` — the latter adds vertical space
- Do not scale a table with `\resizebox` — it produces inconsistent font sizes. Restructure
  the columns instead.
- Column headers without units force the reader to hunt in the caption. Put units in the
  header.

---

## Checklist

- [ ] booktabs rules only, no vertical lines
- [ ] Units in the header
- [ ] Numbers aligned on the decimal point
- [ ] Best value marked, with the criterion stated
- [ ] Significance: test named, correction stated, exact p where possible
- [ ] N and error definition in the notes
- [ ] Caption above, notes below, both smaller than the body
- [ ] Special characters escaped
- [ ] Long tables repeat the header
- [ ] Not scaled with `\resizebox`
