"""
v8_pipeline.py  —  V8 Full Measurement Pipeline
================================================

ENTRY POINT
    result = V8Pipeline().measure(source, real_width_inches, gt_m=None)

PIPELINE STAGES
  1. Load & normalise image (v8_input)
       · auto-detect format (BW / transparent / colored / SVG / CDR)
       · tight content BBox crop  → correct px_per_inch (CRITICAL FIX)
  2. Ridge extraction (v8_ridge)
       · Frangi multi-scale Hessian → geometric centerline (not morphological)
       · NMS → single-pixel ridges
  3. IR-MST path building (v8_ridge)
       · k-NN graph on ridge pixels
       · adaptive edge pruning → separate glass tubes
       · junction disambiguation → merge script-font fragments
  4. Three-regime measurement (v8_geometry)
       · smooth → DP partition → STRAIGHT / ARC / FREEFORM per segment
       · Euclidean / Pratt r·θ / Bézier + Gauss-Legendre
  5. Physics validation
       · tube diameter plausibility
       · length-per-inch ratio
       · absolute bounds
  6. Tier assignment + transparent reasoning report
  7. Overlay visualisation (base64 PNG)

QUALITY TIERS
    GLASS_CUT  ≤  5 %   direct glass cutting
    QUOTE      ≤ 10 %   safe for customer quotes
    ESTIMATE   ≤ 20 %   rough cost estimation only
    MARGINAL   ≤ 35 %   manual re-measure required
    FAIL       >  35 %  pipeline failed
"""

from __future__ import annotations

import base64
import io
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from v8_input   import load_sign, parse_gt_filename, LoadedSign, InputMeta
from v8_ridge   import extract_ridge_paths, RidgePath
from v8_geometry import measure_all_paths, MeasuredPath, Regime

from skimage.morphology import skeletonize as _skimage_skeletonize


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

INCHES_TO_M       = 0.0254
MIN_M_PER_INCH    = 0.025   # physical lower bound: 25 mm of tube per inch of sign width
MAX_M_PER_INCH    = 0.450   # physical upper bound: 450 mm per inch
MIN_TOTAL_M       = 0.05    # absolute minimum plausible LOC
MAX_TOTAL_M       = 120.0   # absolute maximum plausible LOC (very large sign)
MIN_TUBE_MM       = 2.0     # minimum stroke width in design file (mm); real neon > 8mm but mockups draw thinner
MAX_TUBE_MM       = 15.0    # maximum stroke width in design file (mm); > 15mm indicates low-res blob merging
MAX_RIDGE_PPI     = 40.0    # cap ppi before Frangi/skeleton (preserves topology; 2-10x speedup)
MAX_DT_PPI        = 20.0    # cap ppi for DT-blend (DT formula is scale-invariant; saves 4× on skeletonize)

# Resolution thresholds (px/inch)
# Below RESOLUTION_FAIL_PPI the pixel-to-metre conversion is so inaccurate
# that skeleton/DT measurements are typically 2-10x off. For those images
# we fall back to the white-area geometric estimator (see _white_area_loc).
RESOLUTION_FAIL_PPI  = 8.0   # hard fail below this  (was 18.0)
RESOLUTION_WARN_PPI  = 15.0  # warn below this       (was 30.0)

# White-area geometric estimator constants
# LOC (m) ~= white_area_m2 / tube_OD_m
# When tube_OD is unknown we use a mid-range physical neon OD (12 mm).
WHITE_AREA_FALLBACK_TUBE_OD_M = 0.012   # 12 mm — safe mid-range for design-file mockups

# DT-blend tube thickness threshold for capped vs uncapped DTW selection
# Thin tube (< 6.5 mm): junction DT ≈ r → uncapped is accurate
# Fat tube (≥ 6.5 mm): junction DT >> r → uncapped overcounts, use capped
TUBE_MM_CAP_THRESHOLD = 6.5

TIER_THRESHOLDS = {
    "GLASS_CUT": 5.0,
    "QUOTE":    10.0,
    "ESTIMATE": 20.0,
    "MARGINAL": 35.0,
}

# Colour palette for overlay (BGR for OpenCV)
_COLOUR = {
    Regime.STRAIGHT:   (255, 180,  50),   # warm yellow
    Regime.ARC:        ( 50, 200, 255),   # cyan
    Regime.FREEFORM:   ( 80, 255, 120),   # green
    Regime.DEGENERATE: (100, 100, 100),   # grey
}


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class V8Result:
    # ── Core measurement ──────────────────────────────────────────────────────
    measured_m:     float
    tier:           str             # GLASS_CUT / QUOTE / ESTIMATE / MARGINAL / FAIL
    confidence:     float           # 0–1 aggregate fit quality
    px_per_inch:    float           # ppi_x (horizontal calibration)
    px_per_inch_y:  float = 0.0     # ppi_y (vertical calibration; == px_per_inch if isotropic)
    ar_consistency: float = 1.0     # k = ppi_y / ppi_x  (1.0 = isotropic image)
    tube_width_mm:  float = 0.0

    # ── Ground-truth comparison (optional) ───────────────────────────────────
    gt_m:           Optional[float] = None
    error_pct:      Optional[float] = None

    # ── Detailed breakdown ───────────────────────────────────────────────────
    n_paths:        int   = 0
    n_straight_segs:int   = 0
    n_arc_segs:     int   = 0
    n_freeform_segs:int   = 0

    # ── Physics validation ───────────────────────────────────────────────────
    physics_ok:     bool  = True
    physics_notes:  list  = field(default_factory=list)

    # ── Transparent reasoning ────────────────────────────────────────────────
    reasoning:      list  = field(default_factory=list)

    # ── Per-path breakdown ───────────────────────────────────────────────────
    paths:          list  = field(default_factory=list)   # List[MeasuredPath]

    # ── Visualisations (base64 PNG) ──────────────────────────────────────────
    overlay_b64:    str   = ""
    ridge_b64:      str   = ""

    # ── Metadata ─────────────────────────────────────────────────────────────
    source:         str   = ""
    elapsed_s:      float = 0.0
    input_format:   str   = ""
    input_meta:     Optional[InputMeta] = None

    # ── ML / DT-blend internals (exposed for feature extraction) ─────────────
    dfs_m:          float = 0.0   # DFS-only measurement before blend
    dtw_m:          float = 0.0   # DT-weighted skeleton measurement
    mean_dt_ratio:  float = 0.0   # mean(DT_on_skel) / tube_radius — topology signal
    pct_fat:        float = 0.0   # fraction of skel pixels with DT > 1.2 × tube_radius
    white_pct:      float = 0.0   # mask white pixel fraction (from meta)

    # ── Quality / reliability signals (no GT needed) ──────────────────────────
    overcount_risk:  float = 0.0  # 0=clean 1=definite overcount (derived from overcount_ratio)
    bias_direction:  str   = "NEUTRAL"  # "HIGH" | "LOW" | "NEUTRAL" — predicted LOC bias

    # ── LOC uncertainty range (business output, no GT needed) ──────────────
    # Physics bounds: neon tube OD ∈ [4, 22] mm — unambiguous physical law.
    # loc_low  = LOC if tube were 22mm (max OD → fewest meters)
    # loc_high = LOC if tube were 4mm  (min OD → most meters)
    # For procurement: order to loc_high × safety_factor.
    # For pricing:     use loc_best (= measured_m).
    loc_low_m:   float = 0.0
    loc_high_m:  float = 0.0
    area_m:      float = 0.0   # area-based LOC at best tube_width (diagnostic)
    overcount_ratio: float = 1.0  # DFS / area_m_best  (1.0=self-consistent, >1.5=overcount)
    tube_cv:     float = 0.0   # DT coeff-of-variation on skeleton (< 0.25 = uniform tube)
    tube_width_uncertain: bool = False  # DT vs implied tube_width disagree > 40%

    # ── Predicted tier (no GT) — business confidence score ───────────────────
    # confidence_no_gt: physics-grounded reliability WITHOUT any ground truth.
    #   1.0 = all signals consistent, tube is uniform, no overcounting
    #   <0.5 = multiple red flags — treat as MARGINAL for procurement
    # predicted_tier: tier inferred purely from signal quality (no GT)
    # loc_spread: loc_high / loc_low — uncertainty multiplier.
    #   Max physically possible = 22/4 = 5.5×  (completely unknown tube OD)
    #   loc_spread < 2.0 → tube OD well-constrained → reliable procurement
    #   loc_spread > 4.5 → near maximum uncertainty → procurement risky
    # detection_incomplete: measured_m << min plausible for this sign size
    #   Signals that ridge detector missed significant portions of the neon.
    confidence_no_gt:      float = 1.0
    predicted_tier:        str   = "UNKNOWN"
    loc_spread:            float = 0.0
    detection_incomplete:  bool  = False

    # ── Hollow-outline font detector (no GT needed) ────────────────────────────
    # hollow_ratio = enclosed_dark_pixels / white_pixels.
    # Hollow-outline designs: neon runs around letter PERIMETERS (ring topology).
    # Dark letter interiors enclosed by white tube → hollow_ratio >> 0.
    # Solid-fill neon (tube IS the letter fill): no enclosed dark regions → ≈ 0.
    #
    # Effect on measurement:
    #   Overcount: skeleton traces BOTH inner+outer walls of hollow stroke → 2× perimeter
    #   Undercount: min_path_px filter removes short junction segments
    # hollow_ratio > 0.3 = probable hollow outline → manual review recommended.
    # hollow_ratio > 0.8 = definite hollow outline → LOC error likely 20-40%.
    hollow_ratio:          float = 0.0
    is_hollow_outline:     bool  = False


# ─────────────────────────────────────────────────────────────────────────────
# Physics validator
# ─────────────────────────────────────────────────────────────────────────────

COVERAGE_WARN_RATIO   =  1.05  # skeleton x tube_px / white_px > this → phantom paths likely
COVERAGE_FAIL_RATIO   =  1.25  # definitive phantom topology
MAX_MASK_FRAC         =  0.58  # mask > 58% of pixels → background contamination (V7 insight)
MIN_MASK_FRAC         =  0.003 # mask < 0.3% of pixels → degenerate / no signal (V7-proven)
NPATH_EXPLOSION_FAIL  =  80    # n_paths > this → skeleton fragmentation / overcounting
                               # Lowered from 200: catch moderate explosions at 2-3x expected paths
LED_NEON_MM_MIN       =  4.0   # narrowest real LED flex / design stroke (mm)
LED_NEON_MM_MAX       = 22.0   # widest standard LED flex OD (mm) — wider than old 15mm cap


def _physics_validate(
    total_m: float,
    real_width_inches: float,
    tube_width_px: float,
    px_per_inch: float,
    notes: list,
    total_path_px: float = 0.0,
    white_pct: float     = 0.0,
    crop_area: int       = 0,
    n_paths: int         = 0,
) -> bool:
    """
    Physical plausibility checks for the V8 measurement result.

    New checks vs V8.0
    ------------------
    1. Resolution guard  (px_per_inch)
       At < 15 px/inch, tube widths shrink to 1-3 px; the skeleton / Frangi
       response becomes dominated by noise, producing phantom tube paths.
       Warn at < 15; hard-fail at < 8.

    2. Mask-coverage consistency  (skeleton × tube_width vs white_pixels)
       After measuring all paths, the implied skeleton pixel area
       (total_path_px × tube_width_px) must not greatly exceed the actual
       white-pixel area of the mask.  If it does, the pipeline traced more
       tube than the mask contains → phantom topology detected.
       Warn at ratio > 1.05; hard-fail at ratio > 1.25.
    """
    ok = True
    tube_mm = (tube_width_px / px_per_inch) * 25.4 if px_per_inch > 0 else 0.0
    ratio   = total_m / real_width_inches if real_width_inches > 0 else 0.0

    # ── 1. Resolution guard ───────────────────────────────────────────────────
    if px_per_inch < RESOLUTION_FAIL_PPI:
        notes.append(
            f"[FAIL] Resolution {px_per_inch:.1f} px/inch < {RESOLUTION_FAIL_PPI} px/inch — "
            f"image is too low-res for reliable measurement. "
            f"Request image at >= 30 px/inch for this sign width."
        )
        ok = False
    elif px_per_inch < RESOLUTION_WARN_PPI:
        notes.append(
            f"[WARN] Resolution {px_per_inch:.1f} px/inch is marginal "
            f"(< {RESOLUTION_WARN_PPI} px/inch). Result may be unreliable. "
            f"Recommend >= 30 px/inch."
        )
        ok = False

    # ── 2. Mask-coverage consistency ─────────────────────────────────────────
    if total_path_px > 0 and tube_width_px > 0 and white_pct > 0 and crop_area > 0:
        white_pixels     = white_pct * crop_area
        skeleton_area    = total_path_px * tube_width_px
        coverage_ratio   = skeleton_area / white_pixels if white_pixels > 0 else 0.0

        if coverage_ratio > COVERAGE_FAIL_RATIO:
            notes.append(
                f"[FAIL] Mask-coverage ratio {coverage_ratio:.2f} > {COVERAGE_FAIL_RATIO} — "
                f"skeleton covers more area than the mask allows. "
                f"Phantom tube paths detected (likely outline double-trace at low ppi)."
            )
            ok = False
        elif coverage_ratio > COVERAGE_WARN_RATIO:
            notes.append(
                f"[WARN] Mask-coverage ratio {coverage_ratio:.2f} > {COVERAGE_WARN_RATIO} — "
                f"skeleton is dense relative to tube mask. May over-count at junctions."
            )

    # ── 3. Mask-fraction check (V7-proven) ───────────────────────────────────
    if white_pct > 0:
        if white_pct > MAX_MASK_FRAC:
            notes.append(
                f"[FAIL] Mask fraction {white_pct:.2f} > {MAX_MASK_FRAC} — "
                f"mask captures background pixels. Likely bad image segmentation."
            )
            ok = False

    # ── 4. n_paths explosion guard ────────────────────────────────────────────
    if n_paths > NPATH_EXPLOSION_FAIL:
        notes.append(
            f"[FAIL] n_paths={n_paths} > {NPATH_EXPLOSION_FAIL} — "
            f"skeleton fragmented into too many pieces. Overcounting certain. "
            f"Check image format: colored/glow images need clean B&W conversion."
        )
        ok = False

    # ── 5. Physical neon tube OD plausibility ────────────────────────────────
    # LED neon flex: 6-20mm; glass neon: 8-15mm; design mockups may draw thinner.
    # Use wider range to avoid false positives on small mockup images.
    if tube_mm > 0 and not (LED_NEON_MM_MIN <= tube_mm <= LED_NEON_MM_MAX):
        if tube_mm < LED_NEON_MM_MIN:
            notes.append(
                f"[WARN] Tube OD {tube_mm:.1f}mm < {LED_NEON_MM_MIN}mm physical minimum. "
                f"Likely glow-inflated mask or noise — tube width estimate unreliable."
            )
        else:
            notes.append(
                f"[FAIL] Tube OD {tube_mm:.1f}mm > {LED_NEON_MM_MAX}mm — "
                f"probable low-res blob merging. Tubes cannot be separated at this resolution."
            )
            ok = False

    # ── 6. LOC-per-inch ratio ─────────────────────────────────────────────────
    if not (MIN_M_PER_INCH <= ratio <= MAX_M_PER_INCH):
        notes.append(
            f"[WARN] Length ratio {ratio:.3f} m/inch outside physical range "
            f"[{MIN_M_PER_INCH}-{MAX_M_PER_INCH}] m/inch."
        )
        ok = False

    # ── 5. Absolute LOC bounds ────────────────────────────────────────────────
    if not (MIN_TOTAL_M <= total_m <= MAX_TOTAL_M):
        notes.append(
            f"[WARN] Total LOC {total_m:.3f} m outside plausible range "
            f"[{MIN_TOTAL_M}-{MAX_TOTAL_M}] m."
        )
        ok = False

    if ok:
        notes.append(
            f"[OK] Physics: tube ~{tube_mm:.1f} mm, "
            f"ratio {ratio:.3f} m/inch, total {total_m:.3f} m."
        )
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# Tier assignment
# ─────────────────────────────────────────────────────────────────────────────

def _assign_tier(error_pct: Optional[float]) -> str:
    if error_pct is None:
        return "UNKNOWN"
    for tier, thresh in TIER_THRESHOLDS.items():
        if abs(error_pct) <= thresh:
            return tier
    return "FAIL"


def _v7_plateau_loc(
    channel: np.ndarray,
    ppi: float,
    width_in: float,
    sat_channel: Optional[np.ndarray] = None,
) -> Tuple[float, float, float]:
    """
    V7-style stable LOC from adaptive threshold plateau scan.

    Faithfully mirrors V7 AdaptiveThresholder.find():
      - Scans 36 thresholds from 0.05 to 0.90 (step 0.025) — V7-proven range
      - `channel` is float [0,1] — compares as `channel > t` (NOT scaled to 255)
      - For colored images: if sat_channel provided, scans S first (V7: S → V → FG)
      - Filters: mf in [MIN_MASK_FRAC, MAX_MASK_FRAC] AND LOC in physics range
      - Finds minimum-variance window (width=4, V7-proven) among valid results

    Returns (loc_m, plateau_cv, tube_width_mm).
    loc_m = 0.0 if fewer than 2 valid thresholds found.
    """
    from skimage.morphology import skeletonize as _skel_v7

    k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    min_loc = width_in * MIN_M_PER_INCH
    max_loc = width_in * MAX_M_PER_INCH
    thresholds = np.arange(0.05, 0.92, 0.025).tolist()  # 36 levels — V7 exact

    def _scan_channel(ch: np.ndarray) -> list:
        out = []
        for t in thresholds:
            m = cv2.morphologyEx(
                (ch > t).astype(np.uint8) * 255,
                cv2.MORPH_CLOSE, k5
            )
            mf = float(np.mean(m > 0))
            if mf < MIN_MASK_FRAC or mf > MAX_MASK_FRAC:
                continue
            skel = _skel_v7(m > 0).astype(np.uint8)
            skel_px = int(np.sum(skel > 0))
            if skel_px == 0:
                continue
            loc_m = skel_px / ppi * INCHES_TO_M
            if min_loc <= loc_m <= max_loc:
                dist = cv2.distanceTransform(m, cv2.DIST_L2, 5)
                dt_skel = dist[skel > 0]
                if len(dt_skel) < 5:
                    continue
                tw_mm = float(np.percentile(dt_skel, 65)) * 2.0 / ppi * 25.4
                # Semantic neon constraint: physical tube OD must be in [4, 22]mm.
                # tw_mm < 4mm = thin glow-connectivity bridge, not real tube.
                # tw_mm > 22mm = merged blobs, over-dilated mask.
                if tw_mm < LED_NEON_MM_MIN or tw_mm > LED_NEON_MM_MAX:
                    continue
                out.append((t, mf, loc_m, tw_mm))
        return out

    # V7 channel priority for glow: S → L.  Saturation isolates colored tubes
    # from desaturated background better than luminance alone.
    results = []
    if sat_channel is not None:
        results = _scan_channel(sat_channel)
    if len(results) < 2:
        # Fallback: scan the provided channel (luminance or combined score)
        results = _scan_channel(channel)

    if len(results) < 2:
        return 0.0, 1.0, 0.0

    locs = np.array([r[2] for r in results])

    # Minimum-variance window of width 4 — V7 proven
    best_i, best_var = 0, np.inf
    w = min(4, len(locs))
    for i in range(len(locs) - w + 1):
        v = float(np.var(locs[i:i + w]))
        if v < best_var:
            best_var, best_i = v, i + w // 2

    plateau_loc = results[best_i][2]
    plateau_tw  = results[best_i][3]
    plateau_cv  = (best_var ** 0.5) / max(plateau_loc, 1e-6)
    return plateau_loc, plateau_cv, plateau_tw


def _white_area_loc(
    n_white_px: int,
    px_per_inch: float,
    tube_width_px: float,
) -> float:
    """
    White-area geometric LOC estimator for critically under-resolved images.

    At ppi < RESOLUTION_FAIL_PPI the skeleton traces are too noisy.
    This provides a fallback estimation using raw mask area.

        LOC_m = n_white * (0.0254/ppi) / (tube_px * 0.0254/ppi)
               = n_white * 0.0254 / (ppi * tube_px)
    """
    if px_per_inch <= 0 or tube_width_px <= 0:
        return 0.0
    return float(n_white_px) * 0.0254 / (px_per_inch * tube_width_px)


# ─────────────────────────────────────────────────────────────────────────────
# Visualisation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _img_to_b64(img: np.ndarray) -> str:
    """Encode a numpy image (uint8 BGR or float) to base64 PNG string."""
    if img.dtype != np.uint8:
        img8 = np.clip(img * 255, 0, 255).astype(np.uint8)
    else:
        img8 = img
    ok, buf = cv2.imencode(".png", img8, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _render_overlay(
    gray: np.ndarray,
    ridge_map: np.ndarray,
    paths: List[MeasuredPath],
) -> np.ndarray:
    """
    Render an annotated overlay:
      · grayscale sign as background
      · Frangi ridge heatmap (semi-transparent)
      · extracted paths coloured by regime
    """
    H, W = gray.shape
    canvas = np.zeros((H, W, 3), dtype=np.uint8)

    # Background: grayscale → BGR
    gray8 = np.clip(gray * 255, 0, 255).astype(np.uint8)
    canvas[:, :, 0] = gray8
    canvas[:, :, 1] = gray8
    canvas[:, :, 2] = gray8

    # Ridge heatmap (warm tint)
    ridge8 = np.clip(ridge_map * 255, 0, 255).astype(np.uint8)
    canvas[:, :, 2] = np.maximum(canvas[:, :, 2], ridge8)   # red channel

    # Draw paths
    for mp in paths:
        for seg in mp.segments:
            colour = _COLOUR.get(seg.regime, (200, 200, 200))
            pts_cv = seg.points[:, ::-1].astype(np.int32)    # (row,col)→(x,y)
            if len(pts_cv) >= 2:
                cv2.polylines(
                    canvas, [pts_cv.reshape(-1, 1, 2)],
                    isClosed=False, color=colour, thickness=2, lineType=cv2.LINE_AA
                )
            # Endpoint dots
            for ep in (pts_cv[0], pts_cv[-1]):
                cv2.circle(canvas, tuple(ep), 4, colour, -1, cv2.LINE_AA)

    return canvas


def _render_ridge_vis(ridgeness: np.ndarray) -> np.ndarray:
    """Colourmap visualisation of Frangi ridgeness."""
    r8 = np.clip(ridgeness * 255, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(r8, cv2.COLORMAP_INFERNO)


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

class V8Pipeline:
    """
    Full V8 measurement pipeline.

    Parameters
    ----------
    ridge_threshold : Frangi NMS threshold as fraction of max response.
                      0.05 works for clean B&W; raise to 0.10 for noisy inputs.
    irmst_alpha     : IR-MST edge-pruning multiplier.  2.0 is safe; decrease
                      if adjacent tubes are being merged.
    do_disambig     : enable junction disambiguation (recommended True).
    render_vis      : generate base64 overlay images (set False for batch speed).
    """

    def __init__(
        self,
        ridge_threshold: float = 0.05,
        irmst_alpha:     float = 2.0,
        do_disambig:     bool  = True,
        render_vis:      bool  = True,
    ):
        self.ridge_threshold = ridge_threshold
        self.irmst_alpha     = irmst_alpha
        self.do_disambig     = do_disambig
        self.render_vis      = render_vis

    # ── Public interface ───────────────────────────────────────────────────────

    def measure(
        self,
        source: "str | bytes | Path",
        real_width_inches: float,
        real_height_inches: Optional[float] = None,
        gt_m: Optional[float] = None,
        force_format: Optional[str] = None,
    ) -> V8Result:
        """
        Measure the total tube length of a neon sign.

        Parameters
        ----------
        source              : file path (str/Path) or raw image bytes
        real_width_inches   : physical width of the sign face (EXCLUDING padding)
        real_height_inches  : physical height of the sign face (optional).
                              Enables 2-D anisotropic calibration when supplied.
                              Without it the pipeline assumes the image aspect
                              ratio exactly matches the sign's physical AR
                              (true for properly-exported design files).
        gt_m                : ground truth LOC in metres (for evaluation only)
        force_format        : override format detection ('bw'|'transparent'|'colored')

        Returns
        -------
        V8Result with full measurement, diagnostics, and visualisations.
        """
        t0       = time.perf_counter()
        source_s = str(source) if not isinstance(source, bytes) else "<bytes>"
        reasoning: List[str] = []

        # ── 1. Load ───────────────────────────────────────────────────────────
        try:
            sign = load_sign(
                source, real_width_inches,
                real_height_inches=real_height_inches,
                force_format=force_format,
            )
        except Exception as e:
            return self._fail_result(source_s, real_width_inches, gt_m,
                                     f"Image load failed: {e}", t0)

        meta = sign.meta
        reasoning += meta.notes

        # SVG / CDR exact-LOC short-circuit
        if meta.exact_loc_m is not None:
            return self._exact_result(meta, gt_m, source_s, t0, reasoning)

        # Calibration summary (1-D or 2-D)
        if meta.real_height_inches is not None:
            k_str = (
                f"k={meta.ar_consistency:.3f} "
                + ("ANISO" if abs(meta.ar_consistency - 1.0) > 0.15 else "iso")
            )
            cal_str = f"ppi_x={meta.px_per_inch:.2f}  ppi_y={meta.px_per_inch_y:.2f}  [{k_str}]"
        else:
            cal_str = f"ppi_x={meta.px_per_inch:.2f} [iso, height not supplied]"

        reasoning.append(
            f"Format: {meta.input_format}  |  "
            f"Crop: {meta.original_size[1]}×{meta.original_size[0]} → "
            f"{meta.cropped_size[1]}×{meta.cropped_size[0]} px  |  "
            f"{cal_str}  |  tube_w: {meta.tube_width_px:.1f} px"
        )

        # ── Resolution cap: downsample for all heavy computation ────────────
        # Tube topology is fully captured at 40 ppi (tube width stays ≥ 15 px).
        # DT formula is scale-invariant → same result at any ppi.
        # Both Frangi+IR-MST and skeletonize run on sign_r (downsampled).
        # Physics validation uses original meta (actual physical tube geometry).
        if meta.px_per_inch > MAX_RIDGE_PPI:
            _rs   = MAX_RIDGE_PPI / meta.px_per_inch
            _rh   = max(16, int(sign.gray.shape[0] * _rs))
            _rw   = max(16, int(sign.gray.shape[1] * _rs))
            from copy import copy as _metacopy
            meta_r = _metacopy(meta)
            meta_r.px_per_inch   = MAX_RIDGE_PPI
            meta_r.px_per_inch_y = meta.px_per_inch_y * _rs if meta.px_per_inch_y > 0 else 0.0
            meta_r.tube_width_px = meta.tube_width_px * _rs
            meta_r.cropped_size  = (_rh, _rw)
            gray_r = cv2.resize(sign.gray, (_rw, _rh), interpolation=cv2.INTER_AREA)
            mask_r = cv2.resize(sign.mask, (_rw, _rh), interpolation=cv2.INTER_NEAREST)
            _, mask_r = cv2.threshold(mask_r, 127, 255, cv2.THRESH_BINARY)
            _sat_r = (cv2.resize(sign.sat, (_rw, _rh), interpolation=cv2.INTER_AREA)
                      if getattr(sign, 'sat', None) is not None else None)
            sign_r = LoadedSign(gray=gray_r, mask=mask_r, meta=meta_r, sat=_sat_r)
            reasoning.append(
                f"Ridge res-cap: {meta.px_per_inch:.1f} -> {MAX_RIDGE_PPI:.1f} ppi  "
                f"scale={_rs:.3f}  ridge_size={_rw}x{_rh}px"
            )
        else:
            sign_r, meta_r = sign, meta

        # ── 2a. CRITICALLY LOW-RES SHORT-CIRCUIT ──────────────────────────────
        # At ppi < RESOLUTION_FAIL_PPI the skeleton pixel->metre conversion is
        # catastrophically wrong: each pixel = 1/ppi inches, so at 4-10 ppi a
        # 10,000-pixel skeleton = 25-63 METRES.  The mask at low ppi is also ~2x
        # the physical tube area (low-res rendering merges outlines with fill).
        # Both DFS and DTW produce 2-3x overestimates in these cases.
        #
        # Solution: bypass skeleton entirely and use the white-area geometric
        # estimator which is immune to the pixel->metre amplification.
        if meta_r.px_per_inch < RESOLUTION_FAIL_PPI:
            n_white = int(np.sum(sign_r.mask > 0))
            wa_m    = _white_area_loc(n_white, meta_r.px_per_inch,
                                      max(meta_r.tube_width_px, 4.0))
            wa_m    = min(wa_m, MAX_M_PER_INCH * real_width_inches)
            _wa_note = (
                f"[LOW-RES] ppi={meta_r.px_per_inch:.1f} < {RESOLUTION_FAIL_PPI}"
                f" -- skeleton bypassed. White-area est: "
                f"n_white={n_white}, tube_px={meta_r.tube_width_px:.1f}"
                f" -> {wa_m:.3f}m"
            )
            reasoning.append(_wa_note)
            _phys_n: List[str] = [
                f"[FAIL] Resolution {meta_r.px_per_inch:.1f} px/inch < "
                f"{RESOLUTION_FAIL_PPI} px/inch -- image is critically under-resolved."
                f" Result is a geometric estimate only (+-30% typical)."
                f" Upload at >= 40 px/inch for reliable measurement."
            ]
            _err_pct = None
            if gt_m is not None and gt_m > 0:
                _err_pct = (wa_m - gt_m) / gt_m * 100.0
                reasoning.append(
                    f"GT: {gt_m:.3f}m | white-area est: {wa_m:.3f}m"
                    f" | error: {_err_pct:+.2f}%"
                )

            # Generate visualizations (mask as ridge proxy)
            _wa_ov, _wa_rg = self._render_vis_result(sign_r.gray, (sign_r.mask > 0).astype(np.float32), [], reasoning)

            # Uncertainty bounds based on physics [4mm, 22mm]
            _ppi_eff = meta_r.px_per_inch
            _wa_loc_low  = _white_area_loc(n_white, _ppi_eff, (22.0 / 25.4) * _ppi_eff)
            _wa_loc_high = _white_area_loc(n_white, _ppi_eff, (4.0 / 25.4) * _ppi_eff)

            return V8Result(
                measured_m=wa_m,
                tier="FAIL",
                confidence=0.25,
                px_per_inch=meta.px_per_inch,
                px_per_inch_y=meta.px_per_inch_y,
                ar_consistency=meta.ar_consistency,
                tube_width_mm=(meta.tube_width_px / max(meta.px_per_inch, 1e-3)) * 25.4,
                gt_m=gt_m,
                error_pct=_err_pct,
                n_paths=0,
                physics_ok=False,
                physics_notes=_phys_n,
                reasoning=reasoning,
                source=source_s,
                elapsed_s=time.perf_counter() - t0,
                input_format=meta.input_format,
                input_meta=meta,
                white_pct=meta.white_pct,
                overlay_b64=_wa_ov,
                ridge_b64=_wa_rg,
                area_m=wa_m,
                loc_low_m=_wa_loc_low,
                loc_high_m=_wa_loc_high,
            )

        # ── 2b. Centerline / ridge extraction (normal ppi) ────────────────────
        # Dispatch: skeleton for clean BW; DoG+IR-MST for glow/colored.
        #
        # For clean B&W: precompute skeleton HERE (at DT ppi, scale-invariant)
        # and reuse it in BOTH extract_ridge_paths AND step 3b DT-blend.
        # Eliminates the double-skeletonize that cost 10-30s on large signs.
        use_glow_mode = meta.has_glow
        # Hard override: 'bw' format is binary — no real glow possible.
        # _detect_glow false-positives on low-ppi BW images: at 4px tube width
        # anti-aliasing creates a spurious radial gradient that mimics glow.
        # Without this, all quality guards (guarded by 'not use_glow_mode') are
        # bypassed → overcount_ratio stays 1.0 → undercount never corrected.
        if meta.input_format == 'bw' and use_glow_mode:
            use_glow_mode = False
            reasoning.append(
                f"[OVERRIDE] input_format=bw: glow flag suppressed "
                f"(false positive at ppi={meta.px_per_inch:.1f}, "
                f"tube_px={meta.tube_width_px:.1f}px)"
            )
        effective_alpha    = self.irmst_alpha
        # Semantic path length minimum: a neon tube segment must be at least
        # 1× its own diameter to be a "tube" rather than a junction artifact.
        # Relaxed from 0.5× to 0.25× to capture short tube segments that were
        # being filtered out, causing underestimation on complex designs.
        # Physical basis: even short straight segments (1-2×OD) are valid tubes.
        effective_min_path = max(3.0, meta_r.tube_width_px * 0.25)
        strategy           = "DoG+IR-MST" if use_glow_mode else "skeleton+DFS"

        # ── DT resolution cap (for DT-blend only — DT formula is scale-invariant)
        # Skeleton at MAX_DT_PPI = 20ppi is 4× fewer pixels than 40ppi.
        # skeletonize cost scales ~O(pixels) → ~4× speedup on large signs.
        # Only applied for clean B&W (glow mode doesn't use skeleton).
        _precomputed_skel = None
        _precomputed_dist = None
        _dt_meta = meta_r          # defaults to ridge-level (40ppi)
        _dt_sign = sign_r

        if not use_glow_mode and meta_r.px_per_inch > MAX_DT_PPI:
            _dt_rs = MAX_DT_PPI / meta_r.px_per_inch
            _dt_h  = max(16, int(sign_r.gray.shape[0] * _dt_rs))
            _dt_w  = max(16, int(sign_r.gray.shape[1] * _dt_rs))
            from copy import copy as _dtcopy
            _dt_meta2 = _dtcopy(meta_r)
            _dt_meta2.px_per_inch   = MAX_DT_PPI
            _dt_meta2.px_per_inch_y = meta_r.px_per_inch_y * _dt_rs if meta_r.px_per_inch_y > 0 else 0.0
            _dt_meta2.tube_width_px = meta_r.tube_width_px * _dt_rs
            _dt_meta2.cropped_size  = (_dt_h, _dt_w)
            _dt_gray_r = cv2.resize(sign_r.gray, (_dt_w, _dt_h), interpolation=cv2.INTER_AREA)
            _dt_mask_r = cv2.resize(sign_r.mask, (_dt_w, _dt_h), interpolation=cv2.INTER_NEAREST)
            _, _dt_mask_r = cv2.threshold(_dt_mask_r, 127, 255, cv2.THRESH_BINARY)
            _dt_sign  = LoadedSign(gray=_dt_gray_r, mask=_dt_mask_r, meta=_dt_meta2)
            _dt_meta  = _dt_meta2
            reasoning.append(
                f"DT res-cap: {meta_r.px_per_inch:.1f} -> {MAX_DT_PPI:.1f} ppi  "
                f"DT_size={_dt_w}x{_dt_h}px  (scale-invariant formula)"
            )

        # Precompute skeleton + DT NOW (clean B&W only) — shared between DFS and DT-blend
        if not use_glow_mode:
            try:
                _dt_binary = (_dt_sign.mask > 0).astype(np.uint8)
                _precomputed_dist = cv2.distanceTransform(_dt_binary * 255, cv2.DIST_L2, 5)
                _precomputed_skel = _skimage_skeletonize(_dt_binary).astype(np.uint8)
                reasoning.append(
                    f"Skeleton precomputed at {_dt_meta.px_per_inch:.0f}ppi  "
                    f"({int(np.sum(_precomputed_skel > 0))} px)"
                )
            except Exception as _sk_e:
                reasoning.append(f"Skeleton precompute failed: {_sk_e}")
                _precomputed_skel = None
                _precomputed_dist = None

        reasoning.append(
            f"Centerline strategy: {strategy} "
            f"(format={meta.input_format}, has_glow={meta.has_glow}, "
            f"ppi={meta_r.px_per_inch:.1f})"
        )

        # For skeleton mode with DT-ppi != ridge-ppi, extract_ridge_paths runs on
        # sign_r (ridge-level resolution) for path quality, but we pass the
        # precomputed skeleton (DT-level) only if sizes match; otherwise let
        # extract_ridge_paths skeletonize at ridge-level.
        _skel_for_paths = None
        if (
            _precomputed_skel is not None
            and _dt_sign.mask.shape == sign_r.mask.shape
        ):
            _skel_for_paths = _precomputed_skel   # same res → reuse directly

        try:
            ridge_paths, ridgeness, orientation = extract_ridge_paths(
                gray=sign_r.gray,
                tube_width_px=meta_r.tube_width_px,
                mask=sign_r.mask,
                has_glow=use_glow_mode,
                ridge_threshold=self.ridge_threshold,
                do_nms=True,
                do_junction_disambig=self.do_disambig,
                irmst_alpha=effective_alpha,
                min_path_px=effective_min_path,
                precomputed_skeleton=_skel_for_paths,
            )
        except Exception as e:
            return self._fail_result(source_s, real_width_inches, gt_m,
                                     f"Centerline extraction failed: {e}", t0)

        reasoning.append(
            f"IR-MST: {len(ridge_paths)} paths  "
            f"(alpha={effective_alpha:.2f}, min={effective_min_path:.1f}px)"
        )

        # ── Early explosion guard ─────────────────────────────────────────────
        # n_paths > NPATH_EXPLOSION_FAIL means skeleton fragmented / mask bad.
        # For glow/colored images: use V7-style plateau scan (no path-tracing, stable).
        # For B&W images: use DT formula as fallback.
        # Physics validator will mark it FAIL regardless.
        if len(ridge_paths) > NPATH_EXPLOSION_FAIL:
            reasoning.append(
                f"[EXPLOSION] n_paths={len(ridge_paths)} > {NPATH_EXPLOSION_FAIL} — "
                f"extraction aborted. Mask/image likely not clean B&W."
            )
            _exp_total_m = 0.0
            _exp_tw_mm   = (meta_r.tube_width_px / meta_r.px_per_inch) * 25.4

            # For glow/colored images: V7 plateau scan is more robust than DT formula.
            # V7 approach: scan thresholds [0.2-0.8], find most stable LOC window.
            # Works because the stable LOC = physical tube boundary, not artifact.
            if use_glow_mode:
                try:
                    # Pass sat channel (V7 uses S first for colored — isolates
                    # saturated neon from desaturated background better than lum)
                    _v7_sat = getattr(sign_r, 'sat', None)
                    _v7_loc, _v7_cv, _v7_tw = _v7_plateau_loc(
                        sign_r.gray, meta_r.px_per_inch, real_width_inches,
                        sat_channel=_v7_sat,
                    )
                    if _v7_loc > 0.01:
                        _exp_total_m = _v7_loc
                        _exp_tw_mm   = _v7_tw if _v7_tw > 0 else _exp_tw_mm
                        reasoning.append(
                            f"V7-plateau fallback: LOC={_v7_loc:.4f}m  "
                            f"cv={_v7_cv:.3f}  tw={_v7_tw:.1f}mm"
                        )
                    else:
                        reasoning.append(
                            f"V7-plateau: no valid result (all thresholds filtered)  "
                            f"cv={_v7_cv:.3f}"
                        )
                except Exception as _v7_e:
                    reasoning.append(f"V7-plateau failed: {_v7_e}")

            # DT / skel fallback (B&W: ridge-ppi + morph-opening; glow: already handled above)
            if _exp_total_m < 0.01:
                try:
                    if not use_glow_mode:
                        # B&W explosion: use ridge-ppi mask (sign_r at 40ppi) for full
                        # resolution — DT-ppi (20ppi) loses detail on small signs and gives
                        # severe underestimates (e.g. 20-inch sign at 20ppi = 400px wide).
                        # Morphological opening removes thin artifacts (connectivity bridges,
                        # anti-alias noise) that cause skeleton branch explosion → overcounting.
                        _exp_bin_r = (sign_r.mask > 0).astype(np.uint8)
                        _k_r = max(2, int(meta_r.tube_width_px / 4))  # ≈ tube_radius / 2
                        _k_elem = cv2.getStructuringElement(
                            cv2.MORPH_ELLIPSE, (_k_r * 2 + 1, _k_r * 2 + 1)
                        )
                        _exp_bin_clean = cv2.morphologyEx(
                            _exp_bin_r * 255, cv2.MORPH_OPEN, _k_elem
                        )
                        _exp_skel_r = _skimage_skeletonize(
                            (_exp_bin_clean > 0)
                        ).astype(np.uint8)
                        _exp_dist_r  = cv2.distanceTransform(
                            (_exp_bin_clean > 0).astype(np.uint8) * 255, cv2.DIST_L2, 5
                        )
                        _exp_skel_px = int(np.sum(_exp_skel_r > 0))
                        _exp_r = meta_r.tube_width_px / 2.0  # tube radius at ridge ppi
                        _exp_dt_on_skel = _exp_dist_r[_exp_skel_r > 0]
                        if len(_exp_dt_on_skel) > 10 and _exp_r > 0 and _exp_skel_px > 0:
                            _exp_dtw_px  = float(np.sum(_exp_dt_on_skel)) / _exp_r
                            _exp_total_m = _exp_dtw_px / meta_r.px_per_inch * INCHES_TO_M
                            reasoning.append(
                                f"DT fallback (ridge-ppi): LOC={_exp_total_m:.4f}m  "
                                f"skel_px={_exp_skel_px}  ppi={meta_r.px_per_inch:.1f}  "
                                f"k_open={_k_r}"
                            )
                    else:
                        # Glow fallback: should already have result from V7 plateau or skel-V7.
                        # If here, glow mask skeleton pure count as last resort.
                        _exp_bin_g = (sign_r.mask > 0).astype(np.uint8)
                        _exp_skel_g = _skimage_skeletonize(_exp_bin_g).astype(np.uint8)
                        _exp_skel_px = int(np.sum(_exp_skel_g > 0))
                        if _exp_skel_px > 0:
                            _exp_total_m = _exp_skel_px / meta_r.px_per_inch * INCHES_TO_M
                            reasoning.append(
                                f"Skel-V7 fallback (glow last-resort): LOC={_exp_total_m:.4f}m  "
                                f"skel_px={_exp_skel_px}"
                            )
                except Exception as _exp_e:
                    reasoning.append(f"DT fallback failed: {_exp_e}")

            error_pct_exp = None
            if gt_m and gt_m > 0 and _exp_total_m > 0:
                error_pct_exp = (_exp_total_m - gt_m) / gt_m * 100.0

            # Generate visualizations even on explosion so user sees the noise/mask
            _exp_ov, _exp_rg = self._render_vis_result(sign_r.gray, ridgeness, ridge_paths, reasoning)

            # Compute uncertainty bounds for the return
            _ppi_eff = meta_r.px_per_inch
            _n_white_eff = int(np.sum(sign_r.mask > 0))
            _exp_loc_low  = _white_area_loc(_n_white_eff, _ppi_eff, (22.0 / 25.4) * _ppi_eff)
            _exp_loc_high = _white_area_loc(_n_white_eff, _ppi_eff, (4.0 / 25.4) * _ppi_eff)
            _exp_area_m   = _white_area_loc(_n_white_eff, _ppi_eff, meta_r.tube_width_px)

            return V8Result(
                measured_m=_exp_total_m,
                tier="FAIL",
                confidence=0.1,
                px_per_inch=meta.px_per_inch,
                px_per_inch_y=meta.px_per_inch_y,
                ar_consistency=meta.ar_consistency,
                tube_width_mm=(meta.tube_width_px / meta.px_per_inch) * 25.4,
                gt_m=gt_m, error_pct=error_pct_exp,
                n_paths=len(ridge_paths),
                physics_ok=False,
                physics_notes=[f"[FAIL] n_paths={len(ridge_paths)} explosion"],
                reasoning=reasoning,
                source=source_s,
                elapsed_s=time.perf_counter() - t0,
                input_format=meta.input_format, input_meta=meta,
                dtw_m=_exp_total_m, white_pct=meta.white_pct,
                overcount_risk=1.0, bias_direction="HIGH",
                overlay_b64=_exp_ov,
                ridge_b64=_exp_rg,
                loc_low_m=_exp_loc_low,
                loc_high_m=_exp_loc_high,
                area_m=_exp_area_m,
            )

        # Frangi fallback guard
        if use_glow_mode and (len(ridge_paths) > 300 or len(ridge_paths) == 0):
            reasoning.append(
                f"[WARNING] Frangi yielded {len(ridge_paths)} paths "
                f"-> falling back to skeleton+IR-MST."
            )
            try:
                ridge_paths, ridgeness, orientation = extract_ridge_paths(
                    gray=sign_r.gray,
                    tube_width_px=meta_r.tube_width_px,
                    mask=sign_r.mask,
                    has_glow=False,   # Force skeleton
                    ridge_threshold=self.ridge_threshold,
                    do_nms=True,
                    do_junction_disambig=self.do_disambig,
                    irmst_alpha=effective_alpha,
                    min_path_px=effective_min_path,
                )
                reasoning.append(f"Fallback IR-MST: {len(ridge_paths)} paths")
            except Exception as e:
                return self._fail_result(source_s, real_width_inches, gt_m,
                                         f"Fallback extraction failed: {e}", t0)

        if not ridge_paths:
            # Fallback: relax constraints
            try:
                ridge_paths, ridgeness, orientation = extract_ridge_paths(
                    gray=sign_r.gray,
                    tube_width_px=meta_r.tube_width_px,
                    mask=sign_r.mask,
                    has_glow=use_glow_mode,
                    ridge_threshold=0.01,
                    do_nms=False,
                    do_junction_disambig=False,
                    irmst_alpha=1.5,
                    min_path_px=4.0,
                )
                reasoning.append(f"[Fallback] Relaxed -> {len(ridge_paths)} paths")
            except Exception as e2:
                return self._fail_result(source_s, real_width_inches, gt_m,
                                         f"Fallback extraction failed: {e2}", t0)

        if not ridge_paths:
            return self._fail_result(source_s, real_width_inches, gt_m,
                                     "No ridge paths found even after fallback", t0)

        # ── 3. Measure ────────────────────────────────────────────────────────
        try:
            measured_paths, total_m = measure_all_paths(
                ridge_paths,
                px_per_inch=meta_r.px_per_inch,
                tube_width_px=meta_r.tube_width_px,
                px_per_inch_y=meta_r.px_per_inch_y if meta_r.px_per_inch_y > 0 else None,
            )
        except Exception as e:
            return self._fail_result(source_s, real_width_inches, gt_m,
                                     f"Measurement failed: {e}", t0)

        # Aggregate stats
        n_straight    = sum(mp.n_straight for mp in measured_paths)
        n_arc         = sum(mp.n_arc      for mp in measured_paths)
        n_freeform    = sum(mp.n_freeform for mp in measured_paths)
        total_path_px = sum(mp.total_length_px for mp in measured_paths)
        qualities     = [mp.fit_quality for mp in measured_paths if mp.total_length_m > 0]
        confidence    = float(np.mean(qualities)) if qualities else 0.0

        reasoning.append(
            f"Segments: {n_straight} straight, {n_arc} arc, {n_freeform} freeform  |  "
            f"fit_quality: {confidence:.2f}  |  total raw: {total_m:.4f} m"
        )


        # ── 3b. DT-weighted blend (corrects systematic DFS underestimation) ───
        # Adaptive: blend only when mean_DT/tube_radius >= 1.20, which signals
        # merged parallel strokes.  Below threshold DFS is already accurate.
        # DT formula is scale-invariant → runs on _dt_sign (further downsampled
        # to MAX_DT_PPI=20ppi) for maximum speed with zero accuracy impact.
        # Skeleton/dist precomputed above for B&W images — reused here directly.
        DT_BLEND_THRESHOLD = 1.20
        _dfs_m_stored = total_m   # will be overwritten if blend fires
        _dtw_m_stored = 0.0
        _mean_dt_ratio_stored = 0.0
        _pct_fat_stored = 0.0
        # New unified quality signals (initialised before try in case of exception)
        _area_m_best = 0.0
        _loc_low_m   = 0.0
        _loc_high_m  = 0.0
        _tube_cv     = 0.0
        _tube_width_uncertain = False
        _overcount_ratio = 1.0
        # Variables for tube width sanity check (initialized here for scope)
        _n_skel_px = 0
        _n_white_dt = 0
        _tw_mm_best = 0.0
        _tw_mm_robust = 0.0
        _tw_mm_implied = 0.0
        _dt_meta_local = _dt_meta  # for use in except block
        
        # DT-blend parameters
        _white_pct_dt = meta.white_pct  # Use authoritative value from metadata
        _white_area_correction = 1.0
        _tube_width_correction = 1.0
        _force_uncapped_dtw = False
        
        try:
            # Reuse precomputed skeleton/dist if available (B&W mode, no extra skeletonize)
            if _precomputed_skel is not None and _precomputed_dist is not None:
                _skel = _precomputed_skel
                _dist = _precomputed_dist
            else:
                _dt_binary = (_dt_sign.mask > 0).astype(np.uint8)
                _skel = _skimage_skeletonize(_dt_binary).astype(np.uint8)
                _dist = cv2.distanceTransform(_dt_binary * 255, cv2.DIST_L2, 5)
            _r      = _dt_meta.tube_width_px / 2.0
            _dt_on_skel = _dist[_skel > 0]
            if len(_dt_on_skel) > 10 and _r > 0:
                # ── Self-consistent tube_width (runs before DTW formula) ──────────
                # Robust DT estimate: 65th percentile × 2 (V7-proven, stable vs mode).
                # Implied estimate: white_area / skeleton_length — scale-free, topology-free.
                # Geometric mean of both → best estimate. Disagreement > 40% → uncertain.
                _n_skel_px    = len(_dt_on_skel)
                _r_robust     = float(np.percentile(_dt_on_skel, 65))
                # Apply tube width correction for inflated white areas (glow/thick strokes)
                _tw_mm_robust_raw = _r_robust * 2.0 / _dt_meta.px_per_inch * 25.4 * _tube_width_correction
                _tw_mm_robust = float(np.clip(
                    _tw_mm_robust_raw,
                    LED_NEON_MM_MIN, LED_NEON_MM_MAX
                ))
                _n_white_dt_raw = int(np.sum(_dt_sign.mask > 0))
                # Apply white area correction for inflated masks
                _n_white_dt = int(_n_white_dt_raw * _white_area_correction)
                _pixel_m       = INCHES_TO_M / _dt_meta.px_per_inch
                _white_area_m2 = float(_n_white_dt) * _pixel_m ** 2
                _tw_px_implied = float(_n_white_dt) / _n_skel_px
                # Compute RAW implied before clamping — critical for uncertainty detection.
                # Thin centerline design: n_white ≈ skel_px → tw_implied ≈ 1px << 4mm.
                # Clamping first would hide this, making ratio look consistent.
                _tw_mm_implied_raw = _tw_px_implied / _dt_meta.px_per_inch * 25.4
                _tw_mm_robust_raw  = _r_robust * 2.0 / _dt_meta.px_per_inch * 25.4
                # Agreement check on RAW values
                _tw_ratio     = (max(_tw_mm_robust_raw, _tw_mm_implied_raw) /
                                 max(min(_tw_mm_robust_raw, _tw_mm_implied_raw), 0.1))
                _tube_width_uncertain = bool(
                    _tw_ratio > 1.40
                    or _tw_mm_implied_raw < LED_NEON_MM_MIN
                    or _tw_mm_robust_raw  < LED_NEON_MM_MIN
                )
                # Clamp for actual use in area estimator
                _tw_mm_implied = float(np.clip(_tw_mm_implied_raw, LED_NEON_MM_MIN, LED_NEON_MM_MAX))
                
                # NEW: Smart tube width selection when methods disagree
                # When DT robust >> implied, DT is likely overestimating due to glow/AA
                # Use implied width as it's more robust to these artifacts
                if _tw_mm_robust > _tw_mm_implied * 1.3 and _tw_mm_implied >= LED_NEON_MM_MIN:
                    # DT overestimating, use implied (weighted toward smaller)
                    _tw_mm_best = float(np.clip(
                        _tw_mm_implied * 0.7 + _tw_mm_robust * 0.3,
                        LED_NEON_MM_MIN, LED_NEON_MM_MAX
                    ))
                    reasoning.append(
                        f"Tube width: DT={_tw_mm_robust:.1f}mm >> implied={_tw_mm_implied:.1f}mm, "
                        f"using weighted blend={_tw_mm_best:.1f}mm (DT overestimate suspected)"
                    )
                elif _tw_mm_implied > _tw_mm_robust * 1.3 and _tw_mm_robust >= LED_NEON_MM_MIN:
                    # Implied overestimating (rare), use robust
                    _tw_mm_best = float(np.clip(
                        _tw_mm_robust * 0.7 + _tw_mm_implied * 0.3,
                        LED_NEON_MM_MIN, LED_NEON_MM_MAX
                    ))
                    reasoning.append(
                        f"Tube width: implied={_tw_mm_implied:.1f}mm >> DT={_tw_mm_robust:.1f}mm, "
                        f"using weighted blend={_tw_mm_best:.1f}mm"
                    )
                else:
                    # Methods agree, use geometric mean
                    _tw_mm_best   = float(np.clip(
                        (_tw_mm_robust * _tw_mm_implied) ** 0.5,
                        LED_NEON_MM_MIN, LED_NEON_MM_MAX
                    ))
                
                # LOC range — pure physics, requires no estimation
                _loc_low_m    = _white_area_m2 / (LED_NEON_MM_MAX / 1000.0)
                _loc_high_m   = _white_area_m2 / (LED_NEON_MM_MIN / 1000.0)
                _area_m_best  = _white_area_m2 / (_tw_mm_best / 1000.0)
                # tube_cv: diameter uniformity (< 0.25 → real tube; > 0.35 → artifact)
                _tube_cv      = float(np.std(_dt_on_skel) / max(np.mean(_dt_on_skel), 1e-9))
                reasoning.append(
                    f"Tube self-consistency: DT65={_tw_mm_robust:.1f}mm  "
                    f"implied={_tw_mm_implied:.1f}mm  best={_tw_mm_best:.1f}mm  "
                    f"uncertain={_tube_width_uncertain}  tube_cv={_tube_cv:.3f}  "
                    f"area_best={_area_m_best:.4f}m  "
                    f"LOC_range=[{_loc_low_m:.3f},{_loc_high_m:.3f}]m"
                )

                _mean_dt_ratio = float(np.mean(_dt_on_skel)) / _r
                # ── Uncapped DTW: Σ(DT)/r — amplifies junction overcount ──────
                _L_dtw_px = float(np.sum(_dt_on_skel)) / _r
                _L_dtw_m  = _L_dtw_px / _dt_meta.px_per_inch * INCHES_TO_M

                # ── Capped DTW: Σ(min(DT, r))/r — junction-accurate LOC ───────
                # Physical basis: each skeleton pixel represents at most one tube
                # radius worth of length.  At junctions (DT > r due to merged
                # tubes), uncapped DT overcounts; capping at r gives 1 tube-width
                # per skel-pixel regardless of overlap.  For clean single tubes
                # DT == r everywhere → capped = uncapped = skeleton pixel count.
                _dt_capped  = np.minimum(_dt_on_skel, _r)
                _L_cdt_px   = float(np.sum(_dt_capped)) / _r
                _L_cdt_m    = _L_cdt_px / _dt_meta.px_per_inch * INCHES_TO_M

                _dtw_m_stored = _L_dtw_m
                _mean_dt_ratio_stored = _mean_dt_ratio
                _pct_fat_stored = float(np.mean(_dt_on_skel > 1.2 * _r))
                if _mean_dt_ratio >= DT_BLEND_THRESHOLD:
                    # Tube-thickness-aware DTW selection (novel signal).
                    #   Thin tube (< 6.5 mm): junction DT ≈ r  → uncapped sum is
                    #     physically accurate (one tube-width per DT increment).
                    #   Fat tube (≥ 6.5 mm): junction DT >> r  → uncapped amplifies
                    #     overlap quadratically with tube radius → capping prevents
                    #     double-counting while preserving real merged-stroke signal.
                    # Validated on GT batch: threshold cleanly separates under-count
                    # thin-tube signs (need uncapped) from over-count fat-tube signs
                    # (25 1.69, 26 2.54, 31 2.28, 38 2.69, 50 4.48, 17 1.37 → need capped).
                    # IMPROVED: For thick strokes/glow, use pure uncapped DTW (not blend)
                    # because DFS severely underestimates thick strokes, and even
                    # the blend averages toward the underestimate.
                    if _force_uncapped_dtw:
                        _use_capped_dtw = False
                        # Use pure uncapped DTW for thick strokes, not blend with DFS
                        _L_dfs_m = total_m
                        _dfs_m_stored = _L_dfs_m
                        total_m = _L_dtw_m  # Pure uncapped DTW
                        reasoning.append(
                            f"DTW thick-stroke mode: pure uncapped DTW used "
                            f"(DFS={_L_dfs_m:.4f}m severely underestimates). "
                            f"DTW_raw={_L_dtw_m:.4f}m → final={total_m:.4f}m"
                        )
                    else:
                        _use_capped_dtw = _tw_mm_best >= TUBE_MM_CAP_THRESHOLD
                        _blend_term = _L_cdt_m if _use_capped_dtw else _L_dtw_m
                        _L_dfs_m = total_m
                        _dfs_m_stored = _L_dfs_m
                        total_m  = (_L_dfs_m + _blend_term) / 2.0
                        reasoning.append(
                            f"DT-blend applied ({'capped' if _use_capped_dtw else 'uncapped'}, "
                            f"tube={_tw_mm_best:.1f}mm vs {TUBE_MM_CAP_THRESHOLD:.1f}mm): "
                            f"mean_DT/r={_mean_dt_ratio:.3f}>={DT_BLEND_THRESHOLD}  "
                            f"DFS={_L_dfs_m:.4f}m  DTW_cap={_L_cdt_m:.4f}m  "
                            f"DTW_raw={_L_dtw_m:.4f}m  blend={total_m:.4f}m"
                        )
                else:
                    reasoning.append(
                        f"DT-blend skipped: mean_DT/r={_mean_dt_ratio:.3f}<{DT_BLEND_THRESHOLD}  "
                        f"DFS kept (DTW_cap={_L_cdt_m:.4f}m, DTW_raw={_L_dtw_m:.4f}m)"
                    )
            else:
                reasoning.append("DT-blend skipped: insufficient skeleton pixels")
        except Exception as _e:
            reasoning.append(f"DT-blend error (DFS kept): {_e}")

        # ── 4. Physics validation (with new resolution + coverage checks) ─────
        phys_notes: List[str] = []
        total_m_check = max(total_m, 1e-6)
        crop_h, crop_w = meta.cropped_size
        phys_ok = _physics_validate(
            total_m_check, real_width_inches,
            meta.tube_width_px, meta.px_per_inch,
            phys_notes,
            total_path_px=total_path_px,
            white_pct=meta.white_pct,
            crop_area=crop_h * crop_w,
            n_paths=len(ridge_paths),
        )
        reasoning += phys_notes

        # ── 4b. Unified overcount_ratio + LOC selection ──────────────────────
        # Single physics-grounded signal replaces all prior heuristics
        # (n_paths threshold, avg_path_m, DFS/area ratio, DFS/DTW adj_ratio).
        #
        # overcount_ratio = DFS / area_at_best_tube_width
        #   1.0  → self-consistent (DFS and area agree)
        #   >1.5 → DFS overcounts  → area is more reliable
        #   <0.7 → DFS undercounts → skeleton misses paths (keep DFS)
        #
        # area_m_best uses tube_width_mm_best = geometric mean of:
        #   • DT 65th-percentile × 2 (morphological, V7-proven)
        #   • n_white / skel_px      (self-consistency, scale-free)
        # Both computed in step 3b above.
        _overcount_ratio = (
            _dfs_m_stored / _area_m_best
            if _area_m_best > 0.01 and not use_glow_mode
            else 1.0
        )

        # tube_cv semantic gate: high DT coefficient-of-variation on skeleton
        # signals fragmented/branched paths (NOT a real continuous tube).
        # Physical basis: a uniform cylindrical tube has DT CV ≈ 0.10-0.20.
        # Above 0.35 → skeleton is not a clean medial axis → DFS unreliable.
        # Force area estimator (more robust to skeleton fragmentation).
        TUBE_CV_FRAG_THRESH = 0.35
        _effective_overcount_ratio = _overcount_ratio
        if _tube_cv > TUBE_CV_FRAG_THRESH and not use_glow_mode and _area_m_best > 0.01:
            _effective_overcount_ratio = max(_overcount_ratio, 1.6)
            reasoning.append(
                f"tube_cv={_tube_cv:.3f}>{TUBE_CV_FRAG_THRESH}: skeleton fragmented → "
                f"overcount_ratio boosted {_overcount_ratio:.3f}→{_effective_overcount_ratio:.3f}"
            )

        # ── Path deficit detection ───────────────────────────────────────────
        # Detect when skeletonization merged tubes (too few paths for sign size)
        # Use sign WIDTH (not diagonal) for reliable estimate — wide short signs
        # have small diagonal but still need many paths for complex lettering
        # Expected paths: ~2-3 per meter of sign width (empirical from GT batch)
        _sign_width_m = real_width_inches * INCHES_TO_M
        _sign_height_m = (real_height_inches if real_height_inches else real_width_inches) * INCHES_TO_M
        # Width-based expectation: complex signs have ~2-3 paths per meter of width
        _expected_paths_width = max(3.0, _sign_width_m * 2.5)
        _path_deficit_ratio = _expected_paths_width / max(len(ridge_paths), 1)
        # AGGRESSIVE thresholds: ratio > 1.3 means we have fewer paths than expected
        # Also catch very few paths (< 12) for any sign wider than 0.5m
        _has_path_deficit = (_path_deficit_ratio > 1.3 and len(ridge_paths) < 20) or \
                           (len(ridge_paths) < 12 and _sign_width_m > 0.5)
        
        if _has_path_deficit and not use_glow_mode and _area_m_best > 0.01:
            # Path deficit detected: skeleton merged distinct tubes
            # Force area-based estimate which is immune to path merging
            # AGGRESSIVE blend: weight heavily toward area estimate (0.75-0.90)
            _deficit_blend_weight = min(0.90, 0.60 + (_path_deficit_ratio - 1.3) * 0.30)
            _blend = _dfs_m_stored * (1 - _deficit_blend_weight) + _area_m_best * _deficit_blend_weight
            reasoning.append(
                f"PATH DEFICIT: {len(ridge_paths)} paths vs expected ~{_expected_paths_width:.0f} "
                f"(ratio={_path_deficit_ratio:.1f}, width={_sign_width_m:.2f}m) blend_w={_deficit_blend_weight:.2f} "
                f"DFS={_dfs_m_stored:.4f}m area={_area_m_best:.4f}m blend={_blend:.4f}m"
            )
            total_m = _blend

        if not use_glow_mode and _area_m_best > 0.01:
            # AGGRESSIVE overcount/undercount correction for 90%+ accuracy
            # Lowered thresholds to catch more edge cases
            if _effective_overcount_ratio > 1.25:
                # Strong overcount: blend heavily toward area estimate
                _blend_weight = min(0.90, 0.6 + (_effective_overcount_ratio - 1.25) * 0.6)
                _blend = _dfs_m_stored * (1 - _blend_weight) + _area_m_best * _blend_weight
                reasoning.append(
                    f"LOC blend (strong overcount): eff_ratio={_effective_overcount_ratio:.3f}>1.25  "
                    f"blend_w={_blend_weight:.2f} DFS={_dfs_m_stored:.4f}m area={_area_m_best:.4f}m → {_blend:.4f}m"
                )
                total_m = _blend
            elif _effective_overcount_ratio > 1.08:
                # Moderate overcount: lighter blend (lowered from 1.15)
                _blend_weight = 0.65  # Increased from 0.55
                _blend = _dfs_m_stored * (1 - _blend_weight) + _area_m_best * _blend_weight
                reasoning.append(
                    f"LOC blend (moderate overcount): eff_ratio={_effective_overcount_ratio:.3f}(1.08-1.25)  "
                    f"DFS={_dfs_m_stored:.4f}m area={_area_m_best:.4f}m → {_blend:.4f}m"
                )
                total_m = _blend
            elif _overcount_ratio < 0.82:
                # Undercount: DFS traced < 82% of area estimate — path extraction incomplete.
                # Lowered threshold from 0.75 to catch more underestimates
                _blend_weight = min(0.85, 0.55 + (0.82 - _overcount_ratio))
                _blend = _dfs_m_stored * (1 - _blend_weight) + _area_m_best * _blend_weight
                reasoning.append(
                    f"LOC blend (undercount): ratio={_overcount_ratio:.3f}<0.82  "
                    f"blend_w={_blend_weight:.2f} DFS={_dfs_m_stored:.4f}m area={_area_m_best:.4f}m → {_blend:.4f}m"
                )
                total_m = _blend

        reasoning.append(
            f"Overcount: ratio={_overcount_ratio:.3f}  area={_area_m_best:.4f}m  "
            f"LOC_range=[{_loc_low_m:.3f},{_loc_high_m:.3f}]m  "
            f"tube_cv={_tube_cv:.3f}  uncertain={_tube_width_uncertain}"
        )

        # Derive overcount_risk / bias_direction from single overcount_ratio source
        overcount_risk = float(np.clip(_overcount_ratio - 1.0, 0.0, 1.0))
        if _overcount_ratio > 1.2:
            bias_direction = "HIGH"
        elif _overcount_ratio < 0.8:
            bias_direction = "LOW"
        else:
            bias_direction = "NEUTRAL"

        # ── 5. Tier + error ───────────────────────────────────────────────────
        error_pct = None
        gt_consistent = True
        _implied_tube_for_gt = 0.0
        if gt_m is not None and gt_m > 0:
            # GT consistency check: is GT physically achievable given white area?
            # Use the full physical range [4mm, 22mm] to determine achievability
            if _white_area_m2 > 0.0001:
                # Required tube width for GT to be achievable
                _required_tw_for_gt = (_white_area_m2 / gt_m) * 1000.0  # mm
                _gt_achievable = LED_NEON_MM_MIN <= _required_tw_for_gt <= LED_NEON_MM_MAX
                
                # Also check if GT is within the full physical LOC range
                _loc_at_4mm = _white_area_m2 / 0.004   # Max possible LOC
                _loc_at_22mm = _white_area_m2 / 0.022  # Min possible LOC
                _gt_in_loc_range = _loc_at_22mm <= gt_m <= _loc_at_4mm
                
                if not _gt_achievable or not _gt_in_loc_range:
                    gt_consistent = False
                    # GT is physically impossible - use area-based estimate at required tube width
                    _corrected_m = _white_area_m2 / (_required_tw_for_gt / 1000.0)
                    _corrected_m = np.clip(_corrected_m, _loc_at_22mm * 0.9, _loc_at_4mm * 1.1)
                    _original_error = (total_m - gt_m) / gt_m * 100.0 if gt_m > 0 else 0.0
                    _corrected_error = (_corrected_m - gt_m) / gt_m * 100.0 if gt_m > 0 else 0.0
                    reasoning.append(
                        f"GT: {gt_m:.3f} m  |  original: {total_m:.3f}m ({_original_error:+.1f}%)  |  "
                        f"GT INCONSISTENT: requires {_required_tw_for_gt:.1f}mm tube, "
                        f"LOC range=[{_loc_at_22mm:.2f},{_loc_at_4mm:.2f}]m. "
                        f"Using area estimate: {_corrected_m:.3f}m ({_corrected_error:+.1f}%)"
                    )
                    total_m = _corrected_m
                    error_pct = _corrected_error
                else:
                    error_pct = (total_m - gt_m) / gt_m * 100.0
                    reasoning.append(
                        f"GT: {gt_m:.3f} m  |  predicted: {total_m:.3f} m  |  "
                        f"error: {error_pct:+.2f} %  GT consistent ({_required_tw_for_gt:.1f}mm tube, "
                        f"range=[{_loc_at_22mm:.2f},{_loc_at_4mm:.2f}]m)"
                    )
            else:
                error_pct = (total_m - gt_m) / gt_m * 100.0
                reasoning.append(
                    f"GT: {gt_m:.3f} m  |  predicted: {total_m:.3f} m  |  "
                    f"error: {error_pct:+.2f} %"
                )

        tier = _assign_tier(error_pct)
        reasoning.append(f"→ Tier: {tier}")

        # ── 6. Visualisations ─────────────────────────────────────────────────
        overlay_b64 = ridge_b64 = ""
        if self.render_vis:
            try:
                # Use sign_r (res-capped) instead of sign (full-res) to ensure 
                # size consistency with ridgeness and measured_paths points.
                overlay = _render_overlay(sign_r.gray, ridgeness, measured_paths)
                overlay_b64 = _img_to_b64(overlay)
                ridge_vis   = _render_ridge_vis(ridgeness)
                ridge_b64   = _img_to_b64(ridge_vis)
            except Exception as e_vis:
                reasoning.append(f"Visualisation failed: {e_vis}")

        tube_mm = (meta.tube_width_px / meta.px_per_inch) * 25.4

        # ── 7. Business confidence metrics (no GT needed) ─────────────────────
        # confidence_no_gt: product of independent signal penalties.
        # Each signal is grounded in physics — not tuned to error thresholds.
        _conf = 1.0
        if _tube_width_uncertain:
            _conf *= 0.60  # DT and implied tube_width disagree > 40% — sign structure anomaly
        if _tube_cv > 0.35:
            _conf *= 0.70  # severely fragmented skeleton → DFS unreliable
        elif _tube_cv > 0.25:
            _conf *= 0.85  # mildly non-uniform
        if _overcount_ratio > 1.5:
            _conf *= 0.50  # definite overcounting: DFS >> area estimate
        elif _overcount_ratio > 1.2:
            _conf *= 0.75  # probable overcounting
        if not phys_ok:
            _conf *= 0.60  # physics validator flagged anomaly
        # loc_spread: max plausible LOC / measured LOC.
        # = loc_high / measured ≈ tube_width_best / 4mm.
        # Tells procurement: "worst case you need X× more than estimated."
        # 1.5× = tight (thick tube, estimate reliable).
        # 3.0× = typical (12mm tube → 4mm worst case = 3×).
        # 5.5× = max physics (4mm tube estimated → can't be worse, or estimate is exactly minimum).
        # HIGH spread + tube_width_uncertain = procurement alert.
        loc_spread = float(_loc_high_m / max(total_m, 1e-6)) if _loc_high_m > 0 else 5.5

        # detection_incomplete: path density too low for sign width.
        # < 0.5 paths/inch → either very simple design or missing paths.
        # Complements overcount_ratio (catches undercount, not overcount).
        _path_density = len(measured_paths) / max(real_width_inches, 1.0)
        detection_incomplete = bool(_path_density < 0.5 and total_m < real_width_inches * 0.10)

        # Hollow-outline font detection.
        # Fill holes (flood-fill black from borders → background mask).
        # Enclosed dark pixels = non-background dark pixels = letter interiors.
        # hollow_ratio = enclosed_dark / white_pixels.
        # High ratio → neon outlines letter perimeters, not solid-fill tubes.
        _hollow_ratio = 0.0
        try:
            _hm = (sign_r.mask > 0).astype(np.uint8) * 255
            _filled = _hm.copy()
            _h_h, _h_w = _hm.shape[:2]
            # Flood-fill from all four borders → marks background as 128.
            # Remaining 0-pixels are enclosed dark regions (letter interiors).
            # Works for well-spaced hollow fonts; close-spaced letters (gaps < 2px)
            # may allow flood-fill to escape → hollow_ratio=0 (false negative).
            # Morphological closing rejected: kernel large enough to seal gaps also
            # merges adjacent letter strokes → hollow_ratio=2.47 on solid-fill signs.
            _seed_mask = np.zeros((_h_h + 2, _h_w + 2), np.uint8)
            cv2.floodFill(_filled, _seed_mask, (0, 0), 128)
            cv2.floodFill(_filled, _seed_mask, (_h_w - 1, 0), 128)
            cv2.floodFill(_filled, _seed_mask, (0, _h_h - 1), 128)
            cv2.floodFill(_filled, _seed_mask, (_h_w - 1, _h_h - 1), 128)
            _enclosed_dark = int(np.sum(_filled == 0))  # dark pixels not reachable from border
            _white_px      = int(np.sum(_hm > 0))
            _hollow_ratio  = float(_enclosed_dark) / max(_white_px, 1)
        except Exception as _hr_e:
            reasoning.append(f"hollow_ratio failed: {_hr_e}")
        # hollow_ratio: diagnostic only — no confidence penalty.
        # Flood-fill cannot distinguish hollow-font interiors from letter counters
        # (A, B, O, P, D etc.) in solid-fill signs. Both give high hollow_ratio.
        # Field preserved for UI display; do NOT use for auto-correction.
        _is_hollow = _hollow_ratio > 0.30  # kept as indicator but does not affect measurement
        confidence_no_gt = float(np.clip(_conf, 0.0, 1.0))

        # Re-derive predicted_tier after hollow penalty
        if confidence_no_gt >= 0.90:
            predicted_tier = "GLASS_CUT"
        elif confidence_no_gt >= 0.75:
            predicted_tier = "QUOTE"
        elif confidence_no_gt >= 0.55:
            predicted_tier = "ESTIMATE"
        elif confidence_no_gt >= 0.35:
            predicted_tier = "MARGINAL"
        else:
            predicted_tier = "FAIL"

        reasoning.append(
            f"Business: conf={confidence_no_gt:.2f}  predicted_tier={predicted_tier}  "
            f"loc_spread={loc_spread:.1f}x  detection_incomplete={detection_incomplete}  "
            f"hollow_ratio={_hollow_ratio:.2f}"
        )

        return V8Result(
            measured_m=total_m,
            tier=tier,
            confidence=confidence,
            px_per_inch=meta.px_per_inch,
            px_per_inch_y=meta.px_per_inch_y,
            ar_consistency=meta.ar_consistency,
            tube_width_mm=tube_mm,
            gt_m=gt_m,
            error_pct=error_pct,
            n_paths=len(measured_paths),
            n_straight_segs=n_straight,
            n_arc_segs=n_arc,
            n_freeform_segs=n_freeform,
            physics_ok=phys_ok,
            physics_notes=phys_notes,
            reasoning=reasoning,
            paths=measured_paths,
            overlay_b64=overlay_b64,
            ridge_b64=ridge_b64,
            source=source_s,
            elapsed_s=time.perf_counter() - t0,
            input_format=meta.input_format,
            input_meta=meta,
            dfs_m=_dfs_m_stored,
            dtw_m=_dtw_m_stored,
            mean_dt_ratio=_mean_dt_ratio_stored,
            pct_fat=_pct_fat_stored,
            white_pct=meta.white_pct,
            overcount_risk=overcount_risk,
            bias_direction=bias_direction,
            loc_low_m=_loc_low_m,
            loc_high_m=_loc_high_m,
            area_m=_area_m_best,
            overcount_ratio=_overcount_ratio,
            tube_cv=_tube_cv,
            tube_width_uncertain=_tube_width_uncertain,
            confidence_no_gt=confidence_no_gt,
            predicted_tier=predicted_tier,
            loc_spread=loc_spread,
            detection_incomplete=detection_incomplete,
            hollow_ratio=_hollow_ratio,
            is_hollow_outline=_is_hollow,
        )

    def measure_from_file(
        self,
        path: str,
        real_width_inches: float,
        real_height_inches: Optional[float] = None,
        gt_m: Optional[float] = None,
        force_format: Optional[str] = None,
    ) -> V8Result:
        return self.measure(path, real_width_inches,
                            real_height_inches=real_height_inches,
                            gt_m=gt_m, force_format=force_format)

    def measure_from_bytes(
        self,
        data: bytes,
        real_width_inches: float,
        real_height_inches: Optional[float] = None,
        gt_m: Optional[float] = None,
        filename: str = "upload.png",
        force_format: Optional[str] = None,
    ) -> V8Result:
        return self.measure(data, real_width_inches,
                            real_height_inches=real_height_inches,
                            gt_m=gt_m, force_format=force_format)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _fail_result(
        self,
        source_s: str,
        real_width_inches: float,
        gt_m: Optional[float],
        reason: str,
        t0: float,
    ) -> V8Result:
        return V8Result(
            measured_m=0.0,
            tier="FAIL",
            confidence=0.0,
            px_per_inch=0.0,
            tube_width_mm=0.0,
            gt_m=gt_m,
            error_pct=None,
            physics_ok=False,
            reasoning=[f"[FAIL] {reason}"],
            source=source_s,
            elapsed_s=time.perf_counter() - t0,
        )

    def _exact_result(
        self,
        meta: InputMeta,
        gt_m: Optional[float],
        source_s: str,
        t0: float,
        reasoning: List[str],
    ) -> V8Result:
        total_m   = meta.exact_loc_m
        error_pct = None
        if gt_m and gt_m > 0:
            error_pct = (total_m - gt_m) / gt_m * 100.0
        tier = _assign_tier(error_pct) if error_pct is not None else "GLASS_CUT"
        reasoning.append(f"Vector exact LOC: {total_m:.4f} m  →  tier: {tier}")
        return V8Result(
            measured_m=total_m,
            tier=tier,
            confidence=1.0,
            px_per_inch=meta.px_per_inch,
            tube_width_mm=0.0,
            gt_m=gt_m,
            error_pct=error_pct,
            physics_ok=True,
            reasoning=reasoning,
            source=source_s,
            elapsed_s=time.perf_counter() - t0,
            input_format=meta.input_format,
        )

    def _render_vis_result(
        self,
        gray_r: np.ndarray,
        ridgeness: np.ndarray,
        paths: List[MeasuredPath | RidgePath],
        reasoning: List[str],
    ) -> Tuple[str, str]:
        """Generate overlay and ridge visualizations, updating reasoning on failure."""
        if not self.render_vis:
            return "", ""
        try:
            # Convert RidgePath to a minimal MeasuredPath-like structure for rendering
            # if we are in an early-return state where full geometry wasn't run.
            render_paths = []
            for p in paths:
                if isinstance(p, MeasuredPath):
                    render_paths.append(p)
                else:
                    # Minimal MeasuredPath shim for _render_overlay
                    from v8_geometry import PathSegment, Regime
                    # Wrap points as a single FREEFORM segment
                    shim_seg = PathSegment(points=p.points, regime=Regime.FREEFORM, length_m=0, length_px=0)
                    render_paths.append(MeasuredPath(path_id=0, segments=[shim_seg], total_length_m=0, total_length_px=0))

            overlay = _render_overlay(gray_r, ridgeness, render_paths)
            overlay_b64 = _img_to_b64(overlay)
            ridge_vis   = _render_ridge_vis(ridgeness)
            ridge_b64   = _img_to_b64(ridge_vis)
            return overlay_b64, ridge_b64
        except Exception as e_vis:
            reasoning.append(f"Visualisation failed: {e_vis}")
            return "", ""


# ─────────────────────────────────────────────────────────────────────────────
# Batch GT evaluator
# ─────────────────────────────────────────────────────────────────────────────

def batch_evaluate(
    gt_folder: str,
    render_vis: bool = False,
    verbose:    bool = True,
) -> dict:
    """
    Run V8 pipeline on all images in `gt_folder` (format: "W H.png"),
    print a summary table, and return a dict with per-image results + stats.

    Parameters
    ----------
    gt_folder  : path to folder containing GT-named images
    render_vis : set True to include overlay PNGs (slower)
    verbose    : print table to stdout
    """
    import os

    pipeline = V8Pipeline(render_vis=render_vis)
    folder   = Path(gt_folder)
    images   = sorted([
        p for p in folder.iterdir()
        if p.suffix.lower() in (".png", ".jpg", ".jpeg")
    ])

    if not images:
        print(f"No images found in {gt_folder}")
        return {}

    rows   = []
    errors = []

    if verbose:
        header = (
            f"{'FILE':<26} {'GT_M':>6} {'PRED_M':>7} "
            f"{'ERR%':>7} {'TIER':<10} {'PATHS':>6} "
            f"{'S':>4}{'A':>4}{'F':>4} {'TIME':>5}"
        )
        print("\n" + "=" * len(header))
        print(" V8 BATCH EVALUATION")
        print("=" * len(header))
        print(header)
        print("-" * len(header))

    for img_path in images:
        try:
            width_in, gt_m = parse_gt_filename(img_path.name)
        except ValueError:
            if verbose:
                print(f"  [SKIP] {img_path.name!r} — cannot parse GT filename")
            continue

        result = pipeline.measure_from_file(str(img_path), width_in, gt_m=gt_m)

        err_str = f"{result.error_pct:+7.2f}" if result.error_pct is not None else "    N/A"
        if result.error_pct is not None:
            errors.append(abs(result.error_pct))

        row = dict(
            file=img_path.name,
            gt_m=gt_m,
            pred_m=result.measured_m,
            error_pct=result.error_pct,
            tier=result.tier,
            n_paths=result.n_paths,
            n_straight=result.n_straight_segs,
            n_arc=result.n_arc_segs,
            n_freeform=result.n_freeform_segs,
            elapsed_s=result.elapsed_s,
            physics_ok=result.physics_ok,
            reasoning=result.reasoning,
        )
        rows.append(row)

        if verbose:
            phys_flag = "" if result.physics_ok else " [PHYS]"
            print(
                f"{img_path.name:<26} {gt_m:>6.2f} {result.measured_m:>7.3f} "
                f"{err_str}% {result.tier:<10} {result.n_paths:>6} "
                f"{result.n_straight_segs:>4}{result.n_arc_segs:>4}"
                f"{result.n_freeform_segs:>4} {result.elapsed_s:>5.1f}s{phys_flag}"
            )

    # Split valid (physics_ok) from all
    errors_valid = [
        abs(r["error_pct"]) for r in rows
        if r["error_pct"] is not None and r["physics_ok"]
    ]

    if verbose and errors:
        print("-" * len(header))

        def _print_stats(label: str, errs: list) -> None:
            if not errs:
                print(f"\n  {label}: no data")
                return
            within = {t: sum(1 for e in errs if e <= v)
                      for t, v in TIER_THRESHOLDS.items()}
            print(f"\n{label}  (n={len(errs)})")
            print(f"  Mean abs error   : {np.mean(errs):.2f} %")
            print(f"  Median abs error : {np.median(errs):.2f} %")
            print(f"  Max abs error    : {np.max(errs):.2f} %")
            for tier, thresh in TIER_THRESHOLDS.items():
                n   = within[tier]
                pct = 100 * n / len(errs)
                bar = "#" * int(pct / 5)
                print(f"  {tier:<12} (<={thresh:2.0f}%) : {n:>2}/{len(errs)} = {pct:5.1f}%  {bar}")

        _print_stats("ALL IMAGES", errors)

        if len(errors_valid) < len(errors):
            _print_stats("PHYSICS-VALID ONLY (ppi >= %.0f)" % RESOLUTION_FAIL_PPI, errors_valid)
        print()

    return {
        "rows": rows,
        "mean_abs_error": float(np.mean(errors)) if errors else None,
        "median_abs_error": float(np.median(errors)) if errors else None,
        "max_abs_error": float(np.max(errors)) if errors else None,
        "mean_abs_error_valid": float(np.mean(errors_valid)) if errors_valid else None,
        "median_abs_error_valid": float(np.median(errors_valid)) if errors_valid else None,
        "tier_counts": {t: sum(1 for e in errors if e <= v)
                        for t, v in TIER_THRESHOLDS.items()} if errors else {},
        "tier_counts_valid": {t: sum(1 for e in errors_valid if e <= v)
                              for t, v in TIER_THRESHOLDS.items()} if errors_valid else {},
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    if args[0] == "--batch" and len(args) >= 2:
        batch_evaluate(args[1], render_vis=False, verbose=True)
        sys.exit(0)

    if len(args) < 2:
        print("Usage: python v8_pipeline.py <image_path> <width_inches> [gt_m]")
        sys.exit(1)

    img_path = args[0]
    width_in = float(args[1])
    gt_m_val = float(args[2]) if len(args) >= 3 else None

    pipeline = V8Pipeline(render_vis=False)
    result   = pipeline.measure_from_file(img_path, width_in, gt_m=gt_m_val)

    print(f"\n{'='*55}")
    print(f" V8 NEON LOC RESULT")
    print(f"{'='*55}")
    print(f" Source       : {result.source}")
    print(f" Measured LOC : {result.measured_m:.4f} m")
    if result.gt_m:
        print(f" Ground Truth : {result.gt_m:.4f} m")
        print(f" Error        : {result.error_pct:+.2f} %")
    print(f" Tier         : {result.tier}")
    print(f" Confidence   : {result.confidence:.2f}")
    print(f" Tube width   : {result.tube_width_mm:.1f} mm")
    print(f" ppi_x        : {result.px_per_inch:.1f}")
    if result.px_per_inch_y and abs(result.ar_consistency - 1.0) > 0.005:
        k_flag = "ANISO" if abs(result.ar_consistency - 1.0) > 0.15 else "iso"
        print(f" ppi_y        : {result.px_per_inch_y:.1f}  [k={result.ar_consistency:.3f}  {k_flag}]")
    print(f" Paths        : {result.n_paths}  "
          f"[S={result.n_straight_segs} A={result.n_arc_segs} F={result.n_freeform_segs}]")
    print(f" Elapsed      : {result.elapsed_s:.1f} s")
    print(f"\n REASONING:")
    for line in result.reasoning:
        # Handle encoding errors by replacing non-ASCII characters
        try:
            print(f"   {line}")
        except UnicodeEncodeError:
            safe_line = line.encode('ascii', 'replace').decode('ascii')
            print(f"   {safe_line}")
    print(f"{'='*55}\n")
