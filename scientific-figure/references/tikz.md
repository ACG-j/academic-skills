# TikZ route

Two different jobs wear the same name, and they need different approaches:

1. **A data figure in TikZ** — you have numbers and want the plot drawn with the document's
   own fonts. Use pgfplots, and let Python write the data.
2. **A schematic** — a method diagram, a framework, an architecture. Hand-written TikZ.

The failure mode is treating the second like the first: pasting a template and filling in
boxes. That produces the generic boxes-and-arrows diagram that every reviewer has seen a
hundred times.

---

## The rule for schematics

**Embed the real method object, not a label describing it.**

A box labelled "distribution" is weaker than a small drawn distribution. A box labelled
"decision boundary" is weaker than the actual boundary with shaded regions. A box labelled
"attention" is weaker than a matrix with the attention weights visible.

The test: does the figure contain anything that could only have come from *this* method? If
every element would be equally true of any method in the field, it is a generic diagram and
the figure is not doing work.

| Weak | Strong |
|---|---|
| box → box → box with arrows | boxes plus the actual data flowing through them |
| "Module X" | a sketch of what X computes, with real numbers or shapes |
| a pipeline of labelled stages | the same pipeline with one stage expanded to show the mechanism |
| "Our contribution" highlighted | the contribution drawn in more detail than the rest |

This does not mean every schematic needs data. A graphical model with plates and latent
variables is legitimately abstract — but the *structure* is the real object there, and it
must be drawn correctly.

---

## Data figures in TikZ

### The pattern

Model writes the `.tex` skeleton; Python writes the data file. This keeps the data
authoritative and the layout editable.

```latex
\documentclass[border=2pt]{standalone}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\begin{document}
\begin{tikzpicture}
\begin{axis}[
  width=89mm, height=60mm,
  xlabel={Time $t$ (s)},
  ylabel={Error (\%)},
  tick label style={font=\footnotesize},
  label style={font=\small},
  legend style={font=\footnotesize, at={(0.98,0.98)}, anchor=north east},
  grid=major, grid style={gray!25},
]
\addplot[blue, thick, mark=*, mark size=1.5pt] table[x=t, y=y] {fig2.dat};
\addplot[red, thick, dashed] table[x=t, y=fit] {fig2.dat};
\legend{Measured, Fit}
\end{axis}
\end{tikzpicture}
\end{document}
```

```python
# Python supplies only the data
import numpy as np
t = np.linspace(0, 10, 24)
np.savetxt("fig2.dat", np.column_stack([t, y, fit]),
           header="t y fit", comments="", fmt="%.6g")
```

### Why this beats exporting PGF

- The `.dat` file is inspectable — you can see the numbers
- The `.tex` is editable — change an axis, a label, a legend position without re-running Python
- The fonts are the document's fonts by construction, not by configuration
- The figure is reproducible from two small files

### Sizing in TikZ

`width=89mm` sets the axes box, not the whole figure — labels and legend add outside it. For
a figure that must fit a column exactly, wrap it:

```latex
\begin{tikzpicture}
\node[inner sep=0pt] {\input{fig2-body.tikz}};
\end{tikzpicture}
```

Or use `standalone` with `\usepackage{standalone}` and include with `\includegraphics` at a
fixed width.

---

## Compiling and reviewing

TikZ produces a PDF, not a PNG, so the review needs a rasterization step:

```bash
uv run sf_tex2png.py fig.tex -o qa/ --dpi 300
```

It runs `xelatex` → `pdfcrop` → `pdftoppm` and reports the page size, so the same overlay and
crop protocol applies. This matters: a TikZ figure that compiles can still have overlapping
labels, a legend over data, or text too small for the target column — and you cannot see any
of that in the `.tex` source.

**Use xelatex when the figure contains CJK text** (`ctex` or `xeCJK`). pdflatex will fail or
silently drop glyphs.

---

## Common compile failures

| Error | Cause | Fix |
|---|---|---|
| `Dimension too large` | coordinates beyond ~16384 pt (TeX limitation) | scale the data, or use `\pgfplotsset{compat=1.18}` with `axis` scaling |
| `TeX capacity exceeded` | too many points/commands | reduce points, or use `externalize` |
| `Package pgfplots Error: could not retrieve column` | header/column mismatch in the `.dat` | check the `table[x=..., y=...]` names against the header |
| `! Undefined control sequence` on `\addplot` | `pgfplots` not loaded | `\usepackage{pgfplots}` |
| Missing CJK glyphs | pdflatex with CJK | switch to xelatex + `ctex` |
| Very slow compile | thousands of paths | `\usepgfplotslibrary{external}` and `\tikzexternalize` |
| Fonts differ from the body | `standalone` uses its own defaults | set `\documentclass[border=2pt]{standalone}` and load the document's font packages |

**Externalization** for anything non-trivial:

```latex
\usetikzlibrary{external}
\tikzexternalize[prefix=build/]
```

Compiles each figure once, reuses the PDF afterwards. Without it, a 10-figure document takes
minutes per build.

---

## matplot2tikz: matplotlib to editable pgfplots

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplot2tikz

fig, ax = plt.subplots(figsize=(3.5, 2.6))
ax.plot(x, y, label="Data")
matplot2tikz.save("fig2.tex")     # a pgfplots axis you can edit by hand
```

Use it when the figure was built in matplotlib but the venue needs TikZ-native output, or
when you want to hand-tune the result in LaTeX.

Caveats:

- Complex artists (colorbars, 3D, annotations with arrows) translate imperfectly — check the
  result
- Thousands of points produce enormous `.tex` — export PDF instead
- The translated file needs its preamble packages; `matplot2tikz` can emit them with
  `matplot2tikz.save(..., extra_axis_parameters=...)` or via
  `matplot2tikz.get_tikz_code(..., wrap=True)`

After translating, **compile it** — a successful translation is not a successful figure.

---

## Schematic construction

### Structure

```latex
\documentclass[border=4pt]{standalone}
\usepackage{tikz}
\usetikzlibrary{positioning, arrows.meta, fit, backgrounds, calc, shapes.geometric}
\begin{document}
\begin{tikzpicture}[
  font=\small,
  box/.style={draw, rounded corners=2pt, minimum height=8mm, minimum width=18mm, align=center},
  arrow/.style={-{Stealth[length=2mm]}, thick},
]
  \node[box] (input) {Input};
  \node[box, right=8mm of input] (model) {Model};
  \node[box, right=8mm of model] (output) {Output};
  \draw[arrow] (input) -- (model);
  \draw[arrow] (model) -- (output);
\end{tikzpicture}
\end{document}
```

That is the generic version. Make it specific by replacing at least one node with a drawing
of what actually happens there.

### Craft rules

- **Consistent grid**: `positioning` with fixed distances, not eyeballed coordinates
- **One visual vocabulary**: one box style, one arrow style, one colour per role
- **Hierarchy**: the contribution is visually heavier (thicker border, accent colour, more
  detail); context is lighter
- **Alignment**: `align=center` in nodes, and align boxes on shared anchors
- **Text at final size**: set `font=\small` and check it against the target column — a
  schematic scaled to 89 mm often ends up at 5 pt
- **Arrows** should express data flow direction, not just connect boxes

### Anti-patterns

| Pattern | Why it fails |
|---|---|
| 12 boxes in a grid | no hierarchy, no entry point |
| Every box the same weight | the contribution is invisible |
| Gradient fills, drop shadows | decoration that reads as amateur |
| Icons from a stock set | they say nothing about the method |
| Text-only nodes | no method object embedded |
| Inconsistent arrow styles | the reader looks for a meaning that is not there |
| Raster images inside the schematic | resolution mismatch and no vector scaling |

---

## When not to use TikZ

| Situation | Better choice |
|---|---|
| Dense scatter, thousands of points | matplotlib → PDF |
| Complex statistical plots (violins, heatmaps with dendrograms) | matplotlib |
| Interactive or animated | plotly, manim |
| Precise typographic match is *not* needed | matplotlib is faster to iterate |
| A photo or micrograph is involved | matplotlib `imshow`, or compose in LaTeX |

TikZ earns its cost when the figure must share the document's exact typography, or when the
layout needs geometric precision matplotlib makes awkward.
