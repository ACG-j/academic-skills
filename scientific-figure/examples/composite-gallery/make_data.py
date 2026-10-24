# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pandas"]
# ///
"""Shared synthetic data for the composite-gallery figures."""
import numpy as np, pandas as pd
from pathlib import Path

OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(7)

# --- figB: 15 indicators with block structure (N/P/D groups) ---
names = [f"N{i}" for i in range(1,6)] + [f"P{i}" for i in range(1,7)] + [f"D{i}" for i in range(1,6)]
k = len(names)
base = rng.normal(size=(400, k))
# inject correlation inside blocks so the heatmap is not noise
for start, end, rho in ((0,5,0.45), (5,11,0.52), (11,15,0.30)):
    f = rng.normal(size=(400,1))
    base[:, start:end] = rho*f + (1-rho)*base[:, start:end]
df = pd.DataFrame(base, columns=names)
df.to_csv(OUT / "indicators.csv", index=False)

# --- figD: regression predictions from 4 models ---
n = 220
measured = rng.uniform(5, 90, n)
rows = []
for model, bias, noise in (("RF", 0.0, 3.4), ("AdaBoost", 1.2, 3.4), ("GBRT", -0.5, 3.2), ("XGBoost", 0.8, 3.3)):
    pred = measured + bias + rng.normal(0, noise, n)
    for m, p in zip(measured, pred):
        rows.append({"model": model, "measured": m, "predicted": p, "split": rng.choice(["train","test"], p=[0.7,0.3])})
pd.DataFrame(rows).to_csv(OUT / "regression.csv", index=False)

# --- figA: SHAP-like feature effects ---
m = 600
feats = ["Wind_Speed","Slope","Soil_Moisture","Precipitation","NDVI_GIMMS3G","Aspect"]
shap = pd.DataFrame({f: rng.normal(0, 0.5, m) for f in feats})
fv = pd.DataFrame({f: rng.uniform(-3, 3, m) for f in feats})
shap.to_csv(OUT / "shap_values.csv", index=False)
fv.to_csv(OUT / "feature_values.csv", index=False)

# --- figC: trait correlations for the network/bubble panels ---
traits = ["G_vmax","V_cmax","WUE_i","Leaf_N","Chl","SLA","Stomatal_density","Pore_length"]
tc = rng.normal(size=(300, len(traits)))
tc[:, 0] = 0.7*tc[:, 1] + 0.5*rng.normal(size=300)
tc[:, 2] = -0.5*tc[:, 1] + 0.6*rng.normal(size=300)
pd.DataFrame(tc, columns=traits).to_csv(OUT / "traits.csv", index=False)


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
sites = ["CB", "DL", "DH", "XSBN"]
traits = ["G_vmax", "V_cmax", "WUE_i", "Leaf_N", "Chl", "SLA", "Stomatal_density", "Pore_length"]
rows = []
for site, offset in zip(sites, (-0.6, -0.1, 0.4, 1.1)):
    m = 90
    T = rng.normal(size=(m, len(traits)))
    # the network the figure should show: G-V strongly +, WUE- against both,
    # leaf economy traits (N, Chl, SLA) positively coupled
    T[:, 0] = 0.80 * T[:, 1] + 0.5 * rng.normal(size=m)
    T[:, 2] = -0.62 * T[:, 1] + 0.6 * rng.normal(size=m)
    T[:, 4] = 0.70 * T[:, 3] + 0.5 * rng.normal(size=m)
    T[:, 5] = 0.55 * T[:, 4] + 0.6 * rng.normal(size=m)
    T[:, 7] = 0.40 * T[:, 6] + 0.7 * rng.normal(size=m)
    T[:, 0] += offset
    for row in T:
        rec = {"Site": site, "Leaf_type": rng.choice(["Deciduous", "Evergreen"], p=[0.6, 0.4])}
        rec.update({t: v for t, v in zip(traits, row)})
        rows.append(rec)
pd.DataFrame(rows).to_csv(OUT / "traits.csv", index=False)

print("data written to", OUT)
