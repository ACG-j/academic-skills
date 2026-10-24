# Colour

Colour carries meaning, so it has to survive three hostile conditions: a colourblind
reader, a black-and-white print, and a projector. A palette that fails any of them loses
information the figure had already encoded.

**Colour is never the only channel.** Pair it with marker shape or line style so the
encoding survives being printed in greyscale.

---

## Match the palette to what colour encodes

| Colour encodes | Use | Never |
|---|---|---|
| Nothing (one series) | a single colour, or a grey ramp | a rainbow of irrelevant hues |
| Unordered categories | a categorical palette, ≤ 8 | a sequential ramp (adjacent shades blur) |
| Ordered magnitude | sequential (viridis, cividis) | a categorical palette |
| Sign around zero | diverging with a meaningful centre | a rainbow |
| Emphasis on 1–2 items | accent colour + greys for the rest | colouring everything |
| Ordered categories | sequential, or one hue in tints | many hues |

With more than ~8 categories, colour stops working: highlight the two that matter and grey
the rest, facet into small multiples, or label directly.

---

## Categorical palettes

`palettes/palettes.json` holds these with metadata. `sf_palette.py --list` audits them all.

### Wong / Okabe-Ito (the default)

```
#0072B2  #D55E00  #009E73  #CC79A7  #E69F00  #56B4E9  #F0E442  #000000
blue     vermilion green   purple   orange   sky       yellow   black
```

Designed for colourblind safety. Two caveats found by measurement rather than reputation:

- **Yellow (#F0E442) and sky blue (#56B4E9) have low contrast on white** (1.3–2.3:1).
  Fine for large fills, poor for thin lines and small markers.
- **Yellow and orange sit close in grayscale.** In a B&W print they merge unless the marker
  differs.

So the base style's cycle uses only the first four, which survive both conditions:

```
#0072B2  #D55E00  #009E73  #CC79A7
```

### Paul Tol

`tol-bright` (7), `tol-muted` (10), `tol-vibrant` (7). Muted is for print; vibrant for
slides. Both are well-tested, and both degrade past ~6 series on white.

### Emphasis

`emphasis`: one accent plus neutrals — `#D55E00`, `#0072B2`, `#BDBDBD`, `#737373`,
`#000000`. Use when one series is the finding and the rest is context. This is the most
underused pattern: a figure where everything is coloured equally has no emphasis.

---

## Checking a palette

```bash
uv run sf_palette.py --audit wong
uv run sf_palette.py --audit "#0072B2,#D55E00,#009E73" --strict
```

Three measurements, with the thresholds and their provenance:

**Contrast** (WCAG relative luminance). ≥ 4.5:1 for text, ≥ 3:1 for graphical objects.
Below 1.5:1 a colour is effectively invisible — that is the only hard failure.

**Grayscale separation** (CIE L*). Two colours closer than ΔL* 10 merge in a B&W print.
This is the check that catches palettes which look fine in colour.

**Colourblind simulation** (Machado 2009 matrices, ΔE in CIELAB). Under deuteranopia,
protanopia, and tritanopia, series closer than ΔE 10 become one series. Measured example:
matplotlib's default orange `#ff7f0e` and green `#2ca02c` fall to ΔE 4.6 under protanopia —
they are indistinguishable for a protanope, which is roughly 1% of men.

Verify the maths holds by checking the known values:

```
white vs black contrast = 21.0
white L* = 100, black L* = 0, #808080 L* = 53.6
deuteranopia(#D55E00) = #9E8C00, deuteranopia(#009E73) = #8A8676
```

---

## Sequential and diverging colormaps

| Need | Use | Never |
|---|---|---|
| Magnitude | `viridis`, `cividis` | `jet`, `rainbow`, `hsv` |
| Print-only magnitude | `Greys` | |
| Signed values | `RdBu_r`, `PuOr_r`, `coolwarm` | `jet` |
| Cyclic (phase, angle) | `twilight_shifted` | `hsv` |

**Why not jet**: its luminance ramp is non-monotonic, creating false boundaries where the
data is smooth, and its red-green extremes are indistinguishable for colourblind readers.
`sf_lint.py` treats `jet` and friends as a blocking error.

**Diverging needs a meaningful centre.** Zero for a residual, a baseline for a change, a
neutral value for a ratio. A diverging map centred at the data mean implies a meaning the
data may not have.

```python
from matplotlib.colors import TwoSlopeNorm
norm = TwoSlopeNorm(vmin=-3, vcenter=0, vmax=8)   # asymmetric data around zero
```

**Always label the colourbar** with units and the transform (log? normalized? per-capita?).

**Same limits across compared panels.** If panel (a) runs 0–1 and (b) runs 0–10, the reader
will compare colours and conclude wrongly.

---

## Grayscale safety

The test: convert to greyscale (or print), do the series still separate?

If colour is the only channel, no. Fix it with redundancy:

```python
ax.plot(x, y1, color=COLORS[0], marker="o", linestyle="-",  label="A")
ax.plot(x, y2, color=COLORS[1], marker="s", linestyle="--", label="B")
ax.plot(x, y3, color=COLORS[2], marker="^", linestyle="-.", label="C")
```

Order the linestyles so the first three are maximally different: solid, dashed,
dash-dot. Dotted at small sizes is nearly solid.

For heatmaps, a perceptually uniform sequential map is already greyscale-monotonic —
viridis reads as increasing lightness, so it survives B&W.

---

## Accessibility beyond colour

- **Contrast against the background**: a thin pale line on white disappears. `sf_palette.py`
  reports the ratio per colour.
- **Do not encode by hue alone** when the reader may be colourblind: ~8% of men have some
  form of red-green deficiency.
- **Avoid red/green as the only distinction** — Science's guide states this explicitly.
- **Check on a projector**: washed-out contrast hides subtle palettes. Presentation figures
  need higher contrast than print figures.

---

## Anti-patterns

| Pattern | Problem | Fix |
|---|---|---|
| Rainbow for continuous data | false boundaries, non-monotonic lightness | viridis |
| Colour-only encoding | invisible in B&W | add marker/linestyle |
| 12-colour categorical | nobody can match legend to line | highlight 2–3, grey the rest |
| Red/green only | colourblind readers lose it | shape or blue/orange |
| Inconsistent colours across panels | reader re-learns the legend | one palette, one order |
| Colourbar without a label | magnitude has no unit | label it |
| Diverging centred at the mean | implies a meaning | centre at zero or the real reference |
| Saturated colours everywhere | no hierarchy | mute the context, accent the finding |
| Different limits per panel | false comparison | shared limits |
