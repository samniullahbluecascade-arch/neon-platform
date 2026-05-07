"""
apps/pipeline/processor.py
===========================
Production neon tube length measurement pipeline.

KEY INSIGHT (v3 — B&W mode)
────────────────────────────
The input image is ALREADY a clean binary mask:
    white pixels (255)  = neon tube path
    black pixels  (0)   = background

This eliminates ALL segmentation complexity:
  ✗ No background removal needed
  ✗ No colour normalisation needed
  ✗ No reflection suppression needed
  ✗ No per-region adaptive thresholding needed
  ✗ No halo stripping needed

The pipeline is therefore:
    B&W image
       ↓  binary threshold (255 → 1)
    skeletonize()           Zhang-Suen exact thinning
       ↓
    extract_paths()         DFS graph traversal
       ↓
    smooth_savgol()         Savitzky-Golay, window ∝ tube width
       ↓
    classify_segments()     Curvature-based STRAIGHT / ARC / FREEFORM
       ↓
    measure_segments()      Endpoint dist / Pratt r·θ / Bezier+GL
       ↓
    calibrate()             px → inches → metres
       ↓
    apply_memory_factor()   Learned correction
       ↓
    MeasurementResult

This approach achieves dramatically higher skeleton quality because the
input is guaranteed clean — no glow halo, no reflections, no noise.
"""

from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2 as cv
import numpy as np
from scipy.signal import savgol_filter

log = logging.getLogger("apps.pipeline")

# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

KAPPA_STRAIGHT_DEFAULT  = 0.003    # rad/px — below this = straight
KAPPA_PHYS_MAX_DEFAULT  = 0.040    # rad/px — above this = artifact
ARC_UNIFORMITY_THRESH   = 0.35     # std / mean < this → circular arc
PRATT_COND_CEILING      = 1e14     # raised — circles have high condition number
MIN_ARC_ANGLE_RAD       = math.radians(5.0)
MIN_SEGMENT_PX          = 12
SAVGOL_POLY             = 3
SUBSAMPLE_MAX_PTS       = 280


# ─────────────────────────────────────────────────────────────────────────────
#  PART A — BINARY IMAGE LOADER
# ─────────────────────────────────────────────────────────────────────────────

class BWImageLoader:
    """
    Loads and validates a B&W neon mockup image.

    Handles:
    • Any bit-depth (8-bit, 16-bit) → normalised to uint8
    • Any channel count (grayscale, RGB, RGBA) → single-channel
    • Partial anti-aliasing near tube edges → threshold at 127
    • Image orientation metadata (EXIF rotation)
    """

    THRESHOLD = 127   # pixels above this are "tube"

    @classmethod
    def load(cls, path_or_array) -> Tuple[np.ndarray, dict]:
        """
        Load and normalise a B&W neon image.

        Parameters
        ──────────
        path_or_array : str/Path to image file, OR a numpy array already loaded.

        Returns
        ───────
        (binary_mask, meta)
        binary_mask : uint8 ndarray, shape (H,W), values 0 or 255
        meta        : dict with 'height', 'width', 'white_pct', 'tube_width_est_px'
        """
        if isinstance(path_or_array, (str, Path)):
            img = cv.imread(str(path_or_array), cv.IMREAD_UNCHANGED)
            if img is None:
                raise FileNotFoundError(f"Cannot load image: {path_or_array}")
        else:
            img = np.asarray(path_or_array)

        # ── Normalise channels ────────────────────────────────────────────────
        if img.ndim == 2:
            gray = img
        elif img.shape[2] == 4:           # RGBA → use R channel (all channels equal in B&W)
            gray = img[:, :, 0]
        elif img.shape[2] == 3:           # RGB → luminance
            gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        else:
            gray = img[:, :, 0]

        # ── Normalise bit depth ───────────────────────────────────────────────
        if gray.dtype != np.uint8:
            gray = cv.normalize(gray, None, 0, 255, cv.NORM_MINMAX).astype(np.uint8)

        # ── Binary threshold ──────────────────────────────────────────────────
        _, binary = cv.threshold(gray, cls.THRESHOLD, 255, cv.THRESH_BINARY)

        h, w = binary.shape
        white_pct = float(np.mean(binary > 0)) * 100.0

        # Estimate tube width via distance transform of white pixels
        dist       = cv.distanceTransform(binary, cv.DIST_L2, 5)
        vals       = dist[dist > 0]
        tube_w_est = float(np.median(vals) * 2.0) if len(vals) else 8.0

        meta = {
            "height":          h,
            "width":           w,
            "white_pct":       round(white_pct, 3),
            "tube_width_est_px": round(tube_w_est, 2),
        }

        if white_pct < 0.5:
            log.warning("Image has very little white content (%.1f%%) — "
                        "may not be a valid B&W neon mask.", white_pct)
        if white_pct > 60.0:
            log.warning("Image is >60%% white — may not be a clean B&W mask. "
                        "Check that background is pure black.")

        log.info("B&W image loaded: %d×%d  white=%.1f%%  tube_w≈%.1fpx",
                 w, h, white_pct, tube_w_est)
        return binary, meta


# ─────────────────────────────────────────────────────────────────────────────
#  PART B — SKELETONISATION
# ─────────────────────────────────────────────────────────────────────────────

def skeletonize_bw(binary: np.ndarray) -> np.ndarray:
    """
    Zhang-Suen topology-preserving thinning via scikit-image.
    Falls back to iterative morphological erosion if scikit-image is absent.

    Since the input is already a clean binary mask, the skeleton is
    of dramatically higher quality than any glow-based extraction.

    Parameters
    ──────────
    binary : uint8 ndarray (H, W) with values 0 or 255

    Returns
    ───────
    uint8 ndarray (H, W) with values 0 or 255 (single-pixel skeleton)
    """
    try:
        from skimage.morphology import skeletonize as _skel
        result = _skel(binary > 0)
        return result.astype(np.uint8) * 255
    except ImportError:
        log.warning("scikit-image not available; using morphological fallback")

    # Morphological fallback (Guo-Hall approximation)
    prev = np.zeros_like(binary)
    img  = (binary > 0).astype(np.uint8)
    k    = cv.getStructuringElement(cv.MORPH_CROSS, (3, 3))
    while True:
        eroded = cv.erode(img, k)
        temp   = cv.dilate(eroded, k)
        diff   = cv.subtract(img, temp)
        prev   = cv.bitwise_or(prev, diff)
        img    = eroded.copy()
        if cv.countNonZero(img) == 0:
            break
    return prev


# ─────────────────────────────────────────────────────────────────────────────
#  PART C — GRAPH PATH EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

_N8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]


def _pixel_degree(p: tuple, skel_set: set) -> int:
    y, x = p
    return sum(1 for dy, dx in _N8 if (y+dy, x+dx) in skel_set)


def extract_paths(skeleton: np.ndarray,
                  min_length_px: float = 12.0) -> List[np.ndarray]:
    """
    Convert a skeleton image into an ordered list of (x,y) path arrays.

    Algorithm:
    1. Classify every pixel: endpoint (degree=1), junction (≥3), pass-through (=2)
    2. DFS traces from every endpoint through pass-through pixels
    3. Isolated loops (no endpoint) traced greedily from any pixel
    4. Short fragments below min_length_px are discarded

    Returns
    ───────
    List of (N, 2) float arrays, each representing one ordered path of (x, y) coords.
    """
    skel_set: set = set(map(tuple, np.argwhere(skeleton > 0)))
    if not skel_set:
        return []

    endpoints = [p for p in skel_set if _pixel_degree(p, skel_set) == 1]
    junctions = [p for p in skel_set if _pixel_degree(p, skel_set) >= 3]
    node_set  = set(endpoints + junctions)
    visited   : set = set()
    paths     : List[np.ndarray] = []

    def _polyline_len(raw):
        if len(raw) < 2:
            return 0.0
        xy = np.array([[x, y] for y, x in raw], dtype=float)
        return float(np.sum(np.linalg.norm(np.diff(xy, axis=0), axis=1)))

    def trace(start: tuple) -> list:
        path = [start]; visited.add(start); curr = start
        for _ in range(500_000):
            nbrs = [(curr[0]+dy, curr[1]+dx) for dy, dx in _N8
                    if (curr[0]+dy, curr[1]+dx) in skel_set
                    and (curr[0]+dy, curr[1]+dx) not in visited]
            if not nbrs:
                break
            nxt = nbrs[0]; visited.add(nxt); path.append(nxt); curr = nxt
            if curr in node_set:
                break
        return path

    # Traces from endpoints first (most common case for open tube runs)
    for ep in endpoints:
        if ep in visited:
            continue
        raw = trace(ep)
        if _polyline_len(raw) >= min_length_px:
            paths.append(np.array([[x, y] for y, x in raw], dtype=float))

    # Handle remaining pixels (closed loops and disjoint fragments)
    remaining = skel_set - visited
    while remaining:
        start = next(iter(remaining))
        raw   = trace(start)
        remaining -= visited
        if _polyline_len(raw) >= min_length_px:
            paths.append(np.array([[x, y] for y, x in raw], dtype=float))

    log.debug("extract_paths: found %d paths from %d skeleton pixels",
              len(paths), len(skel_set))
    return paths




# ─────────────────────────────────────────────────────────────────────────────
#  PART D — SAVITZKY-GOLAY PATH SMOOTHING
# ─────────────────────────────────────────────────────────────────────────────

def smooth_path_savgol(pts: np.ndarray,
                       window: int = 15,
                       poly:   int = SAVGOL_POLY) -> np.ndarray:
    """
    Savitzky-Golay smoothing along a 2-D path.

    Preserves genuine curvature (S-curves, arcs) while eliminating the
    1-pixel skeleton quantisation jitter that causes Bezier over-splitting
    and phantom length accumulation.

    Endpoints are pinned exactly (edge effect prevention).
    Window is clamped to be odd and ≤ len(pts).
    """
    n = len(pts)
    if n < max(window, 7):
        return pts.copy()
    win = min(window | 1, (n // 2) * 2 - 1)   # odd, ≤ n
    if win < poly + 2:
        return pts.copy()
    sx = savgol_filter(pts[:, 0].astype(float), win, poly)
    sy = savgol_filter(pts[:, 1].astype(float), win, poly)
    sx[0],  sy[0]  = pts[0]
    sx[-1], sy[-1] = pts[-1]
    return np.column_stack([sx, sy])


def subsample_path(pts: np.ndarray, max_pts: int = SUBSAMPLE_MAX_PTS) -> np.ndarray:
    """Uniform re-sampling to cap computation cost without losing shape."""
    n = len(pts)
    if n <= max_pts:
        return pts
    idx = np.round(np.linspace(0, n-1, max_pts)).astype(int)
    return pts[idx]


# ─────────────────────────────────────────────────────────────────────────────
#  PART E — GAUSS-LEGENDRE ARC LENGTH  (machine-precision)
# ─────────────────────────────────────────────────────────────────────────────

class ArcLength:
    """32-point Gauss-Legendre quadrature for cubic Bezier arc length."""
    _N, _W = np.polynomial.legendre.leggauss(32)
    _T     = (_N + 1.0) * 0.5
    _WH    = _W  * 0.5

    @classmethod
    def bezier(cls, P0, P1, P2, P3) -> float:
        P0, P1, P2, P3 = (np.asarray(p, float) for p in (P0, P1, P2, P3))
        t  = cls._T[:, None]; m = 1.0 - t
        dB = 3.0 * (m*m*(P1-P0) + 2.0*t*m*(P2-P1) + t*t*(P3-P2))
        return float(cls._WH @ np.linalg.norm(dB, axis=1))

    @staticmethod
    def polyline(pts: np.ndarray) -> float:
        a = np.asarray(pts, float)
        return float(np.sum(np.linalg.norm(np.diff(a, axis=0), axis=1))) if (
            a.ndim == 2 and len(a) >= 2) else 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  PART F — CUBIC BEZIER FITTING
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BezierSeg:
    P0: np.ndarray; P1: np.ndarray
    P2: np.ndarray; P3: np.ndarray
    length: float = 0.0; max_error: float = 0.0

    def __post_init__(self):
        if self.length == 0.0:
            self.length = ArcLength.bezier(self.P0, self.P1, self.P2, self.P3)

    def at(self, t: float) -> np.ndarray:
        m = 1.0 - t
        return m**3*self.P0 + 3*m**2*t*self.P1 + 3*m*t**2*self.P2 + t**3*self.P3

    def to_svg_cmd(self, first: bool = True) -> str:
        P0, P1, P2, P3 = self.P0, self.P1, self.P2, self.P3
        cmd = f"M {P0[0]:.2f} {P0[1]:.2f} " if first else ""
        return cmd + f"C {P1[0]:.2f} {P1[1]:.2f} {P2[0]:.2f} {P2[1]:.2f} {P3[0]:.2f} {P3[1]:.2f}"


class BezierFitter:
    @staticmethod
    def _chord_params(pts: np.ndarray) -> np.ndarray:
        dists  = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        cumsum = np.concatenate([[0.0], np.cumsum(dists)])
        total  = cumsum[-1]
        return cumsum / total if total > 1e-9 else np.linspace(0, 1, len(pts))

    @classmethod
    def fit_one(cls, pts: np.ndarray) -> BezierSeg:
        pts = np.asarray(pts, float); n = len(pts)
        P0, P3 = pts[0], pts[-1]
        if n == 2:
            d = P3 - P0; return BezierSeg(P0, P0+d/3, P0+2*d/3, P3)
        t  = cls._chord_params(pts); m = 1.0 - t
        b0=m*m*m; b1=3*t*m*m; b2=3*t*t*m; b3=t*t*t
        A   = np.zeros((2*n, 4)); rhs = np.zeros(2*n)
        A[0::2,0]=b1; A[0::2,2]=b2; A[1::2,1]=b1; A[1::2,3]=b2
        rhs[0::2]=pts[:,0]-b0*P0[0]-b3*P3[0]
        rhs[1::2]=pts[:,1]-b0*P0[1]-b3*P3[1]
        sol,_,_,_ = np.linalg.lstsq(A, rhs, rcond=None)
        P1, P2 = sol[[0,1]], sol[[2,3]]
        fitted = np.array([m[i]**3*P0+b1[i]*P1+b2[i]*P2+t[i]**3*P3 for i in range(n)])
        err = float(np.max(np.linalg.norm(fitted-pts, axis=1)))
        return BezierSeg(P0, P1, P2, P3, max_error=err)

    @classmethod
    def fit_adaptive(cls, pts: np.ndarray,
                     max_err: float = 1.5, min_pts: int = 5) -> List[BezierSeg]:
        pts = np.asarray(pts, float)
        if len(pts) < 2: return []
        seg = cls.fit_one(pts)
        if seg.max_error <= max_err or len(pts) <= min_pts:
            return [seg]
        t_params = cls._chord_params(pts)
        errs     = np.linalg.norm(
            np.array([seg.at(ti) for ti in t_params]) - pts, axis=1)
        split    = max(2, min(len(pts)-2, int(np.argmax(errs[1:-1]))+1))
        return (cls.fit_adaptive(pts[:split+1], max_err, min_pts) +
                cls.fit_adaptive(pts[split:],   max_err, min_pts))

    @staticmethod
    def total_length(segs: List[BezierSeg]) -> float:
        return sum(s.length for s in segs)


# ─────────────────────────────────────────────────────────────────────────────
#  PART G — CURVATURE ESTIMATION & SEGMENT CLASSIFICATION
# ─────────────────────────────────────────────────────────────────────────────

class SegmentType(Enum):
    STRAIGHT   = auto()
    ARC        = auto()
    FREEFORM   = auto()
    DEGENERATE = auto()


@dataclass
class PathSegment:
    points:       np.ndarray
    seg_type:     SegmentType
    kappa_mean:   float = 0.0
    kappa_std:    float = 0.0
    physics_valid: bool = True

    @property
    def n_points(self): return len(self.points)
    @property
    def endpoints(self): return self.points[0], self.points[-1]
    @property
    def approx_length(self): return ArcLength.polyline(self.points)


def estimate_curvature(pts: np.ndarray,
                       window: int = 11,
                       resample_ds: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Estimate signed curvature κ(s) along a 2-D path.

    Returns (kappa, resampled_pts) both of length M (uniform arc-length spacing).
    """
    pts = np.asarray(pts, float)
    n   = len(pts)
    if n < 4:
        return np.zeros(n), pts

    # Uniform resampling
    dists  = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cumsum = np.concatenate([[0.0], np.cumsum(dists)])
    total  = cumsum[-1]
    if total < 1e-6:
        return np.zeros(n), pts
    n_new  = max(4, int(total / resample_ds) + 1)
    s_new  = np.linspace(0.0, total, n_new)
    x_new  = np.interp(s_new, cumsum, pts[:,0])
    y_new  = np.interp(s_new, cumsum, pts[:,1])
    rpts   = np.column_stack([x_new, y_new])
    m      = len(rpts)

    # Savitzky-Golay derivatives
    win = min(window | 1, (m//2)*2-1)
    if win < SAVGOL_POLY + 2 or m < win:
        return np.zeros(m), rpts

    Tx  = savgol_filter(rpts[:,0], win, SAVGOL_POLY, deriv=1, delta=resample_ds)
    Ty  = savgol_filter(rpts[:,1], win, SAVGOL_POLY, deriv=1, delta=resample_ds)
    Tx2 = savgol_filter(Tx, win, SAVGOL_POLY, deriv=1, delta=resample_ds)
    Ty2 = savgol_filter(Ty, win, SAVGOL_POLY, deriv=1, delta=resample_ds)

    speed_sq = np.maximum(Tx**2 + Ty**2, 1e-12)
    kappa    = (Tx * Ty2 - Ty * Tx2) / (speed_sq ** 1.5)

    from scipy.ndimage import gaussian_filter1d
    kappa = gaussian_filter1d(kappa, 1.5)
    return kappa, rpts


def classify_path(pts: np.ndarray,
                  tube_width_px: float = 8.0,
                  kappa_straight: float = KAPPA_STRAIGHT_DEFAULT,
                  arc_uniformity: float = ARC_UNIFORMITY_THRESH) -> List[PathSegment]:
    """
    Classify a skeleton path into an ordered list of PathSegments.
    Uses PELT change-point detection on the curvature signal.
    """
    pts = np.asarray(pts, float)
    n   = len(pts)

    if n < MIN_SEGMENT_PX:
        return [PathSegment(pts, SegmentType.DEGENERATE)]

    kappa_phys_max = min(KAPPA_PHYS_MAX_DEFAULT,
                         1.0 / (2.5 * max(1.0, tube_width_px / 2.0)))

    kappa, rpts = estimate_curvature(pts, window=11)
    if len(kappa) < 4:
        return [PathSegment(pts, SegmentType.DEGENERATE)]

    # Simple PELT on |κ|
    changepoints = _pelt_l2(np.abs(kappa), penalty=2.5, min_len=5)

    segments: List[PathSegment] = []
    total_arc = ArcLength.polyline(pts)
    diffs_orig = np.diff(pts, axis=0)
    s_orig     = np.concatenate([[0.0], np.cumsum(np.linalg.norm(diffs_orig, axis=1))])

    prev_cp = 0
    for cp in changepoints:
        seg_kappa = kappa[prev_cp:cp]
        if len(seg_kappa) < 2:
            prev_cp = cp; continue

        # Map curvature slice to original path indices
        frac_s = float(prev_cp) / max(len(kappa)-1, 1)
        frac_e = float(cp-1)    / max(len(kappa)-1, 1)
        s_s    = frac_s * total_arc
        s_e    = frac_e * total_arc
        i_s    = int(np.searchsorted(s_orig, s_s, side="left"))
        i_e    = int(np.searchsorted(s_orig, s_e, side="right"))
        i_s    = max(0, min(i_s, n-1))
        i_e    = max(i_s+1, min(i_e, n))
        seg_pts = pts[i_s:i_e]
        if len(seg_pts) < 2:
            prev_cp = cp; continue

        abs_k = np.abs(seg_kappa)
        km    = float(np.mean(abs_k))
        ks    = float(np.std(seg_kappa))
        k_max = float(abs_k.max()) if len(abs_k) else 0.0
        phys_ok = (k_max <= kappa_phys_max * 1.25)

        if len(seg_kappa) < 3:
            st = SegmentType.DEGENERATE
        elif km < kappa_straight:
            st = SegmentType.STRAIGHT
        elif km >= kappa_straight and (ks / (km + 1e-9)) < arc_uniformity:
            st = SegmentType.ARC
        else:
            st = SegmentType.FREEFORM

        segments.append(PathSegment(seg_pts, st, km, ks, phys_ok))
        prev_cp = cp

    return segments if segments else [PathSegment(pts, SegmentType.FREEFORM, 0, 0, True)]


def _pelt_l2(signal: np.ndarray, penalty: float = 2.5, min_len: int = 5) -> List[int]:
    """Pruned Exact Linear Time change-point detection with L2 cost."""
    n = len(signal)
    if n < 2 * min_len:
        return [n]

    pen = penalty * math.log(n)

    def cost(s, e):
        seg = signal[s:e]
        return float(len(seg) * np.var(seg)) if len(seg) >= 2 else 0.0

    F    = np.full(n+1, np.inf); F[0] = 0.0
    prev = [-1] * (n+1)
    admissible = [0]

    for t in range(min_len, n+1):
        new_adm = []
        best_c, best_s = np.inf, 0
        for s in admissible:
            if t - s < min_len:
                new_adm.append(s); continue
            c = F[s] + cost(s, t) + pen
            if c < best_c:
                best_c, best_s = c, s
            if F[s] + cost(s, t) <= F[t]:
                new_adm.append(s)
        if best_c < F[t]:
            F[t]    = best_c; prev[t] = best_s
        admissible = new_adm if new_adm else [t]

    cps = []
    cp  = n
    while prev[cp] != -1:
        cps.append(cp); cp = prev[cp]
    cps.append(cp); cps.reverse()
    if not cps or cps[-1] != n:
        cps.append(n)
    return cps


# ─────────────────────────────────────────────────────────────────────────────
#  PART H — PRATT CIRCLE FIT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PrattResult:
    cx: float; cy: float; radius: float
    rms_px: float; condition: float
    is_valid: bool; failure_reason: str = ""

    @property
    def centre(self): return np.array([self.cx, self.cy])


def pratt_circle_fit(pts: np.ndarray) -> PrattResult:
    """
    Numerically stable algebraic circle fit (Pratt 1987).
    Iterates singular vectors from smallest upward to handle large arcs.
    """
    pts = np.asarray(pts, float)
    n   = len(pts)
    if n < 3:
        return PrattResult(0,0,0,0,np.inf,False,"n<3")

    cx0, cy0 = pts.mean(axis=0)
    x = pts[:,0]-cx0; y = pts[:,1]-cy0
    r2 = x**2+y**2
    Z  = np.column_stack([r2,x,y,np.ones(n)])

    try:
        _, s_vals, Vt = np.linalg.svd(Z, full_matrices=False)
    except np.linalg.LinAlgError as e:
        return PrattResult(0,0,0,0,np.inf,False,f"SVD error:{e}")

    cond = float(s_vals[0] / max(s_vals[-1], 1e-15))

    # Iterate singular vectors from smallest upward
    A_vec = None
    for k in range(len(s_vals)-1, -1, -1):
        v  = Vt[k]
        ns = v[1]**2 + v[2]**2 - 4.0*v[0]*v[3]
        if ns > 1e-12 and abs(v[0]) > 1e-15:
            A_vec = v; break

    if A_vec is None:
        return PrattResult(cx0,cy0,np.inf,0,cond,False,"no valid SV")

    A, B, C, D = A_vec
    norm_sq = B**2+C**2-4.0*A*D
    if norm_sq <= 0 or abs(A) < 1e-15:
        return PrattResult(cx0,cy0,0,0,cond,False,f"degenerate ns={norm_sq:.2e}")

    sc = 1.0 / math.sqrt(norm_sq)
    A*=sc; B*=sc; C*=sc; D*=sc

    fit_cx = -B/(2.0*A)+cx0
    fit_cy = -C/(2.0*A)+cy0
    radius = math.sqrt(abs((B**2+C**2-4.0*A*D)/(4.0*A**2)))
    if radius < 1e-6:
        return PrattResult(fit_cx,fit_cy,0,0,cond,False,"r≈0")

    dist      = np.linalg.norm(pts - np.array([fit_cx,fit_cy]), axis=1)
    residuals = dist - radius
    rms       = float(math.sqrt(np.mean(residuals**2)))

    return PrattResult(fit_cx, fit_cy, radius, rms, cond, True)


# ─────────────────────────────────────────────────────────────────────────────
#  PART I — THREE-REGIME SEGMENT MEASURER
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SegmentResult:
    seg_type:      SegmentType
    length_px:     float
    method:        str       # endpoint_dist | pratt_arc | bezier_gl | polyline
    quality:       float     # 0-1
    physics_valid: bool
    diagnostics:   dict = field(default_factory=dict)


def measure_segment(seg: PathSegment, max_pratt_rms: float = 2.5) -> SegmentResult:
    """
    Dispatch one PathSegment to the correct length formula:
      STRAIGHT  → Euclidean endpoint distance (exact for straight glass)
      ARC       → Pratt circle fit → r × θ (exact for circular bends)
      FREEFORM  → Bezier + Gauss-Legendre (for organic script curves)
      DEGENERATE→ Polyline fallback
    """
    pts = seg.points

    if seg.seg_type == SegmentType.DEGENERATE or seg.n_points < 2:
        return SegmentResult(
            SegmentType.DEGENERATE, seg.approx_length, "polyline", 0.3,
            seg.physics_valid, {"n": seg.n_points})

    # ── STRAIGHT ─────────────────────────────────────────────────────────────
    if seg.seg_type == SegmentType.STRAIGHT:
        P0, P1 = seg.endpoints
        length = float(np.linalg.norm(P1 - P0))
        # Perpendicular deviation → quality estimate
        if seg.n_points > 4:
            v = P1 - P0; vn = np.linalg.norm(v)
            if vn > 1e-9:
                n_unit = np.array([-v[1]/vn, v[0]/vn])
                devs   = np.abs((pts - P0) @ n_unit)
                quality = max(0.7, 1.0 - float(devs.max()) / max(length, 1.0) * 10.0)
            else:
                quality = 0.8
        else:
            quality = 0.85
        return SegmentResult(
            SegmentType.STRAIGHT, length, "endpoint_dist", quality,
            seg.physics_valid, {"P0": P0.tolist(), "P1": P1.tolist(),
                                 "kappa_mean": seg.kappa_mean})

    # ── ARC ───────────────────────────────────────────────────────────────────
    if seg.seg_type == SegmentType.ARC:
        pr = pratt_circle_fit(pts)
        if not pr.is_valid:
            chord = float(np.linalg.norm(pts[-1] - pts[0]))
            return SegmentResult(
                SegmentType.ARC, chord, "pratt_fallback_chord", 0.7,
                seg.physics_valid, {"reason": pr.failure_reason})

        if pr.rms_px > max_pratt_rms:
            poly = ArcLength.polyline(pts)
            return SegmentResult(
                SegmentType.ARC, poly, "pratt_fallback_poly", 0.55,
                seg.physics_valid, {"pratt_rms": pr.rms_px})

        # Compute angular span
        vecs   = pts - pr.centre
        angles = np.arctan2(vecs[:,1], vecs[:,0])
        angles_uw = np.unwrap(angles)
        span   = float(abs(angles_uw[-1] - angles_uw[0]))
        span   = min(span, 2*math.pi)

        if span < MIN_ARC_ANGLE_RAD:
            chord = float(np.linalg.norm(pts[-1] - pts[0]))
            return SegmentResult(
                SegmentType.ARC, chord, "pratt_near_straight", 0.80,
                seg.physics_valid, {"angle_deg": math.degrees(span)})

        arc_len = pr.radius * span
        quality = max(0.5, 1.0 - pr.rms_px / 5.0)
        return SegmentResult(
            SegmentType.ARC, arc_len, "pratt_arc", quality, seg.physics_valid,
            {"radius_px": pr.radius, "angle_deg": round(math.degrees(span),2),
             "rms_px": round(pr.rms_px, 4), "centre": pr.centre.tolist()})

    # ── FREEFORM ──────────────────────────────────────────────────────────────
    smoothed = smooth_path_savgol(pts, window=15, poly=SAVGOL_POLY)
    sampled  = subsample_path(smoothed, SUBSAMPLE_MAX_PTS)
    segs     = BezierFitter.fit_adaptive(sampled, max_err=1.5)

    if not segs:
        return SegmentResult(
            SegmentType.FREEFORM, ArcLength.polyline(pts), "polyline", 0.45,
            seg.physics_valid, {"n_bezier_segs": 0})

    total_len = BezierFitter.total_length(segs)
    avg_err   = float(np.mean([s.max_error for s in segs]))
    quality   = max(0.0, 1.0 - avg_err / 8.0)
    return SegmentResult(
        SegmentType.FREEFORM, total_len, "bezier_gl", quality, seg.physics_valid,
        {"n_bezier_segs": len(segs), "avg_err_px": round(avg_err, 4)})


def measure_path(pts: np.ndarray,
                 tube_width_px: float = 8.0,
                 curve_factor:  float = 1.05) -> Tuple[float, List[SegmentResult], float]:
    """
    Classify and measure one complete skeleton path.

    Returns
    ───────
    (total_length_px, segment_results, avg_quality)
    curve_factor is applied ONLY to FREEFORM segments (straight/arc are exact).
    """
    pts = np.asarray(pts, float)
    if len(pts) < 2:
        return 0.0, [], 0.0

    # Smooth first
    savgol_win = max(15, int(tube_width_px * 2.0) | 1)
    pts        = smooth_path_savgol(pts, window=savgol_win)
    pts        = subsample_path(pts, SUBSAMPLE_MAX_PTS)

    segments   = classify_path(pts, tube_width_px)
    results    = [measure_segment(s) for s in segments]

    total = 0.0
    for r in results:
        if r.seg_type == SegmentType.FREEFORM:
            total += r.length_px * curve_factor
        else:
            total += r.length_px

    quality = float(np.mean([r.quality for r in results])) if results else 0.0
    return total, results, quality


# ─────────────────────────────────────────────────────────────────────────────
#  PART J — CALIBRATION
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Calibration:
    """
    Pixel ↔ real-world unit conversion.
    Supports 2-point ruler and 4-corner homography modes.
    """
    px_per_inch:  float
    mode:         str   = "2point"   # "2point" | "4corner"
    H:            Optional[np.ndarray] = field(default=None, repr=False)
    H_inv:        Optional[np.ndarray] = field(default=None, repr=False)
    rect_w:       int   = 0
    rect_h:       int   = 0

    def to_meters(self, px: float) -> float:
        return (px / self.px_per_inch) * 0.0254 if self.px_per_inch > 0 else 0.0

    def to_inches(self, px: float) -> float:
        return px / self.px_per_inch if self.px_per_inch > 0 else 0.0

    @property
    def mm_per_px(self) -> float:
        return (1.0 / self.px_per_inch) * 25.4 if self.px_per_inch > 0 else 0.0

    def resolution_str(self) -> str:
        return (f"{self.mode}  {self.px_per_inch:.2f} px/in "
                f"({self.mm_per_px:.2f} mm/px)")


def calibrate_2point(p1: Tuple[int,int], p2: Tuple[int,int],
                     real_inches: float) -> Calibration:
    d = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
    if d <= 0 or real_inches <= 0:
        raise ValueError("Calibration points must be distinct and real_inches > 0")
    return Calibration(px_per_inch=d/real_inches, mode="2point")


def calibrate_4corner(tl, tr, br, bl,
                      real_w_inch: float, real_h_inch: float,
                      dpi_hint: float = 72.0) -> Calibration:
    src = np.array([tl,tr,br,bl], dtype=np.float32)
    rect_w = int(round(real_w_inch * dpi_hint))
    rect_h = int(round(real_h_inch * dpi_hint))
    dst = np.array([[0,0],[rect_w,0],[rect_w,rect_h],[0,rect_h]], dtype=np.float32)
    H,   _ = cv.findHomography(src, dst)
    H_inv,_ = cv.findHomography(dst, src)
    return Calibration(
        px_per_inch=dpi_hint, mode="4corner",
        H=H, H_inv=H_inv, rect_w=rect_w, rect_h=rect_h)


# ─────────────────────────────────────────────────────────────────────────────
#  PART K — FULL MEASUREMENT RESULT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TubePathResult:
    """Per-tube measurement result."""
    index:           int
    length_px:       float
    length_m:        float
    fit_quality:     float
    is_loop:         bool
    is_missed_patch: bool
    physics_valid:   bool
    dominant_regime: str
    n_straight:      int
    n_arc:           int
    n_freeform:      int
    bezier_segs:     List[BezierSeg]
    points_downsampled: List[List[float]]   # for SVG overlay
    segment_details: List[dict]


@dataclass
class MeasurementResult:
    """Complete pipeline output."""
    total_length_px:   float
    total_length_m:    float
    raw_length_m:      float
    memory_correction: float
    tube_mode:         str
    mode_mult:         float
    curve_factor:      float

    tubes:             List[TubePathResult]
    n_tubes:           int
    n_missed:          int
    n_loops:           int

    calibration:       Calibration
    avg_quality:       float
    skeleton_px:       int
    white_pct:         float
    tube_width_px:     float

    topology_warnings: List[str]
    accuracy_pct:      Optional[float]
    gap_from_target_m: Optional[float]

    processing_time_s: float
    image_w:           int
    image_h:           int

    # SVG overlay data
    overlay_svg_paths: List[dict]   # [{id, d, color, length_m, is_missed}]

    def to_dict(self) -> dict:
        return {
            "total_m":          round(self.total_length_m, 4),
            "raw_m":            round(self.raw_length_m, 4),
            "correction":       round(self.memory_correction, 4),
            "mode":             self.tube_mode,
            "mode_mult":        self.mode_mult,
            "curve_factor":     self.curve_factor,
            "n_tubes":          self.n_tubes,
            "n_missed":         self.n_missed,
            "n_loops":          self.n_loops,
            "avg_quality":      round(self.avg_quality, 3),
            "skeleton_px":      self.skeleton_px,
            "white_pct":        self.white_pct,
            "tube_width_px":    self.tube_width_px,
            "accuracy_pct":     self.accuracy_pct,
            "gap_m":            self.gap_from_target_m,
            "px_per_inch":      round(self.calibration.px_per_inch, 3),
            "mm_per_px":        round(self.calibration.mm_per_px, 4),
            "cal_mode":         self.calibration.mode,
            "topology_warnings":self.topology_warnings,
            "time_s":           round(self.processing_time_s, 2),
            "image_w":          self.image_w,
            "image_h":          self.image_h,
            "tubes": [{
                "id":        t.index,
                "length_m":  round(t.length_m, 4),
                "length_px": round(t.length_px, 1),
                "quality":   round(t.fit_quality, 3),
                "is_loop":   t.is_loop,
                "missed":    t.is_missed_patch,
                "regime":    t.dominant_regime,
                "phys_ok":   t.physics_valid,
            } for t in self.tubes],
        }


# ─────────────────────────────────────────────────────────────────────────────
#  PART L — OVERLAY RENDERER
# ─────────────────────────────────────────────────────────────────────────────

TUBE_COLORS_BGR = [
    (255,80,80), (80,255,80), (80,120,255), (255,230,50),
    (255,80,220),(80,230,230),(255,150,50), (150,80,255),
    (80,255,160),(255,80,150),(120,255,255),(255,200,80),
]
MISSED_COLOR_BGR = (160,160,160)


def render_overlay(binary: np.ndarray,
                   skeleton: np.ndarray,
                   result: MeasurementResult,
                   cal_pts: Optional[Tuple] = None,
                   max_dim: int = 1200) -> np.ndarray:
    """
    Render a dark-background diagnostic overlay image.

    Binary mask → grayscale background → coloured Bezier paths per tube.
    """
    # Dark background from the original B&W image
    gray = (binary > 0).astype(np.uint8) * 40   # dim white tubes as dark grey
    vis  = cv.cvtColor(gray, cv.COLOR_GRAY2BGR)

    # Skeleton in cyan
    ys, xs = np.where(skeleton > 0)
    if len(ys):
        vis[ys, xs] = [0, 200, 200]

    # Bezier paths per tube
    h, w = vis.shape[:2]
    for tube in result.tubes:
        col   = MISSED_COLOR_BGR if tube.is_missed_patch else TUBE_COLORS_BGR[tube.index % len(TUBE_COLORS_BGR)]
        thick = 1 if tube.is_missed_patch else 2
        for seg in tube.bezier_segs:
            pts_b = np.array([seg.at(t) for t in np.linspace(0,1,40)])
            pts_b = pts_b.astype(np.int32)
            pts_b[:,0] = np.clip(pts_b[:,0], 0, w-1)
            pts_b[:,1] = np.clip(pts_b[:,1], 0, h-1)
            for j in range(len(pts_b)-1):
                cv.line(vis, tuple(pts_b[j]), tuple(pts_b[j+1]), col, thick, cv.LINE_AA)
        # Label
        if tube.points_downsampled:
            mid = tube.points_downsampled[len(tube.points_downsampled)//2]
            lbl = f"#{tube.index}" + ("*" if tube.is_missed_patch else "")
            cv.putText(vis, lbl, (int(mid[0]), int(mid[1])),
                       cv.FONT_HERSHEY_SIMPLEX, 0.38, col, 1, cv.LINE_AA)

    # Calibration ruler
    if cal_pts and len(cal_pts) >= 2:
        p1, p2 = tuple(cal_pts[0]), tuple(cal_pts[1])
        cv.line(vis, p1, p2, (0,230,230), 2)
        cv.circle(vis, p1, 7, (0,230,230), -1)
        cv.circle(vis, p2, 7, (0,230,230), -1)
        mx, my = (p1[0]+p2[0])//2, (p1[1]+p2[1])//2-14
        cv.putText(vis, f'{result.calibration.to_inches(result.calibration.px_per_inch * abs(p2[0]-p1[0]) / result.calibration.px_per_inch):.1f}"',
                   (mx, my), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0,230,230), 2, cv.LINE_AA)

    # Scale down for storage
    oh, ow = vis.shape[:2]
    if max(oh, ow) > max_dim:
        scale = max_dim / max(oh, ow)
        vis = cv.resize(vis, (int(ow*scale), int(oh*scale)), interpolation=cv.INTER_AREA)

    return vis


# ─────────────────────────────────────────────────────────────────────────────
#  PART M — MAIN PIPELINE ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(
    image_path_or_array,
    calibration:        Calibration,
    tube_mode:          str   = "center",
    curve_factor:       float = 1.05,
    min_path_px:        float = 12.0,
    target_meters:      Optional[float] = None,
    memory_factor:      float = 1.0,
    progress_callback   = None,
    use_ridge_tracker   = False,
) -> MeasurementResult:
    """
    Full B&W neon measurement pipeline.

    Parameters
    ──────────
    image_path_or_array : str/Path or numpy array (B&W image)
    calibration         : Calibration object (from calibrate_2point or calibrate_4corner)
    tube_mode           : "center" | "outline"
    curve_factor        : applied to FREEFORM segments only (default 1.05)
    min_path_px         : minimum skeleton path length in pixels
    target_meters       : expected total length (for accuracy calculation)
    memory_factor       : learned correction factor (from MemoryRecord.correction_factor)
    progress_callback   : callable(pct: int, stage: str) — optional progress reporting

    Returns
    ───────
    MeasurementResult with all per-tube and aggregate data.
    """
    t0 = time.time()

    def _progress(pct: int, stage: str):
        if progress_callback:
            try:
                progress_callback(pct, stage)
            except Exception:
                pass
        log.debug("[%3d%%] %s", pct, stage)

    # ── Step 1: Load & validate image ─────────────────────────────────────────
    _progress(5, "Loading image")
    binary, img_meta = BWImageLoader.load(image_path_or_array)
    h, w = binary.shape
    tube_w = img_meta["tube_width_est_px"]

    if use_ridge_tracker:
        _progress(25, "Ridge Tracking (Fast Marching)")
        ContinuousRidgeTracker = globals()["ContinuousRidgeTracker"]
        tracker = ContinuousRidgeTracker(binary)
        raw_paths = tracker.extract_paths(min_path_px)
        skel_px = sum(len(p) for p in raw_paths)  # approx
        log.info("Ridge Tracker extracted %d paths", len(raw_paths))
    else:
        # ── Step 2: Skeletonise ───────────────────────────────────────────────────
        _progress(20, "Skeletonising")
        skeleton = skeletonize_bw(binary)
        skel_px  = int(np.sum(skeleton > 0))
        log.info("Skeleton: %d pixels", skel_px)
    
        # ── Step 3: Extract paths ─────────────────────────────────────────────────
        _progress(35, "Extracting paths")
        raw_paths = extract_paths(skeleton, min_path_px)

        # Merge short dangling paths into their nearest longer neighbor
        # Any path < 3× tube_width is a junction artifact, not a real tube run
        min_meaningful_px = max(min_path_px, tube_w * 3.0)
        raw_paths = [p for p in raw_paths if ArcLength.polyline(p) >= min_meaningful_px]

    # ── Step 4: Measure each path ─────────────────────────────────────────────
    _progress(50, "Measuring tube paths")
    mode_mult = 2.0 if tube_mode == "outline" else 1.0
    tube_results: List[TubePathResult] = []
    total_px = 0.0

    for i, raw_pts in enumerate(raw_paths):
        _progress(50 + int(40 * i / max(len(raw_paths), 1)),
                  f"Measuring tube {i+1}/{len(raw_paths)}")

        length_px, seg_results, quality = measure_path(
            raw_pts, tube_w, curve_factor)

        length_m = calibration.to_meters(length_px) * mode_mult
        total_px += length_px

        # Dominant regime
        types = [r.seg_type for r in seg_results]
        from collections import Counter
        if types:
            dom = Counter(types).most_common(1)[0][0]
            dom_str = dom.name.lower()
        else:
            dom_str = "freeform"

        # Closed loop detection: endpoints close together
        is_loop = bool(
            len(raw_pts) > 10 and
            np.linalg.norm(raw_pts[0] - raw_pts[-1]) < tube_w * 2.5
        )

        # Gather Bezier segments from FREEFORM sub-segs for overlay
        all_bezier: List[BezierSeg] = []
        for sr in seg_results:
            if sr.seg_type == SegmentType.FREEFORM and "bezier_segs" in sr.diagnostics:
                pass  # bezier segs are computed per segment — rebuild here
        # Re-run Bezier on smoothed path for overlay rendering
        smooth_pts = smooth_path_savgol(raw_pts, window=max(15, int(tube_w*2)|1))
        sub_pts    = subsample_path(smooth_pts)
        all_bezier = BezierFitter.fit_adaptive(sub_pts, max_err=1.5)

        # Downsample points for JSON storage
        ds_step = max(1, len(sub_pts) // 80)
        pts_ds  = sub_pts[::ds_step].tolist()

        tube_results.append(TubePathResult(
            index           = i + 1,
            length_px       = length_px,
            length_m        = length_m,
            fit_quality     = quality,
            is_loop         = is_loop,
            is_missed_patch = False,
            physics_valid   = all(r.physics_valid for r in seg_results),
            dominant_regime = dom_str,
            n_straight      = sum(1 for r in seg_results if r.seg_type==SegmentType.STRAIGHT),
            n_arc           = sum(1 for r in seg_results if r.seg_type==SegmentType.ARC),
            n_freeform      = sum(1 for r in seg_results if r.seg_type==SegmentType.FREEFORM),
            bezier_segs     = all_bezier,
            points_downsampled=pts_ds,
            segment_details = [
                {"type": r.seg_type.name, "length_px": round(r.length_px,2),
                 "method": r.method, "quality": round(r.quality,3),
                 **r.diagnostics}
                for r in seg_results
            ],
        ))

    # Sort longest first
    tube_results.sort(key=lambda t: t.length_px, reverse=True)
    for i, t in enumerate(tube_results):
        t.index = i + 1

    # ── Step 5: Aggregate ─────────────────────────────────────────────────────
    _progress(92, "Aggregating results")
    raw_total_m = sum(t.length_m for t in tube_results)
    total_m     = raw_total_m * memory_factor

    avg_quality = (float(np.mean([t.fit_quality for t in tube_results]))
                   if tube_results else 0.0)
    n_loops     = sum(1 for t in tube_results if t.is_loop)
    n_missed    = sum(1 for t in tube_results if t.is_missed_patch)

    # Topology warnings
    topo_warns: List[str] = []

    # Accuracy vs target
    accuracy_pct = None
    gap_m        = None
    if target_meters and target_meters > 0:
        gap_m    = total_m - target_meters
        accuracy_pct = max(0.0, 1.0 - abs(gap_m) / target_meters) * 100

    # SVG overlay paths
    TUBE_COLORS_HEX = [
        "#FF5050","#50FF50","#5078FF","#FFE632",
        "#FF50DC","#50E6E6","#FF9632","#9650FF",
        "#50FFA0","#FF50A0","#78FFFF","#FFC850",
    ]
    overlay_svg_paths = []
    for tube in tube_results:
        cmds = []
        for k, seg in enumerate(tube.bezier_segs):
            cmds.append(seg.to_svg_cmd(first=(k==0)))
        color = "#AAAAAA" if tube.is_missed_patch else TUBE_COLORS_HEX[tube.index % len(TUBE_COLORS_HEX)]
        overlay_svg_paths.append({
            "id":       f"tube-{tube.index}",
            "d":        " ".join(cmds),
            "color":    color,
            "length_m": round(tube.length_m, 4),
            "missed":   tube.is_missed_patch,
            "loop":     tube.is_loop,
        })

    elapsed = time.time() - t0
    _progress(100, "Done")

    return MeasurementResult(
        total_length_px   = total_px,
        total_length_m    = total_m,
        raw_length_m      = raw_total_m,
        memory_correction = memory_factor,
        tube_mode         = tube_mode,
        mode_mult         = mode_mult,
        curve_factor      = curve_factor,
        tubes             = tube_results,
        n_tubes           = len(tube_results),
        n_missed          = n_missed,
        n_loops           = n_loops,
        calibration       = calibration,
        avg_quality       = avg_quality,
        skeleton_px       = skel_px,
        white_pct         = img_meta["white_pct"],
        tube_width_px     = tube_w,
        topology_warnings = topo_warns,
        accuracy_pct      = round(accuracy_pct, 2) if accuracy_pct is not None else None,
        gap_from_target_m = round(gap_m, 4) if gap_m is not None else None,
        processing_time_s = elapsed,
        image_w           = w,
        image_h           = h,
        overlay_svg_paths = overlay_svg_paths,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  LOCAL RIDGE TRACKER (embedded from ridge_tracker.py)
# ─────────────────────────────────────────────────────────────────────────────

import numpy as np
import cv2 as cv
import math

class ContinuousRidgeTracker:
    """
    Traces the centerlines of neon tubes by following the crests of the 
    Distance Transform topography, using the Hessian matrix to determine
    continuous flow direction, inherently ignoring edge spurs.
    """
    def __init__(self, binary_mask: np.ndarray):
        self.binary = binary_mask
        
        # 1. Compute Distance Transform (topography)
        self.dist = cv.distanceTransform(self.binary, cv.DIST_L2, 5)
        
        # 2. Smooth topography to eliminate jagged edge noise (spur prevention)
        self.smooth_dist = cv.GaussianBlur(self.dist, (15, 15), 4.0)
        
        # 3. Compute Hessian Matrix components
        self.dy, self.dx = np.gradient(self.smooth_dist)
        self.dyy, self.dyx = np.gradient(self.dy)
        self.dxy, self.dxx = np.gradient(self.dx)
        
        # 4. Find eigenvalues and eigenvectors for all pixels
        # For a max-ridge, we want the most negative eigenvalue.
        # Its eigenvector points across the ridge. The other eigenvector points ALONG the ridge.
        # We pre-calculate the ridge direction for every pixel.
        self.ridge_directions = np.zeros((*self.binary.shape, 2), dtype=float)
        self.ridge_strength = np.zeros(self.binary.shape, dtype=float)
        
        self._compute_hessian_fields()

    def _compute_hessian_fields(self):
        # We can vectorize this or do it across the mask
        mask = self.binary > 0
        
        # Flatten masked elements
        dxx = self.dxx[mask]
        dyy = self.dyy[mask]
        dxy = self.dxy[mask]
        
        # Trace and determinant
        trace = dxx + dyy
        # Descriminant calculation
        disc = np.sqrt(np.maximum((dxx - dyy)**2 + 4 * dxy**2, 0))
        
        # Eigenvalues
        # e1 is the larger (less negative), e2 is the smaller (more negative)
        e2 = (trace - disc) / 2.0
        
        # The eigenvector for e1 (which points ALONG the ridge)
        # If e1 is for (trace + disc)/2, the matrix is [dxx - e1, dxy]
        # Eigenvector is [-dxy, dxx - e1]
        e1 = (trace + disc) / 2.0
        vec_x = -dxy
        vec_y = dxx - e1
        
        # Normalize
        norm = np.sqrt(vec_x**2 + vec_y**2) + 1e-12
        vec_x /= norm
        vec_y /= norm
        
        # Set ridge strength as magnitude of e2 (how sharp the ridge is)
        # We only care where e2 is negative (it's a ridge, not a valley)
        r_str = np.zeros_like(e2)
        r_str[e2 < 0] = np.abs(e2[e2 < 0])
        
        self.ridge_strength[mask] = r_str
        self.ridge_directions[mask, 0] = vec_x
        self.ridge_directions[mask, 1] = vec_y

    def extract_paths(self, min_path_px: float = 12.0) -> list[np.ndarray]:
        """
        Extract paths by seeding at high ridge-strength pixels and marching
        along the principal continuous direction until the edge.
        """
        visited = np.zeros_like(self.binary, dtype=bool)
        visited_mask_8u = np.zeros_like(self.binary, dtype=np.uint8)
        paths = []
        
        # Sort seeds by ridge strength (start at the most obvious centers)
        y_coords, x_coords = np.nonzero(self.ridge_strength > 0.05)
        strengths = self.ridge_strength[y_coords, x_coords]
        
        # Sort descending
        sort_idx = np.argsort(strengths)[::-1]
        seeds = [(x_coords[i], y_coords[i]) for i in sort_idx]
        
        step_sz = 1.0
        
        for sx, sy in seeds:
            if visited[sy, sx]:
                continue
                
            # Initialize a path marching in both directions from the seed
            path_fwd = []
            path_bwd = []
            
            # March Forward
            cx, cy = float(sx), float(sy)
            for _ in range(5000):
                ix, iy = int(round(cx)), int(round(cy))
                if not (0 <= ix < self.binary.shape[1] and 0 <= iy < self.binary.shape[0]):
                    break
                if self.binary[iy, ix] == 0:
                    break
                
                visited[iy, ix] = True
                path_fwd.append((cx, cy))
                
                # Get direction
                vx = self.ridge_directions[iy, ix, 0]
                vy = self.ridge_directions[iy, ix, 1]
                
                # We need to maintain momentum. If dot product is negative, flip direction.
                if len(path_fwd) > 1:
                    px, py = path_fwd[-2]
                    mdx, mdy = cx - px, cy - py
                    dot = mdx * vx + mdy * vy
                    if dot < 0:
                        vx, vy = -vx, -vy
                
                cx += vx * step_sz
                cy += vy * step_sz
                
            # March Backward
            cx, cy = float(sx), float(sy)
            # Initialize backward direction by flipping initial vector
            ix, iy = int(round(cx)), int(round(cy))
            initial_vx = -self.ridge_directions[iy, ix, 0]
            initial_vy = -self.ridge_directions[iy, ix, 1]
            
            # Step once backward
            cx += initial_vx * step_sz
            cy += initial_vy * step_sz
            
            for _ in range(5000):
                ix, iy = int(round(cx)), int(round(cy))
                if not (0 <= ix < self.binary.shape[1] and 0 <= iy < self.binary.shape[0]):
                    break
                if self.binary[iy, ix] == 0:
                    break
                if visited[iy, ix]:
                    break
                    
                visited[iy, ix] = True
                path_bwd.append((cx, cy))
                
                # Get direction
                vx = self.ridge_directions[iy, ix, 0]
                vy = self.ridge_directions[iy, ix, 1]
                
                px, py = path_bwd[-2] if len(path_bwd) > 1 else (sx, sy)
                mdx, mdy = cx - px, cy - py
                dot = mdx * vx + mdy * vy
                if dot < 0:
                    vx, vy = -vx, -vy
                
                cx += vx * step_sz
                cy += vy * step_sz
                
            full_path = path_bwd[::-1] + path_fwd
            
            if len(full_path) >= min_path_px:
                # Downsample slightly to avoid huge arrays
                full_path = np.array(full_path)
                paths.append(full_path)
                
                # Mark all pixels within the tube radius as visited so we don't get parallel tracks
                # Draw the path on the visited mask with thickness of 6 pixels to suppress nearby seeds
                pts = np.array(full_path, dtype=np.int32).reshape((-1, 1, 2))
                cv.polylines(visited_mask_8u, [pts], isClosed=False, color=1, thickness=5)
                visited = visited_mask_8u > 0
                
        return paths


# ─────────────────────────────────────────────────────────────────────────────
#  VECTOR GRAPH PIPELINE (built on top of the B&W pipeline)
# ─────────────────────────────────────────────────────────────────────────────

import argparse
import csv
import os
import re
import sys
import zipfile
from typing import Iterable


@dataclass
class VectorGraphNode:
    node_id: int
    yx: Tuple[int, int]
    degree: int


@dataclass
class VectorGraphEdge:
    edge_id: int
    start_node_id: Optional[int]
    end_node_id: Optional[int]
    points_px: np.ndarray
    is_loop: bool = False
    bezier_segs_px: List[BezierSeg] = field(default_factory=list)
    length_px: float = 0.0

    def to_svg_path_d(self) -> str:
        if not self.bezier_segs_px:
            return ""
        return " ".join(seg.to_svg_cmd(first=(i == 0)) for i, seg in enumerate(self.bezier_segs_px))


@dataclass
class VectorGraphResult:
    image_w: int
    image_h: int
    tube_width_px: float
    n_nodes: int
    n_edges: int
    total_length_px: float
    total_length_m: float
    calibration: Calibration
    nodes: List[VectorGraphNode]
    edges: List[VectorGraphEdge]

    def to_dict(self) -> Dict:
        return {
            "image_w": self.image_w,
            "image_h": self.image_h,
            "tube_width_px": round(self.tube_width_px, 3),
            "n_nodes": self.n_nodes,
            "n_edges": self.n_edges,
            "total_length_px": round(self.total_length_px, 3),
            "total_length_m": round(self.total_length_m, 6),
            "px_per_inch": round(self.calibration.px_per_inch, 6),
            "mm_per_px": round(self.calibration.mm_per_px, 6),
            "edges": [
                {
                    "edge_id": e.edge_id,
                    "start_node_id": e.start_node_id,
                    "end_node_id": e.end_node_id,
                    "is_loop": e.is_loop,
                    "n_points": int(len(e.points_px)),
                    "n_bezier_segs": int(len(e.bezier_segs_px)),
                    "length_px": round(e.length_px, 3),
                    "length_m": round(self.calibration.to_meters(e.length_px), 6),
                }
                for e in self.edges
            ],
        }


def _vx_nbrs(p: Tuple[int, int], skel_set: Set[Tuple[int, int]]) -> List[Tuple[int, int]]:
    y, x = p
    return [(y + dy, x + dx) for dy, dx in _N8 if (y + dy, x + dx) in skel_set]


def _vx_degree(p: Tuple[int, int], skel_set: Set[Tuple[int, int]]) -> int:
    return len(_vx_nbrs(p, skel_set))


def _vx_step_key(a: Tuple[int, int], b: Tuple[int, int]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    return (a, b) if a <= b else (b, a)


def build_vector_graph(
    skeleton: np.ndarray,
    min_edge_length_px: float = 12.0,
) -> Tuple[List[VectorGraphNode], List[VectorGraphEdge]]:
    """
    Convert a 1-pixel skeleton into a node/edge graph.

    Nodes: skeleton pixels whose degree != 2.
    Edges: maximal chains of degree-2 pixels between nodes.
    Loops: remaining all-degree-2 components are traced separately.
    """
    skel_set: Set[Tuple[int, int]] = set(map(tuple, np.argwhere(skeleton > 0)))
    if not skel_set:
        return [], []

    node_pixels = [p for p in skel_set if _vx_degree(p, skel_set) != 2]
    node_id_of: Dict[Tuple[int, int], int] = {}
    nodes: List[VectorGraphNode] = []

    for i, p in enumerate(node_pixels):
        node_id_of[p] = i
        nodes.append(VectorGraphNode(node_id=i, yx=p, degree=_vx_degree(p, skel_set)))

    visited_steps: Set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()
    edges: List[VectorGraphEdge] = []

    def trace_from(node_p: Tuple[int, int], nbr_p: Tuple[int, int]) -> Optional[VectorGraphEdge]:
        path = [node_p, nbr_p]
        prev = node_p
        curr = nbr_p
        visited_steps.add(_vx_step_key(prev, curr))

        for _ in range(500000):
            if curr in node_id_of and curr != node_p:
                break

            nbrs = _vx_nbrs(curr, skel_set)
            next_candidates = [q for q in nbrs if q != prev]
            if not next_candidates:
                break

            unvisited = [q for q in next_candidates if _vx_step_key(curr, q) not in visited_steps]
            nxt = unvisited[0] if unvisited else next_candidates[0]
            step = _vx_step_key(curr, nxt)
            if step in visited_steps:
                break

            visited_steps.add(step)
            path.append(nxt)
            prev, curr = curr, nxt

            if curr == node_p:
                break

        pts_xy = np.array([[x, y] for y, x in path], dtype=float)
        if len(pts_xy) < 2:
            return None

        poly_len = ArcLength.polyline(pts_xy)
        if poly_len < min_edge_length_px:
            return None

        return VectorGraphEdge(
            edge_id=len(edges),
            start_node_id=node_id_of.get(path[0], None),
            end_node_id=node_id_of.get(path[-1], None),
            points_px=pts_xy,
            is_loop=(path[0] == path[-1]),
        )

    for node_p in node_pixels:
        for nbr in _vx_nbrs(node_p, skel_set):
            step = _vx_step_key(node_p, nbr)
            if step in visited_steps:
                continue
            edge = trace_from(node_p, nbr)
            if edge is not None:
                edge.edge_id = len(edges)
                edges.append(edge)

    # leftover pure loops (components without node pixels)
    for p in list(skel_set):
        for q in _vx_nbrs(p, skel_set):
            step0 = _vx_step_key(p, q)
            if step0 in visited_steps:
                continue

            loop_path = [p, q]
            visited_steps.add(step0)
            prev, curr = p, q

            for _ in range(500000):
                nbrs = _vx_nbrs(curr, skel_set)
                next_candidates = [n for n in nbrs if n != prev]
                if not next_candidates:
                    break

                nxt = next_candidates[0]
                step = _vx_step_key(curr, nxt)
                if step in visited_steps:
                    if nxt == loop_path[0]:
                        loop_path.append(nxt)
                    break

                visited_steps.add(step)
                loop_path.append(nxt)
                prev, curr = curr, nxt
                if curr == loop_path[0]:
                    break

            pts_xy = np.array([[x, y] for y, x in loop_path], dtype=float)
            poly_len = ArcLength.polyline(pts_xy)
            if poly_len >= min_edge_length_px:
                edges.append(VectorGraphEdge(
                    edge_id=len(edges),
                    start_node_id=None,
                    end_node_id=None,
                    points_px=pts_xy,
                    is_loop=True,
                ))

    return nodes, edges


def merge_close_aligned_edges(
    edges: List[VectorGraphEdge],
    tube_width_px: float,
    endpoint_tol_mult: float = 1.25,
    max_join_angle_deg: float = 28.0,
) -> List[VectorGraphEdge]:
    """
    Merge broken graph edges when their endpoints are close and tangent-aligned.

    This is intentionally conservative. It only merges when:
      - endpoints are within endpoint_tol_mult × tube_width_px
      - local tangent mismatch <= max_join_angle_deg
    """
    if len(edges) < 2:
        return edges

    endpoint_tol = max(4.0, tube_width_px * endpoint_tol_mult)
    max_join_angle = math.radians(max_join_angle_deg)

    def edge_endpoints(edge: VectorGraphEdge):
        pts = edge.points_px
        return pts[0], pts[-1]

    def edge_tangents(edge: VectorGraphEdge):
        pts = edge.points_px
        if len(pts) >= 3:
            t0 = pts[1] - pts[0]
            t1 = pts[-1] - pts[-2]
        elif len(pts) == 2:
            t0 = pts[1] - pts[0]
            t1 = pts[1] - pts[0]
        else:
            t0 = np.array([1.0, 0.0])
            t1 = np.array([1.0, 0.0])
        return t0, t1

    def normalize(v: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(v)
        return v / n if n > 1e-12 else v

    active = [VectorGraphEdge(
        edge_id=e.edge_id,
        start_node_id=e.start_node_id,
        end_node_id=e.end_node_id,
        points_px=e.points_px.copy(),
        is_loop=e.is_loop,
        bezier_segs_px=list(e.bezier_segs_px),
        length_px=e.length_px,
    ) for e in edges]

    changed = True
    while changed:
        changed = False
        n = len(active)
        for i in range(n):
            if changed:
                break
            ei = active[i]
            if ei.is_loop:
                continue
            ai0, ai1 = edge_endpoints(ei)
            ti0, ti1 = edge_tangents(ei)
            nti0, nti1 = normalize(ti0), normalize(ti1)

            for j in range(i + 1, n):
                ej = active[j]
                if ej.is_loop:
                    continue
                bj0, bj1 = edge_endpoints(ej)
                tj0, tj1 = edge_tangents(ej)
                ntj0, ntj1 = normalize(tj0), normalize(tj1)

                candidates = [
                    (ai1, bj0, nti1, -ntj0, "tail-head"),
                    (ai1, bj1, nti1, ntj1,  "tail-tail"),
                    (ai0, bj0, -nti0, -ntj0, "head-head"),
                    (ai0, bj1, -nti0, ntj1, "head-tail"),
                ]

                best = None
                best_dist = float("inf")
                for p, q, tp, tq, mode in candidates:
                    d = float(np.linalg.norm(p - q))
                    if d > endpoint_tol:
                        continue
                    dot = float(np.clip(np.dot(normalize(tp), normalize(tq)), -1.0, 1.0))
                    ang = math.acos(dot)
                    if ang <= max_join_angle and d < best_dist:
                        best = mode
                        best_dist = d

                if best is None:
                    continue

                # Build merged point list with minimal interpolation bridge.
                a = ei.points_px
                b = ej.points_px
                if best == "tail-head":
                    merged = np.vstack([a, b])
                elif best == "tail-tail":
                    merged = np.vstack([a, b[::-1]])
                elif best == "head-head":
                    merged = np.vstack([a[::-1], b])
                else:  # head-tail
                    merged = np.vstack([b, a])

                # Remove duplicate-near join points
                keep = [merged[0]]
                for k in range(1, len(merged)):
                    if np.linalg.norm(merged[k] - keep[-1]) > 0.5:
                        keep.append(merged[k])
                merged = np.asarray(keep, dtype=float)

                new_edge = VectorGraphEdge(
                    edge_id=0,
                    start_node_id=None,
                    end_node_id=None,
                    points_px=merged,
                    is_loop=bool(np.linalg.norm(merged[0] - merged[-1]) <= endpoint_tol * 0.5),
                )

                active = [e for k, e in enumerate(active) if k not in (i, j)]
                active.append(new_edge)
                changed = True
                break

    for idx, e in enumerate(active):
        e.edge_id = idx
    return active


def vectorize_graph_edge(
    edge: VectorGraphEdge,
    tube_width_px: float,
    max_err_px: float = 1.5,
    max_pts: int = SUBSAMPLE_MAX_PTS,
) -> VectorGraphEdge:
    pts = np.asarray(edge.points_px, dtype=float)
    if len(pts) < 2:
        edge.length_px = 0.0
        edge.bezier_segs_px = []
        return edge

    win = max(15, int(tube_width_px * 2.0) | 1)
    pts_sm = smooth_path_savgol(pts, window=win, poly=SAVGOL_POLY)
    pts_sm = subsample_path(pts_sm, max_pts)

    segs = BezierFitter.fit_adaptive(pts_sm, max_err=max_err_px)
    edge.bezier_segs_px = segs
    edge.length_px = float(sum(seg.length for seg in segs)) if segs else ArcLength.polyline(pts_sm)
    return edge


def filename_width_inches(path: str) -> float:
    name = os.path.basename(path)
    m = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)", name)
    if not m:
        raise ValueError(f"Cannot parse width from filename: {name}")
    return float(m.group(1))


def calibration_from_filename_width(path: str, image_width_px: int) -> Calibration:
    width_in = filename_width_inches(path)
    if image_width_px <= 0:
        raise ValueError("image_width_px must be > 0")
    px_per_inch = float(image_width_px) / width_in
    return Calibration(px_per_inch=px_per_inch, mode="filename_width")


def run_vector_graph_pipeline(
    image_path_or_array,
    calibration: Optional[Calibration] = None,
    min_edge_length_px: float = 12.0,
    bezier_max_err_px: float = 1.5,
    use_ridge_tracker: bool = False,
    merge_edges: bool = True,
) -> VectorGraphResult:
    binary, meta = BWImageLoader.load(image_path_or_array)
    h, w = binary.shape
    tube_w = float(meta["tube_width_est_px"])

    if calibration is None:
        if isinstance(image_path_or_array, (str, Path)):
            calibration = calibration_from_filename_width(str(image_path_or_array), w)
        else:
            raise ValueError("calibration is required when input is not a file path")

    if use_ridge_tracker:
        tracker = ContinuousRidgeTracker(binary)
        ridge_paths = tracker.extract_paths(min_path_px=min_edge_length_px)
        edges = [VectorGraphEdge(edge_id=i, start_node_id=None, end_node_id=None,
                                 points_px=np.asarray(p, dtype=float), is_loop=False)
                 for i, p in enumerate(ridge_paths)]
        nodes = []
    else:
        skeleton = skeletonize_bw(binary)
        nodes, edges = build_vector_graph(
            skeleton,
            min_edge_length_px=max(min_edge_length_px, tube_w * 2.0),
        )

    if merge_edges and edges:
        edges = merge_close_aligned_edges(edges, tube_w)

    total_px = 0.0
    for i, edge in enumerate(edges):
        edge.edge_id = i
        vectorize_graph_edge(edge, tube_w, max_err_px=bezier_max_err_px)
        total_px += edge.length_px

    return VectorGraphResult(
        image_w=w,
        image_h=h,
        tube_width_px=tube_w,
        n_nodes=len(nodes),
        n_edges=len(edges),
        total_length_px=total_px,
        total_length_m=calibration.to_meters(total_px),
        calibration=calibration,
        nodes=nodes,
        edges=edges,
    )


def export_vector_graph_svg(result: VectorGraphResult, out_path: str, stroke_px: float = 1.0) -> None:
    width_mm = result.image_w * result.calibration.mm_per_px
    height_mm = result.image_h * result.calibration.mm_per_px
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm:.6f}mm" height="{height_mm:.6f}mm" viewBox="0 0 {result.image_w} {result.image_h}">'
    ]
    for edge in result.edges:
        d = edge.to_svg_path_d()
        if not d:
            continue
        color = "#5078FF" if edge.is_loop else "#FF5050"
        lines.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{stroke_px}"/>')
    lines.append("</svg>")
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")


def render_vector_graph_overlay(
    image_path_or_array,
    result: VectorGraphResult,
    out_path: str,
    show_nodes: bool = True,
    show_edges: bool = True,
    show_beziers: bool = True,
) -> None:
    binary, _ = BWImageLoader.load(image_path_or_array)
    vis = cv.cvtColor(binary, cv.COLOR_GRAY2BGR)

    if show_edges:
        for edge in result.edges:
            pts = np.asarray(edge.points_px, dtype=np.int32)
            if len(pts) >= 2:
                cv.polylines(vis, [pts.reshape((-1, 1, 2))], False, (0, 255, 255), 1, cv.LINE_AA)

    if show_beziers:
        for edge in result.edges:
            color = (255, 0, 0) if edge.is_loop else (0, 0, 255)
            for seg in edge.bezier_segs_px:
                pts_b = np.array([seg.at(t) for t in np.linspace(0.0, 1.0, 40)], dtype=np.int32)
                for i in range(len(pts_b) - 1):
                    cv.line(vis, tuple(pts_b[i]), tuple(pts_b[i + 1]), color, 2, cv.LINE_AA)

    if show_nodes:
        for node in result.nodes:
            y, x = node.yx
            color = (0, 255, 0) if node.degree == 1 else (255, 0, 255)
            cv.circle(vis, (x, y), 3, color, -1, cv.LINE_AA)

    cv.imwrite(out_path, vis)


def extract_zip_flat(zip_path: str, out_dir: str) -> List[str]:
    out = []
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            name = os.path.basename(member)
            if not name:
                continue
            dest = str(Path(out_dir) / name)
            with zf.open(member) as src, open(dest, "wb") as dst:
                dst.write(src.read())
            out.append(dest)
    return out


def iter_pngs(path: str) -> Iterable[str]:
    p = Path(path)
    if p.is_file() and p.suffix.lower() == ".png":
        yield str(p)
        return
    if p.is_dir():
        for fp in sorted(p.rglob("*.png")):
            yield str(fp)


def batch_run_dataset(
    input_path: str,
    out_dir: str,
    use_ridge_tracker: bool = False,
    merge_edges: bool = True,
    write_svg: bool = True,
    write_overlay: bool = True,
) -> List[Dict]:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    svg_dir = out_root / "svg"
    overlay_dir = out_root / "overlay"
    if write_svg:
        svg_dir.mkdir(parents=True, exist_ok=True)
    if write_overlay:
        overlay_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict] = []
    for img_path in iter_pngs(input_path):
        try:
            result = run_vector_graph_pipeline(
                img_path,
                calibration=None,
                use_ridge_tracker=use_ridge_tracker,
                merge_edges=merge_edges,
            )
            stem = Path(img_path).stem
            if write_svg:
                export_vector_graph_svg(result, str(svg_dir / f"{stem}.svg"))
            if write_overlay:
                render_vector_graph_overlay(img_path, result, str(overlay_dir / f"{stem}.png"))
            row = {
                "file": os.path.basename(img_path),
                "total_length_px": result.total_length_px,
                "total_length_m": result.total_length_m,
                "n_nodes": result.n_nodes,
                "n_edges": result.n_edges,
                "tube_width_px": result.tube_width_px,
                "px_per_inch": result.calibration.px_per_inch,
                "mm_per_px": result.calibration.mm_per_px,
            }
            rows.append(row)
        except Exception as exc:
            rows.append({
                "file": os.path.basename(img_path),
                "error": str(exc),
            })

    with open(out_root / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sorted({k for row in rows for k in row.keys()}))
        writer.writeheader()
        writer.writerows(rows)

    with open(out_root / "summary.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    return rows


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Single-file B&W neon pipeline: measure, vectorize, export SVG, and batch-run datasets."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_measure = sub.add_parser("measure", help="Run the original processor pipeline on one PNG.")
    p_measure.add_argument("image")
    p_measure.add_argument("--width-in", type=float, default=None, help="Physical sign width in inches. If omitted, parsed from filename.")
    p_measure.add_argument("--use-ridge-tracker", action="store_true")
    p_measure.add_argument("--target-meters", type=float, default=None)

    p_vector = sub.add_parser("vector", help="Run vector graph pipeline on one PNG and export SVG/overlay.")
    p_vector.add_argument("image")
    p_vector.add_argument("--width-in", type=float, default=None)
    p_vector.add_argument("--out-svg", default=None)
    p_vector.add_argument("--out-overlay", default=None)
    p_vector.add_argument("--use-ridge-tracker", action="store_true")
    p_vector.add_argument("--no-merge-edges", action="store_true")

    p_batch = sub.add_parser("batch", help="Run vector graph pipeline on all PNGs in a folder.")
    p_batch.add_argument("input")
    p_batch.add_argument("out_dir")
    p_batch.add_argument("--use-ridge-tracker", action="store_true")
    p_batch.add_argument("--no-merge-edges", action="store_true")
    p_batch.add_argument("--no-svg", action="store_true")
    p_batch.add_argument("--no-overlay", action="store_true")

    p_unzip = sub.add_parser("unzip", help="Flat-extract a ZIP dataset.")
    p_unzip.add_argument("zip_path")
    p_unzip.add_argument("out_dir")

    args = parser.parse_args()

    if args.cmd == "unzip":
        files = extract_zip_flat(args.zip_path, args.out_dir)
        print(json.dumps({"count": len(files), "files": files[:10]}, indent=2))
        return 0

    if args.cmd == "measure":
        binary, meta = BWImageLoader.load(args.image)
        width_in = args.width_in if args.width_in is not None else filename_width_inches(args.image)
        cal = Calibration(px_per_inch=binary.shape[1] / width_in, mode="filename_width")
        result = run_pipeline(
            args.image,
            calibration=cal,
            target_meters=args.target_meters,
            use_ridge_tracker=args.use_ridge_tracker,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    if args.cmd == "vector":
        binary, _ = BWImageLoader.load(args.image)
        width_in = args.width_in if args.width_in is not None else filename_width_inches(args.image)
        cal = Calibration(px_per_inch=binary.shape[1] / width_in, mode="filename_width")
        result = run_vector_graph_pipeline(
            args.image,
            calibration=cal,
            use_ridge_tracker=args.use_ridge_tracker,
            merge_edges=not args.no_merge_edges,
        )
        print(json.dumps(result.to_dict(), indent=2))
        if args.out_svg:
            export_vector_graph_svg(result, args.out_svg)
        if args.out_overlay:
            render_vector_graph_overlay(args.image, result, args.out_overlay)
        return 0

    if args.cmd == "batch":
        rows = batch_run_dataset(
            args.input,
            args.out_dir,
            use_ridge_tracker=args.use_ridge_tracker,
            merge_edges=not args.no_merge_edges,
            write_svg=not args.no_svg,
            write_overlay=not args.no_overlay,
        )
        print(json.dumps({"count": len(rows), "out_dir": args.out_dir}, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
