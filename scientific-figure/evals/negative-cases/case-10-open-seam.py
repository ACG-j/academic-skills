# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Negative case: a matrix whose borders stop mid-air

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
for i in range(3):
    for j in range(3):
        ax = fig.add_axes([0.1 + j * 0.28, 0.1 + i * 0.28, 0.26, 0.26])
        if i < j:
            ax.axis("off")
        else:
            ax.scatter(rng.random(8), rng.random(8), s=4)
        ax.set_xticks([]); ax.set_yticks([])
fig.savefig("case-10.png", dpi=300)
fig.savefig("case-10.pdf")
