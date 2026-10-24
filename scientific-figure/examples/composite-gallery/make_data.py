# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pandas"]
# ///
"""Data for the two replications: an 11-variable correlation matrix with a known
significant structure, and 8 traits sampled across 4 sites."""
import numpy as np, pandas as pd
from pathlib import Path
from math import sqrt, erf

OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(11)

# --- 11 variables: Feature_1..Feature_10 + Target_Y -----------------------
n = 11
names = [f"Feature_{i}" for i in range(1, n)] + ["Target_Y"]
k = len(names)
Z = rng.normal(size=(500, k))
# Target_Y (last) driven by Feature_1, Feature_4 and Feature_7 — a realistic pattern
Z[:, 10] += 0.75 * Z[:, 0] + 0.55 * Z[:, 3] + 0.45 * Z[:, 6]
# a correlated block among Features 2-5
f = rng.normal(size=(500, 1))
Z[:, 1:5] = 0.45 * f + (1 - 0.45) * Z[:, 1:5]
pd.DataFrame(Z, columns=names).to_csv(OUT / "corr11.csv", index=False)

# --- 8 traits x 4 sites ---------------------------------------------------
# The reference figure's network spans the whole matrix: G_vmax links not only to its
# neighbours but across to WUE_i, SLA and Pore_length. A data set whose correlations
# sit in two tidy blocks cannot produce that, so the generative model here is a
# hub: G_vmax drives several traits at different strengths, and the leaf-economy
# traits form a second, overlapping cluster.
sites = ["CB", "DL", "DH", "XSBN"]
traits = ["G_vmax", "V_cmax", "WUE_i", "Leaf_N", "Chl", "SLA", "Stomatal_density", "Pore_length"]
rows = []
for site, offset in zip(sites, (-0.7, -0.2, 0.5, 1.2)):
    m = 90
    hub = rng.normal(size=m)                      # G_vmax: the hub
    T = rng.normal(size=(m, len(traits)))          # idiosyncratic part
    # A hub with graded reach: a few strong links, several weak ones. Uniformly strong
    # links make every pair significant, and a network where everything is connected is
    # as unreadable as one where nothing is.
    T[:, 0] = hub
    T[:, 1] = 0.80 * hub + 0.45 * T[:, 1]          # V_cmax   strong +
    T[:, 2] = -0.72 * hub + 0.50 * T[:, 2]         # WUE_i    strong -
    T[:, 5] = 0.55 * hub + 0.70 * T[:, 5]          # SLA      moderate +
    T[:, 7] = 0.30 * hub + 0.90 * T[:, 7]          # Pore_length weak +
    T[:, 6] = 0.22 * hub + 0.95 * T[:, 6]          # Stomatal  weak +
    T[:, 3] = 0.28 * hub + 0.85 * T[:, 3]          # Leaf_N   weak +
    T[:, 4] = 0.18 * hub + 0.90 * T[:, 4]          # Chl      very weak +
    # one strong within-cluster pair, independent of the hub
    T[:, 4] = 0.62 * T[:, 3] + 0.62 * T[:, 4]      # Chl <- Leaf_N
    T[:, 0] += offset
    for row in T:
        rec = {"Site": site, "Leaf_type": rng.choice(["Deciduous", "Evergreen"], p=[0.6, 0.4])}
        rec.update({t: v for t, v in zip(traits, row)})
        rows.append(rec)
pd.DataFrame(rows).to_csv(OUT / "traits.csv", index=False)
print("wrote", OUT)
