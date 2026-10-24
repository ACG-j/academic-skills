# Styles: sizes, fonts, and journal specifications

Sizing is the constraint everything else follows from. A figure drawn at 12 in and shrunk
to an 89 mm column has 6 pt text become 1.7 pt — unreadable, and invisible on screen
because the figure looks fine at 100%.

**Draw at final size.** Then the font sizes in the script are the font sizes in print.

---

## Units

| From | To | Multiply by |
|---|---|---|
| mm | inch | ÷ 25.4 |
| inch | mm | × 25.4 |
| mm | pt | × 2.8346 |
| pt | mm | ÷ 2.8346 |
| inch | pt | × 72 |
| px at 300 dpi | mm | ÷ 300 × 25.4 |

Single column widths: 57 mm = 2.244 in, 89 mm = 3.504 in, 90 mm = 3.543 in.

---

## Font sizes for print

| Element | Range | Typical |
|---|---|---|
| Axis labels | 7–9 pt | 8 pt |
| Tick labels | 6–8 pt | 7 pt |
| Legend | 6–8 pt | 7 pt |
| Panel labels | 8–10 pt | 8 pt bold |
| Annotation | 6–8 pt | 7 pt |

**Absolute floor: 5 pt.** Below that, print loses strokes. Journals commonly state 5–7 pt
for final size.

If the numbers do not fit at 7 pt in an 89 mm column, the figure is carrying too much
information — split it or reduce the content, do not shrink the font.

---

## Font families

| Context | Family | Why |
|---|---|---|
| Most journals' submission specs | Arial / Helvetica (sans) | stated in author guides |
| IEEE, APS, ACM body-matching | Times New Roman (serif) | matches the typeset body |
| Chinese journals and theses | SimSun 宋体 + Times for Latin | standard 中文排版 |
| Slides, posters | Arial / Helvetica | screen legibility |

**Two families maximum** per figure. Mixing three is always visible and always accidental.

**Math**: `mathtext.fontset = 'stix'` matches Times closely and needs no LaTeX install.
`'cm'` for Computer Modern when the document is LaTeX with CM. `text.usetex = True` only
when LaTeX is available and the figure must match exactly — it slows rendering and adds a
dependency to every build.

Symbols italic, units upright: `$t$ (s)`, never `$t (s)$` or `t (s)`.

---

## Journal specifications

`styles/journals.json` carries the machine-readable version; `sf_style.py --list` prints it.

| Style | Column (mm) | Base font | Family | Line art |
|---|---|---|---|---|
| `nature` | 89 (183 double) | 7 pt | Arial | 450 dpi |
| `science` | 57 (121 double) | 7 pt | Helvetica | 300 dpi |
| `ieee` | 88.9 (181.9) | 8 pt | Times | 600 dpi |
| `elsevier` | 90 (190) | 8 pt | Arial | 500 dpi |
| `cell` | 85 (178) | 7 pt | Arial | 300 dpi |
| `pnas` | 87 (180) | 8 pt | Arial | 600 dpi |
| `acs` | 84.6 (177.8) | 8 pt | Arial | 600 dpi |
| `aps` | 86 (178) | 8 pt | Times | 600 dpi |
| `acm` | 84.6 (177.8) | 9 pt | Libertine/Times | 300 dpi |
| `journal-cn` | 80 (170) | 9 pt | SimSun + Times | 600 dpi |
| `thesis-cn` | 150 (A4 版心) | 10.5 pt | SimSun + Times | 600 dpi |

**These numbers drift.** Journals revise guides, and the rules differ by article type and
submission stage — Nature's flagship final-submission page does not govern Nature
Communications, and Extended Data has separate limits. Treat this table as a starting
point and verify against the target journal's live author guide before submission.

The JSON records a `reviewed` date for exactly this reason. A spec that is three years old
is a hypothesis.

---

## Applying a style

```python
import matplotlib.pyplot as plt
from pathlib import Path

STYLE_DIR = Path("<skill>/styles")
plt.style.use([STYLE_DIR / "base.mplstyle", STYLE_DIR / "nature.mplstyle"])
```

Apply once, at the top. Per-figure `rcParams` edits drift between figures and are invisible
in review — the fifth figure quietly uses 9 pt while the first four use 7 pt.

```bash
uv run sf_style.py --list                       # what exists, with specs
uv run sf_style.py --preview nature -o qa/      # render at the real physical size
uv run sf_style.py --apply nature               # print the snippet
uv run sf_style.py --from-spec my.json --register   # add a venue
```

`--preview` renders at the target size, so the preview *is* the legibility test: if 6 pt
tick labels are unreadable in the preview, they are unreadable in print.

---

## What the base style guarantees

`styles/base.mplstyle`:

- `pdf.fonttype = 42`, `ps.fonttype = 42` — TrueType embedding, journals ask for Type 42
- `svg.fonttype = 'none'` — text stays text, editable in Illustrator/Inkscape
- `savefig.bbox = tight` with a small pad — no wasted whitespace, no clipped labels
- Top/right spines off, ticks inward, minor ticks on
- Wong colourblind-safe cycle, ordered so the first four survive deuteranopia and B&W
- `axes.unicode_minus = false` — see the trap below
- `mathtext.fontset = 'stix'` — serif math that matches Times without LaTeX
- 300 dpi default for raster

Override any of it per figure. The preset exists so the *default* is right, not so the
figure cannot differ.

---

## Chinese text

The trap: matplotlib's default fonts contain no CJK glyphs. Chinese renders as boxes, and
the only signal is a warning buried in stderr.

```python
plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "SimSun", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False
```

The fallback chain matters: list a CJK font first, then a Latin font, so mixed text renders
correctly. `axes.unicode_minus = False` is not optional — with it on, matplotlib uses U+2212
from the math font, which many CJK fonts lack, producing a missing-glyph box for every
negative number.

`sf_doctor.py` checks that a CJK family exists *and* that a test render produces no
missing-glyph warning. `sf_lint.py --run` reports missing glyphs as a blocking error.

For Chinese documents, use `journal-cn` or `thesis-cn`: they set 宋体 for text with Times
for Latin and digits, which is the conventional pairing.

---

## Multi-panel sizing

Total width is the constraint, not per-panel width.

```python
# Two panels across an 89 mm column, 3 mm gap
fig, axes = plt.subplots(1, 2, figsize=(3.504, 2.2), gridspec_kw={"wspace": 0.35})
```

- Panel width = (column − gaps) / n. For 89 mm, two panels with a 3 mm gap gives 43 mm each.
- Keep `wspace`/`hspace` large enough that labels do not collide; `sf_lint.py --run` catches
  it when they do.
- Shared axes: `sharex=True, sharey=True` removes duplicated tick labels and buys width.

---

## Line weights and markers

| Element | Weight at final size |
|---|---|
| Axes frame | 0.6–0.8 pt |
| Data line | 0.9–1.3 pt |
| Marker edge | 0.6–1.0 pt |
| Error bar | 0.7–1.0 pt |
| Reference line | 0.6–0.8 pt, dashed |

At 300 dpi, 0.5 pt is about 2 px — visible on screen, at the edge of disappearing in print.
Below 0.5 pt is a defect.

Marker size 3–4 pt is standard for line plots. Scatter with many points needs 1–2 pt and
transparency.

---

## Resolution

| Content | dpi |
|---|---|
| Line art / vector original | not applicable — keep vector |
| Raster line art fallback | 600 |
| Combination art | 500–1000 (Elsevier asks 1000) |
| Photos, micrographs | 300 |
| Review PNG | 200–300 |

`sf_export.py` reports the actual dpi and flags anything under 300.
