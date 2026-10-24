# Review record — fig1

Two rounds. Round 1 found a defect that static analysis cannot see; round 2 confirmed the
fix and looked for what the fix broke.

Target: Nature single column, 89 mm, 7 pt. Rendered at 300 dpi (932 × 674 px).

## Round 1

Crops chosen after reading the coordinate overlay (`sf_crop.py --overlay`):

| # | Region | Defect | Severity | Evidence | Fix | Status |
|---|---|---|---|---|---|---|
| 1 | y-label | `-0.5` and `-1.0` render with a hyphen, which reads as a dash or a range | error | crop `01-ylabel` — the glyph is short and centred low | `axes.unicode_minus = true` in base style | fixed r2 |
| 2 | y-label | serif label beside sans tick labels | warn | crop `01-ylabel` vs `03-bottom` — visibly different letterforms | verify the font stack; `mathtext` renders `$A$` in STIX by design | accepted — math italic is intentional |
| 3 | bottom | suspected blank band below the x-label | info | crop `03-bottom` — no blank band, `bbox_inches='tight'` trimmed it | none | not a defect |
| 4 | legend | does the legend cover data? | — | crop `02-legend` — sits in empty upper-right space | none | passes |

**Finding 3 is worth recording as a miss.** The full-figure view suggested a large empty
band at the bottom; the crop showed the axis label sitting close to the edge with the margin
already trimmed. Judging from the downscaled view alone would have produced a false fix.

## Round 2

After setting `axes.unicode_minus = true`, the canvas width changed from 925 to 932 px — the
minus sign is wider than the hyphen, so the layout shifted slightly. `sf_diff.py` reported a
canvas-size change and 4.6% changed pixels, which is expected for a glyph substitution that
affects every negative tick label.

Re-cropped the same three regions:

| # | Region | Check | Result |
|---|---|---|---|
| 1 | y-label | minus sign is U+2212, full width, vertically centred | fixed — verified in crop |
| 2 | y-label | no new collision with the tick labels | passes |
| 3 | bottom | x-label not clipped after the width change | passes |
| 4 | legend | still clear of the data | passes |

## Judgement pass

1. **Does it argue a mechanism?** Partly. It shows a signal with a CI band; it does not mark
   the peak or a threshold. For a methods illustration that is acceptable; for a result
   figure the peak should be annotated. Recorded as a known gap rather than fixed, because
   this example exists to demonstrate the process.
2. **One hero?** Single panel, so yes trivially.
3. **Skeptic's hole?** N=24 is in the legend, the interval is named (95% CI), units are on
   both axes. Reproducible: seeded, script committed.
4. **Paper figure at a glance?** Yes — despined, 7 pt, Wong palette, no chart junk.

## What the automated layers caught, and what they missed

| Check | Caught by |
|---|---|
| Reproducibility (seeded) | L1 |
| Units on both axes | L1 |
| Uncertainty drawn | L1 |
| Style applied | L1 |
| Vector export present | L1 |
| No collisions, no tiny fonts, no clipping | L2 |
| **Hyphen instead of minus** | **visual review only** |
| **Serif/sans mismatch in the label** | **visual review only** |
| False "blank band" defect | caught by the crop before it became a fix |

The last three rows are the argument for the crop-and-look pass. A figure can pass every
automated check and still print a hyphen where a minus sign belongs.
