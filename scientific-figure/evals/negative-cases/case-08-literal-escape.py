# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Negative case: a LaTeX escape rendered literally by matplotlib

Planted defect — `sf_lint.py --all` must report it. This file exists so the lint has a
known-bad input; a linter with no failing fixtures is untested.
"""
from pathlib import Path
STYLE = Path(__file__).resolve().parents[2] / "styles"

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
plt.style.use([STYLE / "base.mplstyle"])
rng = np.random.default_rng(0)
fig, ax = plt.subplots(figsize=(3.5, 2.6))
ax.plot(np.linspace(0, 5, 20), rng.random(20), label="Leaf\_type series")
ax.set_xlabel("Time $t$ (s)"); ax.set_ylabel("Signal (V)")
ax.legend()
fig.savefig("case-08.png", dpi=300)
fig.savefig("case-08.pdf")
