# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Negative case: a full matrix with every cell drawn, including the ones meant to be empty

Planted defect — `sf_lint.py --all` must report it. This file exists so the lint has a
known-bad input; a linter with no failing fixtures is untested.
"""
from pathlib import Path
STYLE = Path(__file__).resolve().parents[2] / "styles"

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
plt.style.use([STYLE / "base.mplstyle"])
rng = np.random.default_rng(0)
fig = plt.figure(figsize=(3.5, 3.0))
for i in range(4):
    for j in range(4):
        ax = fig.add_axes([0.08 + j * 0.23, 0.08 + i * 0.23, 0.21, 0.21])
        if i > j:
            ax.scatter(rng.random(10), rng.random(10), s=3)
        ax.set_xticks([]); ax.set_yticks([])
        for side in ("top", "right", "bottom", "left"):
            ax.spines[side].set_visible(True)
fig.savefig("case-11.png", dpi=300)
fig.savefig("case-11.pdf")
