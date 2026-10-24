# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy", "pandas"]
# ///
"""Diamond-lattice triangular correlation plot.

The reference's structure, exactly:
  * variables are the nodes of a triangular lattice laid out on a 45-degree diamond
  * a node's position encodes the PAIR (i, j), not a row/column index
  * lattice edges are drawn as dashed diagonals, so the reader can trace a pair
  * bubble area encodes |r|, bubble colour encodes the sign of r
  * the diagonal edge of the triangle is marked with large open circles (the "spine")
  * two legends: p-value mapped to bubble size, Pearson r mapped to colour

The whole point of the layout is that a pair can be found by following one diagonal
from each of the two labels — which a square matrix cannot do for the upper triangle.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from matplotlib.lines import Line2D
from matplotlib.colors import TwoSlopeNorm
from math import sqrt, erf

STYLE = Path(__file__).resolve().parents[2] / "styles"
plt.style.use([STYLE / "base.mplstyle", STYLE / "elsevier.mplstyle"])

DATA = Path(__file__).resolve().parent / "data"
OUT = Path(__file__).resolve().parent
MM = 1 / 25.4

df = pd.read_csv(DATA / "corr11.csv")
names = list(df.columns)
k = len(names)
r = df.corr().values
N = len(df)


def p_value(rv: float) -> float:
    if abs(rv) >= 0.9999:
        return 0.0
    t = abs(rv) * sqrt((N - 2) / max(1e-12, 1 - rv**2))
    return 2 * (1 - 0.5 * (1 + erf(t / sqrt(2))))


def lattice(i: int, j: int) -> tuple[float, float]:
    """Position of the pair (i, j) on the diamond lattice.

    Label i sits on the upper-left edge, label j on the upper-right edge. The pair is
    where the descending diagonal from label i meets the ascending diagonal from label j,
    so a reader traces two lines to find any cell. That traceability is the entire reason
    for this layout over a square matrix.
    """
    return (j - i, -(i + j))


fig = plt.figure(figsize=(255 * MM, 130 * MM))
# Main lattice on the left, legends on the right.
ax = fig.add_axes([0.04, 0.03, 0.70, 0.94])
lax = fig.add_axes([0.775, 0.08, 0.155, 0.84])
lax.axis("off")

cmap = plt.get_cmap("RdBu_r")
norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)

# --- lattice edges -------------------------------------------------------
# Only the diagonals that actually connect nodes of the triangle are drawn; drawing
# the full infinite family leaves a field of empty diamonds around the data.
def _diag_family(sign: int) -> None:
    """sign=+1 draws the "descending" family, -1 the "ascending" one."""
    for c in range(0, 2 * (k - 1) + 1):
        pts = []
        for i in range(k):
            for j in range(i, k):
                x, y = lattice(i, j)
                if abs(y - (sign * x)) < 1e-9 and abs(y - sign * (x - c) - 2 * c) < 1e-9:
                    pts.append((x, y))
        if len(pts) >= 2:
            pts.sort()
            ax.plot([pts[0][0], pts[-1][0]], [pts[0][1], pts[-1][1]],
                    linestyle=(0, (2.2, 2.2)), color="#9A9A9A", linewidth=0.5, zorder=0)


# Simpler and exact: connect every node to its lattice neighbours.
nodes = {(i, j): lattice(i, j) for i in range(k) for j in range(i, k)}
for (i, j), (x, y) in nodes.items():
    for step in ((1, 0), (0, 1), (1, 1)):
        neighbour = (i + step[0], j + step[1])
        if neighbour in nodes:
            nx, ny = nodes[neighbour]
            ax.plot([x, nx], [y, ny], linestyle=(0, (2.2, 2.2)),
                    color="#9A9A9A", linewidth=0.5, zorder=0)

# --- bubbles -------------------------------------------------------------
for i in range(k):
    for j in range(i + 1, k):
        x, y = lattice(i, j)
        value = r[i, j]
        p = p_value(value)
        ax.scatter(x, y, s=40 + 420 * abs(value) ** 1.4,
                   facecolor=cmap(norm(value)), edgecolor="#2B2B2B",
                   linewidth=0.55, alpha=0.92, zorder=3)

# --- the spine: the i == j edge of the triangle, large open circles ------
for i in range(k):
    x, y = lattice(i, i)
    ax.scatter(x, y, s=190, facecolor="white", edgecolor="#2B2B2B",
               linewidth=0.9, zorder=2)

# --- labels along the two upper edges ------------------------------------
# Right labels sit on the (0, j) edge, left labels on the spine (i, i). Each is pushed
# out perpendicular to the edge it belongs to, which is the only arrangement where a
# label cannot land on its neighbour or on a bubble.
SHORT = {name: name.replace("Feature_", "F").replace("Target_Y", "Y") for name in names}
for j in range(k):
    x, y = lattice(0, j)
    ax.text(x + 0.40, y + 0.40, SHORT[names[j]], rotation=-45, ha="left", va="bottom",
            fontsize=7.2, color="#1A1A1A")
for i in range(k):
    x, y = lattice(i, i)
    ax.text(x - 0.40, y + 0.40, SHORT[names[i]], rotation=45, ha="right", va="bottom",
            fontsize=7.2, color="#1A1A1A")

ax.set_xlim(-(k - 1) - 3.2, (k - 1) + 3.2)
ax.set_ylim(-2 * (k - 1) - 3.2, 3.2)
ax.set_aspect("equal")
ax.axis("off")
ax.text(-0.04, 0.5, "Sample-level correlation", transform=ax.transAxes,
        rotation=90, ha="center", va="center", fontsize=9)

# --- legends -------------------------------------------------------------
lax.set_xlim(0, 1); lax.set_ylim(0, 1)

lax.text(0.05, 0.97, "p-value", fontsize=8, va="top", fontweight="bold")
for n, (label, size) in enumerate((("≥ 0.05", 30), ("< 0.05", 70), ("< 0.01", 120), ("< 0.001", 180))):
    yy = 0.885 - n * 0.075
    lax.scatter(0.10, yy, s=size, facecolor="white", edgecolor="#2B2B2B", linewidth=0.8)
    lax.text(0.30, yy, label, fontsize=7, va="center")

lax.text(0.05, 0.56, "Pearson\nCorr. coeff.", fontsize=8, va="top", fontweight="bold")
cax = fig.add_axes([0.945, 0.10, 0.014, 0.34])
cb = fig.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), cax=cax)
cb.set_ticks([-1, -0.5, 0, 0.5, 1])
cb.ax.tick_params(labelsize=7, length=2)
cb.outline.set_linewidth(0.4)

fig.savefig(OUT / "figE.png", dpi=300)
fig.savefig(OUT / "figE.pdf")
print("saved figE")
