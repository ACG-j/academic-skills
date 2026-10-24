# Integrity: making the figure honest

A figure can be technically correct and still mislead. This file covers the ways that
happens and what to do instead.

The rule underneath all of it: **the figure must not make a claim the data does not
support.** Everything below is a specific case.

---

## Never alter the data to improve the figure

- Do not remove points that do not fit
- Do not hide an inconvenient category
- Do not tune axis limits to amplify an effect
- Do not invent values for missing data
- Do not selectively enhance part of an image

If a point looks wrong, investigate it. Removing it is a scientific decision that belongs
in the text with a stated reason, not a silent edit in a plotting script.

**Keep the layers separate**: raw data (immutable), the transformation (code, with seeds),
and the presentation (the figure). Overwriting raw data breaks reproducibility and, in most
fields, research integrity rules.

---

## Axes

**Bar charts start at zero.** A bar encodes length from a baseline; truncating it makes a
2% difference look like 200%. If the differences are too small to see from zero, the chart
type is wrong — use a dot plot or a lollipop, which encode position and may legitimately
start elsewhere.

**Point and line charts may use a nonzero limit** — position encoding tolerates it — but
show enough context and never choose limits solely to magnify a small effect.

**Do not extend the axis far past the data** to make variation look smaller. Science's
guide states scales should not extend beyond the plotted data.

**Comparable panels share limits.** If they cannot, make the difference unmistakable.

**Log axes**: label them as log, state the base, and declare the policy for zero and
negative values. Never silently drop them. Equal distances on a log axis are ratios, not
differences — a reader who assumes linear will misread the trend.

```python
ax.set_yscale("log")
ax.set_ylabel("Count (log scale)")   # say it on the axis, not only in the caption
```

For signed data spanning orders of magnitude, `SymLogNorm` with a disclosed linear region,
or `TwoSlopeNorm` around a meaningful centre.

---

## Uncertainty

**Show it when an estimate is displayed.** A mean without spread invites the reader to treat
it as exact.

**Name the interval.** SD, SE, 95% CI, percentile interval, bootstrap CI, IQR, posterior
interval — these are not interchangeable, and a bare error bar is ambiguous.

| You have | Show |
|---|---|
| Replicate measurements | SD (spread) or SE (precision of the mean) |
| An estimate with a CI | the CI, stated at its level |
| A full distribution | the distribution (violin, ECDF, strip), not a bar of means |
| A model prediction | the prediction interval, and say it is one |

**State N**, per series when it varies. A skeptic's first question is "how many".

**Do not add error bars mechanically** to a single measurement. If there is no uncertainty,
say so rather than inventing a bar.

**Significance stars are not uncertainty.** If used, name the test, the correction for
multiple comparisons, and give exact p-values where practical.

---

## Missing and excluded data

- **Distinguish** missing, zero, below-detection-limit, and excluded. They are four different
  things and collapsing them is a claim.
- **Do not silently connect** across a gap in a time series. Break the line, or state that
  the interpolation is a model.
- **Give missing values a legend entry** or a neutral colour in the colormap (`cmap.set_bad`).
- **Record exclusions** and why, outside the plotting code as well.

```python
y_with_gaps = np.where(mask, y, np.nan)   # NaN leaves a visible gap
ax.plot(x, y_with_gaps)                    # matplotlib breaks the line at NaN
```

---

## Aggregation, smoothing, and binning

These are transformations, and transformations are claims.

- **Record** bin edges, bandwidth, smoothing method, and whether the choice was made before
  or after seeing the result.
- **Do not let smoothing imply data between measured points.** A spline through 5 points
  suggests knowledge of the curve that does not exist.
- **Show raw observations** when feasible; jitter is acceptable but not so far that a point's
  category becomes ambiguous.
- **Test sensitivity** to reasonable bin/bandwidth choices when the conclusion depends on it.

---

## Normalization

State the formula and the reference: per-capita, percent of baseline, z-score, min-max,
library-size. A normalized axis without a stated reference is uninterpretable.

Fit normalization parameters on the appropriate data partition — normalizing using the test
set leaks information and inflates apparent performance.

---

## Area, volume, and 3D

- **Prefer position** on a common scale; it is the encoding humans read most accurately.
- **If area encodes magnitude, scale the area**, not the radius. A bubble with twice the
  radius has four times the area and reads as four times the value.
- **Avoid 3D bars, pies, and perspective surfaces** for simple comparisons — occlusion and
  perspective distort the values being compared.
- **Genuine 3D data** (a surface, a manifold) is fine, but add orthogonal views and
  orientation cues.

---

## Dual axes

Two y-axes let the author choose the apparent correlation by choosing the scales. Use only
when the two quantities are physically linked (temperature and pressure in the same system),
and colour-code each axis to its series so the mapping is explicit.

If the goal is to show a relationship, a scatter plot of the two variables answers it
directly and honestly.

---

## Images and micrographs

- **Adjust brightness/contrast consistently** across the whole image unless a disclosed
  method requires otherwise.
- **Never selectively erase, clone, or enhance** features.
- **Preserve background** and non-specific signal.
- **Mark and explain** splices, omitted lanes, composites, stitched fields.
- **Keep originals**; some publishers request them during review.
- **Upsampling does not improve quality.** It changes pixel count, not information, and
  publishers explicitly warn against presenting it as such.

---

## The caption

The caption states the conclusion, not "Figure 3 shows the results". It carries:

- What is plotted, with units
- What the error bars / bands represent and at what level
- N, and what the replicates are
- The test used, if significance is marked
- Any transform (log, normalized, smoothed)

Figure and caption must not contradict each other. A caption claiming a trend the figure
does not show is a defect in the caption, and the figure is the one that is right.

---

## Quick audit

Run this before delivery:

- [ ] No data removed or hidden without a stated reason
- [ ] Bars start at zero; no axis truncated to amplify
- [ ] Axis limits show the data, not less
- [ ] Uncertainty drawn where estimates are shown, and its type is named
- [ ] N stated
- [ ] Missing data visible as missing, not as zero and not bridged
- [ ] Log axes labelled
- [ ] Normalization formula and reference stated
- [ ] Bubbles scale area, not radius
- [ ] Dual axes justified by a physical link
- [ ] Images adjusted globally, splices marked
- [ ] Caption states the conclusion and matches the figure
