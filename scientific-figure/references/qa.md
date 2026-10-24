# Review protocol (QA)

The review is the part that turns "looks fine" into "checked". This file is the checklist
you run against every crop, plus the rules that keep the review honest.

---

## Why crops, and why the model chooses them

A defect that matters is small. A 0.5 pt line that vanishes at print size, a hyphen where a
minus sign belongs, a legend that covers three data points, an axis label 2 px from the
edge, two tick labels touching. None of these survive a downscaled full-figure view, and
none are visible to static analysis.

So: look at the full figure for structure, then at native-resolution crops for detail.

**The model decides what to crop.** Run `sf_crop.py --image fig.png --overlay` first — it
returns the same figure with a labelled 0–1 grid. Read coordinates off that image and write
them into a spec. Guessing coordinates from a bare image is off by several percent, which
is exactly enough to cut a label in half and then review a truncated fragment as if it were
complete.

This also means the protocol works on any image: matplotlib, TikZ, Origin, MATLAB, a figure
lifted from a PDF.

`--auto full,grid,edges` exists for coverage when nothing has been judged yet. It is a
starting point: mechanical tiling spends equal attention on a large empty area and on a
cramped legend, while defects cluster in text.

---

## Reading a crop at the right size

`sf_crop.py` fits every crop to a readable size band. Two rules it enforces, and that you
should know when reading its output:

- **It never enlarges a large crop.** Upscaling adds no information.
- **It never lets a crop exceed ~1600 px on the long edge**, because the image tool
  downscales past its pixel budget and the detail is lost silently.

If a crop comes back blurry, the source render was too low-resolution. Re-render at higher
dpi rather than zooming harder — `sf_lint.py --image` warns when the review PNG is too
small.

---

## The checklist

Run through this for every crop. Not every item applies to every region; the point is to
have looked.

### Text

- [ ] **Complete** — no glyph cut off by the crop or the canvas edge
- [ ] **Correct glyphs** — minus signs are `−` not `-`; × not x; µ not u; ° present; no tofu
- [ ] **Units present** on every quantitative axis label, in parentheses or after a slash
- [ ] **Symbols italic, units upright** — `$t$ (s)`, not `t (s)` or `$t (s)$`
- [ ] **Sub/superscripts** rendered as such, not `10^6` or `e6`
- [ ] **Consistent size** across labels, ticks, legend, annotation
- [ ] **No collision** — no two text elements touch or overlap
- [ ] **Readable at final size** — 6 pt floor for print, 5 pt absolute minimum
- [ ] **Chinese renders** — no missing-glyph boxes, no font fallback that changes the style

### Legend

- [ ] **Covers no data** — check against the plotted points, not just by eye
- [ ] **Order matches** the reading order of the series (or the visual order)
- [ ] **Entries complete** — nothing plotted is missing from the legend
- [ ] **Marker and linestyle shown**, not colour alone
- [ ] **Not redundant** — a one-series figure rarely needs a legend; label the line instead
- [ ] **Frame** helps or hurts depending on the background; a frame over data is worse than none

### Axes and ticks

- [ ] **Scale honest** — bar charts start at zero; a truncated axis is disclosed
- [ ] **Tick density** readable; no overlapping labels
- [ ] **Tick labels** at sensible precision — `1.0` not `1.000000`
- [ ] **Minor ticks** consistent and not busier than the data
- [ ] **Log axes labelled as log**
- [ ] **Limits** show the data with a little air, not so much that variation vanishes
- [ ] **Spines** — a removed spine must not remove needed information

### Data marks

- [ ] **Line weights** survive at final size (0.5 pt floor; 0.7–1.2 pt typical)
- [ ] **Markers** distinguishable at 1:1, not just when zoomed
- [ ] **Error bars / bands** present where uncertainty exists, with the interval type stated
- [ ] **Overplotting** handled — alpha, jitter, or aggregation
- [ ] **Missing data** shown as a gap, not silently bridged
- [ ] **Colour carries no meaning alone** — redundant marker or linestyle

### Composition

- [ ] **Hero panel** identifiable in under a second
- [ ] **Alignment** — panels, labels, and edges line up
- [ ] **Whitespace** balanced; no large dead zone and no cramped corner
- [ ] **Annotations** point at what they describe, and sit in empty space
- [ ] **Panel labels** (a), (b) consistent in size, position, and style
- [ ] **Aspect ratio** appropriate — not stretched to fill a box

### Colour

- [ ] **Grayscale legible** — desaturate mentally; do the series still separate by marker/shape?
- [ ] **Colourblind safe** — run `sf_palette.py --audit` on the actual palette
- [ ] **Contrast** against the background sufficient for thin marks and text
- [ ] **Colormap** perceptually uniform (viridis/cividis), diverging centred at a meaningful value
- [ ] **Colourbar** labelled with units and the transform
- [ ] **Consistent** across panels meant to be compared

### Honesty

- [ ] **Nothing hidden** — no point removed, no axis tuned to amplify an effect
- [ ] **Uncertainty not decorative** — error bars mean something and are defined
- [ ] **N** visible when it varies
- [ ] **Transforms disclosed** — normalization, smoothing, binning, log
- [ ] **Figure and caption agree**

---

## Severity

| Severity | Meaning | Action |
|---|---|---|
| **error** | Misleading, unreadable, or broken. Ships as a defect. | Must fix before delivery |
| **warn** | Degrades quality; a reviewer would notice. | Fix, or accept explicitly with a reason |
| **info** | Preference or context. | Note and move on |

Calibration, because severity inflation makes the review useless:

- A missing unit on a quantitative axis is an **error**, not a warning — the number is
  meaningless without it.
- A minus sign rendered as a hyphen is an **error** — it reads as a range or a dash.
- A legend overlapping two points is a **warn**; overlapping the entire series is an
  **error**.
- "I would have used a different blue" is **info**, and probably not worth recording.

---

## Recording findings

Write them down, in a table, with evidence:

| # | Region | Defect | Severity | Evidence | Fix | Status |
|---|---|---|---|---|---|---|
| 1 | y-label | `-0.5` uses a hyphen, reads as a dash | error | crop `02-y-label` | `axes.unicode_minus=True` | fixed r2 |
| 2 | legend | covers 3 points near t=8 | warn | crop `01-legend` | move to `upper left` | fixed r2 |
| 3 | x-ticks | `10` collides with `9` | error | crop `04-xticks` | `MaxNLocator(6)` | fixed r2 |

Why evidence matters: a finding without it is an opinion, and opinions get argued about
instead of fixed. "Crop `02-y-label` shows a hyphen" ends the discussion.

Keep the record next to the figure (`qa/review.md`). It is also the artifact that proves the
review happened.

---

## Rounds

**Round 1 — structure.** Full figure plus the text regions. Find: missing information,
hierarchy problems, collisions, clipping, legend placement, obvious colour problems.

**Round 2 — detail.** Zoomed crops. Find: glyph quality, line weight at 1:1, alignment off
by a pixel, antialiasing artifacts, minus signs, subscript rendering, colour drift between
panels.

**Round 3+ — regression.** Only after a fix. Diff first, then crop the clusters the diff
flags. Do not re-review the whole figure; that wastes the attention the diff just saved.

A round that finds nothing is a legitimate outcome, but only after looking. "I looked at the
full figure and it seemed fine" is not a round.

---

## Failure modes of the review itself

- **Reviewing the downscaled full figure only.** Guarantees missing every small defect.
- **Guessing crop coordinates.** Produces truncated crops, then "defects" that are really
  crop artifacts.
- **Trusting the lint pass.** It cannot see anything data-dependent. A figure can pass every
  automated check and still be unreadable.
- **Fixing without diffing.** The fix becomes the next defect.
- **Recording findings without evidence.** They cannot be verified or closed.
- **Stopping at round one.** The detail defects are all in round two.
- **Chasing preferences.** If the third round only finds taste, stop and record the taste as
  accepted.

---

## The judgement pass

Four questions the checklist cannot answer, because they need the science, not the pixels.
Answer them explicitly before delivery.

1. **Does the figure argue a mechanism?** Cover the caption. Is the claim still readable?
   If the key event — the threshold crossing, the inflection, the region where data runs
   out — is only in the caption, it belongs on the figure.
2. **Is there one hero?** Run the drop test: remove each panel, does the claim weaken? If
   not, that panel was decoration.
3. **Would a skeptic find a hole?** Where is the uncertainty, what is N, can it be
   reproduced? These must be answerable from the figure.
4. **Does it read as a paper figure at a glance?** Half a second, before parsing content.
   If it reads as a homework plot, the gap is composition and typography, not data.

A figure that clears every mechanical check and fails question 1 is still not done. The
mechanical layer buys "nothing to attack"; only these four buy "a reader stops on the page".

---

## Composite figures: what replication practice taught

Replicating four published composite figures (SHAP beeswarm, correlation heatmap with a
companion bar panel, bubble matrix + scatter matrix, regression mosaic with marginals)
surfaced defects that the checklist above catches only if the reviewer knows to look.

**Subplot spacing is the dominant defect class.** A multi-panel figure fails first at its
seams: one panel's y tick labels run into its neighbour's x tick labels. `sf_lint.py`
reports these with the two axes indices (`axes 0 vs 2`), which is the difference between a
finding you can act on and one you cannot. Fixes, in order of preference:

1. Remove the tick labels that carry no information (a marginal histogram needs no y scale)
2. Reduce the tick count to what the panel width supports — three per axis is often right
3. Increase `wspace`/`hspace` for that subgridspec
4. Enlarge the canvas, if the content genuinely needs the room

**A label touching a neighbour is not the same as a label touching its own axis.** Two
x-tick labels of one axis abutting is normal. An x-tick label and a y-tick label meeting at
the origin is how axes are drawn. The lint now distinguishes these by role rather than by
string, which removed a class of false positives while keeping the real seam defects.

**Hand-placed axes overlap by construction.** `fig.add_axes([x, y, w, h])` for a colourbar
puts it wherever the fractions say, with no knowledge of the gridspec. Every time it was
used in the replication, it landed on a panel. Give the colourbar its own gridspec column.

**Dense matrix labels set the canvas size.** A 15×15 annotated matrix at 180 mm gives ~9 mm
cells, which cannot hold 6 pt text. Either the canvas grows or the annotations go; shrinking
the font below the 6 pt floor is not an option.

**What the lint still cannot see.** Two things, both of which needed the visual pass:

- *Semantic placement.* A rotated label may sit closer to its neighbour's row than to its
  own, so the reader cannot tell which trait a mark belongs to. Zero collisions, wrong
  meaning. Row/column-aligned axes fixed it; no automated check would have flagged it.
- *Over-correction.* After a fix the spacing can become so generous that the figure reads
  as disconnected — a colourbar floating far from the series it belongs to. Only looking at
  the whole figure catches this.
