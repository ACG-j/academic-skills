# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy", "pandas"]
# ///
"""figD — regression fit with marginal histograms and residual panels, 4 models.

Claim: all four ensembles track the measured value within ±20%; the residual
distribution is symmetric and centred, so no model shows systematic bias.

The reference's real technique is the marginal-panel layout: each model gets a
2x2 mosaic where the main scatter shares its x with a top histogram and its y with
a right histogram, plus a separate residual panel with its own histogram. That is
what makes the distribution of errors readable next to the fit.
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

df = pd.read_csv(DATA / "regression.csv")
models = ["RF", "AdaBoost", "GBRT", "XGBoost"]

MM = 1 / 25.4
fig = plt.figure(figsize=(190 * MM, 165 * MM))
outer = fig.add_gridspec(2, 2, hspace=0.46, wspace=0.34)

for index, model in enumerate(models):
    sub = df[df["model"] == model]
    row, col = divmod(index, 2)
    inner = outer[row, col].subgridspec(
        2, 3, width_ratios=[0.34, 1.0, 0.34], height_ratios=[0.34, 1.0],
        wspace=0.42, hspace=0.20,
    )
    ax_res = fig.add_subplot(inner[:, 0])      # residual scatter
    ax_top = fig.add_subplot(inner[0, 1])      # marginal x histogram
    ax_main = fig.add_subplot(inner[1, 1])     # fit scatter
    ax_right = fig.add_subplot(inner[1, 2])    # marginal y histogram

    resid = sub["predicted"] - sub["measured"]
    for split, marker, face in (("train", "o", "#3B4A6B"), ("test", "o", "#FFFFFF")):
        part = sub[sub["split"] == split]
        ax_main.scatter(part["measured"], part["predicted"], s=9, marker=marker,
                        facecolors=face, edgecolors="#2B2B2B", linewidths=0.45,
                        label=f"{split.capitalize()} set", zorder=3)
        ax_res.scatter(resid[sub["split"] == split], part["measured"], s=9, marker=marker,
                       facecolors=face, edgecolors="#2B2B2B", linewidths=0.45, zorder=3)

    lo, hi = 5, 92
    ax_main.plot([lo, hi], [lo, hi], color="#2B2B2B", linewidth=0.8, zorder=2)
    # ±20% band, the reference's tolerance envelope
    ax_main.fill_between([lo, hi], [lo * 0.8, hi * 0.8], [lo * 1.2, hi * 1.2],
                         color="#B9B9B9", alpha=0.35, linewidth=0, zorder=1)
    ax_main.text(72, 44, "+20%", rotation=32, fontsize=6, color="#B22222")
    ax_main.text(34, 62, "-20%", rotation=32, fontsize=6, color="#B22222")

    ax_main.set_xlim(lo, hi); ax_main.set_ylim(lo, hi)
    ax_main.set_xticks([20, 50, 80]); ax_main.set_yticks([20, 50, 80])
    ax_main.set_xlabel("Measured, $d$ [mm]", labelpad=2)
    ax_main.set_ylabel("Predicted, $d$ [mm]", labelpad=2)
    ax_main.legend(loc="lower right", fontsize=6.2, handletextpad=0.4, borderpad=0.3)

    # metrics box, computed rather than copied
    r2 = np.corrcoef(sub["measured"], sub["predicted"])[0, 1] ** 2
    rmse = float(np.sqrt((resid ** 2).mean()))
    mae = float(resid.abs().mean())
    mape = float((resid.abs() / sub["measured"]).mean() * 100)
    medae = float(resid.abs().median())
    # The metrics box goes OUTSIDE the plotted area. Inside it covered the fit line —
    # the runtime lint flagged '-20%' overlapping the box, and the data underneath.
    ax_main.text(
        1.03, 0.98,
        f"Test Metrics:\n$R^2$: {r2:.3f}\nRMSE: {rmse:.2f}\nMAE: {mae:.2f}\n"
        f"MAPE: {mape:.3f}\nMedAE: {medae:.2f}",
        transform=ax_main.transAxes, va="top", ha="left", fontsize=6.0, clip_on=False,
        bbox={"boxstyle": "round,pad=0.28", "facecolor": "white", "edgecolor": "#8C8C8C", "linewidth": 0.5},
    )

    ax_top.hist(sub["measured"], bins=14, color="#8E9BC0", edgecolor="#2B2B2B", linewidth=0.4)
    ax_top.set_ylabel("Count", fontsize=6.2, labelpad=1)
    ax_top.tick_params(labelbottom=False)
    ax_top.set_yticks([])          # a marginal histogram needs no y scale
    ax_top.tick_params(labelsize=6.0)
    ax_right.hist(sub["predicted"], bins=14, orientation="horizontal",
                  color="#8E9BC0", edgecolor="#2B2B2B", linewidth=0.4)
    ax_right.set_xlabel("Count", fontsize=6.2, labelpad=1)
    ax_right.tick_params(labelleft=False)
    ax_right.set_xticks([])        # nor an x scale
    ax_right.tick_params(labelsize=6.0)

    ax_res.axvline(0, color="#2B2B2B", linewidth=0.7)
    ax_res.set_xlabel("Residuals [mm]", labelpad=2)
    ax_res.set_ylabel("Measured, $d$ [mm]", labelpad=2)
    ax_res.set_xlim(-14, 14)
    ax_res.set_xticks([-10, 0, 10])
    ax_res.tick_params(pad=1.5)
    ax_res.tick_params(labelsize=6.0)
    ax_res.set_ylim(lo - 4, hi + 4)
    ax_res.set_yticks([20, 50, 80])

    ax_top.set_title(f"({chr(97 + index)}) {model}", fontsize=7.5, pad=4)

fig.savefig(OUT / "figD.png", dpi=300)
fig.savefig(OUT / "figD.pdf")
print("saved figD")
