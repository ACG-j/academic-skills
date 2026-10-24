# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Negative case: 4 pt text, unreadable in print

Planted defect — `sf_lint.py --all` must report it. This file exists so the lint has a
known-bad input; a linter with no failing fixtures is untested.
"""
from pathlib import Path
STYLE = Path(__file__).resolve().parents[2] / "styles"

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
plt.style.use([STYLE / "base.mplstyle"])
# Setting font.size alone does NOT shrink text when the style sets
# axes.labelsize / xtick.labelsize explicitly — every size must be lowered.
for key in ("font.size", "axes.labelsize", "xtick.labelsize", "ytick.labelsize",
            "axes.titlesize", "legend.fontsize"):
    plt.rcParams[key] = 4
rng = np.random.default_rng(0)
x = np.linspace(0, 10, 24)
fig, ax = plt.subplots(figsize=(3.5, 2.6))
ax.plot(x, np.sin(x), "o-")
ax.set_xlabel("Time $t$ (s)"); ax.set_ylabel("Signal (V)")
fig.savefig("case-02.png", dpi=300)
fig.savefig("case-02.pdf")
