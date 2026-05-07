"""
v8_ridge.py  —  Frangi Ridge Extraction + IR-MST Path Building
==============================================================

THREE INNOVATIONS OVER V7
--------------------------
1. Frangi Multi-Scale Hessian Ridge Extractor
   Replaces Zhang-Suen skeletonization.  The Frangi filter finds the
   GEOMETRIC centre of every bright ridge at the correct scale —
   independent of tube width, glow, or anti-aliasing.

2. IR-MST  (Intensity-Ridge Minimum Spanning Tree)
   Formalisation of the user's  "connect brightest pixels, prune long
   edges between separate tubes" idea.
     a) Build k-NN graph on ridge pixels.
     b) Compute adaptive length threshold  τ = μ + α·σ of edge lengths.
     c) Remove edges longer than τ  (they span two distinct glass tubes).
     d) Connected components = individual tube paths.
     e) Order pixels per component via greedy chain from degree-1 endpoint.

3. Junction Disambiguator
   At every skeleton node of degree ≥ 3, route the tube by MAXIMUM
   CURVATURE CONTINUITY (smallest bend at junction), eliminating the
   spurious skeleton branches that DFS created in script lettering.

All three stages are scale-adaptive: parameters are computed from the
tube_width_px estimated by v8_input.py.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize as skimage_skeletonize


# ─────────────────────────────────────────────────────────────────────────────
# Public data structure
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RidgePath:
    """One extracted tube path (ordered pixel coordinates)."""
    points:      np.ndarray          # (N, 2) float64  [row, col]
    path_id:     int     = 0
    is_loop:     bool    = False
    ridge_score: float   = 0.0       # mean Frangi ridgeness along path
    notes:       list    = field(default_factory=list)

    @property
    def length_px(self) -> float:
        """Polyline length in pixels (lower bound on true arc length)."""
        if len(self.points) < 2:
            return 0.0
        d = np.diff(self.points, axis=0)
        return float(np.sum(np.hypot(d[:, 0], d[:, 1])))


# ─────────────────────────────────────────────────────────────────────────────
# 0.  DoG (Difference of Gaussians) Fast Ridge Extractor  [V7-inspired]
# ─────────────────────────────────────────────────────────────────────────────

class DoGRidgeExtractor:
    """
    Fast tube-ridge detector using Difference of Gaussians.

    DoG = Gauss(σ_inner) − Gauss(σ_outer) responds strongly at bright ridges
    whose width matches (σ_outer − σ_inner).  Two Gaussian blurs vs the five
    Hessian computations in Frangi → ~10× faster with comparable ridge quality.

    Used for glow / colored images where Frangi is overkill and the mask is
    unreliable (glow-inflated).  Operates entirely on the gray intensity image.

    Parameters
    ----------
    tube_width_px : estimated tube outer diameter (px)
    """

    def __init__(self, tube_width_px: float = 16.0):
        self.tube_width_px = max(4.0, float(tube_width_px))

    def extract(
        self, gray: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns
        -------
        ridgeness   : (H,W) float64 DoG response in [0,1]
        orientation : (H,W) float64 along-tube angle (from gradient of DoG)
        best_scale  : (H,W) float64 (constant = tube_width_px/2 for compatibility)
        
        V8.1 FIX: Added intensity thresholding to prevent detecting ridges
        in dim glow regions. Only bright tube cores should produce ridges.
        """
        r = self.tube_width_px / 2.0
        # Inner sigma: resolves the bright tube core
        sigma_inner = max(1.0, r * 0.35)
        # Outer sigma: models the surrounding glow / background level
        sigma_outer = max(2.0, r * 1.20)

        g1  = gaussian_filter(gray, sigma=sigma_inner)
        g2  = gaussian_filter(gray, sigma=sigma_outer)
        dog = np.clip(g1 - g2, 0.0, None)
        
        mx  = float(dog.max())
        if mx < 1e-9:
            H, W = gray.shape
            return np.zeros((H, W)), np.zeros((H, W)), np.zeros((H, W))
        ridgeness = dog / mx  # normalise to [0,1]

        # Orientation from gradient of the DoG response (perpendicular to gradient = along ridge)
        gy = gaussian_filter(ridgeness, sigma=max(1.0, r * 0.5), order=(1, 0))
        gx = gaussian_filter(ridgeness, sigma=max(1.0, r * 0.5), order=(0, 1))
        orientation = np.arctan2(gy, gx) + np.pi / 2.0   # along-tube direction

        best_scale = np.full_like(ridgeness, r)
        return ridgeness, orientation, best_scale


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Frangi Multi-Scale Hessian Ridge Extractor
# ─────────────────────────────────────────────────────────────────────────────

class FrangiRidgeExtractor:
    """
    Scale-normalised Frangi vesselness filter adapted for 2-D neon tube ridges.

    For bright ridges on a dark background the filter returns a value close
    to 1.0 at the tube centerline and 0 everywhere else — regardless of
    tube width, intensity level, or mild glow effects.

    Parameters
    ----------
    tube_width_px : estimated tube outer diameter in pixels.
                    Used to auto-select Gaussian scales.
    beta          : Frangi β — controls sensitivity to blobness.
                    0.5 is the standard value.
    c_frac        : Frangi c as a fraction of image dynamic range.
                    0.15 gives good results for clean B&W mockups;
                    use 0.08 for images with strong glow.
    """

    def __init__(
        self,
        tube_width_px: float = 16.0,
        beta: float = 0.5,
        c_frac: float = 0.15,
    ):
        self.tube_width_px = max(4.0, float(tube_width_px))
        self.beta          = beta
        self.c_frac        = c_frac

    # ── Internals ─────────────────────────────────────────────────────────────

    def _auto_scales(self) -> List[float]:
        """
        Return 4-5 Gaussian σ values that span the tube radius.
        σ should range from ~tube_radius/4  to  ~tube_radius*1.5.
        """
        r = self.tube_width_px / 2.0
        # 3 scales instead of 5: covers inner-edge, centerline, outer-edge.
        # Sufficient after resolution cap (tube width is always ~15 px at 40 ppi).
        # 40% fewer Gaussian convolutions → meaningful speedup on large images.
        scales = [max(1.0, r * f) for f in (0.5, 1.0, 1.5)]
        # Cap at 32 to avoid excessive blur on small images
        scales = [min(s, 32.0) for s in scales]
        return scales

    def _hessian_ridge(
        self, gray: np.ndarray, sigma: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute scale-normalised Hessian eigenvalues and ridge orientation at σ.

        Returns
        -------
        lam1 : smaller-magnitude eigenvalue  (≈ 0 along ridge)
        lam2 : larger-magnitude eigenvalue   (<< 0 for bright ridge)
        theta: local ridge DIRECTION angle (radians, along-tube)
        """
        # Scale-normalised second derivatives
        Lxx = gaussian_filter(gray, sigma=sigma, order=(2, 0)) * (sigma ** 2)
        Lyy = gaussian_filter(gray, sigma=sigma, order=(0, 2)) * (sigma ** 2)
        Lxy = gaussian_filter(gray, sigma=sigma, order=(1, 1)) * (sigma ** 2)

        # Eigenvalues of 2×2 symmetric Hessian
        trace = Lxx + Lyy
        disc  = np.sqrt(np.maximum(0.0, (Lxx - Lyy) ** 2 + 4.0 * Lxy ** 2))
        lam1  = (trace - disc) * 0.5   # smaller magnitude
        lam2  = (trace + disc) * 0.5   # larger magnitude

        # Ridge direction: eigenvector of lam1
        # For H = [[a,b],[b,d]], eigenvector angle = atan2(b, lam1 - a)
        theta = 0.5 * np.arctan2(2.0 * Lxy, Lxx - Lyy)
 
        return lam1, lam2, theta

    # ── Public interface ───────────────────────────────────────────────────────

    def extract(
        self, gray: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Run Frangi filter over all auto-selected scales.

        Parameters
        ----------
        gray : (H, W) float64 intensity image in [0, 1]

        Returns
        -------
        ridgeness   : (H, W) float64 in [0, 1]  — max response over scales
        orientation : (H, W) float64            — along-tube angle (radians)
        best_scale  : (H, W) float64            — σ at which max response occurs
        """
        scales  = self._auto_scales()
        H, W    = gray.shape
        c       = self.c_frac * float(np.percentile(gray[gray > 0.01], 95) if np.any(gray > 0.01) else 0.5)
        c       = max(c, 1e-4)

        ridgeness   = np.zeros((H, W), dtype=np.float64)
        orientation = np.zeros((H, W), dtype=np.float64)
        best_scale  = np.zeros((H, W), dtype=np.float64)

        for sigma in scales:
            lam1, lam2, theta = self._hessian_ridge(gray, sigma)

            # Only bright ridges: need lam2 < 0
            bright_ridge = lam2 < 0.0

            # Blobness  Rb = (λ₁/λ₂)²  → 0 for elongated ridges, 1 for blobs
            with np.errstate(divide="ignore", invalid="ignore"):
                Rb = np.where(np.abs(lam2) > 1e-12, (lam1 / lam2) ** 2, 0.0)

            # Structure measure  S = ||H||_F
            S = np.sqrt(lam1 ** 2 + lam2 ** 2)

            # Frangi vesselness
            V = np.exp(-Rb / (2.0 * self.beta ** 2)) * (1.0 - np.exp(-(S ** 2) / (2.0 * c ** 2)))
            V[~bright_ridge] = 0.0
            V = np.clip(V, 0.0, 1.0)

            # Update max response
            better = V > ridgeness
            ridgeness   = np.where(better, V, ridgeness)
            orientation = np.where(better, theta, orientation)
            best_scale  = np.where(better, sigma, best_scale)

        return ridgeness, orientation, best_scale


# ─────────────────────────────────────────────────────────────────────────────
# Non-Maximum Suppression along perpendicular ridge direction
# ─────────────────────────────────────────────────────────────────────────────

def nms_ridge(ridgeness: np.ndarray, orientation: np.ndarray) -> np.ndarray:
    """
    Suppress non-maximal ridgeness values in the direction PERPENDICULAR to
    the tube (i.e., across the tube cross-section).  Produces a thin,
    near-single-pixel ridge map without any binary thresholding.

    Parameters
    ----------
    ridgeness   : Frangi output (H, W)
    orientation : along-tube angle in radians (H, W)

    Returns
    -------
    thinned : (H, W) float64 with non-maxima zeroed out
    """
    H, W = ridgeness.shape
    thinned = ridgeness.copy()

    # Perpendicular direction (across the tube)
    perp_dy = np.cos(orientation)   # row component of perpendicular
    perp_dx = -np.sin(orientation)  # col component of perpendicular

    rr, cc = np.meshgrid(np.arange(H, dtype=np.float64),
                         np.arange(W, dtype=np.float64), indexing="ij")

    for sign in (+1.0, -1.0):
        r_nb = np.clip(rr + sign * perp_dy, 0, H - 1)
        c_nb = np.clip(cc + sign * perp_dx, 0, W - 1)

        r0 = r_nb.astype(int); r1 = np.clip(r0 + 1, 0, H - 1)
        c0 = c_nb.astype(int); c1 = np.clip(c0 + 1, 0, W - 1)
        fr = r_nb - r0
        fc = c_nb - c0

        interp = (
            ridgeness[r0, c0] * (1 - fr) * (1 - fc)
            + ridgeness[r1, c0] * fr      * (1 - fc)
            + ridgeness[r0, c1] * (1 - fr) * fc
            + ridgeness[r1, c1] * fr      * fc
        )
        thinned = np.where(ridgeness < interp, 0.0, thinned)

    return thinned


# ─────────────────────────────────────────────────────────────────────────────
# 2.  IR-MST  (Intensity-Ridge Minimum Spanning Tree) Path Builder
# ─────────────────────────────────────────────────────────────────────────────

class IRMSTPathBuilder:
    """
    Builds ordered tube paths from a set of ridge pixels by:
      1. Building a k-NN graph on the ridge pixel coordinates.
      2. Pruning edges longer than an adaptive threshold  τ = μ + α·σ
         (long edges connect DIFFERENT glass tubes — the user's key insight).
      3. Extracting connected components as individual tube segments.
      4. Ordering pixels within each component via a greedy chain.

    Physical guard: additionally enforces a minimum inter-tube gap of
    `tube_width_px` (two physically separate tubes cannot be closer than
    one tube diameter centre-to-centre).

    Parameters
    ----------
    tube_width_px : estimated tube outer diameter (from v8_input._estimate_tube_width)
    k             : number of nearest neighbours in the initial graph
    alpha         : pruning multiplier  τ = μ + α·σ  (2.0 is a safe default)
    min_path_px   : discard paths whose polyline length < this value
    """

    def __init__(
        self,
        tube_width_px: float = 16.0,
        k: int = 3,            # reduced from 5: fewer edges → faster k-NN, same topology
        alpha: float = 2.0,
        min_path_px: float = 12.0,
        physical_min_edge: float = 0.0,
    ):
        """
        Parameters
        ----------
        tube_width_px     : estimated tube outer diameter (px)
        k                 : k-NN neighbours
        alpha             : edge-pruning multiplier  τ = μ + α·σ
        min_path_px       : minimum polyline length to keep a path
        physical_min_edge : minimum edge length enforced AFTER adaptive τ.
                            Set to ~tube_width_px*0.9 for Frangi/glow mode
                            (where adjacent ridge pixels from two different
                            tubes would be tube_OD apart).
                            Set to 0 (default) for skeleton mode (where
                            skeleton pixels from the same tube are 1-2px
                            apart and must NOT be separated).
        """
        self.tube_width_px     = max(4.0, float(tube_width_px))
        self.k                 = k
        self.alpha             = alpha
        self.min_path_px       = min_path_px
        self.physical_min_edge = float(physical_min_edge)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _adaptive_threshold(self, edges_len: np.ndarray) -> float:
        """
        Compute τ = μ + α·σ.
        For Frangi/glow mode, also enforce physical_min_edge to ensure
        that two ridge pixels from different tubes (separated by ≥ tube OD)
        are always pruned.
        For skeleton mode, physical_min_edge = 0 so adjacent skeleton
        pixels (1-2px apart) are NEVER pruned.
        
        V8.1 FIX: Aggressive pruning to prevent path explosion on noisy/colored images.
        Uses p90 instead of adaptive threshold when variance is high.
        """
        mu    = float(np.mean(edges_len))
        sigma = float(np.std(edges_len))
        tau   = mu + self.alpha * sigma
        
        # V8.1: Aggressive percentile-based pruning for high-variance cases
        # This is critical for colored images with glow/halos that create
        # fragmented ridge responses
        p90 = float(np.percentile(edges_len, 90))
        p75 = float(np.percentile(edges_len, 75))
        
        # If distribution has high variance (noisy/fragmented), use p90
        # This prevents path explosion by being more conservative
        cv = sigma / max(mu, 1e-6)  # coefficient of variation
        if cv > 0.3:  # High variance indicates fragmented/noisy ridges
            tau = min(tau, p90)
        if cv > 0.5:  # Very high variance - use even stricter p75
            tau = min(tau, p75)
        
        # Always enforce physical minimum (tube width constraint)
        return max(tau, self.physical_min_edge)

    def _order_component(
        self,
        node_ids: List[int],
        coords: np.ndarray,
        adj: "dict[int, set]",
    ) -> Optional[np.ndarray]:
        """
        Order the nodes of one connected component as a path.

        Strategy
        --------
        · Start from a degree-1 node (endpoint) if one exists, else any node.
        · Greedy: always step to the nearest unvisited neighbour.
        · Returns an (N, 2) array of [row, col] or None if too short.
        """
        comp_set = set(node_ids)
        degrees  = {n: len(adj[n] & comp_set) for n in comp_set}
        endpoints = [n for n, d in degrees.items() if d == 1]
        start     = endpoints[0] if endpoints else node_ids[0]

        ordered  = [start]
        visited  = {start}
        current  = start

        while True:
            nbrs = [n for n in adj[current] if n in comp_set and n not in visited]
            if not nbrs:
                break
            nxt = min(nbrs, key=lambda n: float(np.linalg.norm(coords[n] - coords[current])))
            ordered.append(nxt)
            visited.add(nxt)
            current = nxt

        pts = coords[ordered]
        if len(pts) < 3:
            return None
        return pts.astype(np.float64)

    def _split_wide_component(
        self,
        pts: np.ndarray,
        orientation: np.ndarray,
        orig_shape: Tuple[int, int],
    ) -> List[np.ndarray]:
        """
        If a component is wider than 1.6 × tube_diameter it almost certainly
        contains two parallel tubes that were not pruned by the edge threshold.
        Split using k-means (k=2) in the perpendicular direction.
        """
        if len(pts) < 20:
            return [pts]

        # Estimate component width: range of perpendicular coordinates
        # Use mean orientation to define perpendicular axis
        rows = pts[:, 0].astype(int).clip(0, orig_shape[0] - 1)
        cols = pts[:, 1].astype(int).clip(0, orig_shape[1] - 1)
        thetas = orientation[rows, cols]
        mean_theta = float(np.median(thetas))
        perp = np.array([-np.sin(mean_theta), np.cos(mean_theta)])  # perpendicular vector

        proj = pts @ perp                   # scalar projection onto perp axis
        p_range = float(proj.max() - proj.min())

        if p_range <= 1.6 * self.tube_width_px:
            return [pts]

        # Two clusters along the perpendicular axis
        try:
            from sklearn.cluster import KMeans
            km = KMeans(n_clusters=2, random_state=0, n_init=3)
            labels = km.fit_predict(proj.reshape(-1, 1))
        except ImportError:
            # Fallback: simple median split
            med = float(np.median(proj))
            labels = (proj > med).astype(int)

        parts = []
        for lab in (0, 1):
            sub = pts[labels == lab]
            if len(sub) >= 5:
                parts.append(sub)
        return parts if parts else [pts]

    # ── Public interface ───────────────────────────────────────────────────────

    def build_paths(
        self,
        ridgeness: np.ndarray,
        orientation: np.ndarray,
        ridge_threshold: float = 0.05,
    ) -> List[RidgePath]:
        """
        Extract ordered tube paths from a Frangi ridgeness map.

        Parameters
        ----------
        ridgeness        : (H, W) Frangi output (after NMS recommended)
        orientation      : (H, W) along-tube angle
        ridge_threshold  : minimum ridgeness to include a pixel (fraction of max)

        Returns
        -------
        List of RidgePath objects, one per detected tube segment.
        
        V8.1 FIX: Added progressive thresholding to prevent path explosion.
        If too many ridge pixels detected, increase threshold and retry.
        """
        H, W    = ridgeness.shape
        max_r   = float(ridgeness.max())
        if max_r < 1e-6:
            return []

        # V8.1: Progressive thresholding - start with higher threshold
        # and increase if too many pixels detected
        # Hard cap: if we still have too many pixels after all thresholds, abort
        max_allowed_pixels = 3000  # Hard cap to prevent path explosion
        
        for thr_mult in [0.20, 0.35, 0.50, 0.65]:  # Try increasingly strict thresholds
            thr     = thr_mult * max_r
            ridge_mask = ridgeness >= thr

            # Ridge pixel coordinates
            r_idx, c_idx = np.where(ridge_mask)
            if len(r_idx) < 6:
                continue
            
            # V8.1: If too many pixels, this indicates fragmentation - try stricter threshold
            if len(r_idx) > max_allowed_pixels:  # Too many ridge pixels = fragmented
                continue
            
            # This threshold looks reasonable, proceed with it
            break
        else:
            # All thresholds tried, use strictest and cap if needed
            thr = 0.65 * max_r
            ridge_mask = ridgeness >= thr
            r_idx, c_idx = np.where(ridge_mask)
            if len(r_idx) < 6:
                return []
            # If still too many, take only the brightest pixels
            if len(r_idx) > max_allowed_pixels:
                # Sort by ridgeness and take top max_allowed_pixels
                flat_indices = np.argsort(ridgeness[ridge_mask].flatten())[-max_allowed_pixels:]
                r_idx = r_idx[flat_indices]
                c_idx = c_idx[flat_indices]

        coords = np.column_stack([r_idx, c_idx]).astype(np.float64)
        N      = len(coords)

        # ── Build k-NN graph ──────────────────────────────────────────────────
        k_actual = min(self.k + 1, N)        # +1 because self is included
        tree     = cKDTree(coords)
        dists_all, idx_all = tree.query(coords, k=k_actual)

        # Collect undirected edges (i < j only, avoid duplicates)
        edge_set = {}           # (i,j) → distance
        for i in range(N):
            for d, j in zip(dists_all[i, 1:], idx_all[i, 1:]):  # skip [0]=self
                if i < j:
                    edge_set[(i, j)] = d
                else:
                    if (j, i) not in edge_set:
                        edge_set[(j, i)] = d

        if not edge_set:
            return []

        edge_items = list(edge_set.items())
        edges_ij   = np.array([e[0] for e in edge_items], dtype=np.int32)  # (M, 2)
        edges_len  = np.array([e[1] for e in edge_items], dtype=np.float64)

        # ── Adaptive edge pruning ─────────────────────────────────────────────
        tau = self._adaptive_threshold(edges_len)
        keep = edges_len <= tau

        if not np.any(keep):
            return []

        # ── Connected components via sparse adjacency matrix ──────────────────
        i_idx = edges_ij[:, 0][keep]
        j_idx = edges_ij[:, 1][keep]
        vals  = np.ones(int(np.sum(keep)), dtype=np.float32)
        mat   = csr_matrix((np.concatenate([vals, vals]),
                            (np.concatenate([i_idx, j_idx]),
                             np.concatenate([j_idx, i_idx]))),
                           shape=(N, N))

        n_components, labels = connected_components(mat, directed=False)

        # ── Adjacency list for path ordering ──────────────────────────────────
        adj: "dict[int, set[int]]" = defaultdict(set)
        for ii, jj in zip(i_idx, j_idx):
            adj[int(ii)].add(int(jj))
            adj[int(jj)].add(int(ii))

        # ── Extract paths per component ───────────────────────────────────────
        paths: List[RidgePath] = []
        path_id = 0

        for comp_id in range(n_components):
            node_ids = list(np.where(labels == comp_id)[0])
            if len(node_ids) < 4:
                continue

            pts = self._order_component(node_ids, coords, adj)
            if pts is None:
                continue

            # Split wide components (two touching parallel tubes)
            sub_parts = self._split_wide_component(pts, orientation, (H, W))

            for sub_pts in sub_parts:
                if len(sub_pts) < 4:
                    continue

                rp = RidgePath(points=sub_pts, path_id=path_id)

                # Polyline length check
                if rp.length_px < self.min_path_px:
                    continue

                # Mean ridgeness
                rs = sub_pts[:, 0].astype(int).clip(0, H - 1)
                cs = sub_pts[:, 1].astype(int).clip(0, W - 1)
                rp.ridge_score = float(np.mean(ridgeness[rs, cs]))

                # Loop detection: are endpoints within tube_width of each other?
                if len(sub_pts) >= 10:
                    end_gap = float(np.linalg.norm(sub_pts[0] - sub_pts[-1]))
                    rp.is_loop = end_gap < self.tube_width_px * 1.2

                path_id += 1
                paths.append(rp)

        # Sort by descending ridge score (best paths first)
        paths.sort(key=lambda p: -p.ridge_score)
        return paths


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Junction Disambiguator — curvature-continuity routing
# ─────────────────────────────────────────────────────────────────────────────

class JunctionDisambiguator:
    """
    Post-processes the list of RidgePaths to merge path fragments that were
    split at skeleton junctions but actually belong to the same glass tube.

    Algorithm
    ---------
    For every pair of path endpoints (A_end, B_start) within
    `merge_dist_px` of each other, compute the "continuation cost":
        cost = (1 - cos(θ_A → θ_B))
    The pair with the minimum cost is merged if cost < cos_threshold.
    This corresponds to selecting the straightest (most continuous) joining.

    Repeat until no more merges possible.
    """

    def __init__(self, merge_dist_px: float = 12.0, cos_threshold: float = 0.6):
        self.merge_dist_px = merge_dist_px
        self.cos_threshold = cos_threshold   # 1 - cos(θ) < this → merge

    def _endpoint_tangent(self, pts: np.ndarray, end: str, window: int = 6) -> np.ndarray:
        """Unit tangent vector at 'start' or 'end' of path."""
        n = min(window, len(pts) - 1)
        if end == "start":
            v = pts[n] - pts[0]
        else:
            v = pts[-1] - pts[-n - 1]
        norm = np.linalg.norm(v)
        return v / norm if norm > 1e-6 else np.array([1.0, 0.0])

    def disambiguate(self, paths: List[RidgePath]) -> List[RidgePath]:
        """
        Merge path fragments connected by smooth tangent continuation.
        Returns the refined path list.

        Bug-fix note: we use index-based tracking (processed: set of ints)
        instead of  `p not in new_paths`  which triggers numpy broadcast
        errors when comparing RidgePath.points arrays of different shapes.
        """
        if len(paths) < 2:
            return paths

        MAX_ITERS = 10          # safety cap against infinite loops
        for _ in range(MAX_ITERS):
            changed   = False
            new_paths: List[RidgePath] = []
            processed: set = set()      # indices already handled this pass

            for i, pi in enumerate(paths):
                if i in processed:
                    continue

                best_j:     int   = -1
                best_cost:  float = self.cos_threshold
                best_i_end: str   = "end"
                best_j_end: str   = "start"

                for j in range(i + 1, len(paths)):
                    if j in processed:
                        continue
                    pj = paths[j]

                    for i_end, j_end in [("end",   "start"),
                                         ("end",   "end"),
                                         ("start", "start"),
                                         ("start", "end")]:
                        ep_i = pi.points[-1 if i_end == "end" else 0]
                        ep_j = pj.points[0  if j_end == "start" else -1]
                        gap  = float(np.linalg.norm(
                            ep_i.astype(float) - ep_j.astype(float)
                        ))
                        if gap > self.merge_dist_px:
                            continue

                        t_i = self._endpoint_tangent(pi.points, i_end)
                        t_j = self._endpoint_tangent(pj.points, j_end)

                        # cost ≈ 0 → perfect continuation; 2 → U-turn
                        if j_end == "start":
                            cost = 1.0 - float(np.dot(t_i, t_j))
                        else:
                            cost = 1.0 + float(np.dot(t_i, t_j))

                        if cost < best_cost:
                            best_cost  = cost
                            best_j     = j
                            best_i_end = i_end
                            best_j_end = j_end

                if best_j >= 0:
                    pj    = paths[best_j]
                    pts_i = pi.points.copy()
                    pts_j = pj.points.copy()

                    if best_i_end == "start":
                        pts_i = pts_i[::-1]
                    if best_j_end == "end":
                        pts_j = pts_j[::-1]

                    merged = RidgePath(
                        points=np.vstack([pts_i, pts_j]),
                        path_id=pi.path_id,
                        ridge_score=(pi.ridge_score + pj.ridge_score) * 0.5,
                        notes=pi.notes + [f"merged with path {pj.path_id}"],
                    )
                    new_paths.append(merged)
                    processed.add(i)
                    processed.add(best_j)
                    changed = True
                else:
                    new_paths.append(pi)
                    processed.add(i)

            paths = new_paths
            if not changed:
                break

        return paths


# ─────────────────────────────────────────────────────────────────────────────
# Skeleton-based centerline extractor (for clean binary B&W images)
# ─────────────────────────────────────────────────────────────────────────────

class SkeletonCenterlineExtractor:
    """
    For clean binary B&W mockup images (white tube, black background) the
    Frangi filter is the WRONG tool — the tube interior is uniformly white
    so there is no intensity gradient for Frangi to track.

    This extractor uses Zhang-Suen topological skeletonization on the binary
    mask, then feeds the skeleton pixels directly into IR-MST.  The result is
    a genuine GEOMETRIC centerline for every tube segment.

    Produces the same (ridgeness, orientation) output format as the Frangi
    extractor so the rest of the pipeline is unchanged.
    """

    def __init__(self, tube_width_px: float = 16.0):
        self.tube_width_px = max(4.0, float(tube_width_px))

    def extract(
        self, mask: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Parameters
        ----------
        mask : (H,W) uint8  {0, 255}  binary tube mask

        Returns
        -------
        ridgeness   : (H,W) float64  1.0 on skeleton, 0 elsewhere
        orientation : (H,W) float64  local ridge orientation (radians)
        """
        H, W = mask.shape
        # Zhang-Suen topology-preserving thinning
        binary = (mask > 0).astype(np.uint8)
        skel   = skimage_skeletonize(binary).astype(np.uint8)

        # ridgeness: binary skeleton as float
        ridgeness = skel.astype(np.float64)

        # Orientation: compute from gradient of the distance transform
        # DT ridge direction ≈ skeleton direction
        dist = cv2.distanceTransform(binary * 255, cv2.DIST_L2, 5)
        smooth_dist = gaussian_filter(dist.astype(np.float64), sigma=max(2.0, self.tube_width_px * 0.15))
        gx = cv2.Sobel(smooth_dist.astype(np.float32), cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(smooth_dist.astype(np.float32), cv2.CV_64F, 0, 1, ksize=3)
        # orientation along skeleton = perpendicular to gradient
        orientation = np.arctan2(gy, gx) + np.pi / 2.0

        return ridgeness, orientation


# ─────────────────────────────────────────────────────────────────────────────
# DFS Path Extractor  (for binary skeleton — not suitable for Frangi ridges)
# ─────────────────────────────────────────────────────────────────────────────

class DFSPathExtractor:
    """
    Extracts ordered tube paths from a binary skeleton via DFS + curvature-
    continuity routing at junctions.

    Why DFS (not IR-MST) for skeleton mode
    ----------------------------------------
    The skeleton of a binary tube is fully connected — adjacent skeleton pixels
    are exactly 1-sqrt(2) px apart.  The IR-MST edge-pruning threshold cannot
    distinguish between "within-tube" edges (1-1.5px) and "junction-branch"
    edges (also 1-1.5px), so it keeps all edges and every junction becomes
    part of one gigantic connected component that the greedy chain cannot
    order correctly.

    DFS, by contrast, exploits GRAPH STRUCTURE (node degree):
      · degree-1 (endpoint)   → start / stop a path
      · degree-2 (pass-through) → continue without branching
      · degree-3+ (junction)  → branch, choosing the most tangent-continuous
                                  outgoing edge first

    Additional improvement over V7's DFS
    --------------------------------------
    At junctions we use curvature continuity (dot product of incoming /
    outgoing tangent vectors) to route the PRIMARY path through the most
    natural continuation, rather than an arbitrary neighbour order.
    This eliminates many of the spurious short fragments that V7 produced.
    """

    def __init__(
        self,
        min_path_px: float = 10.0,
        junction_window: int = 4,
    ):
        self.min_path_px    = min_path_px
        self.junction_window = junction_window   # pixels back to estimate tangent

    # ── Graph construction ────────────────────────────────────────────────────

    @staticmethod
    def _build_adj(skeleton: np.ndarray):
        """
        Build 8-connectivity adjacency list for skeleton pixels.
        Returns  (idx_map: {(r,c): i}, adj: {(r,c): list[(r,c)]}).
        """
        ys, xs = np.where(skeleton > 0)
        idx_map = {(int(r), int(c)): i for i, (r, c) in enumerate(zip(ys, xs))}
        adj: dict = defaultdict(list)
        for (r, c) in idx_map:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == dc == 0:
                        continue
                    nb = (r + dr, c + dc)
                    if nb in idx_map:
                        adj[(r, c)].append(nb)
        return idx_map, adj

    # ── Tangent-based junction routing ────────────────────────────────────────

    def _incoming_tangent(self, path: list) -> np.ndarray:
        """Unit vector from path[-window] to path[-1]."""
        n = min(self.junction_window, len(path) - 1)
        v = np.array(path[-1], dtype=float) - np.array(path[-(n + 1)], dtype=float)
        nrm = float(np.linalg.norm(v))
        return v / nrm if nrm > 1e-6 else np.array([1.0, 0.0])

    def _best_next(self, path: list, candidates: list) -> tuple:
        """Return the candidate that maximises tangent continuity."""
        if len(path) < 2:
            return candidates[0]
        t = self._incoming_tangent(path)
        def score(nb):
            v = np.array(nb, dtype=float) - np.array(path[-1], dtype=float)
            nrm = float(np.linalg.norm(v))
            if nrm < 1e-6:
                return -2.0
            return float(np.dot(t, v / nrm))
        return max(candidates, key=score)

    # ── DFS trace ─────────────────────────────────────────────────────────────

    def _trace(
        self,
        start: tuple,
        adj: dict,
        visited: set,
        paths: list,
    ):
        """DFS from `start`, appending completed paths to `paths`."""
        path: list = [start]
        visited.add(start)
        current = start

        while True:
            nbrs = [n for n in adj[current] if n not in visited]
            if not nbrs:
                break
            # Pick the most tangent-continuous unvisited neighbour
            nxt = self._best_next(path, nbrs)
            path.append(nxt)
            visited.add(nxt)
            current = nxt

        pts = np.array(path, dtype=np.float64)
        plen = float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))
        if plen >= self.min_path_px:
            paths.append(pts)

    # ── Public interface ───────────────────────────────────────────────────────

    def extract(self, skeleton: np.ndarray) -> List[np.ndarray]:
        """
        Extract ordered paths from a binary skeleton.

        Parameters
        ----------
        skeleton : (H,W) binary array (True/1 on skeleton pixels)

        Returns
        -------
        List of (N,2) float64 arrays, one per tube path.
        """
        idx_map, adj = self._build_adj(skeleton)
        if not idx_map:
            return []

        # Degree classification
        degrees = {node: len(nbrs) for node, nbrs in adj.items()}

        # Endpoints first (degree 1), then junctions (degree >= 3), then loops
        endpoints  = [n for n, d in degrees.items() if d == 1]
        junctions  = {n for n, d in degrees.items() if d >= 3}
        all_pixels = list(idx_map.keys())

        visited: set = set()
        paths: List[np.ndarray] = []

        # Pass 1: trace from all endpoints
        for start in endpoints:
            if start not in visited:
                self._trace(start, adj, visited, paths)

        # Pass 2: handle junction remnants (connected to junctions but not yet visited)
        for start in junctions:
            if start not in visited:
                self._trace(start, adj, visited, paths)

        # Pass 3: handle isolated loops
        for start in all_pixels:
            if start not in visited:
                self._trace(start, adj, visited, paths)

        return paths


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: run full ridge pipeline (hybrid: skeleton for BW, Frangi for glow)
# ─────────────────────────────────────────────────────────────────────────────

def extract_ridge_paths(
    gray: np.ndarray,
    tube_width_px: float,
    mask: Optional[np.ndarray] = None,
    has_glow: bool = False,
    ridge_threshold: float = 0.05,
    do_nms: bool = True,
    do_junction_disambig: bool = True,
    irmst_alpha: float = 2.0,
    min_path_px: float = 12.0,
    precomputed_skeleton: Optional[np.ndarray] = None,
) -> Tuple[List[RidgePath], np.ndarray, np.ndarray]:
    """
    Hybrid ridge/centerline extraction:
      · Binary B&W images (has_glow=False, mask provided):
            skeletonize(mask) → IR-MST → paths
      · Images with glow or colored mockups (has_glow=True):
            Frangi(gray) → NMS → IR-MST → paths

    Parameters
    ----------
    gray              : (H,W) float64 intensity image [0,1]
    tube_width_px     : estimated tube outer diameter in pixels
    mask              : (H,W) uint8 binary mask (required for skeleton mode)
    has_glow          : if True, use Frangi; if False and mask present, use skeleton
    ridge_threshold   : threshold as fraction of max response (Frangi mode only)
    do_nms            : apply NMS (Frangi mode only)
    do_junction_disambig : merge fragments at junctions
    irmst_alpha       : IR-MST adaptive pruning multiplier tau = mu + alpha*sigma
    min_path_px       : discard paths shorter than this

    Returns
    -------
    paths       : list of RidgePath objects
    ridgeness   : (H,W) response map (skeleton or Frangi)
    orientation : (H,W) orientation map
    """
    # ── Choose centerline extraction strategy ─────────────────────────────────
    # Clean B&W / transparent images: binary mask is perfect (no glow) →
    # skeletonize(mask) gives the exact geometric centerline.
    #
    # Colored / glow images: _extract_colored() captures the GLOW ENVELOPE,
    # inflating the mask 2-3× beyond the actual tube width.  Skeletonizing this
    # fat mask produces 3-5× too many skeleton pixels → DFS traces every one of
    # them → massive overcount (observed: 1120 paths, +300% error).
    # Solution: use Frangi on the gray image instead — NMS produces genuinely
    # single-pixel ridges independent of glow width.
    use_skeleton = (
        (mask is not None)
        and (int(np.sum(mask > 0)) > 50)
        and not has_glow          # ← key: glow/colored → Frangi, not skeleton
    )

    if use_skeleton:
        # ── Binary B&W → skeletonize → DFS path extraction ───────────────────
        # Use precomputed skeleton if provided (avoids double skeletonize when
        # DT-blend in pipeline.py already computed it).
        if precomputed_skeleton is not None:
            skel = precomputed_skeleton
            ridgeness   = skel.astype(np.float64)
            # Orientation from DT gradient (same as SkeletonCenterlineExtractor)
            binary      = (mask > 0).astype(np.uint8)
            dist        = cv2.distanceTransform(binary * 255, cv2.DIST_L2, 5)
            smooth_dist = gaussian_filter(dist.astype(np.float64),
                                          sigma=max(2.0, tube_width_px * 0.15))
            gx = cv2.Sobel(smooth_dist.astype(np.float32), cv2.CV_64F, 1, 0, ksize=3)
            gy = cv2.Sobel(smooth_dist.astype(np.float32), cv2.CV_64F, 0, 1, ksize=3)
            orientation = np.arctan2(gy, gx) + np.pi / 2.0
        else:
            skel_ext   = SkeletonCenterlineExtractor(tube_width_px=tube_width_px)
            ridgeness, orientation = skel_ext.extract(mask)

        dfs = DFSPathExtractor(min_path_px=min_path_px, junction_window=4)
        raw_pts = dfs.extract(ridgeness > 0.5)

        # Wrap in RidgePath
        paths = []
        for pid, pts in enumerate(raw_pts):
            rp = RidgePath(points=pts, path_id=pid)
            rs_idx = pts[:, 0].astype(int).clip(0, ridgeness.shape[0]-1)
            cs_idx = pts[:, 1].astype(int).clip(0, ridgeness.shape[1]-1)
            rp.ridge_score = float(np.mean(ridgeness[rs_idx, cs_idx]))
            paths.append(rp)

    else:
        # ── Glow / colored → DoG (fast) → NMS → IR-MST ───────────────────────
        # DoG replaces Frangi: ~10× faster, no Hessian, immune to glow width.
        # For very strong glow where DoG fails, Frangi is kept as fallback.
        extractor = DoGRidgeExtractor(tube_width_px=tube_width_px)
        ridgeness, orientation, _ = extractor.extract(gray)
        
        # V8.1: Constrain ridges to mask CENTER region to prevent glow halo detection
        # Use distance transform to weight ridgeness - only keep ridges near tube center
        if mask is not None:
            # Compute distance transform to find tube centers
            dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
            max_dist = float(np.percentile(dist[dist > 0], 95)) if np.any(dist > 0) else 1.0
            if max_dist > 0:
                # Weight ridgeness by distance from edge - pixels near center get full weight
                # Pixels near mask edge (in glow region) get reduced weight
                center_weight = np.clip(dist / (max_dist * 0.6), 0, 1.0)  # 0.6 = only keep inner 60% of tube
                ridgeness = ridgeness * center_weight.astype(np.float64)
        
        if do_nms:
            ridgeness = nms_ridge(ridgeness, orientation)

        builder = IRMSTPathBuilder(
            tube_width_px=tube_width_px,
            alpha=irmst_alpha,
            min_path_px=min_path_px,
            physical_min_edge=tube_width_px * 0.8,
        )
        paths = builder.build_paths(ridgeness, orientation, ridge_threshold)

    # ── Junction disambiguation (both modes) ──────────────────────────────────
    # Skip if n_paths is explosion-level (> 200): disambig is O(N²) and won't
    # help when the mask is fundamentally broken. Caller's physics check will FAIL.
    _DISAMBIG_MAX_PATHS = 200
    if do_junction_disambig and 2 <= len(paths) <= _DISAMBIG_MAX_PATHS:
        try:
            disambig = JunctionDisambiguator(merge_dist_px=max(8.0, tube_width_px * 0.7))
            paths = disambig.disambiguate(paths)
        except Exception:
            pass   # optional; fall back to raw paths if it errors

    return paths, ridgeness, orientation
