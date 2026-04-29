"""
v8_ml_predict.py  —  ML model inference helpers for v8_pipeline.py

Two modes:
  1. FULL model  (v8_model.pkl)         features: dfs_m + dtw_m + image stats
     Use after DFS+DT-blend. Most accurate.

  2. FAST model  (v8_model_dt_fast.pkl) features: dtw_m + image stats only
     Use instead of DFS. ~0.5s vs 20-140s. Slightly less accurate.

Integration: import load_models() at pipeline startup; call predict_full()
or predict_fast() in measure().
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Optional

import numpy as np

_MODEL_DIR = Path(__file__).parent

_FULL_MODEL  = None   # loaded lazily
_FAST_MODEL  = None


def _load_pkl(path: Path):
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def load_models(force: bool = False):
    """Load both models once at startup (or on demand)."""
    global _FULL_MODEL, _FAST_MODEL
    if _FULL_MODEL is None or force:
        _FULL_MODEL = _load_pkl(_MODEL_DIR / "v8_model.pkl")
    if _FAST_MODEL is None or force:
        _FAST_MODEL = _load_pkl(_MODEL_DIR / "v8_model_dt_fast.pkl")


def predict_full(
    dfs_m: float,
    dtw_m: float,
    mean_dt_ratio: float,
    white_pct: float,
    tube_mm: float,
    sign_width_in: float,
    confidence: float,
) -> Optional[float]:
    """
    Full-model prediction using DFS + DT-weighted features.
    Returns predicted gt_m in metres, or None if model unavailable.
    """
    global _FULL_MODEL
    if _FULL_MODEL is None:
        load_models()
    if _FULL_MODEL is None:
        return None
    feats = _FULL_MODEL["features"]
    vals  = {
        "dfs_m": dfs_m, "dtw_m": dtw_m, "mean_dt_ratio": mean_dt_ratio,
        "white_pct": white_pct, "tube_mm": tube_mm,
        "sign_width_in": sign_width_in, "confidence": confidence,
    }
    x = np.array([[vals[f] for f in feats]])
    return float(_FULL_MODEL["model"].predict(x)[0])


def predict_fast(
    dtw_m: float,
    mean_dt_ratio: float,
    white_pct: float,
    tube_mm: float,
    sign_width_in: float,
) -> Optional[float]:
    """
    Fast model: DT-only features (no DFS needed).
    Returns predicted gt_m in metres, or None if model unavailable.
    Use for real-time preview — full DFS can run in background.
    """
    global _FAST_MODEL
    if _FAST_MODEL is None:
        load_models()
    if _FAST_MODEL is None:
        return None
    feats = _FAST_MODEL["features"]
    vals  = {
        "dtw_m": dtw_m, "mean_dt_ratio": mean_dt_ratio,
        "white_pct": white_pct, "tube_mm": tube_mm, "sign_width_in": sign_width_in,
    }
    x = np.array([[vals[f] for f in feats]])
    return float(_FAST_MODEL["model"].predict(x)[0])


if __name__ == "__main__":
    # Quick check: print model info if available
    load_models()
    if _FULL_MODEL:
        print(f"Full model features: {_FULL_MODEL['features']}")
        print(f"Full model type: {type(_FULL_MODEL['model'].named_steps['m']).__name__}")
    else:
        print("Full model not found — run v8_ml_train.py first")
    if _FAST_MODEL:
        print(f"Fast model features: {_FAST_MODEL['features']}")
        print(f"Fast model type: {type(_FAST_MODEL['model'].named_steps['m']).__name__}")
    else:
        print("Fast model not found — run v8_ml_train.py first")
