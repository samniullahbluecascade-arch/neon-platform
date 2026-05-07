"""
v8_input.py  —  V8 Universal Input Handler
==========================================
Supports:
  · B&W PNG/JPG      (white-tube, black-background)   ~90 % of inputs
  · Transparent PNG  (alpha channel is the mask)       ~10 % of inputs
  · Colored mockups  (RGB neon on any background)       occasional
  · SVG files        (exact LOC via path length)        when available
  · CDR files        (CorelDraw ZIP → SVG / raster)    when available

Core fix over V7
----------------
V7 used full image-frame width as denominator for px_per_inch → SYSTEMATIC
BIAS whenever the sign has black padding around it (almost always).

V8 detects the tight content BBox first, then calibrates:
    px_per_inch = content_bbox_width_px / real_width_inches
This alone can eliminate a 5-20 % calibration error on padded images.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image


# ─────────────────────────────────────────────────────────────────────────────
# Public data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class InputMeta:
    """Everything the pipeline needs to know about the loaded image."""
    source_path:       str
    input_format:      str                       # 'bw' | 'transparent' | 'colored' | 'svg' | 'cdr'
    original_size:     Tuple[int, int]           # (H, W) before crop
    content_bbox:      Tuple[int, int, int, int] # (r0, r1, c0, c1) tight content box
    cropped_size:      Tuple[int, int]           # (H, W) after crop
    px_per_inch:       float                     # ppi_x: content width → real_width_inches
    real_width_inches: float
    tube_width_px:     float                     # estimated tube OD in pixels
    white_pct:         float                     # fraction of cropped mask that is tube
    has_glow:          bool
    # ── 2-D calibration (populated when real_height_inches is supplied) ───────
    px_per_inch_y:     float = 0.0               # ppi_y: content height → real_height_inches
                                                 #        == px_per_inch when height not given
    ar_consistency:    float = 1.0               # k = ppi_y / ppi_x  (1.0 = isotropic)
    real_height_inches: Optional[float] = None  # physical sign height if known
    # ─────────────────────────────────────────────────────────────────────────
    exact_loc_m:       Optional[float] = None    # set only for SVG/CDR vector inputs
    notes:             list = field(default_factory=list)


@dataclass
class LoadedSign:
    """Normalised, cropped sign ready for the V8 pipeline."""
    gray: np.ndarray   # (H, W)  float64  [0, 1]  — intensity, cropped
    mask: np.ndarray   # (H, W)  uint8    {0,255} — tube pixels, cropped
    meta: InputMeta
    sat:  Optional[np.ndarray] = None  # (H, W) float32 [0,1] HSV saturation — colored only


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def load_sign(
    source: "str | bytes | Path",
    real_width_inches: float,
    real_height_inches: Optional[float] = None,
    force_format: Optional[str] = None,
) -> LoadedSign:
    """
    Universal loader.  source can be a file path or raw image bytes.

    Parameters
    ----------
    source              : path (str/Path) or raw bytes
    real_width_inches   : physical width of the sign face (not the image frame)
    real_height_inches  : physical height of the sign face (optional).
                          When supplied, enables 2-D anisotropic calibration:
                          ppi_x = crop_w / real_width_inches
                          ppi_y = crop_h / real_height_inches
                          k = ppi_y / ppi_x   (1.0 = perfectly isotropic image)
                          |k − 1| > 0.15 triggers a calibration-consistency warning.
    force_format        : override auto-detect — 'bw' | 'transparent' | 'colored'
    """
    if real_width_inches <= 0:
        raise ValueError(f"real_width_inches must be positive, got {real_width_inches}")

    path_str = str(source) if not isinstance(source, bytes) else "<bytes>"
    ext = Path(path_str).suffix.lower() if not isinstance(source, bytes) else ".png"

    # ── Vector paths ──────────────────────────────────────────────────────────
    if ext == ".svg":
        return _load_svg(source, real_width_inches, path_str)
    if ext == ".cdr":
        return _load_cdr(source, real_width_inches, path_str)

    # ── Raster paths ──────────────────────────────────────────────────────────
    pil_img = _read_pil(source)
    fmt = force_format or _detect_format(pil_img)

    sat_full: Optional[np.ndarray] = None
    if fmt == "transparent":
        gray, mask = _extract_transparent(pil_img)
    elif fmt == "colored":
        gray, mask, sat_full = _extract_colored(pil_img)
    else:                            # 'bw' (default)
        gray, mask = _extract_bw(pil_img)

    orig_h, orig_w = gray.shape

    # ── Tight content crop — the key calibration fix ──────────────────────────
    bbox = _content_bbox(mask)
    r0, r1, c0, c1 = bbox
    gray_c = gray[r0 : r1 + 1, c0 : c1 + 1].copy()
    mask_c = mask[r0 : r1 + 1, c0 : c1 + 1].copy()
    sat_c  = sat_full[r0 : r1 + 1, c0 : c1 + 1].copy() if sat_full is not None else None
    crop_h, crop_w = gray_c.shape

    # ── 1-D calibration (always): content width → real_width_inches ─────────────
    px_per_inch = crop_w / real_width_inches          # ppi_x

    # ── 2-D calibration (when height known): derive ppi_y and consistency k ────
    if real_height_inches is not None and real_height_inches > 0:
        px_per_inch_y  = crop_h / real_height_inches
        ar_consistency = px_per_inch_y / px_per_inch  # k = ppi_y / ppi_x
    else:
        px_per_inch_y  = px_per_inch                  # isotropic assumption
        ar_consistency = 1.0

    tube_w_px = _estimate_tube_width(mask_c)
    has_glow  = _detect_glow(gray_c, mask_c)
    white_pct = float(np.sum(mask_c > 0)) / mask_c.size

    # Build calibration note
    if real_height_inches is not None:
        k_tag = (
            f"k={ar_consistency:.3f} "
            + ("ANISOTROPIC - image AR != physical AR" if abs(ar_consistency - 1.0) > 0.15
               else "isotropic")
        )
        cal_note = (
            f"Calibration: ppi_x={px_per_inch:.2f}  ppi_y={px_per_inch_y:.2f} px/inch  [{k_tag}]"
        )
    else:
        cal_note = (
            f"Calibration: ppi_x={px_per_inch:.2f} px/inch  [height not supplied → isotropic assumed]"
        )

    meta = InputMeta(
        source_path=path_str,
        input_format=fmt,
        original_size=(orig_h, orig_w),
        content_bbox=bbox,
        cropped_size=(crop_h, crop_w),
        px_per_inch=px_per_inch,
        real_width_inches=real_width_inches,
        tube_width_px=tube_w_px,
        white_pct=white_pct,
        has_glow=has_glow,
        px_per_inch_y=px_per_inch_y,
        ar_consistency=ar_consistency,
        real_height_inches=real_height_inches,
        notes=[
            f"Format: {fmt}",
            f"Crop: {orig_w}x{orig_h} -> {crop_w}x{crop_h} px "
            f"(removed {100*(1 - crop_w/orig_w):.1f}% width padding)",
            cal_note,
            f"Tube width est: {tube_w_px:.1f} px",
        ],
    )
    return LoadedSign(gray=gray_c, mask=mask_c, meta=meta, sat=sat_c)


# ─────────────────────────────────────────────────────────────────────────────
# GT filename parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_gt_filename(name: str) -> Tuple[float, float]:
    """
    Parse files named  "<width_inches> <gt_meters>.png"
    e.g. "27 3.3.png" → (27.0, 3.3)
    Returns (width_in, gt_m).  Raises ValueError on failure.
    """
    stem = Path(name).stem          # strip extension
    parts = stem.split()
    if len(parts) < 2:
        raise ValueError(f"Cannot parse GT filename: {name!r}")
    return float(parts[0]), float(parts[1])


# ─────────────────────────────────────────────────────────────────────────────
# Format detection
# ─────────────────────────────────────────────────────────────────────────────

def _detect_format(pil_img: Image.Image) -> str:
    """Return 'bw' | 'transparent' | 'colored'."""
    # Check for real transparency
    if pil_img.mode in ("RGBA", "LA", "PA"):
        alpha = np.array(pil_img.getchannel("A"))
        if np.any(alpha < 200):          # meaningful transparency present
            return "transparent"

    # Check saturation
    arr = np.array(pil_img.convert("RGB")).astype(np.float32)
    sat_mean = float(np.mean(_rgb_saturation(arr)))
    if sat_mean > 0.08:
        return "colored"

    return "bw"


def _rgb_saturation(rgb_float: np.ndarray) -> np.ndarray:
    """Compute per-pixel HSV saturation from float32 RGB array (values in [0,255])."""
    norm = rgb_float / 255.0
    mx = norm.max(axis=2)
    mn = norm.min(axis=2)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.where(mx > 1e-6, (mx - mn) / mx, 0.0)
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Extraction strategies
# ─────────────────────────────────────────────────────────────────────────────

def _extract_bw(pil_img: Image.Image) -> Tuple[np.ndarray, np.ndarray]:
    """
    Pure B&W input: white = tube, black = background.

    Adaptive threshold selection
    ----------------------------
    A fixed threshold of 20/255 captures anti-aliasing but also noise /
    thin graphic elements that inflate the skeleton.  We scan a range of
    thresholds and pick the one whose resulting mask has the most plausible
    tube width (i.e. ≥ 5 mm physical thickness, measured via distance
    transform).  This mirrors V7's threshold-scanning strategy.
    
    V8.1 FIX: Added morphological cleanup to prevent double-tracing of outlines
    and hairline artifacts that cause path explosion and coverage ratio issues.
    Also added tube width consistency check and mask area check to prevent
    over/under estimation.
    """
    gray_pil = pil_img.convert("L")
    gray = np.array(gray_pil, dtype=np.float64) / 255.0
    gray8 = (gray * 255).astype(np.uint8)

    # Scan thresholds: try coarse steps first, keep the first one that
    # produces a "thick enough" mask (tube width ≥ physical minimum).
    #
    # Heuristic: real neon tube OD ≥ 5 mm.  For any sign at any resolution,
    # 5 mm ≈ 1.5 % of the SHORTER image dimension works across the typical
    # range of sign widths (6"–60") and image resolutions (400–4000 px wide).
    # i.e.  min_radius_px ≈ 0.75 % of min(H, W)   (radius = OD/2)
    H, W = gray.shape
    min_radius_heuristic = max(4.0, min(H, W) * 0.0075)
    max_radius_heuristic = min_radius_heuristic * 6  # Upper bound for tube width

    best_mask  = None
    best_score = float('inf')
    best_coverage = 0.0

    # Morphological kernels for cleanup
    k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    # Include thr=160 in the scan: for glow / near-white signs the core-only
    # threshold removes the soft halo, tightening the mask and reducing the
    # topological over-length from skeleton tracing glyph outlines.
    # For truly binary images (white=255) thr=160 and thr=40 give the same
    # mask, so the first-match tie-breaker leaves the result unchanged.
    for thr in (20, 40, 80, 127, 160):
        _, m_raw = cv2.threshold(gray8, thr, 255, cv2.THRESH_BINARY)
        if np.sum(m_raw > 0) < 100:
            continue
        
        # V8.1: Apply morphological cleanup to remove thin artifacts and outline double-tracing
        m = cv2.morphologyEx(m_raw, cv2.MORPH_OPEN, k3)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k5)
        
        if np.sum(m > 0) < 100:
            continue
            
        dist    = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        nonzero = dist[dist > 0]
        if len(nonzero) < 50:
            continue
        p75 = float(np.percentile(nonzero, 75))   # ~= tube radius estimate
        p25 = float(np.percentile(nonzero, 25))
        
        # V8.1: Tube width consistency check
        # Reject masks with high width variance (indicates fragmented/outline artifacts)
        consistency = p75 / max(p25, 1.0)
        
        # V8.1: Check mask coverage - too much coverage indicates double-tracing/outline artifacts
        coverage = np.sum(m > 0) / (H * W)
        
        # Score: prefer tightest threshold with good consistency and reasonable coverage
        # Target: tube radius ≈ [min_radius_heuristic, max_radius_heuristic]
        if p75 < min_radius_heuristic:
            continue   # too thin — likely noise or anti-aliasing only
        if p75 > max_radius_heuristic:
            continue   # too thick — likely includes glow/halos or double-tracing
        
        # V8.1: Prefer masks with:
        # - Good consistency (lower is better, < 2.0 is ideal)
        # - Reasonable coverage (< 25% of image - stricter to prevent overestimation)
        # - Tightest valid tube width (to avoid glow inclusion)
        # - BUT: if coverage is very low (< 5%), we might be missing tube (underestimation)
        consistency_penalty = max(0, consistency - 1.5) * 0.3
        coverage_penalty = max(0, coverage - 0.25) * 3.0  # Stricter coverage limit
        
        # V8.1: Bonus for moderate coverage (5-15% is ideal for neon signs)
        coverage_bonus = 0.0
        if 0.05 <= coverage <= 0.15:
            coverage_bonus = -0.1  # Slight preference for ideal coverage range
        
        score = p75 * (1.0 + consistency_penalty + coverage_penalty + coverage_bonus)
        
        if best_mask is None or score < best_score:
            best_score = score
            best_mask  = m
            best_thr   = thr
            best_coverage = coverage

    if best_mask is None:
        # Absolute fallback: Otsu + cleanup
        _, tmp = cv2.threshold(gray8, 0, 255,
                                     cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        best_mask = cv2.morphologyEx(tmp, cv2.MORPH_OPEN, k3)
        best_mask = cv2.morphologyEx(best_mask, cv2.MORPH_CLOSE, k5)

    return gray, best_mask


def _extract_transparent(pil_img: Image.Image) -> Tuple[np.ndarray, np.ndarray]:
    """
    Transparent PNG: alpha channel IS the authoritative mask.
    Grayscale intensity is alpha-weighted so brighter = more central.
    """
    rgba = np.array(pil_img.convert("RGBA"), dtype=np.float64) / 255.0
    alpha = rgba[:, :, 3]
    lum   = 0.299 * rgba[:, :, 0] + 0.587 * rgba[:, :, 1] + 0.114 * rgba[:, :, 2]
    gray  = lum * alpha          # alpha-weighted: zero outside shape, full at core
    mask  = (alpha > 0.05).astype(np.uint8) * 255
    return gray, mask


def _extract_colored(pil_img: Image.Image) -> Tuple[np.ndarray, np.ndarray]:
    """
    Colored neon mockup on dark or light background.

    V8.1 CRITICAL FIX: Use ONLY the brightest core of the tube to prevent
    glow halo from being included in the mask. This prevents path explosion
    in ridge detection.
    
    Strategy:
    1. Use a very strict threshold (top 3-5% of bright pixels only)
    2. NO morphological closing (which bridges gaps between tubes via glow)
    3. Only morphological opening to remove noise
    4. Require tight tube width consistency
    """
    rgb  = np.array(pil_img.convert("RGB"), dtype=np.float32)
    lum  = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]) / 255.0
    sat  = _rgb_saturation(rgb)

    # Detect background type
    H, W = lum.shape
    corners_lum = [lum[0, 0], lum[0, -1], lum[-1, 0], lum[-1, -1]]
    bg_bright   = float(np.mean(corners_lum)) > 0.5

    if bg_bright:
        score = sat                       # light background: tube = high saturation
    else:
        score = np.maximum(lum, sat * 0.7)  # dark background: tube = bright OR saturated

    score8 = (score * 255).astype(np.uint8)
    min_radius_heuristic = max(4.0, min(H, W) * 0.0075)

    # Morphological kernels - only use opening, NO closing (which bridges glow)
    k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    best_mask      = None
    best_score_val = float('inf')

    # V8.1: Use ONLY the brightest pixels - strict percentile thresholds
    # This captures only the tube core, not the glow envelope
    fg_vals = score8[score8 > 20].flatten()  # Higher minimum to exclude background
    if len(fg_vals) >= 100:
        # Try very strict thresholds first (top 3-10% only)
        for pct in (97, 95, 93, 90, 85):
            thr_val = int(np.percentile(fg_vals, pct))
            if thr_val < 30:  # Must be reasonably bright
                continue
            _, m_raw = cv2.threshold(score8, thr_val, 255, cv2.THRESH_BINARY)
            if int(np.sum(m_raw > 0)) < 100:
                continue
            
            # V8.1: Only OPENING to remove noise, NO closing (prevents glow bridging)
            m_cand = cv2.morphologyEx(m_raw, cv2.MORPH_OPEN, k3)
            
            if int(np.sum(m_cand > 0)) < 50:
                continue
            
            # Check tube width - must be physically plausible
            dist    = cv2.distanceTransform(m_cand, cv2.DIST_L2, 5)
            nonzero = dist[dist > 0]
            if len(nonzero) < 50:
                continue
            
            p75 = float(np.percentile(nonzero, 75))
            p25 = float(np.percentile(nonzero, 25))
            
            # Reject if too thin (noise) or too wide (glow included)
            if p75 < min_radius_heuristic or p75 > min_radius_heuristic * 4:
                continue
            
            # Prefer tightest mask (smallest p75) that is still valid
            if p75 < best_score_val:
                best_score_val = p75
                best_mask = m_cand

    if best_mask is None:
        # Fallback: use Otsu but with aggressive opening and NO closing
        _, tmp = cv2.threshold(score8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        best_mask = cv2.morphologyEx(tmp, cv2.MORPH_OPEN, k5)
        best_mask = cv2.morphologyEx(best_mask, cv2.MORPH_OPEN, k3)

    return lum, best_mask, sat


# ─────────────────────────────────────────────────────────────────────────────
# Content BBox — critical calibration fix
# ─────────────────────────────────────────────────────────────────────────────

def _content_bbox(mask: np.ndarray, margin: int = 4) -> Tuple[int, int, int, int]:
    """
    Return tight bounding box of non-zero mask content: (r0, r1, c0, c1).
    Adds `margin` pixels of padding on each side (clamped to image boundary).
    """
    rows = np.any(mask > 0, axis=1)
    cols = np.any(mask > 0, axis=0)
    H, W = mask.shape

    if not np.any(rows) or not np.any(cols):
        return 0, H - 1, 0, W - 1   # degenerate: empty mask

    r0 = max(0, int(np.argmax(rows)) - margin)
    r1 = min(H - 1, int(H - 1 - np.argmax(rows[::-1])) + margin)
    c0 = max(0, int(np.argmax(cols)) - margin)
    c1 = min(W - 1, int(W - 1 - np.argmax(cols[::-1])) + margin)
    return r0, r1, c0, c1


# ─────────────────────────────────────────────────────────────────────────────
# Tube width estimation
# ─────────────────────────────────────────────────────────────────────────────

def _estimate_tube_width(mask: np.ndarray) -> float:
    """
    Estimate tube outer diameter in pixels from the distance transform.

    The 75th-percentile non-zero distance value is a robust estimate of the
    tube RADIUS (it is near the skeleton, away from halo/edge bias).
    Multiply by 2 to get diameter.
    """
    dist    = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    nonzero = dist[dist > 0.5]
    if len(nonzero) < 20:
        return 8.0           # safe fallback
    radius_est = float(np.percentile(nonzero, 75))
    return radius_est * 2.0


# ─────────────────────────────────────────────────────────────────────────────
# Glow detection
# ─────────────────────────────────────────────────────────────────────────────

def _detect_glow(gray: np.ndarray, mask: np.ndarray) -> bool:
    """
    Detect genuine glow / bloom (real photos or colored mockups with halo).

    Algorithm
    ---------
    1. If ≥ 75 % of tube pixels have intensity ≥ 0.90 it is a BINARY / NEAR-
       BINARY image (e.g. clean B&W mockup with light anti-aliasing).
       Return False — skeleton mode is appropriate.
    2. Otherwise measure the Pearson correlation between distance-from-edge
       and pixel brightness.  A correlation > 0.35 indicates a genuine radial
       brightness gradient (glow / bloom) → return True.

    Note: anti-aliasing on clean B&W mockups creates a 1-2px edge band which
    gives a small spurious correlation, so we use a slightly higher threshold
    (0.35 vs the original 0.25) and ignore pixels in the outermost ring.
    """
    tube_pixels = gray[mask > 0]
    if len(tube_pixels) < 50:
        return False

    # Guard #1: near-binary images have almost all pixels at max brightness
    bright_frac = float(np.mean(tube_pixels >= 0.88))
    if bright_frac > 0.70:
        return False   # binary / near-binary → no glow

    # Guard #2: distance-brightness correlation (only on interior pixels)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    # Ignore the outermost 1px ring to avoid anti-aliasing noise
    interior = dist > 1.5
    if np.sum(interior) < 100:
        return False
    d_vals = dist[interior].astype(np.float64)
    g_vals = gray[interior].astype(np.float64)
    if np.std(g_vals) < 1e-3:
        return False
    corr = float(np.corrcoef(d_vals, g_vals)[0, 1])
    return abs(corr) > 0.35


# ─────────────────────────────────────────────────────────────────────────────
# PIL reader
# ─────────────────────────────────────────────────────────────────────────────

def _read_pil(source: "str | bytes | Path") -> Image.Image:
    if isinstance(source, bytes):
        return Image.open(io.BytesIO(source))
    img = Image.open(str(source))
    img.load()          # force decode — avoids lazy-load issues with TIFF etc.
    return img


# ─────────────────────────────────────────────────────────────────────────────
# SVG vector loader — exact LOC
# ─────────────────────────────────────────────────────────────────────────────

def _load_svg(source, real_width_inches: float, path_str: str) -> LoadedSign:
    """
    Parse SVG path data and compute exact LOC via analytic arc-length.
    Requires: pip install svgpathtools
    """
    try:
        from svgpathtools import svg2paths2
    except ImportError:
        raise ImportError(
            "svgpathtools is required for SVG input.  "
            "Install with:  pip install svgpathtools"
        )

    if isinstance(source, bytes):
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".svg", delete=False)
        tmp.write(source)
        tmp.close()
        svg_path = tmp.name
    else:
        svg_path = str(source)

    paths, _, svg_attrs = svg2paths2(svg_path)
    total_svg_units = sum(float(p.length()) for p in paths)

    # Parse viewport width (handle 'px', 'pt', 'mm' suffixes)
    vp_raw = str(svg_attrs.get("width", "100"))
    vp_val = float("".join(c for c in vp_raw if c.isdigit() or c == ".") or "100")
    svg_units_per_inch = vp_val / real_width_inches
    exact_loc_m = (total_svg_units / svg_units_per_inch) * 0.0254

    # Minimal raster for visualisation (best-effort)
    try:
        import cairosvg
        png_bytes = cairosvg.svg2png(url=svg_path)
        pil_img   = Image.open(io.BytesIO(png_bytes))
        gray, mask = _extract_bw(pil_img)
    except Exception:
        gray = np.zeros((200, 400), dtype=np.float64)
        mask = np.zeros((200, 400), dtype=np.uint8)

    H, W = gray.shape
    meta = InputMeta(
        source_path=path_str,
        input_format="svg",
        original_size=(H, W),
        content_bbox=(0, H - 1, 0, W - 1),
        cropped_size=(H, W),
        px_per_inch=W / real_width_inches,
        real_width_inches=real_width_inches,
        tube_width_px=0.0,
        white_pct=0.0,
        has_glow=False,
        exact_loc_m=exact_loc_m,
        notes=[f"SVG exact LOC = {exact_loc_m:.4f} m (vector, no pixel approx)"],
    )
    return LoadedSign(gray=gray, mask=mask, meta=meta)


# ─────────────────────────────────────────────────────────────────────────────
# CDR loader (CorelDraw ZIP format, X4 and later)
# ─────────────────────────────────────────────────────────────────────────────

def _load_cdr(source, real_width_inches: float, path_str: str) -> LoadedSign:
    """
    Modern CDR files (CorelDraw X4+) are ZIP archives.
    We look for an embedded SVG first, then a raster preview.
    """
    data = source if isinstance(source, bytes) else open(str(source), "rb").read()

    if data[:2] != b"PK":
        raise ValueError(
            "CDR file is not in ZIP format (only CorelDraw X4+ CDR files are "
            "supported).  Export to SVG from CorelDraw for best results."
        )

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()

        # Prefer embedded SVG
        svg_candidates = [n for n in names if n.lower().endswith(".svg")]
        if svg_candidates:
            svg_data = z.read(svg_candidates[0])
            result   = _load_svg(svg_data, real_width_inches, path_str)
            result.meta.input_format = "cdr"
            result.meta.notes.insert(0, "CDR → embedded SVG (exact LOC)")
            return result

        # Fall back to raster preview
        raster_candidates = [n for n in names if n.lower().endswith((".png", ".jpg", ".jpeg"))]
        if raster_candidates:
            img_data = z.read(raster_candidates[0])
            pil_img  = Image.open(io.BytesIO(img_data))
            fmt      = _detect_format(pil_img)
            if fmt == "transparent":
                gray, mask = _extract_transparent(pil_img)
            else:
                gray, mask = _extract_bw(pil_img)
            bbox    = _content_bbox(mask)
            r0, r1, c0, c1 = bbox
            gray    = gray[r0:r1+1, c0:c1+1]
            mask    = mask[r0:r1+1, c0:c1+1]
            H, W    = gray.shape
            tw      = _estimate_tube_width(mask)
            meta    = InputMeta(
                source_path=path_str,
                input_format="cdr",
                original_size=(gray.shape[0], gray.shape[1]),
                content_bbox=bbox,
                cropped_size=(H, W),
                px_per_inch=W / real_width_inches,
                real_width_inches=real_width_inches,
                tube_width_px=tw,
                white_pct=float(np.sum(mask > 0)) / mask.size,
                has_glow=_detect_glow(gray, mask),
                notes=["CDR → raster preview (approximate LOC)"],
            )
            return LoadedSign(gray=gray, mask=mask, meta=meta)

    raise ValueError(
        f"CDR ZIP has no SVG or raster content: {path_str}\n"
        f"Found entries: {names[:10]}"
    )
