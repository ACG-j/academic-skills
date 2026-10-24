# Export

Saving a file is not exporting it. A PDF can carry unembedded fonts, an SVG can have its
text turned into outlines, a PNG can be 72 dpi, and the physical width can be wrong for the
column. All four look fine when you open them.

`sf_export.py` runs the script and then inspects what actually landed on disk.

---

## Format matrix

| Format | Use for | The trap | Verify with |
|---|---|---|---|
| **PDF** | submission; the default vector choice | fonts not embedded → substitute on the editor's machine | `pdffonts` shows every font `emb=yes`, no Type 3 |
| **SVG** | web, Illustrator/Inkscape editing | text converted to paths → uneditable | `<text>` elements present |
| **PGF** | embedding in LaTeX with the document's fonts | two incompatible flavours (below) | flavour detection |
| **TikZ** | hand-written or `matplot2tikz` output; editable as data | compile time; package dependencies | it compiles |
| **EPS** | older journal pipelines | needs conversion, fonts handled differently | opens, magic comment present |
| **PNG** | review, slides, web | not vector; dpi decoupled from physical size | dpi ≥ 300, width ≥ 600 px |
| **TIFF** | journals that demand raster line art | large files; needs Pillow | mode, dpi |

Default export: **PDF + SVG + PNG**. The PDF goes to the venue, the SVG stays editable, the
PNG is for review.

---

## PGF has two flavours and they are not interchangeable

This trips people up, so it is worth stating plainly:

**matplotlib's `pgf` backend** emits raw PGF drawing commands — `\pgfpath`, `\pgfusepath` —
inside a `pgfpicture`. The result is a vector snapshot that renders with the document's
fonts. It is *not* editable as plot data: you cannot change a data point in LaTeX.

**matplot2tikz / tikzplotlib** emit a pgfplots `axis` environment with `\addplot table` or
`coordinates`. This *is* editable as data — you can change a number in the `.tex`.

```python
# Raw PGF: font-exact, not data-editable
fig.savefig("fig.pgf")

# pgfplots: data-editable, needs matplot2tikz
import matplot2tikz
matplot2tikz.save("fig.tex")
```

`sf_export.py` detects which one a `.pgf` file is and says so, because "I exported PGF so
it is editable in LaTeX" is only true for the second kind.

**Dense scatter warning**: thousands of points become thousands of `\pgfpath` calls and
LaTeX compilation crawls. Above a few thousand marks, export PDF instead.

---

## Font embedding

Journals ask for **Type 42** (TrueType) embedding. matplotlib's default PDF output embeds
Type 3 bitmap-ish fonts, which render poorly and are commonly rejected.

```python
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42
```

`styles/base.mplstyle` sets both. `sf_export.py` reads the PDF with `pdffonts` and reports
each font with its embedding state — an unembedded font is a blocking error, Type 3 is a
blocking error.

---

## SVG: editable text versus outlines

```python
plt.rcParams["svg.fonttype"] = "none"    # keep text as text (default in the base style)
plt.rcParams["svg.fonttype"] = "path"    # convert to outlines
```

- `none` — text stays `<text>`, editable in Illustrator/Inkscape. **Requires the font on the
  viewing machine.** For sharing with a co-author who lacks your fonts, use `path`.
- `path` — visually identical everywhere, no font dependency, no longer editable as text.

For submission, send PDF, not SVG. For internal editing, `none`.

---

## Physical size

The single most common export defect: the figure is the right shape but the wrong size, so
the venue rescales it and every font size changes.

Set `figsize` in inches to the target column width:

```python
MM = 1 / 25.4
fig, ax = plt.subplots(figsize=(89 * MM, 65 * MM))   # Nature single column
```

Then `savefig(..., bbox_inches="tight")` trims the margins, which **reduces** the width by a
few millimetres. That is usually fine for a PDF included with `\includegraphics[width=\linewidth]`,
but it means the PNG is narrower than the nominal figsize. `sf_export.py` reports the actual
physical width and flags a mismatch beyond 1.5 mm.

If exact width matters, either skip `bbox_inches="tight"` or compensate by widening the
figsize.

---

## LaTeX inclusion

`sf_export.py --snippet NAME --caption "..."` prints a ready block:

```latex
\begin{figure}[tbp]
  \centering
  \includegraphics[width=\linewidth]{fig2.pdf}
  \caption{...}
  \label{fig:fig2}
\end{figure}
```

For a PGF file, `\input{fig.pgf}` instead, with the required preamble:

```latex
\usepackage{pgf}
\usepackage{lmodern}   # or the font package the figure expects
```

The `.pgf` header states its own requirements — read it rather than guessing.

**Width choices**:

| Setting | Effect |
|---|---|
| `width=\linewidth` | fills the column; scales fonts if the figure was not drawn at that width |
| `width=0.8\linewidth` | leaves margin; same scaling caveat |
| no width | uses the PDF's natural size — correct only if drawn at the target width |

**For a full-width figure in a two-column document**: `\begin{figure*}`, then
`width=\textwidth`.

---

## Verification

```bash
uv run sf_export.py --inspect out/fig2.pdf
uv run sf_export.py --script plot.py --outdir out --target-mm 89 --snippet fig2
```

What it checks per format:

| Format | Checks |
|---|---|
| PDF | every font embedded; no Type 3; font list |
| SVG | `<text>` count, editable-text flag, font-embedding presence |
| PNG | dpi, pixel size, colour mode, physical width vs target |
| PGF | flavour (raw PGF vs pgfplots), size, `\pgfusepath` count |
| EPS | magic comment |

---

## Delivery checklist

- [ ] Vector format present (PDF or SVG) — never raster-only for line art
- [ ] PDF fonts embedded, no Type 3
- [ ] SVG text editable if the file is meant for editing
- [ ] Physical width matches the target column
- [ ] Raster at ≥ 300 dpi if a raster is required
- [ ] Every format the venue asks for, verified rather than assumed
- [ ] LaTeX block emitted, caption states the conclusion
- [ ] Source script and data path recorded next to the artifacts

---

## An export manifest

For a multi-figure project, record what each artifact is. It takes one line per figure and
answers the question that arrives six months later: which script produced this PDF, from
which data, with which style.

```csv
id,path,format,width_mm,dpi,script,source_data,style,claim
fig2,out/fig2.pdf,pdf,89,,scripts/fig2_allocation.py,data/processed/allocation.csv,nature,"Sorted allocation wins above 60% load"
fig2,out/fig2.png,png,77.6,300,scripts/fig2_allocation.py,data/processed/allocation.csv,nature,""
```

`sf_export.py` emits the facts needed for it (`facts` in the JSON: physical width, dpi, font
list, format).
