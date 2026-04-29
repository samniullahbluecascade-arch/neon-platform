"""
v8_ml_train.py  —  Train ML correction model on extracted pipeline features.

INPUT:  features.json   (produced by v8_feature_extract.py)
OUTPUT: v8_model.pkl    (sklearn Pipeline: scaler + regressor)
        v8_model_meta.json  (feature list, LOO CV stats)

MODEL DESIGN
-----------
Predicts gt_m directly from a small, interpretable feature set.
With ~70-80 samples, we use:
  - Ridge regression      (L2, handles collinear DFS/DTW)
  - Gradient Boosting     (handles nonlinear blend ratios)
  - Random Forest         (robust to outliers)

Evaluated with Leave-One-Out cross-validation → unbiased estimate
on a small dataset. Best model saved to v8_model.pkl.

FEATURES USED (7):
  dfs_m          — DFS measurement (primary predictor)
  dtw_m          — DT-weighted measurement (secondary)
  mean_dt_ratio  — topology signal: > 1.2 = merged parallel strokes
  white_pct      — sign density (dense = more merging)
  tube_mm        — tube width (thick tubes = DFS more reliable)
  sign_width_in  — sign scale
  confidence     — ridge extraction quality

Usage:
    cd F:\\python_files\\Version_8_beta
    python v8_ml_train.py
"""

import sys
import json
import pickle
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

FEATURES_JSON = Path(r"F:\python_files\Version_8_beta\features.json")
MODEL_PKL     = Path(r"F:\python_files\Version_8_beta\v8_model.pkl")
META_JSON     = Path(r"F:\python_files\Version_8_beta\v8_model_meta.json")

FEATURE_COLS = [
    "dfs_m",          # DFS measurement  (primary signal)
    "dtw_m",          # DT-weighted      (secondary signal)
    "mean_dt_ratio",  # topology: merged strokes inflate DT
    "white_pct",      # sign density
    "tube_mm",        # tube width
    "sign_width_in",  # scale
    "confidence",     # fit quality
]

# DT-only features: usable WITHOUT running DFS (~0.5s vs 20-140s)
DT_ONLY_COLS = [
    "dtw_m",
    "mean_dt_ratio",
    "white_pct",
    "tube_mm",
    "sign_width_in",
]

# ── Load data ─────────────────────────────────────────────────────────────────

with open(FEATURES_JSON) as f:
    raw = json.load(f)

# Filter: physics-valid rows only (bad-ppi images can't be corrected by ML)
# Also filter: dfs_m > 0 and dtw_m > 0 (pipeline must have produced valid output)
rows = [
    r for r in raw
    if r["physics_ok"]
    and r["dfs_m"] > 0.01
    and r["dtw_m"] > 0.01
    and r["gt_m"] and r["gt_m"] > 0
    and r["err_pct"] is not None
    and abs(r["err_pct"]) < 60   # exclude extreme outliers that poison training
]

print(f"Loaded {len(raw)} total rows, {len(rows)} valid for training")
print(f"(excluded {len(raw)-len(rows)} rows: phys-fail / zero-DFS / extreme error)")

if len(rows) < 10:
    print("ERROR: need at least 10 valid rows. Run v8_feature_extract.py first.")
    sys.exit(1)

# Build X, y
X = np.array([[r[c] for c in FEATURE_COLS] for r in rows], dtype=np.float64)
y = np.array([r["gt_m"] for r in rows], dtype=np.float64)
names = [r["file"] for r in rows]
n = len(rows)

print(f"\nFeatures: {FEATURE_COLS}")
print(f"X shape: {X.shape}   y shape: {y.shape}")
print(f"GT range: {y.min():.2f} – {y.max():.2f} m\n")

# ── Helpers ───────────────────────────────────────────────────────────────────

def tier_name(e_pct):
    a = abs(e_pct)
    if a <=  5: return "GLASS_CUT"
    if a <= 10: return "QUOTE    "
    if a <= 20: return "ESTIMATE "
    if a <= 35: return "MARGINAL "
    return "FAIL     "

def print_stats(label, errs_pct):
    errs = [abs(e) for e in errs_pct]
    print(f"\n  {label}  (n={len(errs)}):")
    print(f"    mean={np.mean(errs):.2f}%  median={np.median(errs):.2f}%  max={np.max(errs):.2f}%")
    for thresh, tname in [(5,"GLASS_CUT"),(10,"QUOTE"),(20,"ESTIMATE"),(35,"MARGINAL")]:
        cnt = sum(1 for e in errs if e <= thresh)
        bar = "#" * (cnt * 2)
        print(f"    {tname:<10} (<={thresh:2d}%): {cnt:>2}/{len(errs)} = {100*cnt/len(errs):5.1f}%  {bar}")

# ── Baseline: DFS-only ────────────────────────────────────────────────────────

dfs_errs = [(r["dfs_m"] - r["gt_m"]) / r["gt_m"] * 100 for r in rows]
blend_errs = [(r["measured_m"] - r["gt_m"]) / r["gt_m"] * 100 for r in rows]
print_stats("BASELINE — DFS-only", dfs_errs)
print_stats("CURRENT  — DT-blend", blend_errs)

# ── LOO Cross-validation ──────────────────────────────────────────────────────

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline as SKPipeline
    from sklearn.linear_model import Ridge, Lasso, ElasticNet
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.model_selection import LeaveOneOut, cross_val_predict
    from sklearn.metrics import mean_absolute_error
except ImportError:
    print("\nERROR: scikit-learn not installed. Run: pip install scikit-learn")
    sys.exit(1)

loo = LeaveOneOut()

models = {
    "Ridge(a=1)":   SKPipeline([("sc", StandardScaler()), ("m", Ridge(alpha=1.0))]),
    "Ridge(a=0.1)": SKPipeline([("sc", StandardScaler()), ("m", Ridge(alpha=0.1))]),
    "Ridge(a=10)":  SKPipeline([("sc", StandardScaler()), ("m", Ridge(alpha=10.0))]),
    "ElasticNet":   SKPipeline([("sc", StandardScaler()), ("m", ElasticNet(alpha=0.1, l1_ratio=0.5, max_iter=2000))]),
    "GBR(d1,n50)":  SKPipeline([("sc", StandardScaler()), ("m", GradientBoostingRegressor(n_estimators=50,  max_depth=1, learning_rate=0.1, random_state=42))]),
    "GBR(d2,n50)":  SKPipeline([("sc", StandardScaler()), ("m", GradientBoostingRegressor(n_estimators=50,  max_depth=2, learning_rate=0.1, random_state=42))]),
    "RF(n50)":      SKPipeline([("sc", StandardScaler()), ("m", RandomForestRegressor(n_estimators=50, max_depth=4, random_state=42))]),
}

print(f"\n\n=== LOO CROSS-VALIDATION (n={n}) ===\n")
print(f"{'MODEL':<18} {'mean%':>7} {'med%':>7} {'max%':>7}  {'GC':>4} {'Q':>4} {'E':>4} {'M':>4}")
print("-" * 70)

best_name  = None
best_med   = 1e9
best_preds = None

results = {}
for mname, model in models.items():
    preds = cross_val_predict(model, X, y, cv=loo)
    errs  = [(p - g) / g * 100 for p, g in zip(preds, y)]
    aerrs = [abs(e) for e in errs]
    gc = sum(1 for e in aerrs if e <=  5)
    q  = sum(1 for e in aerrs if e <= 10)
    es = sum(1 for e in aerrs if e <= 20)
    mg = sum(1 for e in aerrs if e <= 35)
    med = np.median(aerrs)
    print(f"  {mname:<16} {np.mean(aerrs):>7.2f} {med:>7.2f} {np.max(aerrs):>7.2f}"
          f"  {gc:>4} {q:>4} {es:>4} {mg:>4}")
    results[mname] = {"mean": float(np.mean(aerrs)), "median": float(med),
                      "max": float(np.max(aerrs)), "gc": gc, "q": q, "e": es, "m": mg,
                      "preds": list(preds), "errs": errs}
    if med < best_med:
        best_med   = med
        best_name  = mname
        best_preds = preds

print(f"\n  Best (median): {best_name}")

# Show detailed LOO predictions for best model
print(f"\n=== BEST MODEL: {best_name} — per-image LOO predictions ===")
print(f"{'FILE':<26} {'GT':>5}  {'DFS':>6}  {'ML':>6}  {'ERR-DFS':>9}  {'ERR-ML':>9}  VERDICT")
print("-" * 85)

errs_ml = results[best_name]["errs"]
better = worse = same = 0
for i, r in enumerate(rows):
    p       = best_preds[i]
    e_dfs   = dfs_errs[i]
    e_ml    = errs_ml[i]
    verdict = "BETTER" if abs(e_ml) < abs(e_dfs) - 0.5 else ("WORSE" if abs(e_ml) > abs(e_dfs) + 0.5 else "same")
    if verdict == "BETTER": better += 1
    elif verdict == "WORSE": worse += 1
    else: same += 1
    print(f"{r['file']:<26} {r['gt_m']:>5.2f}  {r['dfs_m']:>6.3f}  {p:>6.3f}  "
          f"{e_dfs:>+8.1f}%  {e_ml:>+8.1f}%  {verdict}")

print(f"\n  Better: {better}/{n}  Worse: {worse}/{n}  Same: {same}/{n}")
print_stats(f"ML ({best_name}) LOO", errs_ml)

# ── Train final model on all data & save ──────────────────────────────────────

final_model = models[best_name]
final_model.fit(X, y)

with open(MODEL_PKL, "wb") as f:
    pickle.dump({"model": final_model, "features": FEATURE_COLS}, f)

meta_out = {
    "best_model": best_name,
    "features": FEATURE_COLS,
    "n_train": n,
    "loo_stats": results[best_name],
    "baseline_dfs": {
        "mean": float(np.mean([abs(e) for e in dfs_errs])),
        "median": float(np.median([abs(e) for e in dfs_errs])),
    },
}
with open(META_JSON, "w") as f:
    json.dump(meta_out, f, indent=2)

print(f"\nFull model saved: {MODEL_PKL}")
print(f"Meta saved:       {META_JSON}")

# ── DT-only fast model (no DFS at inference) ──────────────────────────────────

X_dt = np.array([[r[c] for c in DT_ONLY_COLS] for r in rows], dtype=np.float64)
print(f"\n\n=== DT-ONLY FAST MODEL (no DFS needed) features={DT_ONLY_COLS} ===\n")
print(f"{'MODEL':<18} {'mean%':>7} {'med%':>7} {'max%':>7}  {'GC':>4} {'Q':>4} {'E':>4}")
print("-" * 60)

best_dt_name  = None
best_dt_med   = 1e9
best_dt_preds = None

for mname, model in models.items():
    preds = cross_val_predict(model, X_dt, y, cv=loo)
    errs  = [(p - g) / g * 100 for p, g in zip(preds, y)]
    aerrs = [abs(e) for e in errs]
    gc = sum(1 for e in aerrs if e <=  5)
    q  = sum(1 for e in aerrs if e <= 10)
    es = sum(1 for e in aerrs if e <= 20)
    med = np.median(aerrs)
    print(f"  {mname:<16} {np.mean(aerrs):>7.2f} {med:>7.2f} {np.max(aerrs):>7.2f}  {gc:>4} {q:>4} {es:>4}")
    if med < best_dt_med:
        best_dt_med   = med
        best_dt_name  = mname
        best_dt_preds = preds

print(f"\n  Best DT-only (median): {best_dt_name}")
print_stats(f"DT-only best ({best_dt_name}) LOO", [(p-g)/g*100 for p,g in zip(best_dt_preds, y)])

# Save DT-only model
MODEL_DT_PKL = Path(r"F:\python_files\Version_8_beta\v8_model_dt_fast.pkl")
final_dt = models[best_dt_name]
final_dt.fit(X_dt, y)
with open(MODEL_DT_PKL, "wb") as f:
    pickle.dump({"model": final_dt, "features": DT_ONLY_COLS}, f)
print(f"\nDT-fast model saved: {MODEL_DT_PKL}  (inference time: <0.5s vs 20-140s)")
print(f"\nFeature importances (if GBR/RF):")
try:
    est = final_model.named_steps["m"]
    if hasattr(est, "feature_importances_"):
        for fname, imp in sorted(zip(FEATURE_COLS, est.feature_importances_),
                                 key=lambda x: -x[1]):
            print(f"  {fname:<20} {imp:.4f}")
    elif hasattr(est, "coef_"):
        sc = final_model.named_steps["sc"]
        coefs = est.coef_
        # Unnormalize: effective sensitivity = coef / scale
        for fname, c, s in zip(FEATURE_COLS, coefs, sc.scale_):
            print(f"  {fname:<20} coef={c:+.4f}  (raw sensitivity={c/s:+.4f})")
except Exception as ex:
    print(f"  (could not extract: {ex})")
