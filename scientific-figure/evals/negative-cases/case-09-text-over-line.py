# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Negative case: an annotation sitting on top of the curve it annotates

Planted defect — `sf_lint.py --all` must report it. This file exists so the lint has a
known-bad input; a linter with no failing fixtures is untested.
"""
from pathlib import Path
STYLE = Path(__file__).resolve().parents[2] / "styles"

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
plt.style.use([STYLE / "base.mplstyle"])
x = np.linspace(0, 10, 100)
fig, ax = plt.subplots(figsize=(3.5, 2.6))
ax.plot(x, np.sin(x), linewidth=2.0)
ax.text(5.05, -0.943, "on the curve", ha="center", va="center", fontsize=8)
ax.set_xlabel("Time $t$ (s)"); ax.set_ylabel("Signal (V)")
fig.savefig("case-09.png", dpi=300)
fig.savefig("case-09.pdf")
