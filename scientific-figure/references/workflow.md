# Workflow

Six stages, in order. Each one ends with an artifact or a decision, so "done" is
observable rather than felt.

The stages exist because skipping them is what produces figures that plot correctly and
still fail review. Stage 1 catches "what is this figure even claiming", stage 2 catches
"the chart type fights the data", and stage 5 catches everything nobody looked at.

---

## Stage 1 — Contract

Before any code, write down what the figure must prove. One sentence, no hedging.

```yaml
figure_id: fig2_allocation
core_claim: "Sorted allocation beats proportional allocation by 18% once demand exceeds capacity."
backend: matplotlib        # matplotlib | tikz | other
panels:
  - id: a
    type: sorted_bar
    defends: "ranking across the six strategies"
  - id: b
    type: residual
    defends: "the winner's advantage vanishes below 40% load"
hero_panel: a
hierarchy:                 # what the eye should hit, in order
  overview: "which strategy wins"
  deviation: "where the advantage disappears"
export: [pdf, svg, png]
source_data: data/processed/allocation.csv
stats_on_figure: "95% CI error bars; N=30 per bar"
target: {venue: nature, column: single, width_mm: 89}
```

**The cover test.** Read the claim, cover the caption, look at the figure. If the claim is
not readable from the figure alone, the figure is displaying data rather than arguing —
that is a stage-2 problem, not a caption problem.

**The drop test.** Delete each panel in turn. If the claim survives, that panel was
decoration.

Skip-if: the user already stated the claim, the panel layout, and the venue.

---

## Stage 2 — Design

Choose in this order; each choice constrains the next.

1. **What does colour encode?** Nothing → one colour or a grey ramp. Category → a
   categorical palette. Magnitude → a sequential colormap. Sign around zero → diverging
   with a meaningful centre.
2. **What does position encode?** Prefer position over colour, colour over size.
3. **Chart type.** See `design.md` for the decision table. The common failure is a chart
   type chosen for looks: a pie for nine categories, a 3D bar for a two-way comparison, a
   line for unordered categories.
4. **Panel hierarchy.** One hero panel carries the claim; the rest are context and should
   be visibly smaller. An equal 2×2 grid almost always means the hierarchy was never
   decided.
5. **Annotation.** What must be marked on the figure itself — a threshold, an inflection,
   the region where data runs out. A figure whose key event is only in the caption is
   half-built.
6. **Target style.** Run `sf_style.py --list` and pick by venue, or read `styles.md`.

Skip-if: the request names both the chart type and the venue.

---

## Stage 3 — Implement

Write the script or the `.tex`. Requirements that pay off immediately:

- **Data from a file, never inlined.** Inline arrays cannot be reviewed, cannot be
  re-derived, and hide transcription errors. More than ~20 inline numbers is a smell.
- **Seed every RNG** so a rerun produces the same figure.
- **Apply the style once**, at the top. Per-figure rcParams edits drift and are invisible
  in review.
- **Save a review PNG** alongside the vector output, at a dpi high enough to inspect
  (200+). The PDF is for the venue; the PNG is for the eyes.
- **Name files after the figure id**, so the artifact and the contract stay linked.

For TikZ, `sf_tex2png.py` compiles and rasterizes in one step so the same review protocol
applies.

---

## Stage 4 — Lint

Two layers, run in order. Both are cheap; neither replaces stage 5.

```bash
uv run sf_lint.py --static plot.py     # source: reproducibility, units, uncertainty, format
uv run sf_lint.py --run plot.py        # render: collisions, legend overlap, font size, clipping
```

Reading the output:

- **error** — blocking. Fix before review; a 4 pt font or a legend over the data is not a
  matter of taste.
- **warn** — decide explicitly. Some are legitimate (a log axis, a dual axis with a real
  physical link); record the decision.
- **info** — context, ignore unless it contradicts the intent.

The static layer cannot see anything that depends on the data — whether the legend lands
on a curve, whether two labels touch. That is what the runtime layer and stage 5 are for.

Skip-if: never for L1. L2 needs a runnable script, so a hand-written TikZ figure skips
straight to stage 5 after `sf_tex2png.py`.

---

## Stage 5 — Review

The stage that decides whether the figure ships.

### 5.1 Overlay, don't guess

```bash
uv run sf_crop.py --image fig.png --overlay -o qa/
```

Look at the returned grid image and read off normalized coordinates. Estimating positions
from a bare image drifts by several percent — enough to cut a label in half.

### 5.2 Write the crop spec

```json
{"crops": [
  {"name": "legend",  "why": "text legible, no data underneath", "box": [0.64, 0.01, 0.98, 0.15]},
  {"name": "y-label", "why": "rotated text complete, unit present", "box": [0.00, 0.20, 0.09, 0.80]},
  {"name": "peak",    "why": "band vs points overlap", "box": [0.25, 0.08, 0.50, 0.35], "zoom": 1.8}
]}
```

What to include: every text element, the legend, each axis's tick row, any annotation, the
densest data region, and anything that looks empty but should not be.

### 5.3 Inspect and record

```bash
uv run sf_crop.py --image fig.png --spec qa/crops.json -o qa/r1/tiles
```

Read each crop with an image model against the `qa.md` checklist. Record every finding:

| Region | Defect | Severity | Evidence | Fix | Status |
|---|---|---|---|---|---|
| y-label | minus signs render as hyphens | error | crop `02-y-label` shows `-0.5` | `axes.unicode_minus=True` | open |

Evidence means "which crop, what you saw". A finding without evidence is a guess and will
be argued about later.

### 5.4 Fix, diff, re-review

```bash
# after fixing
uv run sf_diff.py --before qa/r1/fig.png --after qa/r2/fig.png -o qa/diff
```

The diff reports clusters of changed pixels as normalized boxes. Crop the clusters and look
at them — a fix for one defect routinely breaks something adjacent. This is why the second
round exists.

### 5.5 Round two

The first round finds structure: layout, hierarchy, missing elements. The second finds
detail: glyph quality, line weight at 1:1, antialiasing artifacts, alignment off by a
pixel, a colour that shifts between panels.

Two rounds minimum. More if the second round finds a blocking issue.

**Exit:** zero blocking findings, every warning either fixed or explicitly accepted with a
reason, review record written.

---

## Stage 6 — Deliver

```bash
uv run sf_export.py --script plot.py --outdir out --target-mm 89 --snippet fig2 --caption "..."
```

This runs the script, inspects every artifact it produced (font embedding, editable SVG
text, physical width, dpi, PGF flavour), and prints the LaTeX block.

Delivery checklist:

- [ ] Every format the venue asks for, verified rather than assumed
- [ ] PDF fonts embedded, no Type 3
- [ ] Physical width matches the target column
- [ ] Review record written and blocking findings at zero
- [ ] LaTeX insertion block, with a caption that states the conclusion
- [ ] Source script and data path recorded next to the artifacts

---

## Iteration when the figure is already wrong

Often the task is not "make a figure" but "this figure is bad, fix it". Order of
operations:

1. **Lint it first.** Static analysis on the existing script catches the structural
   problems (no style, jet, no units, no uncertainty) in seconds.
2. **Render and overlay.** Then crop. Judging an existing figure is the same protocol.
3. **Fix in order of leverage:** data honesty → missing information (units, uncertainty,
   N) → layout (collisions, clipping) → typography → colour. Reversing this order means
   polishing a figure that is still misleading.
4. **Diff each round.** On an unfamiliar figure the diff is the only way to know what your
   edit actually did.

## When to stop

Stop when a skeptical reader cannot find a defect, not when the figure is pretty. If two
consecutive review rounds find nothing but stylistic preferences, the figure is done — and
those preferences should be recorded as accepted warnings rather than chased.
