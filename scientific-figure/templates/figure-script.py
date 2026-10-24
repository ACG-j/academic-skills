# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Template plotting script — copy, then replace the data and the labels.

Why each block exists:
  * the style is applied ONCE at the top, so every panel shares one typography
  * data is read from a path, never inlined, so it can be reviewed and re-derived
  * the RNG is seeded, so a rerun reproduces the figure
  * a review PNG is saved next to the vector output, for the crop-and-look pass
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# --- style: applied once ---------------------------------------------------
STYLE_DIR = Path("/path/to/scientific-figure/styles")
plt.style.use([STYLE_DIR / "base.mplstyle", STYLE_DIR / "nature.mplstyle"])

MM = 1 / 25.4
OUT = Path(__file__).parent
FIGURE_ID = "fig2"

# --- data ------------------------------------------------------------------
# df = pd.read_csv(Path("data/processed/allocation.csv"))
rng = np.random.default_rng(0)
x = np.linspace(0, 10, 24)
y = np.sin(x / 2) + rng.normal(0, 0.05, x.size)
lo, hi = y - 0.15, y + 0.15

# --- figure: one hero, the rest context ------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(89 * MM, 40 * MM), gridspec_kw={"width_ratios": [2, 1]})
ax = axes[0]

ax.plot(x, y, "o-", label="Measurement (N=24)")
ax.fill_between(x, lo, hi, alpha=0.25, linewidth=0, label="95% CI")

# Annotate the mechanism, in empty space — never over data.
peak = int(np.argmax(y))
ax.annotate(
    f"peak $A$={y[peak]:.2f} V",
    xy=(x[peak], y[peak]),
    xytext=(x[peak] + 1.5, y[peak] + 0.4),
    arrowprops={"arrowstyle": "->", "linewidth": 0.7},
    fontsize=7,
)

ax.set_xlabel("Time $t$ (s)")
ax.set_ylabel("Amplitude $A$ (V)")
ax.legend(loc="lower left")

axes[1].bar(["A", "B", "C"], [0.6, 0.8, 0.7], color="#0072B2", width=0.6)
axes[1].set_ylim(0, 1.0)          # bars start at zero
axes[1].set_ylabel("Score")
axes[1].set_xlabel("Group")

# --- export ----------------------------------------------------------------
for ext in ("pdf", "svg", "png"):
    fig.savefig(OUT / f"{FIGURE_ID}.{ext}", dpi=300)
print(f"saved {OUT}/{FIGURE_ID}.{{pdf,svg,png}}")
