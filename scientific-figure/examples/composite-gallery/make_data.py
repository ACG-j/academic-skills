# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pandas"]
# ///
"""Shared synthetic data for the four replication figures."""
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
print("data written to", OUT)
