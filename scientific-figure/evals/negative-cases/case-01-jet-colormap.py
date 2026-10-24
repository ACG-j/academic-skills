# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Negative case: jet colormap on continuous data

Planted defect — `sf_lint.py --all` must report it. This file exists so the lint has a
known-bad input; a linter with no failing fixtures is untested.
"""
from pathlib import Path
STYLE = Path(__file__).resolve().parents[2] / "styles"

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
plt.style.use([STYLE / "base.mplstyle"])
rng = np.random.default_rng(0)
data = rng.random((20, 20))
fig, ax = plt.subplots(figsize=(3.5, 2.6))
im = ax.imshow(data, cmap="jet")
ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
fig.savefig("case-01.png", dpi=300)
fig.savefig("case-01.pdf")
