# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy", "pandas"]
# ///
"""Scatter matrix with a correlation network overlaid on its upper triangle.

The reference's structure, exactly:
  * lower triangle = pairwise scatter plots, coloured by site, marker by leaf type
  * diagonal = the trait name in a box
  * UPPER triangle = empty, and that emptiness is used: trait labels sit along the top,
    and curved network edges connect them. Edge colour = sign of r, edge style =
    p-value, edge width = |r|
  * a per-cell least-squares trend line in each scatter
  * four legends stacked on the right: site, leaf type, r sign, p value

The network overlay is the whole idea: it turns the wasted upper triangle into a
readable summary of the same correlations the scatter cells encode.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from matplotlib.patches import FancyArrowPatch, Circle
from matplotlib.lines import Line2D
from math import sqrt, erf

STYLE = Path(__file__).resolve().parents[2] / "styles"
plt.style.use([STYLE / "base.mplstyle", STYLE / "elsevier.mplstyle"])

DATA = Path(__file__).resolve().parent / "data"
OUT = Path(__file__).resolve().parent
MM = 1 / 25.4

df = pd.read_csv(DATA / "traits.csv")
traits = ["G_vmax", "V_cmax", "WUE_i", "Leaf_N", "Chl", "SLA", "Stomatal_density", "Pore_length"]
k = len(traits)

SITE_COLOURS = {"CB": "#1B7F79", "DL": "#6BB8D6", "DH": "#F2A07B", "XSBN": "#D62728"}
SITE_LABELS = {"CB": "Cold-temperate forest", "DL": "Warm-temperate forest",
               "DH": "Subtropical forest", "XSBN": "Tropical forest"}
MARKERS = {"Deciduous": "o", "Evergreen": "^"}


def p_value(rv: float, n: int) -> float:
    if abs(rv) >= 0.9999:
        return 0.0
    t = abs(rv) * sqrt((n - 2) / max(1e-12, 1 - rv**2))
    return 2 * (1 - 0.5 * (1 + erf(t / sqrt(2))))


r = df[traits].corr().values
N = len(df)

fig = plt.figure(figsize=(215 * MM, 145 * MM))

def _full_frame(ax) -> None:
    """Restore all four spines on a matrix cell.

    The base style drops the top and right spines, which is correct for a normal plot
    and wrong for a matrix: without them the grid reads as disconnected corner
    brackets instead of a table.
    """
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_linewidth(0.6)


# Grid: k x k. Diagonal cells hold the trait names, the lower triangle holds the
# scatters, and the upper triangle is left empty for the network.
left, bottom, width, height = 0.055, 0.05, 0.56, 0.62
cell_w = width / k
cell_h = height / k

axes = {}
for i in range(k):
    for j in range(k):
        x0 = left + j * cell_w
        y0 = bottom + (k - 1 - i) * cell_h
        axes[(i, j)] = fig.add_axes([x0, y0, cell_w * 0.93, cell_h * 0.93])

for i in range(k):
    for j in range(k):
        ax = axes[(i, j)]
        if i == j:
            ax.set_xticks([]); ax.set_yticks([])
            _full_frame(ax)
            ax.text(0.5, 0.5, traits[i].replace("_", "\n"), ha="center", va="center",
                    fontsize=6.2, transform=ax.transAxes, linespacing=0.90)
            continue
        if i < j:
            # Reserved for the network. Keep the frame and drop only the ticks: a cell
            # switched off with axis("off") leaves its neighbours' borders stopping
            # mid-air at every seam.
            ax.set_xticks([]); ax.set_yticks([])
            _full_frame(ax)
            continue
        xv = df[traits[j]].to_numpy()
        yv = df[traits[i]].to_numpy()
        for site, colour in SITE_COLOURS.items():
            for leaf, marker in MARKERS.items():
                mask = (df["Site"] == site) & (df["Leaf_type"] == leaf)
                ax.scatter(xv[mask], yv[mask], s=2.6, marker=marker, color=colour,
                           alpha=0.75, linewidths=0)
        if np.std(xv) > 0 and np.std(yv) > 0:
            b, a = np.polyfit(xv, yv, 1)
            xs = np.array([xv.min(), xv.max()])
            ax.plot(xs, a + b * xs, color="#2B2B2B", linewidth=0.6, zorder=5)
        ax.set_xticks([]); ax.set_yticks([])
        _full_frame(ax)

# --- network over the upper triangle -------------------------------------
# Nodes sit on the TOP-LEFT corner of each diagonal cell, so they descend in a
# staircase across the matrix. On a flat line the arcs collapse into a braid; on the
# staircase they span the upper triangle and read as a network.
net = fig.add_axes([left, bottom, width * 1.10, height * 1.34], frameon=False)
net.set_xlim(0, width * 1.10); net.set_ylim(0, height * 1.34)
net.set_xticks([]); net.set_yticks([])

node_x: dict[str, float] = {}
node_y: dict[str, float] = {}
for idx, name in enumerate(traits):
    # Top-right corner of diagonal cell (idx, idx): the diagonal cells step down-right,
    # so their corners form the staircase the arcs hang from.
    node_x[name] = (idx + 1) * cell_w
    node_y[name] = (k - idx) * cell_h

for idx, name in enumerate(traits):
    net.scatter(node_x[name], node_y[name], s=34, color="#8C8C8C", zorder=6, clip_on=False)
    # Label above and to the right of the node, clear of both the node and the cell text.
    # Label up and to the LEFT of the node. The arcs leave each node heading right and
    # down, so the upper-left quadrant is the only one they cannot cross.
    net.text(node_x[name] - 0.012, node_y[name] + 0.012, name,
             ha="right", va="bottom", fontsize=6.6, style="italic",
             clip_on=False, zorder=7)

for a in range(k):
    for b in range(a + 1, k):
        rv = r[a, b]
        pv = p_value(rv, N)
        # Draw only edges that carry a claim: a meaningful effect size or a strong
        # significance. Everything else turns the network into a hairball in which no
        # single relation can be read, which defeats the purpose of the overlay.
        if abs(rv) < 0.30 and pv > 0.001:
            continue
        colour = "#C0392B" if rv < 0 else "#2B4C9B"
        style = "-" if pv < 0.05 else (0, (2.2, 2.2))
        width_pt = 0.35 + 2.6 * abs(rv)
        x1, y1 = node_x[traits[a]], node_y[traits[a]]
        x2, y2 = node_x[traits[b]], node_y[traits[b]]
        # Negative rad bulges the arc up-left, into the empty upper triangle.
        rad = -0.22 - 0.20 * (b - a) / k
        net.add_patch(
            FancyArrowPatch((x1, y1), (x2, y2),
                            connectionstyle=f"arc3,rad={rad}",
                            arrowstyle="-", color=colour, linewidth=width_pt,
                            linestyle=style, alpha=0.85, zorder=4, clip_on=False)
        )

# --- legends -------------------------------------------------------------
leg = fig.add_axes([0.685, 0.06, 0.30, 0.88])
leg.axis("off")
leg.set_xlim(0, 1); leg.set_ylim(0, 1)

y = 0.97
leg.text(0.02, y, "Site", fontsize=8.5, fontweight="bold", va="top")
y -= 0.045
for site, colour in SITE_COLOURS.items():
    leg.scatter(0.06, y, s=26, color=colour)
    leg.text(0.13, y, f"{site}: {SITE_LABELS[site]}", fontsize=6.8, va="center")
    y -= 0.038

y -= 0.03
leg.text(0.02, y, "Leaf type", fontsize=8.5, fontweight="bold", va="top")
y -= 0.045
for leaf, marker in MARKERS.items():
    leg.scatter(0.06, y, s=26, marker=marker, color="#1A1A1A")
    leg.text(0.13, y, leaf, fontsize=6.8, va="center")
    y -= 0.038

y -= 0.03
leg.text(0.02, y, "Pearson's $r$", fontsize=8.5, fontweight="bold", va="top")
y -= 0.045
for label, colour in (("< 0", "#C0392B"), ("≥ 0", "#2B4C9B")):
    leg.plot([0.03, 0.10], [y, y], color=colour, linewidth=1.4)
    leg.text(0.13, y, label, fontsize=6.8, va="center")
    y -= 0.038

y -= 0.03
leg.text(0.02, y, "$P$ value", fontsize=8.5, fontweight="bold", va="top")
y -= 0.045
for label, style in (("< 0.05", "-"), ("≥ 0.05", (0, (2, 2)))):
    leg.plot([0.03, 0.10], [y, y], color="#1A1A1A", linewidth=1.2, linestyle=style)
    leg.text(0.13, y, label, fontsize=6.8, va="center")
    y -= 0.038

fig.savefig(OUT / "figF.png", dpi=300)
fig.savefig(OUT / "figF.pdf")
print("saved figF")
