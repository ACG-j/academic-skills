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

# lint needs the scripts' own dependencies
uv run --with pandas ../../scripts/sf_lint.py --run figB-corrmap-vif.py
```

| Figure | Layout | What it exercises |
|---|---|---|
| `figA` | beeswarm + 3×2 effect grid | a companion colourbar in a composed figure; narrow panels vs their own tick labels |
| `figB` | 15×15 annotated matrix + VIF bars | cell-text legibility setting the canvas size; shared row order across panels |
| `figC` | triangular bubble matrix + scatter matrix | label-to-mark association in dense encodings; long trait names in diagonal cells |
| `figD` | 4 regression mosaics with marginals | seam collisions between marginal histograms and main panels |

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
beeswarm that they read as unrelated. Both were caught only by looking at the whole figure.

That is the argument for the crop-and-look pass, and for reviewing composition separately
from reviewing collisions.
