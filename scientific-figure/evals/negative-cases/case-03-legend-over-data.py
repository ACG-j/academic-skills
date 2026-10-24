# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Negative case: legend placed on top of the series

Planted defect — `sf_lint.py --all` must report it. This file exists so the lint has a
known-bad input; a linter with no failing fixtures is untested.
"""
from pathlib import Path
STYLE = Path(__file__).resolve().parents[2] / "styles"

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
plt.style.use([STYLE / "base.mplstyle", STYLE / "nature.mplstyle"])
rng = np.random.default_rng(0)
x = np.linspace(0, 10, 40)
fig, ax = plt.subplots(figsize=(3.504, 2.6))
# Three nearly-flat series crossing the middle: a centre legend hides them.
for i, name in enumerate(["alpha", "beta", "gamma"]):
    ax.plot(x, 1.0 + 0.05 * np.sin(x / (i + 1)) + i * 0.02, "o-", label=f"series {name}")
ax.set_ylim(0.8, 1.3)
ax.legend(loc="center", fontsize=9)   # lands on the data
ax.set_xlabel("Time $t$ (s)"); ax.set_ylabel("Signal (V)")
fig.savefig("case-03.png", dpi=300)
fig.savefig("case-03.pdf")
