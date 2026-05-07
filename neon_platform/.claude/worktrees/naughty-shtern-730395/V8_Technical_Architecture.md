, I think # V8 Neon Sign Measurement System - Complete Technical Architecture

## System Overview

The V8 system measures the total length of neon tube (LOC - Length of Content) in sign designs from various input formats. It processes images, vector files, and mockups to output accurate tube length measurements in meters.

---

## 1. INPUT LAYER (v8_input.py)

### Purpose
Universal input handler that normalizes any input format into a standardized internal representation.

### Supported Formats
| Format | Extension | Handling |
|--------|-----------|----------|
| Black & White PNG/JPG | `.png`, `.jpg` | Direct processing |
| Transparent PNG | `.png` | Alpha channel as mask |
| Colored Mockups | `.png`, `.jpg` | Saturation-based extraction |
| SVG Vector | `.svg` | Exact path length calculation |
| CorelDraw CDR | `.cdr` | ZIP extraction → SVG or raster |

### Key Processing Steps

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Input File    │────▶│  Format Detection  │────▶│   Extraction    │
│  (any format)   │     │  (BW/Transparent/  │     │  (gray + mask)  │
│                 │     │   Colored/SVG/CDR) │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  LoadedSign     │◀────│  Tight Content    │◀────│  Tube Width     │
│  (normalized)   │     │  Bounding Box     │     │  Estimation     │
│                 │     │  (CRITICAL FIX)   │     │  (DT-based)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Critical Innovation: Tight Content Crop
**Problem in V7**: Used full image frame width → systematic bias when sign has black padding  
**V8 Solution**: Detect tight content bounding box first, then calibrate:
```
px_per_inch = content_bbox_width_px / real_width_inches
```

### Output Data Structure: `LoadedSign`
- `gray`: Float64 array [0,1] - intensity image (cropped)
- `mask`: UInt8 array {0,255} - tube pixel mask (cropped)
- `meta`: `InputMeta` object with calibration data
- `sat`: Optional saturation channel (colored images only)

---

## 2. RIDGE EXTRACTION LAYER (v8_ridge.py)

### Purpose
Find the geometric centerline of neon tubes regardless of tube width, glow effects, or anti-aliasing.

### Two Extraction Strategies

#### Strategy A: Skeleton + IR-MST (for clean B&W)
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Binary Mask   │────▶│  Skeletonization  │────▶│  Distance       │
│                 │     │  (Zhang-Suen)     │     │  Transform (DT)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  RidgePath[]    │◀────│  IR-MST Graph     │◀────│  k-NN Graph on   │
│  (ordered pixels)│     │  Building         │     │  Skeleton Pixels │
│                 │     │  (prune long edges)│    │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

#### Strategy B: Frangi + DoG (for glow/colored images)
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Gray Image    │────▶│  Frangi Filter    │────▶│  Non-Maximum    │
│                 │     │  (Hessian-based)   │     │  Suppression    │
│                 │     │  Multi-scale       │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  RidgePath[]    │◀────│  IR-MST on        │◀────│  Ridge Pixels   │
│                 │     │  Ridge Pixels      │     │  (brightest)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### IR-MST Algorithm (Intensity-Ridge Minimum Spanning Tree)
1. **Build k-NN graph** on ridge/skeleton pixels (k=8)
2. **Compute adaptive threshold**: τ = μ + α·σ of edge lengths
3. **Prune long edges** > τ (they span separate glass tubes)
4. **Connected components** = individual tube paths
5. **Order pixels** via greedy chain from degree-1 endpoints

### Junction Disambiguation
At skeleton nodes with degree ≥ 3, route by **maximum curvature continuity** (smallest bend), eliminating spurious branches in script lettering.

---

## 3. GEOMETRY MEASUREMENT LAYER (v8_geometry.py)

### Purpose
Measure accurate arc length along extracted paths using three geometric regimes.

### Pipeline Per Path
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Ordered Points │────▶│  Savitzky-Golay   │────▶│  Segment        │
│  (from ridge)   │     │  Smoothing        │     │  Partitioner    │
│                 │     │  (window ∝ tube)  │     │  (DP-based)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Total Length   │◀────│  Three-Regime     │◀────│  Regime         │
│  (meters)       │     │  Measurement      │     │  Classification │
│                 │     │                   │     │  (per segment)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Three Measurement Regimes

| Regime | Detection | Method | Formula |
|--------|-----------|--------|---------|
| **STRAIGHT** | R² > 0.999 | Euclidean distance | `length = √((x₂-x₁)² + (y₂-y₁)²)` |
| **ARC** | Circle fit RMS < 1.8px, arc angle > 4° | Pratt algebraic circle fit | `length = radius × θ` |
| **FREEFORM** | Neither above | Adaptive Bézier + Gauss-Legendre | 64-point numerical integration |

### Key Algorithms
- **RANSAC line fitting**: Robust to outlier skeleton pixels at junctions
- **Pratt circle fit**: Numerically stable algebraic method
- **Dynamic Programming partitioner**: Optimal segment boundaries vs PELT on curvature

---

## 4. ML CORRECTION LAYER (v8_ml_train.py, v8_ml_predict.py)

### Purpose
Learn residual corrections from pipeline features to improve accuracy.

### Two Model Modes

#### Full Model (v8_model.pkl)
- **Features**: dfs_m, dtw_m, mean_dt_ratio, white_pct, tube_mm, sign_width_in, confidence
- **Use case**: After full DFS+DT-blend pipeline
- **Accuracy**: Highest
- **Time**: 20-140s per image

#### Fast Model (v8_model_dt_fast.pkl)
- **Features**: dtw_m, mean_dt_ratio, white_pct, tube_mm, sign_width_in (no DFS)
- **Use case**: Real-time preview
- **Accuracy**: Slightly lower
- **Time**: ~0.5s per image

### Model Training Pipeline
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Batch Process  │────▶│  Feature Extract  │────▶│  features.json  │
│  All GT Images  │     │  (v8_feature_)    │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Best Model     │◀────│  Model Selection  │◀────│  Train 3 Models │
│  (saved .pkl)   │     │  (LOO CV)         │     │  (Ridge/GB/RF)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Models Evaluated
1. **Ridge Regression** (L2) - handles collinear DFS/DTW
2. **Gradient Boosting** - handles nonlinear blend ratios
3. **Random Forest** - robust to outliers

**Selection**: Leave-One-Out cross-validation on ~70-80 samples

---

## 5. ORCHESTRATION LAYER (v8_pipeline.py)

### Purpose
Coordinate all components, apply physics validation, and produce final measurement.

### Complete Data Flow
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INPUT                                          │
│  (PNG/JPG/SVG/CDR + real_width_inches + optional real_height_inches)       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         v8_input.load_sign()                                │
│  • Format detection and extraction                                          │
│  • Tight content bounding box (CRITICAL FIX)                                  │
│  • Calibration: px_per_inch = content_width / real_width                      │
│  • Tube width estimation via distance transform                             │
│  • Glow detection for strategy selection                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────┴─────────────────┐
                    │                                   │
            ┌───────▼────────┐              ┌───────────▼────────┐
            │  SVG/CDR Path  │              │  Low Resolution?   │
            │  (exact LOC)   │              │  (ppi < 8)        │
            └───────┬────────┘              └───────────┬────────┘
                    │                                   │
                    │ YES                               │ YES
                    ▼                                   ▼
            ┌───────────────┐              ┌─────────────────────────┐
            │ Return exact  │              │ White-area geometric    │
            │ vector length │              │ estimator fallback      │
            │ (bypass all)  │              │ (physics-based)         │
            └───────────────┘              └─────────────────────────┘
                                                    │
                                            NO      │
                    ┌───────────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  Resolution capping       │
        │  (40 ppi for Frangi,     │
        │   20 ppi for DT)         │
        │  Scale-invariant         │
        └─────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  Strategy Selection:    │
        │  • Glow/colored → DoG   │
        │  • Clean B&W → Skeleton │
        └─────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  v8_ridge.extract_      │
        │  ridge_paths()           │
        │  • Frangi/DoG ridges    │
        │  • IR-MST graph building │
        │  • Junction disambiguation│
        └─────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  Path Explosion Guard   │
        │  (n_paths > 200?)        │
        │  → V7 plateau fallback   │
        └─────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  v8_geometry.measure_    │
        │  all_paths()            │
        │  • Smoothing             │
        │  • DP segmentation       │
        │  • Three-regime measure  │
        └─────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  DT-Weighted Blend      │
        │  (corrects DFS under-   │
        │   estimation at merged  │
        │   parallel strokes)      │
        │  • Capped vs uncapped    │
        │    based on tube width   │
        └─────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  Physics Validation      │
        │  • Resolution check       │
        │  • Coverage consistency   │
        │  • Tube OD plausibility   │
        │  • LOC-per-inch ratio     │
        └─────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  Overcount Detection     │
        │  (DFS vs area-based)     │
        │  → Area correction if     │
        │   ratio > 1.5             │
        └─────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  ML Correction (optional)│
        │  → predict_full() or     │
        │   predict_fast()          │
        └─────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  Tier Assignment         │
        │  • GLASS_CUT (≤5%)      │
        │  • QUOTE (≤10%)         │
        │  • ESTIMATE (≤20%)       │
        │  • MARGINAL (≤35%)       │
        │  • FAIL (>35%)            │
        └─────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  V8Result Output         │
        │  • measured_m            │
        │  • confidence metrics     │
        │  • uncertainty bounds     │
        │  • reasoning log          │
        │  • visualization B64      │
        └─────────────────────────┘
```

### Key Pipeline Innovations

#### DT-Weighted Blend (Step 3b)
Corrects systematic DFS underestimation at merged parallel strokes:
- **Uncapped DTW**: `Σ(DT_on_skel) / tube_radius` — amplifies junction overcount
- **Capped DTW**: `Σ(min(DT, radius)) / tube_radius` — junction-accurate
- **Selection**: Use capped when `mean_DT/radius >= 1.20` AND `tube_width >= 6.5mm`

#### Overcount Detection
```
overcount_ratio = DFS_measurement / area_based_estimate
```
- `ratio > 1.5` → definite overcounting → use area estimate
- `ratio < 0.5` → undercounting → use area estimate
- `ratio 0.8-1.2` → self-consistent → keep DFS

#### Physics Validation Checks
1. **Resolution guard**: ppi ≥ 8 (fail), ppi ≥ 15 (warn)
2. **Coverage consistency**: skeleton_area / white_area ≤ 1.25
3. **Mask fraction**: 0.3% ≤ white% ≤ 58%
4. **n_paths explosion**: ≤ 200 paths
5. **Tube OD**: 4mm ≤ diameter ≤ 22mm
6. **LOC-per-inch**: 25mm ≤ ratio ≤ 450mm per inch

---

## 6. OUTPUT: V8Result Data Structure

### Core Measurements
| Field | Type | Description |
|-------|------|-------------|
| `measured_m` | float | Final tube length in meters |
| `tier` | str | Quality tier (GLASS_CUT/QUOTE/ESTIMATE/MARGINAL/FAIL) |
| `confidence` | float | 0-1 aggregate fit quality |
| `px_per_inch` | float | Horizontal calibration |
| `px_per_inch_y` | float | Vertical calibration (if anisotropic) |
| `tube_width_mm` | float | Estimated tube outer diameter |

### Uncertainty Bounds (Business-Critical)
| Field | Description |
|-------|-------------|
| `loc_low_m` | Minimum plausible LOC (22mm tube assumption) |
| `loc_high_m` | Maximum plausible LOC (4mm tube assumption) |
| `area_m` | Area-based estimate at best tube width |
| `overcount_ratio` | DFS / area consistency check |

### Quality Signals (No GT Required)
| Field | Description |
|-------|-------------|
| `confidence_no_gt` | Physics-grounded reliability 0-1 |
| `predicted_tier` | Tier inferred from signal quality |
| `loc_spread` | `loc_high / measured` — uncertainty multiplier |
| `detection_incomplete` | Path density too low |
| `hollow_ratio` | Enclosed dark / white pixels (outline fonts) |
| `tube_cv` | DT coefficient of variation (<0.25 = uniform) |
| `tube_width_uncertain` | DT vs implied tube width disagree >40% |

### Diagnostic Internals
| Field | Description |
|-------|-------------|
| `dfs_m` | DFS-only measurement before blend |
| `dtw_m` | DT-weighted measurement |
| `mean_dt_ratio` | Mean(DT_on_skel) / tube_radius |
| `white_pct` | Mask white pixel fraction |
| `n_paths` | Number of extracted tube paths |
| `n_straight_segs` | Straight segment count |
| `n_arc_segs` | Arc segment count |
| `n_freeform_segs` | Freeform segment count |

### Visualizations
| Field | Format | Description |
|-------|--------|-------------|
| `overlay_b64` | Base64 PNG | Annotated measurement overlay |
| `ridge_b64` | Base64 PNG | Ridge detection heatmap |

---

## 7. BATCH EVALUATION (run_batch.py)

### Purpose
Run pipeline on entire Ground_Truth folder and compute accuracy statistics.

### Process
```
For each image file "W GT.png":
    1. Parse filename → width_inches, gt_meters
    2. Run V8Pipeline.measure()
    3. Record: predicted_m, error_pct, tier, timing
    4. Generate accuracy chart
```

### Output Statistics
- Mean absolute error (%)
- Median absolute error (%)
- Max absolute error (%)
- Tier distribution (GLASS_CUT/QUOTE/ESTIMATE/MARGINAL/FAIL counts)

---

## 8. SYSTEM CONSTANTS & PHYSICAL BOUNDS

### Resolution Thresholds
| Constant | Value | Meaning |
|----------|-------|---------|
| `MAX_RIDGE_PPI` | 40 | Cap for Frangi/skeleton (preserves topology) |
| `MAX_DT_PPI` | 20 | Cap for DT-blend (scale-invariant) |
| `RESOLUTION_FAIL_PPI` | 8 | Hard fail below (use area estimator) |
| `RESOLUTION_WARN_PPI` | 15 | Warn below (marginal reliability) |

### Physical Neon Bounds
| Constant | Value | Meaning |
|----------|-------|---------|
| `LED_NEON_MM_MIN` | 4.0 | Narrowest real LED flex / design stroke |
| `LED_NEON_MM_MAX` | 22.0 | Widest standard LED flex OD |
| `MIN_M_PER_INCH` | 0.025 | 25mm tube per inch of sign (lower bound) |
| `MAX_M_PER_INCH` | 0.450 | 450mm per inch (upper bound) |
| `MIN_TOTAL_M` | 0.05 | Absolute minimum plausible LOC |
| `MAX_TOTAL_M` | 120.0 | Absolute maximum plausible LOC |

### Quality Thresholds
| Tier | Error Threshold | Use Case |
|------|-----------------|----------|
| GLASS_CUT | ≤ 5% | Direct glass cutting |
| QUOTE | ≤ 10% | Safe for customer quotes |
| ESTIMATE | ≤ 20% | Rough cost estimation |
| MARGINAL | ≤ 35% | Manual re-measure required |
| FAIL | > 35% | Pipeline failed |

---

## 9. FILE ORGANIZATION

```
Version_8_beta/
├── v8_input.py           # Universal input handler
├── v8_ridge.py           # Ridge extraction (Frangi/DoG + IR-MST)
├── v8_geometry.py        # Three-regime measurement
├── v8_pipeline.py        # Main orchestration + physics validation
├── v8_ml_train.py        # ML model training
├── v8_ml_predict.py      # ML model inference
├── v8_feature_extract.py # Feature extraction for training
├── v8_generate.py        # Test image generation
├── v8_app.py             # Web application entry point
├── run_batch.py          # Batch evaluation script
├── v8_model.pkl          # Trained full model
├── v8_model_dt_fast.pkl  # Trained fast model
├── v8_model_meta.json    # Model metadata
├── features.json         # Training features database
├── Ground_Truth/         # Test images with GT filenames
├── assets/               # Training/test assets
└── SVG_output/           # Vector output storage
```

---

## 10. KEY ALGORITHMS SUMMARY

### Algorithm 1: Tight Content Crop
```python
# Find bounding box of non-zero mask pixels
rows = np.any(mask > 0, axis=1)
cols = np.any(mask > 0, axis=0)
r0, r1 = first/last True in rows
c0, c1 = first/last True in cols
# Crop and recalibrate
px_per_inch = (c1 - c0) / real_width_inches
```

### Algorithm 2: IR-MST Path Building
```python
# Build k-NN graph on ridge pixels
kdtree = cKDTree(ridge_pixels)
edges = kdtree.query_pairs(k=8, distance_upper_bound=max_dist)
# Compute adaptive threshold
lengths = [edge_lengths]
tau = mean(lengths) + alpha * std(lengths)
# Prune long edges (span separate tubes)
valid_edges = [e for e in edges if length(e) <= tau]
# Connected components = tube paths
paths = connected_components(valid_edges)
```

### Algorithm 3: Three-Regime Measurement
```python
for segment in dp_partition(path):
    if ransac_line_r2(segment) > 0.999:
        length = euclidean_distance(endpoints)
        regime = STRAIGHT
    elif pratt_circle_fit(segment) and arc_angle > 4°:
        length = radius * arc_angle
        regime = ARC
    else:
        length = bezier_gauss_legendre_integral(segment)
        regime = FREEFORM
```

### Algorithm 4: DT-Weighted Blend
```python
# Compute both capped and uncapped DTW
dt_on_skel = distance_transform[skeleton > 0]
r = tube_width_px / 2

# Uncapped: amplifies at junctions
L_uncapped = sum(dt_on_skel) / r

# Capped: junction-accurate
L_capped = sum(min(dt, r) for dt in dt_on_skel) / r

# Select based on tube thickness and DT ratio
if mean(dt_on_skel)/r >= 1.20 and tube_mm >= 6.5:
    blend = (DFS + L_capped) / 2
else:
    blend = (DFS + L_uncapped) / 2
```

---

## 11. PERFORMANCE CHARACTERISTICS

| Component | Typical Time | Dominant Operation |
|-----------|--------------|-------------------|
| Input loading | 0.1-0.3s | PIL decode + format detection |
| Ridge extraction (skeleton) | 0.5-2s | Zhang-Suen skeletonization |
| Ridge extraction (Frangi) | 2-10s | Multi-scale Hessian computation |
| IR-MST graph building | 0.1-0.5s | k-NN query + MST |
| Geometry measurement | 0.1-1s | RANSAC + Pratt fits per segment |
| DT-blend | 0.05-0.2s | Distance transform |
| ML prediction | <0.01s | sklearn inference |
| **Total (clean B&W)** | **1-5s** | Skeleton + geometry |
| **Total (glow/colored)** | **5-20s** | Frangi + geometry |
| **Total (large sign)** | **20-140s** | High-res Frangi |

---

## 12. ERROR SOURCES & MITIGATIONS

| Error Source | Mitigation |
|--------------|------------|
| Black padding around sign | Tight content crop (V8 fix) |
| Glow/bloom effects | DoG/Frangi ridge extraction |
| Anti-aliasing artifacts | Adaptive threshold scanning |
| Merged parallel strokes | DT-weighted blend |
| Skeleton overcounting at junctions | Capped DTW + overcount_ratio check |
| Low resolution (< 8 ppi) | White-area geometric estimator |
| Anisotropic images | 2-D calibration with k consistency check |
| Hollow-outline fonts | Hollow ratio detection (diagnostic) |
| Tube width uncertainty | Self-consistency check (DT vs implied) |

---

This architecture provides a robust, physics-grounded measurement system with transparent reasoning, uncertainty quantification, and graceful degradation for challenging inputs.