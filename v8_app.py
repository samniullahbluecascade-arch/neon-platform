"""
v8_app.py  —  Neon Sign Studio  (V8)
======================================

ROUTES
    GET  /                       Studio UI (single-page app)
    POST /api/generate_mockup    Phase 1 : Logo + BG  →  colored neon mockup (PNG b64)
    POST /api/generate_bw        Phase 2 : Mockup     →  B&W tube sketch     (PNG b64)
    POST /api/full_pipeline      Phase 1+2+3 in one shot
    POST /measure                Phase 3 : B&W/colored image → LOC JSON  (existing)
    GET  /evaluate               Batch GT evaluation                       (existing)
    GET  /uploads/<file>         Serve saved uploads

USAGE
    cd "F:/python_files/Version 8"
    python v8_app.py
"""

from __future__ import annotations

import base64
import json
import os
import sys
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_from_directory

# ── Locate v8 modules ─────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from v8_pipeline import V8Pipeline, batch_evaluate, TIER_THRESHOLDS
from v8_input    import parse_gt_filename
from v8_generate import generate_mockup, generate_bw

# ── Config ────────────────────────────────────────────────────────────────────
GT_FOLDER  = Path(__file__).parent / "Ground_Truth"
UPLOAD_DIR = Path(__file__).parent / "uploads_v8"
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_UPLOAD_MB = 50

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

_pipeline = V8Pipeline(render_vis=True)


# ─────────────────────────────────────────────────────────────────────────────
# HTML — Neon Sign Studio UI
# ─────────────────────────────────────────────────────────────────────────────

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Neon Sign Studio — V8</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0a0a0a;--surf:#121212;--surf2:#1a1a1a;--surf3:#222;
  --bdr:#2a2a2a;--bdr2:#383838;
  --txt:#e2e2e2;--dim:#777;--dimmer:#444;
  --amber:#ffb347;--orange:#ff6b35;
  --green:#00e87a;--yellow:#ffe620;--red:#ff3c3c;--blue:#3d8bff;
  --amber-glow:rgba(255,179,71,.12);
}
body{font-family:'SF Mono','Fira Code','Cascadia Code',monospace;
     background:var(--bg);color:var(--txt);min-height:100vh;font-size:13px}

/* ── Header ── */
.hdr{display:flex;align-items:center;gap:14px;padding:18px 28px;
     background:linear-gradient(135deg,#110800 0%,#080810 100%);
     border-bottom:1px solid var(--bdr)}
.hdr-title{font-size:19px;color:var(--amber);letter-spacing:3px;
           text-transform:uppercase;font-weight:700}
.hdr-badge{background:var(--orange);color:#fff;font-size:9px;
           padding:2px 7px;border-radius:10px;letter-spacing:1.5px}

/* ── Tabs ── */
.tabs{display:flex;background:var(--surf);border-bottom:1px solid var(--bdr);padding:0 28px}
.tab{background:none;border:none;color:var(--dim);padding:13px 18px;cursor:pointer;
     font-family:inherit;font-size:12px;border-bottom:2px solid transparent;
     transition:color .15s,border-color .15s;letter-spacing:.5px}
.tab:hover{color:var(--txt)}
.tab.on{color:var(--amber);border-bottom-color:var(--amber)}

/* ── Main layout ── */
.main{padding:28px;max-width:1380px;margin:0 auto}
.panel{display:none}.panel.on{display:block}

/* ── Three-phase grid ── */
.phase-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:18px}
@media(max-width:900px){.phase-grid{grid-template-columns:1fr}}

/* ── Step card ── */
.card{background:var(--surf);border:1px solid var(--bdr);border-radius:8px;padding:18px;
      transition:border-color .2s,box-shadow .2s}
.card.step-active{border-color:var(--amber);box-shadow:0 0 18px var(--amber-glow)}
.card.step-done{border-color:var(--green)}
.card.step-err{border-color:var(--red)}

.step-num{display:inline-flex;align-items:center;justify-content:center;
          width:26px;height:26px;border-radius:50%;background:var(--surf3);
          color:var(--dim);font-size:11px;font-weight:700;margin-bottom:10px;
          transition:background .2s,color .2s}
.card.step-active .step-num{background:var(--amber);color:#000}
.card.step-done   .step-num{background:var(--green);color:#000}
.card.step-err    .step-num{background:var(--red);color:#fff}

.step-title{font-size:11px;color:var(--dim);text-transform:uppercase;
            letter-spacing:1.2px;margin-bottom:3px}
.step-sub  {font-size:10px;color:var(--dimmer);margin-bottom:14px}

/* ── Form controls ── */
label{display:block;font-size:10px;color:var(--dim);margin-bottom:4px;
      text-transform:uppercase;letter-spacing:.6px}
.req{color:var(--orange);margin-left:2px}
.opt{font-size:9px;color:var(--dimmer);background:var(--surf3);
     border:1px solid var(--bdr);padding:1px 5px;border-radius:3px;
     margin-left:5px;vertical-align:middle}

input[type=file],input[type=number],input[type=text],textarea,select{
  width:100%;background:var(--surf2);border:1px solid var(--bdr);
  color:var(--txt);padding:7px 9px;border-radius:4px;
  font-family:inherit;font-size:12px;margin-bottom:10px;transition:border-color .15s}
input[type=file]{padding:5px 9px;cursor:pointer}
textarea{min-height:54px;resize:vertical;line-height:1.5}
input:focus,textarea:focus,select:focus{outline:none;border-color:var(--amber)}
input[type=number]{-moz-appearance:textfield}
input[type=number]::-webkit-inner-spin-button{opacity:.4}

/* ── Buttons ── */
.btn{display:inline-flex;align-items:center;gap:6px;border:none;
     padding:8px 16px;border-radius:4px;cursor:pointer;
     font-family:inherit;font-size:11px;font-weight:700;
     text-transform:uppercase;letter-spacing:1px;transition:all .15s}
.btn:disabled{opacity:.35;cursor:not-allowed}
.btn-primary{background:var(--amber);color:#000;padding:10px 22px;font-size:12px}
.btn-primary:hover:not(:disabled){background:#ffd080}
.btn-action{background:var(--orange);color:#fff}
.btn-action:hover:not(:disabled){background:#ff8c5a}
.btn-ghost{background:transparent;border:1px solid var(--bdr2);color:var(--dim)}
.btn-ghost:hover:not(:disabled){border-color:var(--amber);color:var(--amber)}
.btn-sm{padding:5px 11px;font-size:10px}

.action-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:4px}
.status-line{font-size:11px;color:var(--dim);min-height:18px}

/* ── Image preview ── */
.preview{width:100%;min-height:130px;background:#000;
         border:1px dashed var(--bdr2);border-radius:4px;
         display:flex;align-items:center;justify-content:center;
         overflow:hidden;margin-bottom:8px;position:relative}
.preview img{max-width:100%;max-height:260px;object-fit:contain;display:block}
.preview .ph{color:var(--dimmer);font-size:10px;text-align:center;padding:18px}
.preview .loading{position:absolute;inset:0;background:rgba(0,0,0,.82);
                  display:flex;align-items:center;justify-content:center;
                  gap:8px;color:var(--amber);font-size:11px}
@keyframes spin{to{transform:rotate(360deg)}}
.spinner{width:16px;height:16px;border:2px solid var(--bdr2);
         border-top-color:var(--amber);border-radius:50%;
         animation:spin .7s linear infinite;flex-shrink:0}

/* ── Download link ── */
.dl-link{font-size:9px;color:var(--dim);background:var(--surf3);
         border:1px solid var(--bdr);padding:3px 8px;border-radius:3px;
         text-decoration:none;display:none}
.dl-link:hover{color:var(--amber);border-color:var(--amber)}

/* ── Error banner ── */
.err-banner{background:rgba(255,60,60,.08);border:1px solid var(--red);
            border-radius:4px;padding:10px 14px;color:var(--red);
            font-size:11px;margin-top:10px;display:none;white-space:pre-wrap}

/* ── LOC results card ── */
.results-card{background:var(--surf);border:1px solid var(--bdr);
              border-radius:8px;padding:22px;margin-top:22px;display:none}
.results-card h3{color:var(--amber);font-size:12px;text-transform:uppercase;
                 letter-spacing:2px;margin-bottom:16px;
                 border-bottom:1px solid var(--bdr);padding-bottom:10px}

.metric-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));
             gap:10px;margin-bottom:16px}
.metric{background:var(--surf2);border:1px solid var(--bdr);
        border-radius:4px;padding:11px 13px}
.m-label{font-size:9px;color:var(--dim);text-transform:uppercase;
          letter-spacing:.5px;margin-bottom:4px}
.m-val{font-size:21px;font-weight:700;color:var(--txt);line-height:1}
.m-unit{font-size:10px;color:var(--dim);margin-left:3px}

.tier-GLASS_CUT{color:var(--green)}
.tier-QUOTE{color:#80ff55}
.tier-ESTIMATE{color:var(--yellow)}
.tier-MARGINAL{color:#ff8800}
.tier-FAIL{color:var(--red)}
.tier-UNKNOWN{color:var(--dim)}

.log{background:#000;border:1px solid var(--bdr);border-radius:4px;
     padding:11px;font-size:10px;line-height:1.75;white-space:pre-wrap;
     max-height:190px;overflow-y:auto;color:#bbb}
.overlay-row{display:flex;gap:18px;flex-wrap:wrap;margin-top:14px}
.overlay-col{flex:1;min-width:200px}
.overlay-col .oc-label{font-size:9px;color:var(--dim);margin-bottom:6px;
                        text-transform:uppercase;letter-spacing:.5px}
.overlay-col img{max-width:100%;max-height:280px;border-radius:4px}

hr{border:none;border-top:1px solid var(--bdr);margin:18px 0}

/* ── Quick Measure / Evaluate ── */
.simple-card{background:var(--surf);border:1px solid var(--bdr);
             border-radius:8px;padding:24px;max-width:900px}
.simple-card h3{color:var(--amber);font-size:12px;text-transform:uppercase;
                letter-spacing:2px;margin-bottom:16px}
.mono-out{background:#000;border:1px solid var(--bdr);border-radius:4px;
          padding:12px;font-size:10px;white-space:pre-wrap;
          max-height:440px;overflow-y:auto;display:none;color:#bbb}
code{background:var(--surf3);padding:1px 5px;border-radius:3px;color:var(--amber)}

/* ── Input pair ── */
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:600px){.row2{grid-template-columns:1fr}}
</style>
</head>
<body>

<!-- ── Header ──────────────────────────────────────────────────────────── -->
<div class="hdr">
  <span class="hdr-title">🌟 Neon Sign Studio</span>
  <span class="hdr-badge">V8</span>
</div>

<!-- ── Tabs ────────────────────────────────────────────────────────────── -->
<div class="tabs">
  <button class="tab on"  onclick="tab('studio',  this)">Sign Studio</button>
  <button class="tab"     onclick="tab('measure', this)">Quick Measure</button>
  <button class="tab"     onclick="tab('evaluate',this)">Batch Evaluate</button>
</div>

<div class="main">

<!-- ═══════════════════  SIGN STUDIO  ═══════════════════════════════════ -->
<div class="panel on" id="panel-studio">

  <!-- ── Mode Toggle ─────────────────────────────────────────────── -->
  <div style="display:flex;gap:10px;margin-bottom:18px;align-items:center;">
    <label style="margin:0;">Workflow Mode:</label>
    <button class="btn btn-sm" id="mode-full" onclick="setMode('full')" style="background:var(--amber);color:#000;">Full Pipeline</button>
    <button class="btn btn-sm btn-ghost" id="mode-bw-only" onclick="setMode('bw-only')">B&W from Mockup</button>
  </div>

  <div class="phase-grid">

    <!-- ── CARD 1 : Design Input ──────────────────────────────────── -->
    <div class="card step-active" id="c1">
      <div class="step-num">1</div>
      <div class="step-title" id="c1-title">Design Input</div>
      <div class="step-sub" id="c1-sub">Upload your logo/design + optional background scene</div>

      <!-- Logo upload (shown in full mode) -->
      <div id="logo-section">
        <label>Logo / Design Image <span class="req">*</span></label>
        <input type="file" id="logo-file" accept=".png,.jpg,.jpeg,.webp,.bmp"
               onchange="onLogoChange()">
      </div>

      <!-- Mockup upload (shown in B&W-only mode) -->
      <div id="mockup-section" style="display:none;">
        <label>Colored Mockup Image <span class="req">*</span></label>
        <input type="file" id="mockup-file" accept=".png,.jpg,.jpeg,.webp,.bmp"
               onchange="onMockupChange()">
      </div>

      <label>Background Environment <span class="opt">optional</span></label>
      <input type="file" id="bg-file" accept=".png,.jpg,.jpeg,.webp,.bmp">

      <label>Additional Instructions <span class="opt">optional</span></label>
      <textarea id="extra"
        placeholder="e.g. Make the lettering electric blue, add a border frame, neon flex tube only…"></textarea>

      <div class="preview" id="logo-prev">
        <div class="ph">Logo preview appears here</div>
      </div>
    </div>

    <!-- ── CARD 2 : Colored Mockup ────────────────────────────────── -->
    <div class="card" id="c2">
      <div class="step-num">2</div>
      <div class="step-title">Colored Neon Mockup</div>
      <div class="step-sub">Gemini renders photorealistic LED neon sign on scene</div>

      <div class="preview" id="mockup-prev">
        <div class="ph">Run Step 1 to generate mockup</div>
      </div>

      <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px">
        <a class="dl-link" id="mockup-dl" download="neon_mockup.png">⬇ Download</a>
      </div>

      <button class="btn btn-ghost btn-sm" id="bw-btn"
              onclick="runGenerateBW()" disabled>
        Convert to B&W Sketch →
      </button>
    </div>

    <!-- ── CARD 3 : B&W Sketch + LOC ──────────────────────────────── -->
    <div class="card" id="c3">
      <div class="step-num">3</div>
      <div class="step-title">B&W Sketch + LOC</div>
      <div class="step-sub">Tube centerlines extracted then measured</div>

      <div class="preview" id="bw-prev">
        <div class="ph">Run Step 2 to generate B&W sketch</div>
      </div>

      <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px">
        <a class="dl-link" id="bw-dl" download="neon_bw_sketch.png">⬇ Download</a>
      </div>

      <hr>

      <div class="row2">
        <div>
          <label>Sign Width (inches) <span class="req">*</span></label>
          <input type="number" id="width-in" value="24" step="0.5" min="1"
                 placeholder="e.g. 24">
        </div>
        <div>
          <label>Ground Truth LOC (m) <span class="opt">optional</span></label>
          <input type="number" id="gt-m" step="0.01" placeholder="blank = unknown">
        </div>
      </div>

      <button class="btn btn-ghost btn-sm" id="measure-btn"
              onclick="runMeasure()" disabled>
        Measure LOC →
      </button>
    </div>

  </div><!-- phase-grid -->

  <!-- ── Pipeline actions ──────────────────────────────────────────── -->
  <div class="action-row">
    <button class="btn btn-primary" id="full-btn"
            onclick="runFullPipeline()" disabled>
      ⚡ Run Full Pipeline
    </button>
    <button class="btn btn-action" id="step1-btn"
            onclick="runGenerateMockup()" disabled>
      Step 1 — Generate Mockup
    </button>
    <span class="status-line" id="studio-status"></span>
  </div>

  <div class="err-banner" id="studio-err"></div>

  <!-- ── LOC Results ────────────────────────────────────────────────── -->
  <div class="results-card" id="loc-card">
    <h3>📊 LOC Measurement Results</h3>

    <div class="metric-grid">
      <div class="metric">
        <div class="m-label">Measured LOC</div>
        <div><span class="m-val" id="r-loc">—</span><span class="m-unit">m</span></div>
      </div>
      <div class="metric">
        <div class="m-label">Tier</div>
        <div class="m-val" id="r-tier">—</div>
      </div>
      <div class="metric">
        <div class="m-label">Confidence</div>
        <div><span class="m-val" id="r-conf">—</span><span class="m-unit">%</span></div>
      </div>
      <div class="metric">
        <div class="m-label">Tube Width</div>
        <div><span class="m-val" id="r-tube">—</span><span class="m-unit">mm</span></div>
      </div>
      <div class="metric">
        <div class="m-label">px / inch</div>
        <div class="m-val" id="r-ppi">—</div>
      </div>
      <div class="metric">
        <div class="m-label">Paths [S / A / F]</div>
        <div class="m-val" id="r-paths">—</div>
      </div>
      <div class="metric">
        <div class="m-label">Uncertainty</div>
        <div class="m-val" id="r-uncertainty">—</div>
      </div>
      <div class="metric">
        <div class="m-label">Area-based</div>
        <div><span class="m-val" id="r-area">—</span><span class="m-unit">m</span></div>
      </div>
      <div class="metric">
        <div class="m-label">Bias / Risk</div>
        <div class="m-val" id="r-bias">—</div>
      </div>
      <div class="metric">
        <div class="m-label">Overcount Ratio</div>
        <div class="m-val" id="r-ocr">—</div>
      </div>
      <div class="metric" id="r-err-card" style="display:none">
        <div class="m-label">Error vs GT</div>
        <div><span class="m-val" id="r-err">—</span><span class="m-unit">%</span></div>
      </div>
      <div class="metric">
        <div class="m-label">Elapsed</div>
        <div><span class="m-val" id="r-elapsed">—</span><span class="m-unit">s</span></div>
      </div>
    </div>

    <label>Reasoning Log</label>
    <div class="log" id="r-log"></div>

    <div class="overlay-row">
      <div class="overlay-col">
        <div class="oc-label">Ridge + Path Overlay</div>
        <img id="r-overlay" style="display:none">
      </div>
      <div class="overlay-col">
        <div class="oc-label">Frangi Ridge Map</div>
        <img id="r-ridge" style="display:none">
      </div>
    </div>
  </div>

</div><!-- panel-studio -->


<!-- ═══════════════════  QUICK MEASURE  ═══════════════════════════════ -->
<div class="panel" id="panel-measure">
  <div class="simple-card">
    <h3>Quick Measure</h3>

    <label>Sign Image (PNG / JPG / SVG / CDR) <span class="req">*</span></label>
    <input type="file" id="q-img"
           accept=".png,.jpg,.jpeg,.svg,.cdr,.bmp,.tiff,.webp">

    <div class="row2">
      <div>
        <label>Sign Width (inches) <span class="req">*</span></label>
        <input type="number" id="q-width" value="24" step="0.5" min="1">
      </div>
      <div>
        <label>Ground Truth LOC (m) <span class="opt">optional</span></label>
        <input type="number" id="q-gt" step="0.01" placeholder="blank = unknown">
      </div>
    </div>

    <label>Force Format <span class="opt">optional</span></label>
    <select id="q-fmt">
      <option value="">auto-detect</option>
      <option value="bw">B&amp;W (white tube on black)</option>
      <option value="transparent">Transparent PNG</option>
      <option value="colored">Colored mockup</option>
    </select>

    <button class="btn btn-primary" id="q-btn" onclick="runQuickMeasure()">
      ⚡ Measure LOC
    </button>

    <div class="err-banner" id="q-err"></div>

    <div style="margin-top:16px">
      <div class="mono-out" id="q-out"></div>
      <div class="overlay-row" id="q-results-row" style="display:none">
        <div class="overlay-col">
          <div class="oc-label">Ridge + Path Overlay</div>
          <img id="q-overlay" style="max-width:100%;max-height:350px;border-radius:4px;display:none">
        </div>
        <div class="overlay-col">
          <div class="oc-label">Frangi Ridge Map</div>
          <img id="q-ridge" style="max-width:100%;max-height:350px;border-radius:4px;display:none">
        </div>
      </div>
    </div>
  </div>
</div>


<!-- ═══════════════════  BATCH EVALUATE  ══════════════════════════════ -->
<div class="panel" id="panel-evaluate">
  <div class="simple-card">
    <h3>Batch Evaluate</h3>
    <p style="font-size:11px;color:var(--dim);margin-bottom:16px">
      Runs V8 on every image in the Ground Truth folder.<br>
      Each file must be named <code>{width_in} {gt_m}.png</code>.
    </p>
    <button class="btn btn-primary" onclick="runEvaluate()">📊 Run Evaluation</button>
    <div class="mono-out" id="eval-out" style="margin-top:16px"></div>
  </div>
</div>

</div><!-- main -->

<script>
// ── State ─────────────────────────────────────────────────────────────────
let mockupB64 = null;   // current Phase-1 result (raw base64, no data-URL prefix)
let bwB64     = null;   // current Phase-2 result

// ── Tab switch ────────────────────────────────────────────────────────────
function tab(name, btn) {
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('on'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('on'));
  btn.classList.add('on');
  document.getElementById('panel-' + name).classList.add('on');
}

// ── Mode toggle ───────────────────────────────────────────────────────────
let currentMode = 'full'; // 'full' or 'bw-only'

function setMode(mode) {
  currentMode = mode;
  
  // Update button styles
  const fullBtn = document.getElementById('mode-full');
  const bwBtn = document.getElementById('mode-bw-only');
  
  if (mode === 'full') {
    fullBtn.style.background = 'var(--amber)';
    fullBtn.style.color = '#000';
    bwBtn.style.background = 'transparent';
    bwBtn.style.color = 'var(--dim)';
    
    // Show logo section, hide mockup section
    document.getElementById('logo-section').style.display = 'block';
    document.getElementById('mockup-section').style.display = 'none';
    document.getElementById('c2').style.display = 'block';
    
    // Update card 1 title/subtitle
    document.getElementById('c1-title').textContent = 'Design Input';
    document.getElementById('c1-sub').textContent = 'Upload your logo/design + optional background scene';
    
    // Update primary buttons
    document.getElementById('full-btn').style.display = 'inline-flex';
    document.getElementById('step1-btn').style.display = 'inline-flex';
    document.getElementById('full-btn').textContent = '⚡ Run Full Pipeline';
    document.getElementById('full-btn').onclick = runFullPipeline;
    
  } else {
    // B&W-only mode
    bwBtn.style.background = 'var(--amber)';
    bwBtn.style.color = '#000';
    fullBtn.style.background = 'transparent';
    fullBtn.style.color = 'var(--dim)';
    
    // Hide logo section, show mockup section
    document.getElementById('logo-section').style.display = 'none';
    document.getElementById('mockup-section').style.display = 'block';
    document.getElementById('c2').style.display = 'none'; // Hide card 2 in B&W-only mode
    
    // Update card 1 title/subtitle
    document.getElementById('c1-title').textContent = 'Mockup Input';
    document.getElementById('c1-sub').textContent = 'Upload existing colored mockup for B&W conversion';
    
    // Update primary buttons
    document.getElementById('full-btn').style.display = 'inline-flex';
    document.getElementById('step1-btn').style.display = 'none';
    document.getElementById('full-btn').textContent = '⚡ Convert to B&W →';
    document.getElementById('full-btn').onclick = runBWOnlyPipeline;
  }
  
  _updatePrimaryBtns();
  clearErr('studio-err');
}

// ── Logo file → preview ───────────────────────────────────────────────────
function onLogoChange() {
  const file = document.getElementById('logo-file').files[0];
  if (!file) return;
  const url = URL.createObjectURL(file);
  document.getElementById('logo-prev').innerHTML =
    `<img src="${url}" alt="logo">`;
  _updatePrimaryBtns();
}

// ── Mockup file → preview ─────────────────────────────────────────────────
function onMockupChange() {
  const file = document.getElementById('mockup-file').files[0];
  if (!file) return;
  const url = URL.createObjectURL(file);
  document.getElementById('logo-prev').innerHTML =
    `<img src="${url}" alt="mockup">`;
  _updatePrimaryBtns();
}

function _updatePrimaryBtns() {
  let has = false;
  if (currentMode === 'full') {
    has = document.getElementById('logo-file').files.length > 0;
    document.getElementById('step1-btn').disabled = !has;
  } else {
    has = document.getElementById('mockup-file').files.length > 0;
  }
  document.getElementById('full-btn').disabled  = !has;
}

// ── Spinner helpers ───────────────────────────────────────────────────────
function showLoading(prevId, msg) {
  const el = document.getElementById(prevId);
  el.innerHTML =
    `<div class="loading"><div class="spinner"></div>${msg}</div>`;
}
function setErr(bannerId, msg) {
  const el = document.getElementById(bannerId);
  el.textContent = '❌ ' + msg;
  el.style.display = 'block';
}
function clearErr(bannerId) {
  document.getElementById(bannerId).style.display = 'none';
}

// ── Card state ────────────────────────────────────────────────────────────
function cardState(id, state) {   // state: '' | 'step-active' | 'step-done' | 'step-err'
  const c = document.getElementById(id);
  c.classList.remove('step-active','step-done','step-err');
  if (state) c.classList.add(state);
}

// ── Set preview image from base64 ─────────────────────────────────────────
function setPreview(prevId, b64, dlId, filename) {
  document.getElementById(prevId).innerHTML =
    `<img src="data:image/png;base64,${b64}" alt="result">`;
  if (dlId) {
    const dl = document.getElementById(dlId);
    dl.href    = 'data:image/png;base64,' + b64;
    dl.download = filename;
    dl.style.display = 'inline-block';
  }
}

// ── Status line ───────────────────────────────────────────────────────────
function setStatus(msg) {
  document.getElementById('studio-status').textContent = msg;
}

// ─────────────────────────────────────────────────────────────────────────
// Step 1 — Generate Mockup
// ─────────────────────────────────────────────────────────────────────────
async function runGenerateMockup() {
  const logoFile = document.getElementById('logo-file').files[0];
  if (!logoFile) { setErr('studio-err', 'Upload a logo/design image first.'); return; }

  clearErr('studio-err');
  document.getElementById('step1-btn').disabled = true;
  document.getElementById('full-btn').disabled  = true;
  showLoading('mockup-prev', 'Generating colored mockup…');
  cardState('c2', 'step-active');
  setStatus('Step 1 — calling Gemini for colored neon mockup…');

  const fd = new FormData();
  fd.append('logo', logoFile);
  const bgFile = document.getElementById('bg-file').files[0];
  if (bgFile) fd.append('background', bgFile);
  fd.append('additional', document.getElementById('extra').value);

  try {
    const r = await fetch('/api/generate_mockup', { method: 'POST', body: fd });
    const d = await r.json();
    if (d.error) throw new Error(d.error);

    mockupB64 = d.image_b64;
    setPreview('mockup-prev', mockupB64, 'mockup-dl', 'neon_mockup.png');
    cardState('c1', 'step-done');
    cardState('c2', 'step-done');
    document.getElementById('bw-btn').disabled = false;
    setStatus('✓ Mockup generated — run Step 2 to convert to B&W sketch');
  } catch(e) {
    cardState('c2', 'step-err');
    document.getElementById('mockup-prev').innerHTML =
      '<div class="ph" style="color:var(--red)">Generation failed</div>';
    setErr('studio-err', e.message);
    setStatus('');
  } finally {
    _updatePrimaryBtns();
  }
}

// ─────────────────────────────────────────────────────────────────────────
// Step 2 — Convert to B&W
// ─────────────────────────────────────────────────────────────────────────
async function runGenerateBW() {
  if (!mockupB64) { setErr('studio-err', 'Generate the colored mockup first (Step 1).'); return; }
  clearErr('studio-err');

  document.getElementById('bw-btn').disabled = true;
  showLoading('bw-prev', 'Converting to B&W tube sketch…');
  cardState('c3', 'step-active');
  setStatus('Step 2 — extracting tube centerlines via Gemini…');

  const blob = b64Blob(mockupB64, 'image/png');
  const fd   = new FormData();
  fd.append('mockup', blob, 'mockup.png');

  try {
    const r = await fetch('/api/generate_bw', { method: 'POST', body: fd });
    const d = await r.json();
    if (d.error) throw new Error(d.error);

    bwB64 = d.image_b64;
    setPreview('bw-prev', bwB64, 'bw-dl', 'neon_bw_sketch.png');
    cardState('c3', 'step-active');   // stays active — width still needed
    document.getElementById('measure-btn').disabled = false;
    setStatus('✓ B&W sketch ready — enter sign width and run Measure LOC');
  } catch(e) {
    cardState('c3', 'step-err');
    document.getElementById('bw-prev').innerHTML =
      '<div class="ph" style="color:var(--red)">Conversion failed</div>';
    setErr('studio-err', e.message);
    setStatus('');
  } finally {
    document.getElementById('bw-btn').disabled = false;
  }
}

// ─────────────────────────────────────────────────────────────────────────
// Step 3 — Measure LOC
// ─────────────────────────────────────────────────────────────────────────
async function runMeasure() {
  if (!bwB64) { setErr('studio-err', 'Generate the B&W sketch first (Step 2).'); return; }

  const widthIn = parseFloat(document.getElementById('width-in').value);
  if (!widthIn || widthIn <= 0) {
    setErr('studio-err', 'Enter a valid sign width in inches (Step 3 panel).');
    return;
  }

  clearErr('studio-err');
  document.getElementById('measure-btn').disabled = true;
  setStatus('Step 3 — running V8 LOC pipeline…');

  const blob = b64Blob(bwB64, 'image/png');
  const fd   = new FormData();
  fd.append('image',              blob, 'bw_sketch.png');
  fd.append('real_width_inches',  widthIn);
  fd.append('force_format',       'bw');
  const gt = document.getElementById('gt-m').value.trim();
  if (gt) fd.append('gt_m', gt);

  try {
    const r = await fetch('/measure', { method: 'POST', body: fd });
    const d = await r.json();
    if (d.error) throw new Error(d.error);

    cardState('c3', 'step-done');
    renderResults(d);
    setStatus('✓ Full pipeline complete');
  } catch(e) {
    setErr('studio-err', e.message);
    setStatus('');
  } finally {
    document.getElementById('measure-btn').disabled = false;
  }
}

// ─────────────────────────────────────────────────────────────────────────
// B&W-Only Pipeline — mockup → B&W → measure (skip Phase 1)
// ─────────────────────────────────────────────────────────────────────────
async function runBWOnlyPipeline() {
  const mockupFile = document.getElementById('mockup-file').files[0];
  if (!mockupFile) { setErr('studio-err', 'Upload a colored mockup image first.'); return; }

  const widthIn = parseFloat(document.getElementById('width-in').value);
  if (!widthIn || widthIn <= 0) {
    setErr('studio-err', 'Enter sign width (inches) in the Step 3 panel before running.');
    return;
  }

  clearErr('studio-err');
  document.getElementById('full-btn').disabled  = true;

  showLoading('bw-prev', 'Phase 2 — converting mockup to B&W…');
  cardState('c3', 'step-active');
  document.getElementById('loc-card').style.display = 'none';
  setStatus('Running B&W-only pipeline — this may take 20–60 s…');

  const fd = new FormData();
  fd.append('mockup', mockupFile);
  fd.append('additional',         document.getElementById('extra').value);
  fd.append('real_width_inches',  widthIn);
  const gt = document.getElementById('gt-m').value.trim();
  if (gt) fd.append('gt_m', gt);

  try {
    const r = await fetch('/api/bw_only_pipeline', { method: 'POST', body: fd });
    const d = await r.json();
    if (d.error) throw new Error(d.error);

    bwB64     = d.bw_b64;

    setPreview('bw-prev',     bwB64,     'bw-dl',     'neon_bw_sketch.png');

    document.getElementById('measure-btn').disabled= false;

    cardState('c1', 'step-done');
    cardState('c3', 'step-done');

    renderResults(d.measurement);
    setStatus('✓ B&W-only pipeline complete');

  } catch(e) {
    cardState('c3', 'step-err');
    document.getElementById('bw-prev').innerHTML =
      '<div class="ph" style="color:var(--red)">Pipeline failed</div>';
    setErr('studio-err', e.message);
    setStatus('');
  } finally {
    document.getElementById('full-btn').disabled = false;
  }
}

// ─────────────────────────────────────────────────────────────────────────
// Full Pipeline — all 3 phases in one server-side call
// ─────────────────────────────────────────────────────────────────────────
async function runFullPipeline() {
  const logoFile = document.getElementById('logo-file').files[0];
  if (!logoFile) { setErr('studio-err', 'Upload a logo/design image first.'); return; }

  const widthIn = parseFloat(document.getElementById('width-in').value);
  if (!widthIn || widthIn <= 0) {
    setErr('studio-err', 'Enter sign width (inches) in the Step 3 panel before running full pipeline.');
    return;
  }

  clearErr('studio-err');
  document.getElementById('full-btn').disabled  = true;
  document.getElementById('step1-btn').disabled = true;

  showLoading('mockup-prev', 'Phase 1 — generating mockup…');
  showLoading('bw-prev',     'Phase 2 — waiting…');
  cardState('c2', 'step-active');
  cardState('c3', 'step-active');
  document.getElementById('loc-card').style.display = 'none';
  setStatus('Running full pipeline — this may take 30–90 s…');

  const fd = new FormData();
  fd.append('logo', logoFile);
  const bgFile = document.getElementById('bg-file').files[0];
  if (bgFile) fd.append('background', bgFile);
  fd.append('additional',         document.getElementById('extra').value);
  fd.append('real_width_inches',  widthIn);
  const gt = document.getElementById('gt-m').value.trim();
  if (gt) fd.append('gt_m', gt);

  try {
    const r = await fetch('/api/full_pipeline', { method: 'POST', body: fd });
    const d = await r.json();
    if (d.error) throw new Error(d.error);

    mockupB64 = d.mockup_b64;
    bwB64     = d.bw_b64;

    setPreview('mockup-prev', mockupB64, 'mockup-dl', 'neon_mockup.png');
    setPreview('bw-prev',     bwB64,     'bw-dl',     'neon_bw_sketch.png');

    document.getElementById('bw-btn').disabled     = false;
    document.getElementById('measure-btn').disabled= false;

    cardState('c1', 'step-done');
    cardState('c2', 'step-done');
    cardState('c3', 'step-done');

    renderResults(d.measurement);
    setStatus('✓ Full pipeline complete');

  } catch(e) {
    cardState('c2', 'step-err');
    cardState('c3', 'step-err');
    document.getElementById('mockup-prev').innerHTML =
      '<div class="ph" style="color:var(--red)">Pipeline failed</div>';
    document.getElementById('bw-prev').innerHTML =
      '<div class="ph" style="color:var(--red)">Pipeline failed</div>';
    setErr('studio-err', e.message);
    setStatus('');
  } finally {
    _updatePrimaryBtns();
  }
}

// ─────────────────────────────────────────────────────────────────────────
// Quick Measure
// ─────────────────────────────────────────────────────────────────────────
async function runQuickMeasure() {
  clearErr('q-err');
  document.getElementById('q-results-row').style.display = 'none';
  const imgFile = document.getElementById('q-img').files[0];
  if (!imgFile) { setErr('q-err', 'Upload a sign image.'); return; }

  const widthIn = parseFloat(document.getElementById('q-width').value);
  if (!widthIn || widthIn <= 0) { setErr('q-err', 'Enter a valid sign width.'); return; }

  const btn = document.getElementById('q-btn');
  btn.disabled    = true;
  btn.textContent = '⏳ Measuring…';

  const fd = new FormData();
  fd.append('image',             imgFile);
  fd.append('real_width_inches', widthIn);
  const gt = document.getElementById('q-gt').value.trim();
  if (gt) fd.append('gt_m', gt);
  const fmt = document.getElementById('q-fmt').value;
  if (fmt) fd.append('force_format', fmt);

  try {
    const r = await fetch('/measure', { method: 'POST', body: fd });
    const d = await r.json();
    if (d.error) throw new Error(d.error);

    const tier = d.tier || 'UNKNOWN';
    let log = '';
    log += `Measured LOC : ${(d.measured_m||0).toFixed(4)} m\n`;
    log += `Uncertainty  : [${(d.loc_low_m||0).toFixed(4)} - ${(d.loc_high_m||0).toFixed(4)}] m\n`;
    log += `Area-based   : ${(d.area_m||0).toFixed(4)} m\n`;
    if (d.gt_m)          log += `Ground Truth : ${d.gt_m.toFixed(4)} m\n`;
    if (d.error_pct!=null) log +=
      `Error        : ${d.error_pct>=0?'+':''}${d.error_pct.toFixed(2)} %\n`;
    log += `Tier         : ${tier}\n`;
    log += `Confidence   : ${((d.confidence||0)*100).toFixed(1)} %\n`;
    log += `Bias/Risk    : ${d.bias_direction || 'NEUTRAL'} (risk=${(d.overcount_risk||0).toFixed(2)})\n`;
    log += `Tube width   : ${(d.tube_width_mm||0).toFixed(1)} mm  (cv=${(d.tube_cv||0).toFixed(2)}${d.tube_width_uncertain?' ⚠UNCERTAIN':''})\n`;
    log += `px / inch    : ${(d.px_per_inch||0).toFixed(1)}\n`;
    log += `Paths        : ${d.n_paths||0}  `+
           `[S=${d.n_straight_segs||0} A=${d.n_arc_segs||0} F=${d.n_freeform_segs||0}]\n`;
    log += `Overcount Ratio: ${(d.overcount_ratio||1.0).toFixed(3)}\n`;
    log += `Format       : ${d.input_format||'?'}\n`;
    log += `Elapsed      : ${(d.elapsed_s||0).toFixed(1)} s\n`;
    if (d.physics_ok===false) log += '⚠  Physics check FAILED\n';
    log += '\nReasoning:\n' + (d.reasoning||[]).map(l=>'  '+l).join('\n');

    const out = document.getElementById('q-out');
    out.textContent   = log;
    out.style.display = 'block';

    if (d.overlay_b64 || d.ridge_b64) {
      document.getElementById('q-results-row').style.display = 'flex';
    }
    if (d.overlay_b64) {
      const img = document.getElementById('q-overlay');
      img.src          = 'data:image/png;base64,' + d.overlay_b64;
      img.style.display= 'block';
    }
    if (d.ridge_b64) {
      const img = document.getElementById('q-ridge');
      img.src          = 'data:image/png;base64,' + d.ridge_b64;
      img.style.display= 'block';
    }
  } catch(e) {
    setErr('q-err', e.message);
  } finally {
    btn.disabled    = false;
    btn.textContent = '⚡ Measure LOC';
  }
}

// ─────────────────────────────────────────────────────────────────────────
// Batch Evaluate
// ─────────────────────────────────────────────────────────────────────────
async function runEvaluate() {
  const out = document.getElementById('eval-out');
  out.style.display = 'block';
  out.textContent   = '⏳ Running batch evaluation…';
  try {
    const r = await fetch('/evaluate');
    const d = await r.json();
    out.textContent = JSON.stringify(d, null, 2);
  } catch(e) {
    out.textContent = '❌ ' + e.message;
  }
}

// ─────────────────────────────────────────────────────────────────────────
// Render LOC results card
// ─────────────────────────────────────────────────────────────────────────
function renderResults(d) {
  const card = document.getElementById('loc-card');
  card.style.display = 'block';
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  const tier = d.tier || 'UNKNOWN';
  document.getElementById('r-loc').textContent  = (d.measured_m||0).toFixed(4);
  document.getElementById('r-tier').innerHTML   =
    `<span class="tier-${tier}">${tier}</span>`;
  document.getElementById('r-conf').textContent = ((d.confidence||0)*100).toFixed(1);
  document.getElementById('r-tube').textContent = (d.tube_width_mm||0).toFixed(1);
  document.getElementById('r-ppi').textContent  = (d.px_per_inch||0).toFixed(1);
  document.getElementById('r-paths').textContent=
    `${d.n_paths||0}  [${d.n_straight_segs||0} / ${d.n_arc_segs||0} / ${d.n_freeform_segs||0}]`;
  document.getElementById('r-elapsed').textContent = (d.elapsed_s||0).toFixed(1);

  // V8.1 New Metrics
  document.getElementById('r-uncertainty').textContent = 
    `[${(d.loc_low_m||0).toFixed(3)} - ${(d.loc_high_m||0).toFixed(3)}] m`;
  document.getElementById('r-area').textContent = (d.area_m||0).toFixed(4);
  document.getElementById('r-bias').textContent = 
    `${d.bias_direction || 'NEUTRAL'} (${(d.overcount_risk||0).toFixed(2)})`;
  document.getElementById('r-ocr').textContent = (d.overcount_ratio||1.0).toFixed(3);

  if (d.error_pct != null) {
    document.getElementById('r-err-card').style.display = 'block';
    document.getElementById('r-err').textContent =
      (d.error_pct>=0?'+':'') + d.error_pct.toFixed(2);
  }

  document.getElementById('r-log').textContent = (d.reasoning||[]).join('\n');

  if (d.overlay_b64) {
    const img = document.getElementById('r-overlay');
    img.src = 'data:image/png;base64,' + d.overlay_b64;
    img.style.display = 'block';
  }
  if (d.ridge_b64) {
    const img = document.getElementById('r-ridge');
    img.src = 'data:image/png;base64,' + d.ridge_b64;
    img.style.display = 'block';
  }
}

// ─────────────────────────────────────────────────────────────────────────
// Utility — base64 string → Blob
// ─────────────────────────────────────────────────────────────────────────
function b64Blob(b64, mime) {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return new Blob([arr], { type: mime });
}
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Helper — bytes → base64 string (no data-URL prefix)
# ─────────────────────────────────────────────────────────────────────────────

def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


# ─────────────────────────────────────────────────────────────────────────────
# Helper — file upload → (bytes, mime)
# ─────────────────────────────────────────────────────────────────────────────

def _read_upload(field: str) -> tuple[bytes, str]:
    """Read a required file upload field; returns (bytes, mime_type)."""
    f = request.files.get(field)
    if f is None or f.filename == "":
        raise ValueError(f"Missing file upload: '{field}'")
    raw = f.read()
    if not raw:
        raise ValueError(f"Empty file upload: '{field}'")
    mime = f.mimetype or "application/octet-stream"
    return raw, mime


# ─────────────────────────────────────────────────────────────────────────────
# Result serialisation
# ─────────────────────────────────────────────────────────────────────────────

def _result_to_dict(r) -> dict:
    return {
        "measured_m":      round(r.measured_m,    6),
        "tier":            r.tier,
        "confidence":      round(r.confidence,    4),
        "px_per_inch":     round(r.px_per_inch,   2),
        "tube_width_mm":   round(r.tube_width_mm, 2),
        "gt_m":            r.gt_m,
        "error_pct":       round(r.error_pct, 4) if r.error_pct is not None else None,
        "n_paths":         r.n_paths,
        "n_straight_segs": r.n_straight_segs,
        "n_arc_segs":      r.n_arc_segs,
        "n_freeform_segs": r.n_freeform_segs,
        "physics_ok":      r.physics_ok,
        "physics_notes":   r.physics_notes,
        "reasoning":       r.reasoning,
        "source":          r.source,
        "elapsed_s":       round(r.elapsed_s, 3),
        "input_format":    r.input_format,
        "overlay_b64":     r.overlay_b64,
        "ridge_b64":       r.ridge_b64,
        # ── V8.1 New Metrics ──
        "loc_low_m":       round(getattr(r, "loc_low_m", 0), 4),
        "loc_high_m":      round(getattr(r, "loc_high_m", 0), 4),
        "area_m":          round(getattr(r, "area_m", 0), 4),
        "overcount_ratio": round(getattr(r, "overcount_ratio", 1.0), 3),
        "overcount_risk":  round(getattr(r, "overcount_risk", 0), 3),
        "bias_direction":  getattr(r, "bias_direction", "NEUTRAL"),
        "tube_cv":         round(getattr(r, "tube_cv", 0), 3),
        "tube_width_uncertain": getattr(r, "tube_width_uncertain", False),
        "dfs_m":           round(getattr(r, "dfs_m", 0), 4),
        "dtw_m":           round(getattr(r, "dtw_m", 0), 4),
        "mean_dt_ratio":   round(getattr(r, "mean_dt_ratio", 0), 3),
        "pct_fat":         round(getattr(r, "pct_fat", 0), 3),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return render_template_string(_HTML)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ── Phase 1 ──────────────────────────────────────────────────────────────────

@app.route("/api/generate_mockup", methods=["POST"])
def api_generate_mockup():
    """
    POST /api/generate_mockup
    Form fields:
      logo          : file  (required) — logo / design image
      background    : file  (optional) — background environment photo
      additional    : str   (optional) — extra instructions for the prompt
    Returns:
      { "image_b64": "<PNG base64>" }
    """
    try:
        logo_bytes, logo_mime = _read_upload("logo")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    bg_bytes = bg_mime = None
    bg_file = request.files.get("background")
    if bg_file and bg_file.filename:
        raw = bg_file.read()
        if raw:
            bg_bytes = raw
            bg_mime  = bg_file.mimetype or "image/jpeg"

    additional = request.form.get("additional", "").strip()

    try:
        png = generate_mockup(logo_bytes, logo_mime, bg_bytes, bg_mime, additional)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"image_b64": _b64(png)})


# ── Phase 2 ──────────────────────────────────────────────────────────────────

@app.route("/api/generate_bw", methods=["POST"])
def api_generate_bw():
    """
    POST /api/generate_bw
    Form fields:
      mockup       : file (required) — colored neon mockup PNG
      additional   : str  (optional) — extra instructions for B&W conversion
    Returns:
      { "image_b64": "<PNG base64>" }   (post-processed strict binary)
    """
    try:
        mockup_bytes, mockup_mime = _read_upload("mockup")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    additional = request.form.get("additional", "").strip()

    try:
        png = generate_bw(mockup_bytes, mockup_mime, additional)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"image_b64": _b64(png)})


# ── B&W-Only Pipeline (Phase 2 + 3 server-side) ───────────────────────────────

@app.route("/api/bw_only_pipeline", methods=["POST"])
def api_bw_only_pipeline():
    """
    POST /api/bw_only_pipeline
    Form fields:
      mockup             : file   (required) — colored neon mockup PNG
      additional         : str    (optional) — extra instructions for B&W conversion
      real_width_inches  : float  (required)
      gt_m               : float  (optional)
    Returns:
      {
        "bw_b64":      "<PNG base64>",
        "measurement": { ...V8Result dict... }
      }
    """
    # ── Mockup ───────────────────────────────────────────────────────────────
    try:
        mockup_bytes, mockup_mime = _read_upload("mockup")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    additional = request.form.get("additional", "").strip()

    # ── Width ─────────────────────────────────────────────────────────────────
    try:
        width_in = float(request.form.get("real_width_inches", 0))
        if width_in <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "real_width_inches must be a positive number"}), 400

    gt_raw = request.form.get("gt_m", "").strip()
    gt_m   = float(gt_raw) if gt_raw else None

    # ── Phase 2 : Mockup → B&W Sketch ────────────────────────────────────────
    try:
        bw_png = generate_bw(mockup_bytes, mockup_mime, additional)
    except Exception as exc:
        return jsonify({"error": f"Phase 2 (B&W conversion) failed: {exc}"}), 500

    # ── Phase 3 : B&W → LOC Measurement ──────────────────────────────────────
    try:
        result = _pipeline.measure_from_bytes(
            bw_png, width_in, gt_m=gt_m,
            filename="studio_bw.png",
            force_format="bw",
        )
    except Exception as exc:
        return jsonify({"error": f"Phase 3 (LOC measurement) failed: {exc}"}), 500

    return jsonify({
        "bw_b64":      _b64(bw_png),
        "measurement": _result_to_dict(result),
    })


# ── Full Pipeline (Phase 1 + 2 + 3 server-side) ───────────────────────────────

@app.route("/api/full_pipeline", methods=["POST"])
def api_full_pipeline():
    """
    POST /api/full_pipeline
    Form fields:
      logo               : file   (required)
      background         : file   (optional)
      additional         : str    (optional)
      real_width_inches  : float  (required)
      gt_m               : float  (optional)
    Returns:
      {
        "mockup_b64":  "<PNG base64>",
        "bw_b64":      "<PNG base64>",
        "measurement": { ...V8Result dict... }
      }
    """
    # ── Logo ─────────────────────────────────────────────────────────────────
    try:
        logo_bytes, logo_mime = _read_upload("logo")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    bg_bytes = bg_mime = None
    bg_file = request.files.get("background")
    if bg_file and bg_file.filename:
        raw = bg_file.read()
        if raw:
            bg_bytes = raw
            bg_mime  = bg_file.mimetype or "image/jpeg"

    additional = request.form.get("additional", "").strip()

    # ── Width ─────────────────────────────────────────────────────────────────
    try:
        width_in = float(request.form.get("real_width_inches", 0))
        if width_in <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "real_width_inches must be a positive number"}), 400

    gt_raw = request.form.get("gt_m", "").strip()
    gt_m   = float(gt_raw) if gt_raw else None

    # ── Phase 1 : Logo → Colored Mockup ──────────────────────────────────────
    try:
        mockup_png = generate_mockup(logo_bytes, logo_mime, bg_bytes, bg_mime, additional)
    except Exception as exc:
        return jsonify({"error": f"Phase 1 (mockup generation) failed: {exc}"}), 500

    # ── Phase 2 : Mockup → B&W Sketch ────────────────────────────────────────
    try:
        bw_png = generate_bw(mockup_png, "image/png")
    except Exception as exc:
        return jsonify({"error": f"Phase 2 (B&W conversion) failed: {exc}"}), 500

    # ── Phase 3 : B&W → LOC Measurement ──────────────────────────────────────
    try:
        result = _pipeline.measure_from_bytes(
            bw_png, width_in, gt_m=gt_m,
            filename="studio_bw.png",
            force_format="bw",
        )
    except Exception as exc:
        return jsonify({"error": f"Phase 3 (LOC measurement) failed: {exc}"}), 500

    return jsonify({
        "mockup_b64":  _b64(mockup_png),
        "bw_b64":      _b64(bw_png),
        "measurement": _result_to_dict(result),
    })


# ── Existing Phase 3 stand-alone ─────────────────────────────────────────────

@app.route("/measure", methods=["POST"])
def measure():
    """
    POST /measure
    Form fields:
      image              : file   (required)
      real_width_inches  : float  (required)
      gt_m               : float  (optional)
      force_format       : str    (optional)  'bw'|'transparent'|'colored'
    Returns JSON V8Result dict.
    """
    if "image" not in request.files or request.files["image"].filename == "":
        return jsonify({"error": "No image file provided"}), 400

    f         = request.files["image"]
    img_bytes = f.read()
    if not img_bytes:
        return jsonify({"error": "Empty file"}), 400

    try:
        width_in = float(request.form.get("real_width_inches", 24))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid real_width_inches"}), 400

    gt_raw  = request.form.get("gt_m", "").strip()
    gt_m    = float(gt_raw) if gt_raw else None
    fmt     = request.form.get("force_format")

    result = _pipeline.measure_from_bytes(
        img_bytes, width_in, gt_m=gt_m,
        filename=f.filename or "upload.png",
        force_format=fmt,
    )
    return jsonify(_result_to_dict(result))


# ── Batch evaluation ──────────────────────────────────────────────────────────

@app.route("/evaluate", methods=["GET"])
def evaluate():
    if not GT_FOLDER.exists():
        return jsonify({"error": f"GT folder not found: {GT_FOLDER}"}), 404
    summary = batch_evaluate(str(GT_FOLDER), render_vis=False, verbose=False)
    return jsonify(summary)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"\n{'='*60}")
    print(f"  Neon Sign Studio V8  →  http://127.0.0.1:{port}")
    print(f"  GT folder : {GT_FOLDER}")
    print(f"{'='*60}\n")
    app.run(debug=True, host="0.0.0.0", port=port)
