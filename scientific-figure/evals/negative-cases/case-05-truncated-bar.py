# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Negative case: bar chart with a nonzero baseline

Planted defect — `sf_lint.py --all` must report it. This file exists so the lint has a
known-bad input; a linter with no failing fixtures is untested.
"""
from pathlib import Path
STYLE = Path(__file__).resolve().parents[2] / "styles"

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
plt.style.use([STYLE / "base.mplstyle"])
fig, ax = plt.subplots(figsize=(3.5, 2.6))
values = [3.1, 3.5, 3.2]          # inline data — also a reproducibility defect
ax.bar(["A", "B", "C"], values)
ax.set_ylim(3.0, 3.6)             # exaggerates a 0.4 difference
ax.set_xlabel("Group"); ax.set_ylabel("Score (a.u.)")
fig.savefig("case-05.png", dpi=300)
fig.savefig("case-05.pdf")
