# Design: choosing the figure

The chart type is a communication decision, not a taste decision. This file is the decision
path from "what am I claiming" to "what am I drawing".

---

## Start from the claim, not the data

Ask: **what is the reader supposed to conclude?** Then pick the encoding that makes that
conclusion hardest to miss.

| The claim is about | Encode with |
|---|---|
| Comparison between categories | position (bar, dot) |
| Trend over an ordered axis | position along a line |
| Relationship between two variables | position on two axes (scatter) |
| Distribution | shape (histogram, ECDF, violin, raincloud) |
| Composition of a whole | part-to-whole — and think twice, see below |
| Magnitude across two dimensions | colour or area on a grid (heatmap) |
| Deviation from a reference | a residual, a difference, a diverging colour |
| Rank and its stability | sorted bar, slopegraph, forest plot |
| Uncertainty around an estimate | band, bars, distribution — and name the interval |

---

## Chart type decision table

| Situation | Use | Avoid |
|---|---|---|
| One value per category, ranked | horizontal bar | pie, donut |
| Few short categories, natural order | vertical bar | horizontal bar (wastes space) |
| Values over time | line | bars for dense series |
| Many time series | line + direct labels at the end | a 10-entry legend |
| Two variables, many points | scatter (+ fit if the relationship is the point) | line through unordered points |
| Distribution across groups | violin, raincloud, strip | bar of means alone |
| Distribution shape matters | ECDF, histogram | box plot alone (hides bimodality) |
| Range per item | lollipop, dumbbell | grouped bar |
| Correlation matrix | heatmap with a diverging map centred at 0 | rainbow, unsorted matrix |
| Part-to-whole, 2–4 parts | stacked bar | pie |
| Part-to-whole, 5+ parts | bar chart, not a whole | pie, donut |
| Two-way comparison with a third value | grouped bar, or facet | 3D bar |
| Rank change between two conditions | slopegraph | two separate bar charts |
| Effect sizes with CIs | forest plot | bar with error bars |
| Confusion / flow between states | confusion matrix, Sankey | stacked area for flows |

**Pie charts**: a pie encodes angle, which humans read poorly. With more than three slices
the comparisons become guesses. If the whole genuinely matters (it is 100% of something),
a single stacked bar reads better.

**3D**: perspective distorts the very lengths the chart exists to compare. Reserve 3D for
data that is genuinely three-dimensional (a surface, a manifold), and add orthogonal views.

**Dual axes**: two y-axes invite false correlation because the reader sees two lines
crossing and infers meaning. Only use it when the two quantities are physically linked, and
colour-code each axis to its series.

---

## Panel composition

**One hero.** The panel carrying the headline should be visibly the largest, and the eye
should land on it first. A 2×2 equal grid means no hierarchy was decided.

```python
fig, axes = plt.subplots(1, 2, figsize=(7, 2.8), gridspec_kw={"width_ratios": [2, 1]})
```

**Panel labels** — (a), (b), (c) — same size, same position relative to each panel, same
weight. Put them in the axes' top-left corner consistently, not wherever space allows.

**Alignment.** Axis labels, panel edges, and legends should line up across panels. This is
the single most visible difference between a composed figure and four figures pasted
together.

**Shared axes.** Panels meant to be compared share limits. If they must differ, make the
difference unmistakable (label it, or use a break).

---

## Annotation

Annotation is what turns a plot into an argument. Without it the reader has to do the
inference the figure exists to save them from.

Annotate:
- **Thresholds and reference lines** — with the value and its meaning ("$i_f = 1.4$ A,
  failure threshold"), not just a dashed line
- **The inflection or transition** — the point where behaviour changes
- **Regions** — shade the decision region, the extrapolation zone, the regime that matters
- **Direct labels** instead of a legend when the series count is small; the label sits at
  the end of the line and removes the legend lookup entirely
- **The surprising point** — the outlier is usually the finding

Do not annotate:
- Every point (that is a table)
- The obvious (an arrow to the peak saying "peak")
- Anything that requires covering data

**Placement rule:** annotation goes in genuinely empty space, verified against the plotted
points. `sf_lint.py --run` reports when a legend covers more than 12% of the points; the same
instinct applies to annotations, which the lint cannot check.

---

## Data-ink discipline

Every mark should carry information. Remove:

- Grids that do not help read a value (a 5-point line does not need a grid)
- Frames around panels that already have axes
- Legends for single series
- Redundant axis labels when the unit is in the caption and the axis is self-evident — but
  keep the unit if a reader could misread the scale
- Decorative colour that encodes nothing

Keep:
- Zero lines and reference lines
- Minor ticks when reading precision matters
- Whitespace — a cramped figure is harder to read than a sparse one

---

## Common defects, and what they look like

| Defect | Symptom | Fix |
|---|---|---|
| Wrong chart type | reader has to compute a ratio | switch encoding |
| No hierarchy | eye has no entry point | hero panel + size ratios |
| Chart junk | grid + frame + gradient + shadow | remove until it hurts |
| Truncated axis on bars | difference looks 5× larger than it is | start at zero, or switch to dots |
| Rainbow colormap | false boundaries in continuous data | viridis |
| Colour-only encoding | mush in grayscale | add marker/linestyle |
| Legend over data | three points invisible | move outside, or direct-label |
| Too many series | 12-colour legend nobody reads | highlight 2–3, grey the rest |
| No uncertainty | point estimates read as fact | band, bars, or distribution |
| No N | reader cannot judge reliability | annotate |
| Unlabelled transform | log axis read as linear | label the scale |
| Text too small | 5 pt after reduction | raise to 7+ pt |
| Inconsistent sizes | labels differ between panels | one style preset |
| Cropped content | label touches the edge | increase margins |
| Empty space | data crammed into a corner | set limits to the data |

---

## A worked sequence

Claim: "Sorted allocation beats proportional by 18% above 60% demand, and the advantage
disappears below it."

1. **Encoding**: comparison of two strategies across a continuous variable → line chart,
   x = demand, y = advantage, with the region above 60% shaded.
2. **Hero**: the single panel *is* the hero; no composition needed.
3. **Annotation**: shade the >60% region, mark the crossing point at 60% with its value,
   label both lines directly at the right edge instead of a legend.
4. **Uncertainty**: CI band from 30 replicates, stated in the axis label or caption.
5. **Style**: 89 mm Nature single column, 7 pt.
6. **Review**: crop the crossing annotation (is it legible against the shading?), the y-axis
   label (units, minus sign if negative), the right-edge direct labels (do they collide?).

That sequence — claim, encoding, hero, annotation, uncertainty, style, review — is the
whole design stage.

---

## Composite-figure archetypes

Four layouts recur in published work and are worth knowing by name, because each has a
characteristic failure that is easy to reproduce.

| Archetype | Structure | Characteristic failure |
|---|---|---|
| **Beeswarm + effect grid** | one wide beeswarm panel; a grid of small effect panels beside it | the beeswarm's colourbar is hand-placed and lands on the grid; narrow effect panels cannot hold their own tick labels |
| **Matrix + companion bars** | an annotated square matrix; a bar panel sharing its row order | cell annotations below 6 pt; the bar panel's axis collides with the matrix's ticks |
| **Bubble matrix + scatter matrix** | a triangular correlation encoding; a lower-triangle scatter matrix | diamond-lattice labels drift away from their rows; diagonal name boxes too narrow for long trait names |
| **Regression mosaic** | per-model blocks of scatter + marginals + residuals | marginals flush against the main panel, so tick labels collide at every seam |

Shared rules that emerged:

- **Marginals need no scale.** A histogram attached to a main panel is read by shape, not by
  value. Removing its tick labels buys the seam spacing that was the actual problem.
- **Give companion axes their own gridspec column.** Never `fig.add_axes()` for a colourbar in
  a composed figure.
- **The canvas size is set by the densest element.** For an annotated matrix that is the cell
  text; for a mosaic it is the label rows. Size for that element first, then distribute.
- **Prefer row/column alignment over rotated diagonal lattices** when the figure must be read
  precisely. A diamond layout looks elegant and makes label-to-mark association ambiguous at
  small sizes.

---

## Two layouts that are all structure

Both of these are worth building once, because their value is entirely in the geometry and
a square-matrix substitute loses it.

### Diamond-lattice triangular correlation plot

Variables label the two upper edges; every pair `(i, j)` sits where the descending diagonal
from label `i` meets the ascending one from label `j`. Bubble area is `|r|`, colour is the
sign of `r`, a second size legend carries the p-value, and one edge of the triangle is drawn
with large open circles as a visual spine.

Why not a square matrix: a reader finds any pair by tracing two lines, with no need to scan
for a row and a column. Why it is hard: the label run along one diagonal is one lattice step
per variable, so the rotated text must fit inside a step. Compact aliases and a canvas wide
enough for the run are both required — enlarging the canvas alone does not help.

```python
def lattice(i, j):
    return (j - i, -(i + j))     # two diagonal families at 45 degrees
```

### Scatter matrix with a correlation network on the upper triangle

The lower triangle is ordinary pairwise scatters. The upper triangle is deliberately empty,
and that emptiness carries the network: trait nodes climb the diagonal, and curved edges
join them, coloured by the sign of `r`, dashed when `p ≥ 0.05`, thickened by `|r|`.

Four placement rules decide whether it reads. All four were wrong on the first attempt:

- **Nodes climb.** One cell of height per index, on the top-right corner of each diagonal
  cell, so they descend in a staircase. Put them on one horizontal line and the arcs
  collapse into a short flat braid that reads as nothing.
- **Curvature is generous and signed.** `arc3,rad` around −0.25 to −0.45 makes edges bow up
  into the empty triangle. A small magnitude produces near-straight lines.
- **The data must span the matrix.** A hub that only correlates with its neighbours yields
  short local arcs. A hub with graded reach across the whole index range — strong to the
  first few, weak to the last — is what produces the long crossing edges that make the
  overlay worth drawing.
- **Filter the edges.** Above roughly 20 edges the network becomes a hairball in which no
  relation is readable. Draw only `|r| ≥ 0.3` or `p < 0.001`, and say so in the caption.

Keep the network on its own frameless axes so it can overlap the matrix without fighting it
for layout.

### Matrix layouts fight the style preset

`base.mplstyle` sets `axes.spines.top: false` and `axes.spines.right: false`. That is the
right default for a line chart and wrong for any grid of cells: with two spines missing,
each cell shows an L-shaped fragment and the table reads as disconnected brackets.

```python
def full_frame(ax):
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_linewidth(0.6)
```

Apply it to **every** cell in the block — scatters, diagonal labels, and cells reserved for
an overlay. A reserved cell keeps its frame and clears only its ticks; switching it off with
`ax.axis("off")` deletes the cell and leaves its neighbours' borders ending in mid-air.
