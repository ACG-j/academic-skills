# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Negative case: data inlined in the script, no source file

Planted defect — `sf_lint.py --all` must report it. This file exists so the lint has a
known-bad input; a linter with no failing fixtures is untested.
"""
from pathlib import Path
STYLE = Path(__file__).resolve().parents[2] / "styles"

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
plt.style.use([STYLE / "base.mplstyle"])
values = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9, 3, 2, 3, 8, 4, 6, 2, 6, 4, 3, 3]
fig, ax = plt.subplots(figsize=(3.5, 2.6))
ax.plot(range(len(values)), values, "o-")
ax.set_xlabel("Index"); ax.set_ylabel("Value (a.u.)")
fig.savefig("case-07.png", dpi=300)
fig.savefig("case-07.pdf")
