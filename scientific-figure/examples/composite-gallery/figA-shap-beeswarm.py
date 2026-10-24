# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy", "pandas"]
# ///
"""figA — SHAP beeswarm (left) beside per-feature effect panels (right).

Claim: Soil_Moisture and NDVI dominate the model, and the effect of each driver is
monotone in the middle of its range but saturates at the extremes.

The reference's real technique is the beeswarm: for each feature, points are coloured
by feature value and stacked vertically by SHAP density, so the reader sees both the
spread and the direction of the effect in one row. The companion grid of small panels
adds the binned distribution underneath each scatter.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

STYLE = Path(__file__).resolve().parents[2] / "styles"
plt.style.use([STYLE / "base.mplstyle", STYLE / "elsevier.mplstyle"])

DATA = Path(__file__).resolve().parent / "data"
OUT = Path(__file__).resolve().parent
MM = 1 / 25.4

shap = pd.read_csv(DATA / "shap_values.csv")
feat = pd.read_csv(DATA / "feature_values.csv")
order = ["Wind_Speed", "Slope", "Soil_Moisture", "Precipitation", "NDVI_GIMMS3G", "Aspect"]

fig = plt.figure(figsize=(190 * MM, 108 * MM))
gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 0.05, 1.55], wspace=0.16)

# --- beeswarm ------------------------------------------------------------
ax = fig.add_subplot(gs[0, 0])
rng = np.random.default_rng(3)
for row, name in enumerate(order):
    values = shap[name].to_numpy()
    colour = feat[name].to_numpy()
    # Density stacking: bin along x, then fan the points within each bin.
    bins = np.linspace(values.min(), values.max(), 42)
    idx = np.clip(np.digitize(values, bins) - 1, 0, len(bins) - 2)
    jitter = np.zeros_like(values)
    for b in range(len(bins) - 1):
        mask = idx == b
        count = int(mask.sum())
        if count:
            spread = min(0.34, 0.012 * count)
            jitter[mask] = np.linspace(-spread, spread, count)
    ax.scatter(values, row + jitter, c=colour, cmap="coolwarm", s=3.2,
               linewidths=0, alpha=0.85, rasterized=True)

ax.set_yticks(range(len(order)))
ax.set_yticklabels(order, fontsize=7)
ax.invert_yaxis()
ax.set_xlabel("SHAP value (impact on model output)", fontsize=7.5)
ax.set_ylim(len(order) - 0.5, -0.5)
ax.axvline(0, color="#555555", linewidth=0.7)

# The colourbar gets its own gridspec column. Placing it with fig.add_axes() by
# fraction is what put it on top of the right-hand panels in the first attempt.
cax = fig.add_subplot(gs[0, 1])
cb = fig.colorbar(plt.cm.ScalarMappable(cmap="coolwarm",
                   norm=plt.Normalize(-3, 3)), cax=cax)
cb.ax.set_title("Feature value", fontsize=6.0, pad=4, rotation=0)
cb.ax.tick_params(labelsize=6.0)
cb.set_ticks([])          # ends are named in the caption; a 5 mm bar cannot host labels
cb.outline.set_visible(False)

# --- per-feature effect grid --------------------------------------------
inner = gs[0, 2].subgridspec(3, 2, hspace=0.78, wspace=0.50)
panels = ["Evapotranspiration", "LST_Night", "Solar_Radiation",
          "LST_Day", "Elevation", "Cloud_Cover"]
for i, label in enumerate(panels):
    sub = fig.add_subplot(inner[i // 2, i % 2])
    x = feat[order[i % len(order)]].to_numpy()
    y = shap[order[i % len(order)]].to_numpy()

    # binned distribution behind the scatter, as in the reference
    counts, edges = np.histogram(x, bins=22)
    centres = (edges[:-1] + edges[1:]) / 2
    twin = sub.twinx()
    twin.bar(centres, counts, width=(edges[1] - edges[0]) * 0.9,
             color="#D9D9D9", edgecolor="none", zorder=0)
    twin.set_yticks([]); twin.set_ylim(0, counts.max() * 3.2)
    twin.spines["right"].set_visible(False)
    twin.spines["top"].set_visible(False)

    sub.scatter(x, y, s=4, color="#3B4A6B", alpha=0.75, linewidths=0, zorder=2)
    # LOWESS-ish trend: a moving median, robust to the outliers a fit would chase
    sort_idx = np.argsort(x)
    xs, ys = x[sort_idx], y[sort_idx]
    window = max(9, len(xs) // 14)
    smooth = pd.Series(ys).rolling(window, center=True, min_periods=3).median().to_numpy()
    sub.plot(xs, smooth, color="#C0504D", linewidth=1.0, zorder=3)

    sub.set_xlabel(label, fontsize=6.6, labelpad=1.5)
    sub.set_ylabel("SHAP (log-odds)", fontsize=6.4, labelpad=1.5)
    sub.tick_params(labelsize=6.0)
    # Round tick positions, not data extremes: -2.999 is not a readable axis label.
    lo_t, hi_t = float(np.floor(x.min())), float(np.ceil(x.max()))
    sub.set_xticks([lo_t, 0, hi_t])
    sub.set_xlim(lo_t - 0.15, hi_t + 0.15)
    sub.set_zorder(twin.get_zorder() + 1)
    sub.patch.set_visible(False)
    sub.set_title(f"({chr(97 + i)})", fontsize=7, pad=2, loc="left")

fig.savefig(OUT / "figA.png", dpi=300)
fig.savefig(OUT / "figA.pdf")
print("saved figA")
