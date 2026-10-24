---
name: scientific-figure
description: Produce publication-grade scientific figures — matplotlib or hand-written TikZ — with multi-journal styling, vector export (PDF/SVG/PGF/TikZ/EPS), and a three-layer review that crops the render and inspects every label, legend, and line at native resolution. Use whenever a figure is headed into a paper, thesis, conference, or report; when a plot must match a journal's column width or a Chinese thesis template; when exporting to LaTeX/TikZ; when auditing an existing figure for units, uncertainty, colourblind safety, or grayscale legibility; or when a figure "looks wrong but I can't say why". Triggers on 科研绘图、论文插图、期刊格式、TikZ 示意图、技术路线图、三线表、图表校对.
whenToUse: A figure is going into a scientific document, or an existing figure needs auditing against publication standards. Not for interactive dashboards, animations, GIS maps, or decorative art.
---

# Scientific figures

A figure is finished when a demanding reviewer cannot find one "yes, but…" — not when
the data is plotted and legible. This skill covers the whole path: decide what the figure
must prove, render it in the right stack, export it in the format the venue accepts, and
review the actual pixels.

**Everything here is a default with a reason, not a rule.** Where a project's own
convention, a journal's live author guide, or the science itself demands otherwise, follow
that and say why. The scripts are optional tools, not a required pipeline.

## Four hard rules

Only these are non-negotiable, because each one is a defect that ships silently:

1. **The review pass is not optional.** Every figure gets rendered, cropped, and looked at
   with an image-capable model before delivery. Static checks cannot see a hyphen where a
   minus sign belongs.
2. **State the physical size and the target format before drawing.** A figure sized for a
   screen becomes a blurred, rescaled mess in a 89 mm column.
3. **Chinese text requires an explicit CJK font.** matplotlib's defaults drop those glyphs
   and emit tofu boxes with only a warning in the log.
4. **Verify the export, don't trust it.** Check font embedding in the PDF, editable text in
   the SVG, and that the TikZ actually compiles.

## Workflow

Six stages. Each has an exit condition and a `skip-if`.

| # | Stage | Exit condition | Skip if |
|---|---|---|---|
| 1 | **Contract** — write the one-sentence claim, hero panel, and what statistics appear on the figure | `contract.yaml` exists | the user already stated the claim and the figure type |
| 2 | **Design** — pick the chart type, panel hierarchy, and target style | chart type + journal style chosen | the request names both |
| 3 | **Implement** — write the plotting script or the TikZ source | script runs, artifact written | never |
| 4 | **Lint** — static source analysis, then runtime layout | no blocking finding | never for L1; L2 may be skipped for TikZ (nothing to execute) |
| 5 | **Review** — overlay, crop, inspect, record, fix, diff | zero blocking findings, at least two rounds | never |
| 6 | **Deliver** — export every required format, verify, emit the LaTeX block | artifacts verified | never |

Read `references/workflow.md` for the stage detail, the contract template, and the
iteration protocol.

## Choose the route

| Situation | Route |
|---|---|
| Data-driven statistical figure, many points, fast iteration | **matplotlib** (`sf_style.py` + `sf_export.py`) |
| Text must match the body's fonts exactly; precise geometric layout; schematic | **TikZ**, model writes the template, Python supplies data |
| Both: a data panel plus a schematic panel | matplotlib for data, TikZ for the schematic, compose in LaTeX |
| A different stack (R/ggplot2, seaborn, plotly, Origin) | allowed — the style, export, and review layers still apply |

Route B is not a template-paste exercise. Read `references/tikz.md` for the rule that
separates a paper-grade schematic from a generic boxes-and-arrows diagram.

## Scripts

All are PEP 723 self-declaring; run them with `uv run`. JSON on stdout, human summary on
stderr, non-zero exit when something is blocking.

| Script | Use it to | Example |
|---|---|---|
| `sf_doctor.py` | check the machine before starting | `uv run sf_doctor.py --fix` |
| `sf_init.py` | scaffold a figure project with a contract | `uv run sf_init.py fig2 --style nature` |
| `sf_style.py` | list, preview, or generate a journal style | `uv run sf_style.py --preview nature -o qa/` |
| `sf_palette.py` | audit a palette for contrast, grayscale, colourblind separation | `uv run sf_palette.py --audit wong` |
| `sf_export.py` | export, verify fonts/formats, emit the LaTeX block | `uv run sf_export.py --script plot.py --target-mm 89 --snippet fig2` |
| `sf_lint.py` | static + runtime + image checks | `uv run sf_lint.py --all plot.py` |
| `sf_crop.py` | overlay a coordinate grid, then crop what the model chose | `uv run sf_crop.py --image fig.png --overlay` |
| `sf_sheet.py` | put many figures or tiles on one page | `uv run sf_sheet.py --dir qa/tiles -o qa/sheet.png` |
| `sf_diff.py` | see exactly what changed between rounds | `uv run sf_diff.py --before qa/r1.png --after qa/r2.png` |
| `sf_tex2png.py` | compile TikZ and rasterize it for review | `uv run sf_tex2png.py fig.tex -o qa/` |
| `sf_table.py` | turn a table into a booktabs LaTeX table | `uv run sf_table.py data.csv --style siunitx` |

## Review protocol

The part that makes the difference between "looks fine" and "actually checked".

**Do not guess coordinates.** Run `sf_crop.py --image fig.png --overlay` first. It returns a
copy with a labelled 0–1 grid; read positions off that image, then write a crop spec. This
works on any image — matplotlib, TikZ, Origin, a screenshot — because it depends on nothing
but pixels.

1. Look at the **full figure** first: does the claim read without the caption?
2. Write a crop spec for the regions that matter — legend, every axis label, tick rows,
   annotations, dense data, suspicious empty space.
3. Read each crop with an image model and check it against `references/qa.md`.
4. Record findings in a table with region, defect, severity, evidence, fix, status.
5. Fix, re-render, `sf_diff.py` against the previous round, then review the clusters it
   flags. Fixing one defect routinely introduces another.
6. Repeat until blocking findings are zero. Two rounds minimum; the second looks at
   pixel-level detail the first cannot see.

Read `references/qa.md` for the checklist, the severity rules, and the finding format.

## Deliverables

A finished figure comes with: the script or `.tex` source, the data it reads, every
requested export, the LaTeX insertion block, and the review record. `sf_export.py` prints
the insertion block and verifies the artifacts.

## References

| Read | When |
|---|---|
| `references/workflow.md` | every task — stages, contract, iteration |
| `references/design.md` | choosing chart type, panel hierarchy, annotation strategy |
| `references/styles.md` | sizing, fonts, journal specs, mm↔inch↔pt |
| `references/palettes.md` | colour choice, colourblind and grayscale safety |
| `references/integrity.md` | anything where the figure could mislead |
| `references/export.md` | formats, font embedding, LaTeX inclusion |
| `references/tikz.md` | TikZ route, schematics, hero figures, compile issues |
| `references/tables.md` | booktabs, siunitx, significance marks, long tables |
| `references/qa.md` | every review round |
| `references/teams.md` | multi-figure work split across agents |
| `references/escape-hatch.md` | animation, interaction, GIS, huge data, Word |

## Not covered

Animation, interactive charts, GIS/map projections, more than ~1e6 points, Word-native
chart objects, and decorative illustration. `references/escape-hatch.md` points at better
tools for each.
