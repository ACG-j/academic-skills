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
