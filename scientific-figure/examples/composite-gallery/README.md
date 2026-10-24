# Composite gallery

Four multi-panel layouts that appear constantly in published work, rebuilt from scratch to
find where this skill's guidance and tooling fall short. Not reproductions — the data is
synthetic, the colours follow `base.mplstyle`, and several layout decisions deliberately
differ from the originals where the original was defective.

```bash
uv run make_data.py            # writes ./data
uv run figA-shap-beeswarm.py
uv run figB-corrmap-vif.py
uv run figC-bubble-scatter-matrix.py
uv run figD-regression-mosaic.py
uv run figE-diamond-lattice.py
uv run figF-network-scatter-matrix.py

# lint needs the scripts' own dependencies
uv run --with pandas ../../scripts/sf_lint.py --run figB-corrmap-vif.py
```

| Figure | Layout | What it exercises |
|---|---|---|
| `figA` | beeswarm + 3×2 effect grid | a companion colourbar in a composed figure; narrow panels vs their own tick labels |
| `figB` | 15×15 annotated matrix + VIF bars | cell-text legibility setting the canvas size; shared row order across panels |
| `figC` | triangular bubble matrix + scatter matrix | label-to-mark association in dense encodings; long trait names in diagonal cells |
| `figD` | 4 regression mosaics with marginals | seam collisions between marginal histograms and main panels |
| `figE` | diamond-lattice triangular correlation plot | label run per lattice step; two size/colour legends |
| `figF` | scatter matrix with a correlation network on the upper triangle | overlay axes; node ladder placement; arc curvature |

## Defects found, and what fixed them

All four passed the static layer immediately and failed the runtime layer:

| Figure | Initial errors | Root cause | Fix |
|---|---|---|---|
| A | 8 | colourbar placed with `fig.add_axes()` landed on the panel grid; 4.6–6.4 pt text | colourbar moved into its own gridspec column; canvas widened; three ticks per panel |
| B | 1 | 5.6 pt cell text in a 15×15 matrix | canvas 180→210 mm so cells can hold 6.5 pt |
| C | 8 | 45° diamond lattice labels drifting from their rows | row/column-aligned triangle; compact aliases |
| D | 7 | marginals flush against the main panel at every seam | marginal ticks removed; mosaic gaps widened |

## What the automated layers missed

`figC`'s first passing version had **zero collisions and was still wrong**: rotated labels
sat closer to the neighbouring row than to their own, so a reader could not tell which trait
a bubble belonged to. `figA`'s first passing version had the colourbar so far from the
beeswarm that they read as unrelated. `figD`'s metrics box, moved outside the axes to escape
the fit line, landed underneath the neighbouring histogram — a cross-panel occlusion that
produces no bbox overlap and so trips no check. All three were caught only by looking at the
whole figure.

That is the argument for the crop-and-look pass, and for reviewing composition separately
from reviewing collisions.

## The two hardest layouts

`figE` and `figF` are the ones where a square-matrix substitute destroys the point.

**`figE`** places every pair `(i, j)` at the crossing of the diagonals from its two labels,
so a reader traces two lines instead of scanning a row and a column. The constraint that
makes it hard: labels advance one lattice step each, so the rotated text must fit inside a
step. Compact aliases plus a canvas wide enough for the run — enlarging the canvas alone
does not fix it, and neither does shrinking the font below 6 pt.

**`figF`** uses the otherwise-wasted upper triangle for a correlation network. Two placement
decisions decide whether it reads: nodes must *climb* one cell per index (on a single
horizontal line the arcs collapse into a braid), and the curvature must be generous and
signed (`arc3,rad ≈ -0.3`) or the edges look like straight lines. The network lives on its
own frameless axes so it can overlap the matrix without competing for layout.

Both initially reported **zero lint findings while nothing had been inspected** — a caught
exception had disabled the whole runtime layer. That is recorded in `references/qa.md`
under "a silent check is worse than no check".
