# Escape hatch: when this skill is the wrong tool

Knowing when to leave is part of the skill. Each case below names the better tool and the
reason, so the decision does not have to be re-derived.

---

## Animation

**Use**: manim (explanatory), matplotlib `FuncAnimation` (data animation), or ffmpeg for a
frame sequence.

Why not this skill: the review protocol inspects still images. An animation needs
frame-by-frame or motion review, and the export formats here are static.

If the deliverable is a paper figure *and* a supplementary animation, build the still figure
here and produce the animation separately from the same data.

---

## Interactive charts

**Use**: plotly, Altair, Bokeh, or Observable.

Why not this skill: interactivity means the reader can change what is displayed, which
breaks the fixed-encoding model the review assumes. Accessibility also changes shape — a
static fallback and a data table are required in addition to the interactive view.

For a paper, interactive figures are supplementary; the main figure is still static.

---

## GIS and maps

**Use**: GeoPandas, cartopy, QGIS, or GMT.

Why not this skill: projections are a domain of their own. Choosing a projection, drawing
graticules, and handling scale bars are not covered here, and getting a projection wrong
produces a map that is subtly false. The style and review layers still apply once the map is
rendered.

---

## Very large data

**Threshold**: roughly above 1e6 marks.

**Use**: datashader (rasterize first), a hexbin/2D-histogram aggregation, or an embedded
raster with a vector overlay.

Why not this skill: a vector export of a million points is a 50 MB file that no viewer
handles and LaTeX cannot compile. Aggregation is the honest alternative — but then say so in
the caption, because the reader is no longer seeing the raw data.

---

## Word / PowerPoint-native charts

**Use**: native chart objects in the application, or embed the exported PDF.

Why not this skill: everything here targets LaTeX-oriented output. Word accepts PDF and
EMF; a PNG at 300 dpi is the fallback.

If the document is Word, still build the figure here and export PDF/PNG — the alternative
(native Word charts) has worse typography and no reproducibility.

---

## Decorative illustration

**Use**: Inkscape, Illustrator, or a generative tool.

Why not this skill: a graphical abstract or a cover image communicates tone, not data. The
review checklist (units, uncertainty, N) does not apply, and forcing it produces stiff
results.

---

## Dashboards and monitoring

**Use**: Grafana, Superset, Streamlit.

Why not this skill: those are live views of changing data, not fixed claims.

---

## 3D scientific visualisation

**Use**: ParaView, PyVista, or matplotlib 3D for simple cases.

Why not this skill: volume rendering, isosurfaces, and camera control need domain tools. The
review protocol still helps for a rendered still — check the colourbar, the axis labels, and
whether the projection is stated.

---

## When the data is the problem

Sometimes the figure cannot be made good because the data does not support the claim. Signs:

- No visible effect after honest scaling
- The uncertainty interval spans the claimed difference
- The comparison groups are not comparable
- N is too small for the claim

**No styling fixes this.** The right move is to report the limitation, change the claim, or
collect more data — and say so rather than producing a figure that implies more than the data
supports.

This is the most important escape hatch: recognising that the request is for a figure that
would mislead, and declining to draw it that way.

---

## Summary

| Need | Tool |
|---|---|
| Static paper figure | **this skill** |
| Animation | manim, FuncAnimation |
| Interactive | plotly, Altair |
| Maps | cartopy, QGIS |
| > 1e6 points | datashader, aggregation |
| Word-native | app chart objects, or embed PDF |
| Decorative art | Inkscape, Illustrator |
| Live dashboard | Grafana, Streamlit |
| Volume rendering | ParaView, PyVista |
| The data does not support the claim | report the limitation |
