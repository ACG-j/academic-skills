# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy", "pandas"]
# ///
"""figB — correlation heatmap with significance marks + VIF bar panel.

Claim: indicators cluster into three correlated blocks; VIF stays below 2.5, so no
indicator needs dropping before regression.

Techniques worth learning from the reference:
  * cells coloured by r, annotated with r AND a significance star on a second line
  * a companion bar panel sharing the row order of the matrix
  * the reference's VIF panel is a third axes with its own value axis on the right
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Rectangle

STYLE = Path(__file__).resolve().parents[2] / "styles"
plt.style.use([STYLE / "base.mplstyle", STYLE / "elsevier.mplstyle"])

DATA = Path(__file__).resolve().parent / "data"
OUT = Path(__file__).resolve().parent

df = pd.read_csv(DATA / "indicators.csv")
names = list(df.columns)
r = df.corr().values
n = len(names)

# p-values from a t-test on r, so the stars mean something rather than being decorative
from math import sqrt, erf
def p_from_r(rv, nn):
    if abs(rv) >= 0.9999:
        return 0.0
    t = abs(rv) * sqrt((nn - 2) / max(1e-12, 1 - rv**2))
    # two-sided normal approximation; adequate for n=400
    return 2 * (1 - 0.5 * (1 + erf(t / sqrt(2))))

def stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""

# VIF: 1/(1-R^2) of each indicator regressed on the rest
vif = []
for i in range(n):
    others = np.delete(r, i, axis=0)[:, np.delete(np.arange(n), i)]
    # R^2 of column i predicted by the others, from the correlation matrix
    try:
        beta = np.linalg.solve(others.T @ others, others.T @ r[np.arange(n) != i, i])
        r2 = float(r[np.arange(n) != i, i] @ beta)
    except np.linalg.LinAlgError:
        r2 = 0.0
    vif.append(1.0 / max(1e-6, 1 - r2))

fig = plt.figure(figsize=(210 / 25.4, 175 / 25.4))
gs = fig.add_gridspec(1, 3, width_ratios=[n, 1.5, 0.25], wspace=0.06)

# --- heatmap -------------------------------------------------------------
ax = fig.add_subplot(gs[0, 0])
norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
im = ax.imshow(r, cmap="RdBu_r", norm=norm)

for i in range(n):
    for j in range(n):
        value = r[i, j]
        star = stars(p_from_r(value, len(df))) if i != j else ""
        colour = "white" if abs(value) > 0.6 else "black"
        ax.text(j, i - 0.13, f"{value:.2f}", ha="center", va="center",
                fontsize=6.5, color=colour)
        if star:
            ax.text(j, i + 0.26, star, ha="center", va="center",
                    fontsize=6.0, color=colour)

ax.set_xticks(range(n)); ax.set_yticks(range(n))
ax.set_xticklabels(names, rotation=0, fontsize=7.0)
ax.set_yticklabels(names, fontsize=7.0)
ax.set_xlabel("Indicator", labelpad=2)
ax.tick_params(length=0)
for spine in ax.spines.values():
    spine.set_visible(False)

# --- VIF bars ------------------------------------------------------------
ax2 = fig.add_subplot(gs[0, 1])
y = np.arange(n)
ax2.barh(y, vif, height=0.62, color="#F2C879", edgecolor="#8A6D1F", linewidth=0.4)
for yi, v in zip(y, vif):
    ax2.text(v + 0.06, yi, f"{v:.2f}", va="center", fontsize=6.4)
ax2.axvline(5, color="#B22222", linestyle="--", linewidth=0.7)
ax2.text(5.1, -0.9, "VIF=5", fontsize=6.2, color="#B22222", va="bottom")
ax2.set_ylim(n - 0.5, -0.5)
ax2.set_yticks([])
ax2.set_xlabel("VIF", labelpad=2)
ax2.set_xlim(0, max(6, max(vif) * 1.25))
ax2.spines["left"].set_visible(False)

# --- colourbar -----------------------------------------------------------
cax = fig.add_subplot(gs[0, 2])
cb = fig.colorbar(im, cax=cax)
cb.set_label("Corr ($r$)", fontsize=7)
cb.ax.tick_params(labelsize=6.4)
cb.outline.set_visible(False)

fig.savefig(OUT / "figB.png", dpi=300)
fig.savefig(OUT / "figB.pdf")
print("saved figB")
