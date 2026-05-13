'use client';
import { useEffect, useState, useRef, ChangeEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { studio, MeasurementResult } from '@/lib/api';
import NavBar from '@/components/NavBar';
import PipelineStrip, { Phase } from '@/components/PipelineStrip';
import TubeSkeleton from '@/components/TubeSkeleton';
import StreamingLog from '@/components/StreamingLog';

type Tab  = 'mockup' | 'sketch' | 'quote';
type Mode = 'full' | 'bw-only';

const COST_PER_METRE = 10;
const MARKUP_RATE    = 0.40;

const TIER_LABELS: Record<string, string> = {
  GLASS_CUT: 'Cut-ready',
  QUOTE:     'Quote-grade',
  ESTIMATE:  'Rough estimate',
  MARGINAL:  'Needs review',
  FAIL:      'Re-upload needed',
  UNKNOWN:   '—',
};

const COLOR_OPTIONS = [
  { hex: '#E8175D', glow: '232,23,93',  name: 'Hot Pink' },
  { hex: '#FF4500', glow: '255,69,0',   name: 'Red Orange' },
  { hex: '#D97706', glow: '217,119,6',  name: 'Warm Amber' },
  { hex: '#0891B2', glow: '8,145,178',  name: 'Neon Cyan' },
  { hex: '#16A34A', glow: '22,163,74',  name: 'Electric Green' },
  { hex: '#7C3AED', glow: '124,58,237', name: 'Ultra Violet' },
  { hex: '#111827', glow: '17,24,39',   name: 'Pure White' },
];

export default function StudioPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  const [mode, setMode] = useState<Mode>('full');
  const [tab,  setTab]  = useState<Tab>('mockup');

  // Inputs
  const [logo, setLogo]             = useState<File | null>(null);
  const [bg,   setBg]               = useState<File | null>(null);
  const [mockupFile, setMockupFile] = useState<File | null>(null);
  const [extra, setExtra]           = useState('');
  const [neonColor, setNeonColor]   = useState(COLOR_OPTIONS[0]);
  const [width, setWidth]           = useState('24');
  const [uvNeon, setUvNeon]         = useState(false);
  const [uvPart, setUvPart]         = useState('');
  const [gt, setGt]                 = useState('');

  // Outputs
  const [mockupB64, setMockupB64]     = useState<string | null>(null);
  const [bwB64, setBwB64]             = useState<string | null>(null);
  const [measurement, setMeasurement] = useState<MeasurementResult | null>(null);

  // Pipeline state
  const [busy,  setBusy]   = useState(false);
  const [phase, setPhase]  = useState<Phase>('idle');
  const [error, setError]  = useState('');
  const phaseTimers  = useRef<ReturnType<typeof setTimeout>[]>([]);
  const phaseTimings = useRef<Partial<Record<Exclude<Phase, 'idle' | 'done' | 'error'>, number>>>({});
  const phaseStarts  = useRef<Partial<Record<Exclude<Phase, 'idle' | 'done' | 'error'>, number>>>({});

  useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [user, loading, router]);

  if (loading || !user) return null;

  const reset = () => {
    setMockupB64(null);
    setBwB64(null);
    setMeasurement(null);
    setError('');
    setPhase('idle');
    setTab('mockup');
    stopPhases();
  };

  const onLogo = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) { setLogo(f); reset(); }
  };
  const onMockupFile = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) { setMockupFile(f); reset(); }
  };

  const UV_INSTRUCTION =
    "leverage all your reasoning to intelligently find out where UV printing is present in the design and don't ever craft that portion with LED neon tube but simply keep it dull and with no glow at all.";
  const uvText = () => uvNeon ? (uvPart ? `${UV_INSTRUCTION} The UV-printed part is: ${uvPart}.` : UV_INSTRUCTION) : '';

  const widthNum = () => {
    const w = parseFloat(width);
    return !w || w <= 0 ? null : w;
  };

  const composedExtra = () => {
    const parts: string[] = [];
    if (extra.trim()) parts.push(extra.trim());
    parts.push(`Preferred neon color: ${neonColor.name} (${neonColor.hex}).`);
    return parts.join(' ');
  };

  const stopPhases = () => {
    phaseTimers.current.forEach(clearTimeout);
    phaseTimers.current = [];
  };

  const advancePhase = (p: Exclude<Phase, 'idle' | 'done' | 'error'>) => {
    const now = Date.now();
    setPhase(prev => {
      if (prev !== 'idle' && prev !== 'done' && prev !== 'error') {
        const start = phaseStarts.current[prev];
        if (start != null) phaseTimings.current[prev] = now - start;
      }
      phaseStarts.current[p] = now;
      return p;
    });
  };

  const startPhases = (kind: 'full' | 'bw') => {
    stopPhases();
    phaseTimings.current = {};
    phaseStarts.current  = {};
    if (kind === 'full') {
      advancePhase('drawing');
      phaseTimers.current.push(setTimeout(() => advancePhase('tracing'), 4500));
      phaseTimers.current.push(setTimeout(() => advancePhase('pricing'), 7200));
    } else {
      advancePhase('drawing');
      phaseTimers.current.push(setTimeout(() => advancePhase('tracing'), 700));
      phaseTimers.current.push(setTimeout(() => advancePhase('pricing'), 2600));
    }
  };

  const finishPhases = () => {
    stopPhases();
    const now = Date.now();
    setPhase(prev => {
      if (prev !== 'idle' && prev !== 'done' && prev !== 'error') {
        const start = phaseStarts.current[prev];
        if (start != null) phaseTimings.current[prev] = now - start;
      }
      return 'done';
    });
  };

  const failPhases = () => {
    stopPhases();
    setPhase('error');
  };

  const runFullPipeline = async () => {
    if (!logo) { setError('Upload a sign design first.'); return; }
    const w = widthNum();
    if (!w) { setError('Enter a valid sign width (in inches).'); return; }
    setMockupB64(null); setBwB64(null); setMeasurement(null);
    setBusy(true); setError('');
    startPhases('full');
    try {
      const fd = new FormData();
      fd.append('logo', logo);
      if (bg) fd.append('background', bg);
      if (composedExtra()) fd.append('additional', composedExtra());
      if (uvText()) fd.append('uv', uvText());
      fd.append('width_inches', String(w));
      if (gt) fd.append('ground_truth_m', gt);
      const r = await studio.fullPipeline(fd);
      setMockupB64(r.mockup_b64);
      setBwB64(r.bw_b64);
      setMeasurement(r.measurement);
      finishPhases();
      setTab('mockup');
    } catch (e: unknown) {
      failPhases();
      setError(e instanceof Error ? e.message : 'Pipeline failed');
    } finally {
      setBusy(false);
    }
  };

  const runBwOnly = async () => {
    if (!mockupFile) { setError('Upload a colored mockup first.'); return; }
    const w = widthNum();
    if (!w) { setError('Enter a valid sign width (in inches).'); return; }
    setBwB64(null); setMeasurement(null);
    setBusy(true); setError('');
    startPhases('bw');
    try {
      const fd = new FormData();
      fd.append('mockup', mockupFile);
      if (composedExtra()) fd.append('additional', composedExtra());
      if (uvText()) fd.append('uv', uvText());
      fd.append('width_inches', String(w));
      if (gt) fd.append('ground_truth_m', gt);
      const r = await studio.bwOnlyPipeline(fd);
      setBwB64(r.bw_b64);
      setMeasurement(r.measurement);
      finishPhases();
      setTab('sketch');
    } catch (e: unknown) {
      failPhases();
      setError(e instanceof Error ? e.message : 'Pipeline failed');
    } finally {
      setBusy(false);
    }
  };

  const inputPreview = (() => {
    if (mode === 'full' && logo) return URL.createObjectURL(logo);
    if (mode === 'bw-only' && mockupFile) return URL.createObjectURL(mockupFile);
    return null;
  })();

  return (
    <div>
      <NavBar />

      <main className="wrapper" style={{ padding: '40px 32px 80px' }}>
        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          <div className="section-tag">The studio</div>
          <h1 className="section-title">Upload. Instruct. Generate.</h1>
          <p className="section-sub">
            {mode === 'full'
              ? 'Drop your customer’s logo. Set your specs. Neonizer renders the mockup, traces the tubes, and prices it out.'
              : 'Drop your colored mockup. Neonizer extracts the cut sheet and prices it out.'}
          </p>
        </div>

        {/* Mode toggle */}
        <div style={{
          display: 'inline-flex',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 999,
          padding: 4,
          marginBottom: 28,
        }}>
          <ModeBtn active={mode === 'full'}    onClick={() => { setMode('full');    reset(); }}>Full pipeline</ModeBtn>
          <ModeBtn active={mode === 'bw-only'} onClick={() => { setMode('bw-only'); reset(); }}>Sketch &amp; quote only</ModeBtn>
        </div>

        {/* Demo layout — same structure as landing's demo-section */}
        <div className="demo-layout">
          {/* LEFT — input + toolbox */}
          <div className="big-input-panel">
            <div>
              <div className="panel-label">1. Upload your {mode === 'full' ? 'artwork' : 'mockup'}</div>
              <label className="big-upload" style={{ display: 'block', position: 'relative' }}>
                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp,.bmp"
                  onChange={mode === 'full' ? onLogo : onMockupFile}
                  style={{ position: 'absolute', inset: 0, opacity: 0, cursor: 'pointer' }}
                />
                {inputPreview ? (
                  <>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={inputPreview} alt="preview" style={{
                      maxWidth: '100%',
                      maxHeight: 200,
                      objectFit: 'contain',
                      margin: '0 auto',
                      borderRadius: 6,
                    }} />
                    <p style={{ marginTop: 12, fontSize: '0.78rem', color: 'var(--text-3)' }}>
                      Click to replace
                    </p>
                  </>
                ) : (
                  <>
                    <div className="big-upload-icon">↑</div>
                    <h4>Drop your {mode === 'full' ? 'sign design' : 'colored mockup'} here</h4>
                    <p>Or click to browse your files</p>
                    <div className="format-chips">
                      <span className="fmt">PNG</span>
                      <span className="fmt">JPG</span>
                      <span className="fmt">WEBP</span>
                      <span className="fmt">BMP</span>
                    </div>
                  </>
                )}
              </label>
            </div>

            <div>
              <div className="panel-label">2. Set your instructions</div>
              <div className="big-instr-box">
                <div className="big-instr-header">
                  <div className="instr-title">
                    <span>AI Instruction Toolbox</span>
                    <span className="badge" style={{
                      color: 'var(--cyan)', background: 'var(--cyan-dim)',
                      border: '1px solid rgba(8,145,178,0.2)',
                      fontSize: '0.6rem', fontWeight: 700,
                      letterSpacing: '0.08em', textTransform: 'uppercase',
                      padding: '2px 8px', borderRadius: 4,
                    }}>Active</span>
                  </div>
                  <div className="ai-status">
                    <span className="status-dot" />
                    {busy ? 'Working' : 'Ready'}
                  </div>
                </div>

                <div className="big-instr-body">
                  <textarea
                    className="big-instr-textarea"
                    value={extra}
                    onChange={e => setExtra(e.target.value)}
                    placeholder="Describe any custom requirements… e.g. 'Make it suitable for outdoor use, warm white glow, approximately 36 inches wide, wall-mounted with a black acrylic backboard.'"
                  />

                  <div className="toolbox-row">
                    <div className="toolbox-field">
                      <label>Neon Color</label>
                      <div className="color-select-wrap">
                        <span className="color-swatch" style={{
                          background: neonColor.hex,
                          boxShadow: `0 0 8px rgba(${neonColor.glow},0.7)`,
                        }} />
                        <select
                          className="color-select"
                          value={neonColor.hex}
                          onChange={e => {
                            const c = COLOR_OPTIONS.find(c => c.hex === e.target.value);
                            if (c) setNeonColor(c);
                          }}
                        >
                          {COLOR_OPTIONS.map(c => <option key={c.hex} value={c.hex}>{c.name}</option>)}
                        </select>
                        <span className="select-arrow">▼</span>
                      </div>
                    </div>

                    <div className="toolbox-field">
                      <label>Width (inches)</label>
                      <div className="width-input-wrap">
                        <input
                          type="number" min={1} max={240} placeholder="24"
                          className="width-input"
                          value={width}
                          onChange={e => setWidth(e.target.value)}
                        />
                        <span className="width-unit">in</span>
                      </div>
                    </div>

                    {mode === 'full' ? (
                      <div className="toolbox-field">
                        <label>Background Image</label>
                        <div className="bg-upload-zone" style={{
                          borderColor: bg ? 'rgba(0,229,200,0.4)' : undefined,
                        }}>
                          <input
                            type="file" accept="image/*"
                            onChange={e => setBg(e.target.files?.[0] ?? null)}
                          />
                          <div className="bg-upload-icon">🖼</div>
                          <div className="bg-upload-text">
                            <p>{bg ? 'Background set ✓' : 'Upload background'}</p>
                            <span>PNG · JPG · WEBP</span>
                          </div>
                        </div>
                        {bg && (
                          <div className="bg-file-name visible">
                            <span>✓</span>
                            <span>{bg.name.length > 22 ? bg.name.slice(0, 20) + '…' : bg.name}</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="toolbox-field">
                        <label>Known length (m)</label>
                        <div className="width-input-wrap">
                          <input
                            type="number" step="0.01" placeholder="optional"
                            className="width-input"
                            value={gt}
                            onChange={e => setGt(e.target.value)}
                          />
                          <span className="width-unit">m</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* UV checkbox */}
                  <div
                    className={`uv-checkbox-wrap ${uvNeon ? 'checked' : ''}`}
                    onClick={() => setUvNeon(!uvNeon)}
                  >
                    <div className="uv-checkbox">
                      <span className="uv-check-icon">✓</span>
                    </div>
                    <div className="uv-label-wrap">
                      <strong>
                        Includes UV Printed Part <span className="uv-badge">UV PRINT</span>
                      </strong>
                      <p>The sign includes a UV-printed component (e.g. printed acrylic backing, printed panel, or graphic insert). The AI will account for this part in the mockup and quote.</p>
                    </div>
                  </div>

                  <div className={`uv-part-field ${uvNeon ? 'visible' : ''}`}>
                    <label className="toolbox-field" style={{ gap: 6, display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'var(--amber)' }}>
                        Which part is UV printed?
                      </span>
                      <textarea
                        value={uvPart}
                        onChange={e => setUvPart(e.target.value)}
                        placeholder="e.g. Acrylic backboard, front panel graphic, logo insert…"
                        style={{
                          height: 60,
                          background: 'rgba(255,180,0,0.04)',
                          border: '1px solid rgba(255,180,0,0.25)',
                          borderRadius: 8, padding: '10px 12px',
                          margin: 0, resize: 'none', width: '100%',
                          color: 'var(--text)', fontFamily: 'var(--font-body)',
                          fontSize: '0.82rem', outline: 'none',
                        }}
                      />
                    </label>
                  </div>

                  <button
                    className="big-gen-btn"
                    onClick={mode === 'full' ? runFullPipeline : runBwOnly}
                    disabled={busy || (mode === 'full' ? !logo : !mockupFile)}
                  >
                    {busy ? <span className="status-pulse">Working…</span> : <><span>✦</span> Generate mockup, sketch &amp; quote</>}
                  </button>

                  {error && (
                    <div style={{
                      marginTop: 12, padding: '10px 13px',
                      background: 'var(--red-dim)',
                      border: '1px solid rgba(220,38,38,0.3)',
                      borderRadius: 8,
                      color: 'var(--red)',
                      fontSize: '0.82rem',
                      display: 'flex', alignItems: 'flex-start', gap: 8,
                    }}>
                      <span>!</span><span>{error}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT — outputs */}
          <div>
            <div className="panel-label" style={{ marginBottom: 12 }}>3. Your outputs</div>
            <div className="big-output-panel">
              {phase !== 'idle' && (
                <PipelineStrip phase={phase} timings={phaseTimings.current} />
              )}

              <div className="big-tabs">
                <button
                  className={`big-tab ${tab === 'mockup' ? 'active' : ''}`}
                  onClick={() => setTab('mockup')}
                  disabled={mode === 'bw-only'}
                >
                  ✦ Neon Mockup
                </button>
                <button
                  className={`big-tab ${tab === 'sketch' ? 'active' : ''}`}
                  onClick={() => setTab('sketch')}
                >
                  ◎ Tech Sketch
                </button>
                <button
                  className={`big-tab ${tab === 'quote' ? 'active' : ''}`}
                  onClick={() => setTab('quote')}
                >
                  $ Cost Quote
                </button>
              </div>

              {tab === 'mockup' && (
                <MockupTab
                  b64={mockupB64}
                  loading={busy && (phase === 'drawing' || phase === 'tracing')}
                  measurement={measurement}
                  width={width}
                  mode={mode}
                />
              )}
              {tab === 'sketch' && (
                <SketchTab
                  b64={bwB64}
                  loading={busy && phase === 'tracing'}
                  measurement={measurement}
                />
              )}
              {tab === 'quote' && (
                <QuoteTab
                  measurement={measurement}
                  loading={busy}
                  uvNeon={uvNeon}
                />
              )}

              <StreamingLog
                active={busy}
                done={phase === 'done'}
                mode={mode === 'bw-only' ? 'bw' : 'full'}
                error={phase === 'error' ? error : null}
              />
            </div>
          </div>
        </div>

        {/* Detailed measurement (advanced) */}
        {measurement && <MeasurementDetail m={measurement} />}
      </main>
    </div>
  );
}

/* ─── sub-components ─────────────────────────────────────────── */

function ModeBtn({ active, children, onClick }: {
  active: boolean; children: React.ReactNode; onClick: () => void;
}) {
  return (
    <button onClick={onClick} style={{
      padding: '8px 18px',
      borderRadius: 999,
      background: active ? 'var(--text)' : 'transparent',
      color: active ? '#fff' : 'var(--text-2)',
      border: 'none',
      cursor: 'pointer',
      fontSize: '0.82rem',
      fontWeight: 600,
      transition: 'all 0.15s cubic-bezier(0.16,1,0.3,1)',
    }}>{children}</button>
  );
}

function MockupTab({ b64, loading, measurement, width, mode }: {
  b64: string | null; loading: boolean; measurement: MeasurementResult | null;
  width: string; mode: Mode;
}) {
  if (mode === 'bw-only') {
    return (
      <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-3)', fontSize: '0.85rem', background: 'var(--bg)' }}>
        Mockup not generated in sketch-only mode.
      </div>
    );
  }

  return (
    <>
      {loading ? (
        <TubeSkeleton variant="mockup" caption="Rendering the neon mockup…" />
      ) : b64 ? (
        <div style={{
          background: '#020209', minHeight: 280,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          position: 'relative', overflow: 'hidden',
        }}>
          <div style={{
            position: 'absolute', inset: 0,
            background: 'radial-gradient(ellipse at center, rgba(232,23,93,0.10) 0%, transparent 60%)',
            pointerEvents: 'none',
          }} />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={`data:image/png;base64,${b64}`} alt="mockup" style={{
            maxWidth: '100%', maxHeight: 380, position: 'relative', zIndex: 1,
          }} />
        </div>
      ) : (
        <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-3)', fontSize: '0.85rem', background: 'var(--bg)' }}>
          Upload a design and click <strong style={{ color: 'var(--text-2)' }}>Generate</strong> to render the mockup.
        </div>
      )}

      {b64 && (
        <a href={`data:image/png;base64,${b64}`} download="neon_mockup.png" style={dlBtnRow}>
          ↓ Download mockup
        </a>
      )}

      <div className="output-details">
        <Detail label="Tube length" value={measurement ? `${measurement.measured_m.toFixed(2)} m` : '—'} />
      </div>
    </>
  );
}

function SketchTab({ b64, loading, measurement }: {
  b64: string | null; loading: boolean; measurement: MeasurementResult | null;
}) {
  return (
    <>
      {loading ? (
        <TubeSkeleton variant="sketch" caption="Tracing every tube path…" />
      ) : b64 ? (
        <div style={{
          background: '#050505', minHeight: 280,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: 20, borderBottom: '1px solid var(--border)',
        }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={`data:image/png;base64,${b64}`} alt="sketch" style={{
            maxWidth: '100%', maxHeight: 380, opacity: 0.9, filter: 'brightness(1.1)',
          }} />
        </div>
      ) : (
        <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-3)', fontSize: '0.85rem', background: 'var(--bg)' }}>
          Click <strong style={{ color: 'var(--text-2)' }}>Generate</strong> to extract the tube sketch.
        </div>
      )}

      {b64 && (
        <a href={`data:image/png;base64,${b64}`} download="cut_sheet.png" style={dlBtnRow}>
          ↓ Download sketch
        </a>
      )}

      <div className="output-details">
        <Detail label="Tube paths"    value={measurement?.n_paths?.toString() ?? '—'} />
        <Detail label="Straight runs" value={measurement?.n_straight_segs?.toString() ?? '—'} />
        <Detail label="Curves"        value={measurement?.n_arc_segs?.toString() ?? '—'} />
        <Detail label="Custom shapes" value={measurement?.n_freeform_segs?.toString() ?? '—'} />
        <Detail label="Tube width"
          value={measurement ? `${measurement.tube_width_mm?.toFixed(1) ?? '—'} mm` : '—'} />
        <Detail label="Status"
          value={measurement ? (measurement.tier === 'GLASS_CUT' ? 'Cut-ready' : 'Review') : '—'}
          variant={measurement?.tier === 'GLASS_CUT' ? 'green' : undefined} />
      </div>
    </>
  );
}

function QuoteTab({ measurement, loading, uvNeon }: {
  measurement: MeasurementResult | null; loading: boolean; uvNeon: boolean;
}) {
  if (loading) {
    return (
      <div style={{ padding: 80, textAlign: 'center', background: 'var(--bg)' }}>
        <span className="status-pulse" style={{
          color: 'var(--amber)', fontWeight: 600,
          letterSpacing: '0.1em', fontFamily: 'var(--font-mono)',
          fontSize: '0.78rem',
        }}>
          PRICING IT OUT…
        </span>
      </div>
    );
  }
  if (!measurement) {
    return (
      <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-3)', fontSize: '0.85rem', background: 'var(--bg)' }}>
        Click <strong style={{ color: 'var(--text-2)' }}>Generate</strong> to see the cost breakdown.
      </div>
    );
  }

  const len           = measurement.measured_m;
  const rawMaterial   = len * COST_PER_METRE;
  const markupAmount  = rawMaterial * MARKUP_RATE;
  const subtotal      = rawMaterial + markupAmount;
  const outdoor       = measurement.shipping_cost ?? 0;
  const uvSurcharge   = uvNeon ? Math.max(15, len * 5) : 0;
  const total         = subtotal + outdoor + uvSurcharge;

  return (
    <div className="quote-display">
      <div className="quote-row"><span className="q-label">Tube length</span><span className="q-value">{len.toFixed(2)} m</span></div>
      <div className="quote-row"><span className="q-label">Cost per metre</span><span className="q-value">${COST_PER_METRE.toFixed(2)}</span></div>
      <div className="quote-row"><span className="q-label">Raw material cost</span><span className="q-value">${rawMaterial.toFixed(2)}</span></div>
      <div className="quote-row"><span className="q-label">Markup applied</span><span className="q-value">{(MARKUP_RATE * 100).toFixed(0)}%</span></div>
      {outdoor > 0     && <div className="quote-row"><span className="q-label">Outdoor surcharge</span><span className="q-value">+${outdoor.toFixed(2)}</span></div>}
      {uvSurcharge > 0 && <div className="quote-row"><span className="q-label">UV print surcharge</span><span className="q-value">+${uvSurcharge.toFixed(2)}</span></div>}
      <div className="quote-row total"><span className="q-label">Total customer quote</span><span className="q-value">${total.toFixed(2)}</span></div>

      <div style={{
        marginTop: 18, padding: '12px 14px',
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        fontSize: '0.72rem',
        color: 'var(--text-3)',
        lineHeight: 1.55,
      }}>
        <strong style={{ color: 'var(--text-2)' }}>How we price:</strong>{' '}
        <span style={{
          fontFamily: 'var(--font-mono)',
          background: 'var(--surface-2)', padding: '2px 6px',
          borderRadius: 4, fontSize: '0.7rem',
          fontVariantNumeric: 'tabular-nums',
        }}>
          (length × ${COST_PER_METRE}/m) + markup + outdoor + UV
        </span>
      </div>
    </div>
  );
}

function quoteTotal(m: MeasurementResult): number {
  const raw = m.measured_m * COST_PER_METRE;
  const sub = raw * (1 + MARKUP_RATE);
  const outdoor = m.shipping_cost ?? 0;
  return sub + outdoor;
}

function Detail({ label, value, variant }: {
  label: string; value: string; variant?: 'amber' | 'green';
}) {
  return (
    <div className={`detail-card ${variant ?? ''}`}>
      <div className="d-label">{label}</div>
      <div className="d-value">{value}</div>
    </div>
  );
}

const dlBtnRow: React.CSSProperties = {
  display: 'block',
  margin: 0,
  padding: '10px 14px',
  borderTop: '1px solid var(--border)',
  borderBottom: '1px solid var(--border)',
  background: 'var(--surface)',
  textAlign: 'right',
  fontSize: '0.74rem',
  fontWeight: 500,
  color: 'var(--text-2)',
  textDecoration: 'none',
};

function MeasurementDetail({ m }: { m: MeasurementResult }) {
  const tier = m.tier || 'UNKNOWN';
  const tierLabel = TIER_LABELS[tier] ?? tier;

  return (
    <section style={{ marginTop: 36 }}>
      <div className="panel-label">4. Measurement details</div>

      <div className="card" style={{ padding: 22 }}>
        <div className="output-details" style={{ padding: 0, marginBottom: 18 }}>
          <Detail label="Tube length"     value={`${m.measured_m?.toFixed(4)} m`} />
          <Detail label="Sign quality"    value={tierLabel}
            variant={tier === 'GLASS_CUT' ? 'green' : undefined} />
          <Detail label="Confidence"      value={`${(m.confidence * 100).toFixed(1)}%`} />
          <Detail label="Tube width"      value={`${m.tube_width_mm?.toFixed(1)} mm`} />
          <Detail label="Resolution"      value={m.px_per_inch ? `${m.px_per_inch.toFixed(0)} dpi` : '—'} />
          <Detail label="Path range"
            value={`[${m.loc_low_m?.toFixed(2)}–${m.loc_high_m?.toFixed(2)}] m`} />
          <Detail label="Total paths"     value={m.n_paths?.toString() ?? '—'} />
          <Detail label="Runtime"         value={`${m.elapsed_s?.toFixed(1)} s`} />
          {m.error_pct != null && (
            <Detail label="vs known length"
              value={(m.error_pct >= 0 ? '+' : '') + m.error_pct.toFixed(2) + '%'} />
          )}
        </div>

        {m.reasoning && m.reasoning.length > 0 && (
          <details>
            <summary style={{
              fontSize: '0.7rem',
              fontWeight: 700,
              fontFamily: 'var(--font-mono)',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: 'var(--text-3)',
              cursor: 'pointer',
              marginBottom: 8,
              userSelect: 'none',
            }}>
              Pipeline trace ({m.reasoning.length} lines)
            </summary>
            <pre style={{
              background: '#0F1117',
              color: 'rgba(255,255,255,0.7)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: 14,
              fontSize: '0.74rem',
              lineHeight: 1.7,
              whiteSpace: 'pre-wrap',
              maxHeight: 280, overflowY: 'auto',
              fontFamily: 'var(--font-mono)',
              fontVariantNumeric: 'tabular-nums',
            }}>
              {m.reasoning.join('\n')}
            </pre>
          </details>
        )}

        {(m.overlay_b64 || m.ridge_b64) && (
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginTop: 18 }}>
            {m.overlay_b64 && (
              <div style={{ flex: 1, minWidth: 240 }}>
                <div className="panel-label">Trace overlay</div>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`data:image/png;base64,${m.overlay_b64}`} alt="overlay" style={{
                  maxWidth: '100%', maxHeight: 320, borderRadius: 8,
                  border: '1px solid var(--border)',
                }} />
              </div>
            )}
            {m.ridge_b64 && (
              <div style={{ flex: 1, minWidth: 240 }}>
                <div className="panel-label">Detail map</div>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`data:image/png;base64,${m.ridge_b64}`} alt="detail" style={{
                  maxWidth: '100%', maxHeight: 320, borderRadius: 8,
                  border: '1px solid var(--border)',
                }} />
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
