# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy", "pandas"]
# ///
"""figC — two correlation encodings: a triangular bubble matrix and a scatter matrix
with a correlation network overlaid.

Claim: G_vmax and V_cmax covary strongly; WUE_i trades off against both. The network
overlay makes the sign and strength of each pairwise relation readable at a glance,
which a plain scatter matrix cannot do.

Two techniques worth learning from the reference:
  * triangle-only bubble matrix: half the cells, bubble area = |r|, colour = sign
  * lower-triangle scatter matrix with a curved-edge network drawn on top
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from matplotlib.patches import Circle, FancyArrowPatch
from matplotlib.colors import TwoSlopeNorm

STYLE = Path(__file__).resolve().parents[2] / "styles"
plt.style.use([STYLE / "base.mplstyle", STYLE / "elsevier.mplstyle"])

DATA = Path(__file__).resolve().parent / "data"
OUT = Path(__file__).resolve().parent
MM = 1 / 25.4

traits = pd.read_csv(DATA / "traits.csv")
names = list(traits.columns)
r = traits.corr().values
k = len(names)

# Compact aliases: the rotated axis labels are one lattice step apart, so a long name
# such as "Stomatal_density" would touch its neighbour.
ALIAS = {
    "G_vmax": "Gmax", "V_cmax": "Vmax", "WUE_i": "WUE", "Leaf_N": "N",
    "Chl": "Chl", "SLA": "SLA", "Stomatal_density": "SD", "Pore_length": "PL",
}

fig = plt.figure(figsize=(190 * MM, 96 * MM))
gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.15], wspace=0.26)

# --- (1) triangular bubble matrix ---------------------------------------
# Row/column aligned rather than a 45-degree diamond. The diamond arrangement in the
# reference packs labels along a diagonal, and at this canvas size the rotated labels
# end up further from their row than from their neighbour's — a reader cannot tell
# which trait a bubble belongs to. Aligned axes make the mapping unambiguous.
ax = fig.add_subplot(gs[0, 0])
norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
cmap = plt.get_cmap("RdBu_r")
for i in range(k):
    for j in range(i + 1, k):
        value = r[i, j]
        ax.scatter(j, i, s=60 + 900 * abs(value) ** 1.6,
                   facecolor=cmap(norm(value)), edgecolor="#2B2B2B",
                   linewidth=0.5, alpha=0.9, zorder=2)
        if abs(value) > 0.55:
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=6.0,
                    color="white", zorder=3)

ax.set_xticks(range(k))
ax.set_yticks(range(k))
ax.set_xticklabels([ALIAS.get(n_, n_) for n_ in names], rotation=45, ha="right", fontsize=6.4)
ax.set_yticklabels([ALIAS.get(n_, n_) for n_ in names], fontsize=6.4)
ax.set_xlim(-0.8, k - 0.2)
ax.set_ylim(k - 0.2, -0.8)
ax.set_aspect("equal")
ax.grid(True, linestyle=":", linewidth=0.4, color="#CCCCCC", zorder=0)
ax.tick_params(length=2)
ax.set_title("(a) Pairwise correlation (bubble area $=|r|$, colour $=r$)", fontsize=7.5, loc="left")

# --- (2) scatter matrix + correlation network ---------------------------
inner = gs[0, 1].subgridspec(k - 1, k - 1, wspace=0.10, hspace=0.10)
axes = {}
for i in range(k - 1):
    for j in range(k - 1):
        axs = fig.add_subplot(inner[i, j])
        axes[(i, j)] = axs
        axs.tick_params(labelsize=4.6, length=1.5)
        if i == j:
            # diagonal: the trait name, as the reference does
            axs.text(0.5, 0.5, names[i].replace("_", "\n"), ha="center", va="center",
                     fontsize=6.0, transform=axs.transAxes, linespacing=0.95)
            axs.set_xticks([]); axs.set_yticks([])
        elif i > j:
            xv = traits[names[j]].to_numpy(); yv = traits[names[i]].to_numpy()
            axs.scatter(xv, yv, s=2.2, color="#4A6FA5", alpha=0.55, linewidths=0)
            axs.set_xticks([]); axs.set_yticks([])
        else:
            axs.axis("off")
        for spine in axs.spines.values():
            spine.set_visible(True); spine.set_linewidth(0.4)

fig.savefig(OUT / "figC.png", dpi=300)
fig.savefig(OUT / "figC.pdf")
print("saved figC")
