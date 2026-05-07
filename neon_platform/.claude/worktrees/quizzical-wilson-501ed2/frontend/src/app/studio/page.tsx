'use client';
import { useEffect, useState, ChangeEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { studio, MeasurementResult } from '@/lib/api';
import NavBar from '@/components/NavBar';

type Mode = 'full' | 'bw-only';
type CardState = '' | 'active' | 'done' | 'err';

const TIER_COLOR: Record<string, string> = {
  GLASS_CUT: '#059669',
  QUOTE: '#0891b2',
  ESTIMATE: '#d97706',
  MARGINAL: '#ea580c',
  FAIL: '#dc2626',
  UNKNOWN: '#8a8a9a',
};

export default function StudioPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  const [mode, setMode] = useState<Mode>('full');

  const [logo, setLogo] = useState<File | null>(null);
  const [bg, setBg] = useState<File | null>(null);
  const [mockupFile, setMockupFile] = useState<File | null>(null);
  const [extra, setExtra] = useState('');
  const [extraBw, setExtraBw] = useState('');
  const [uvNeon, setUvNeon] = useState(false);
  const [width, setWidth] = useState('24');
  const [gt, setGt] = useState('');

  const [mockupB64, setMockupB64] = useState<string | null>(null);
  const [bwB64, setBwB64] = useState<string | null>(null);
  const [measurement, setMeasurement] = useState<MeasurementResult | null>(null);

  const [c1State, setC1State] = useState<CardState>('active');
  const [c2State, setC2State] = useState<CardState>('');
  const [c3State, setC3State] = useState<CardState>('');

  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [user, loading, router]);

  if (loading || !user) return null;

  const inputPreview = (() => {
    if (mode === 'full' && logo) return URL.createObjectURL(logo);
    if (mode === 'bw-only' && mockupFile) return URL.createObjectURL(mockupFile);
    return null;
  })();

  const reset = () => {
    setMockupB64(null);
    setBwB64(null);
    setMeasurement(null);
    setC1State('active');
    setC2State('');
    setC3State('');
    setError('');
    setStatusMsg('');
  };

  const onLogo = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) { setLogo(f); reset(); }
  };
  const onMockupFile = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) { setMockupFile(f); reset(); }
  };
  const onBg = (e: ChangeEvent<HTMLInputElement>) => {
    setBg(e.target.files?.[0] ?? null);
  };

  const UV_INSTRUCTION =
    "leverage all your reasoning to intelligently find out where UV printing is present in the design and don't ever craft that portion with LED neon tube but simply keep it dull and with no glow at all.";

  const uvText = () => uvNeon ? UV_INSTRUCTION : '';

  const widthNum = () => {
    const w = parseFloat(width);
    return !w || w <= 0 ? null : w;
  };

  const runStep1 = async () => {
    if (!logo) { setError('Please upload a logo first.'); return; }
    setBwB64(null); setMeasurement(null);
    setC3State('');
    setBusy(true); setError(''); setStatusMsg('Phase 1 — generating photoreal neon mockup…');
    setC2State('active');
    try {
      const fd = new FormData();
      fd.append('logo', logo);
      if (bg) fd.append('background', bg);
      if (extra.trim()) fd.append('additional', extra.trim());
      if (uvText()) fd.append('uv', uvText());
      const r = await studio.generateMockup(fd);
      setMockupB64(r.image_b64);
      setC1State('done'); setC2State('done');
      setStatusMsg('Mockup ready. Convert to a black-and-white sketch next.');
    } catch (e: unknown) {
      setC2State('err');
      setError(e instanceof Error ? e.message : 'Mockup generation failed');
    } finally { setBusy(false); }
  };

  const runStep2 = async () => {
    if (!mockupB64) { setError('Generate the mockup first.'); return; }
    setMeasurement(null);
    setBusy(true); setError(''); setStatusMsg('Phase 2 — extracting tube centerlines…');
    setC3State('active');
    try {
      const blob = b64ToBlob(mockupB64, 'image/png');
      const fd = new FormData();
      fd.append('mockup', blob, 'mockup.png');
      if (extraBw.trim()) fd.append('additional', extraBw.trim());
      if (uvText()) fd.append('uv', uvText());
      const r = await studio.generateBw(fd);
      setBwB64(r.image_b64);
      setC3State('');
      setStatusMsg('Sketch ready. Click Measure LOC to get the tube length.');
    } catch (e: unknown) {
      setC3State('err');
      setError(e instanceof Error ? e.message : 'B&W conversion failed');
    } finally { setBusy(false); }
  };

  const runStep3 = async () => {
    if (!bwB64) { setError('Generate the B&W sketch first.'); return; }
    const w = widthNum();
    if (!w) { setError('Enter a valid sign width (inches).'); return; }
    setMeasurement(null);
    setC3State('active');
    setBusy(true); setError(''); setStatusMsg('Phase 3 — running LOC measurement pipeline…');
    try {
      const blob = b64ToBlob(bwB64, 'image/png');
      const fd = new FormData();
      fd.append('image', blob, 'bw_sketch.png');
      fd.append('width_inches', String(w));
      fd.append('force_format', 'bw');
      if (gt) fd.append('ground_truth_m', gt);
      const r = await studio.measure(fd);
      setMeasurement(r);
      setC3State('done');
      setStatusMsg('Pipeline complete.');
    } catch (e: unknown) {
      setC3State('err');
      setError(e instanceof Error ? e.message : 'Measurement failed');
    } finally { setBusy(false); }
  };

  const runFullPipeline = async () => {
    if (!logo) { setError('Please upload a logo first.'); return; }
    const w = widthNum();
    if (!w) { setError('Enter a valid sign width (inches).'); return; }
    setMockupB64(null); setBwB64(null); setMeasurement(null);
    setBusy(true); setError(''); setStatusMsg('Running the full pipeline (30–90s)…');
    setC1State('active'); setC2State('active'); setC3State('active');
    try {
      const fd = new FormData();
      fd.append('logo', logo);
      if (bg) fd.append('background', bg);
      if (extra.trim()) fd.append('additional', extra.trim());
      if (extraBw.trim()) fd.append('additional_bw', extraBw.trim());
      if (uvText()) fd.append('uv', uvText());
      fd.append('width_inches', String(w));
      if (gt) fd.append('ground_truth_m', gt);
      const r = await studio.fullPipeline(fd);
      setMockupB64(r.mockup_b64);
      setBwB64(r.bw_b64);
      setMeasurement(r.measurement);
      setC1State('done'); setC2State('done'); setC3State('done');
      setStatusMsg('Full pipeline complete.');
    } catch (e: unknown) {
      setC2State('err'); setC3State('err');
      setError(e instanceof Error ? e.message : 'Full pipeline failed');
    } finally { setBusy(false); }
  };

  const runBwOnly = async () => {
    if (!mockupFile) { setError('Please upload a colored mockup first.'); return; }
    const w = widthNum();
    if (!w) { setError('Enter a valid sign width (inches).'); return; }
    setBwB64(null); setMeasurement(null);
    setBusy(true); setError(''); setStatusMsg('Running B&W pipeline (20–60s)…');
    setC1State('active'); setC3State('active');
    try {
      const fd = new FormData();
      fd.append('mockup', mockupFile);
      if (extra.trim()) fd.append('additional', extra.trim());
      if (uvText()) fd.append('uv', uvText());
      fd.append('width_inches', String(w));
      if (gt) fd.append('ground_truth_m', gt);
      const r = await studio.bwOnlyPipeline(fd);
      setBwB64(r.bw_b64);
      setMeasurement(r.measurement);
      setC1State('done'); setC3State('done');
      setStatusMsg('B&W pipeline complete.');
    } catch (e: unknown) {
      setC3State('err');
      setError(e instanceof Error ? e.message : 'B&W pipeline failed');
    } finally { setBusy(false); }
  };

  return (
    <div style={{ minHeight: '100vh' }}>
      <NavBar />
      <div style={{ maxWidth: '1380px', margin: '0 auto', padding: '2.5rem 2rem 4rem' }}>

        {/* Page header */}
        <div style={{ marginBottom: '2rem' }}>
          <div style={{
            fontFamily: 'Space Mono, monospace', fontSize: '0.7rem',
            color: 'var(--pink)', letterSpacing: '0.18em', textTransform: 'uppercase',
            marginBottom: '0.5rem',
          }}>
            Neon Sign Studio
          </div>
          <h1 style={{
            fontFamily: 'Bebas Neue, sans-serif',
            fontSize: 'clamp(2.4rem, 4vw, 3.4rem)',
            letterSpacing: '0.03em', lineHeight: 1.05,
            marginBottom: '0.6rem',
          }}>
            Logo to <span className="neon-pink">cut-ready quote</span>, in three steps.
          </h1>
          <p style={{ color: 'var(--text-dim)', fontSize: '1rem', maxWidth: 640, lineHeight: 1.6 }}>
            {mode === 'full'
              ? 'Upload a logo. Neonizer renders a photoreal mockup, extracts the tube paths, and measures the tube length for quoting.'
              : 'Upload a colored mockup. Neonizer extracts the tube paths and measures the tube length for quoting.'}
          </p>
        </div>

        {/* Mode toggle */}
        <div style={{
          display: 'inline-flex', background: '#fff', border: '1px solid var(--border)',
          borderRadius: 999, padding: 4, marginBottom: '1.75rem',
        }}>
          <button
            onClick={() => { setMode('full'); reset(); }}
            style={modeBtn(mode === 'full')}
          >Full pipeline</button>
          <button
            onClick={() => { setMode('bw-only'); reset(); }}
            style={modeBtn(mode === 'bw-only')}
          >B&amp;W from mockup</button>
        </div>

        {/* 3-card grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: mode === 'bw-only' ? '1fr 1fr' : '1fr 1fr 1fr',
          gap: '1rem',
          marginBottom: '1.5rem',
        }}>
          {/* Card 1 — Input */}
          <Card num={1} title={mode === 'full' ? 'Design input' : 'Mockup input'}
                sub={mode === 'full' ? 'Upload logo & optional background' : 'Upload a colored mockup'}
                state={c1State}>
            {mode === 'full' ? (
              <>
                <Label required>Logo / design image</Label>
                <input type="file" accept=".png,.jpg,.jpeg,.webp,.bmp" onChange={onLogo}
                       className="input-neon" style={{ padding: '0.45rem', cursor: 'pointer', fontSize: '0.78rem' }} />
                <Label optional>Background environment</Label>
                <input type="file" accept=".png,.jpg,.jpeg,.webp,.bmp" onChange={onBg}
                       className="input-neon" style={{ padding: '0.45rem', cursor: 'pointer', fontSize: '0.78rem' }} />
              </>
            ) : (
              <>
                <Label required>Colored mockup image</Label>
                <input type="file" accept=".png,.jpg,.jpeg,.webp,.bmp" onChange={onMockupFile}
                       className="input-neon" style={{ padding: '0.45rem', cursor: 'pointer', fontSize: '0.78rem' }} />
              </>
            )}
            <Label optional>Additional instructions</Label>
            <textarea
              value={extra} onChange={e => setExtra(e.target.value)}
              placeholder="e.g. electric blue lettering, neon flex tube only…"
              className="input-neon"
              style={{ minHeight: 56, resize: 'vertical', fontSize: '0.78rem' }}
            />
            <label style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              marginTop: '0.7rem', cursor: 'pointer', userSelect: 'none',
            }}>
              <input
                type="checkbox" checked={uvNeon}
                onChange={e => setUvNeon(e.target.checked)}
                style={{ accentColor: 'var(--pink)', width: 14, height: 14, cursor: 'pointer' }}
              />
              <span style={{
                fontSize: '0.72rem',
                color: uvNeon ? 'var(--pink)' : 'var(--text-muted)',
                textTransform: 'uppercase', letterSpacing: '0.08em',
                fontWeight: uvNeon ? 700 : 500,
                transition: 'color 0.15s',
              }}>
                UV neon sign
              </span>
              {uvNeon && (
                <span style={{
                  fontSize: '0.6rem', color: 'var(--pink-deep)',
                  background: 'var(--pink-soft)', border: '1px solid var(--pink)',
                  padding: '1px 6px', borderRadius: 3,
                }}>UV skip injected</span>
              )}
            </label>
            <Preview src={inputPreview} placeholder="Input preview appears here" />
          </Card>

          {/* Card 2 — Mockup (full mode only) */}
          {mode === 'full' && (
            <Card num={2} title="Photoreal mockup" sub="Gemini renders the LED neon sign" state={c2State}>
              <Preview b64={mockupB64} placeholder="Run step 1 to generate the mockup"
                       loading={busy && c2State === 'active' && !mockupB64} />
              {mockupB64 && (
                <a href={`data:image/png;base64,${mockupB64}`} download="neon_mockup.png" style={dlStyle}>
                  ↓ Download mockup
                </a>
              )}
              <Label optional>Additional instructions (sketch phase)</Label>
              <textarea
                value={extraBw} onChange={e => setExtraBw(e.target.value)}
                placeholder="e.g. preserve fine bat-wing detail; remove circle backer ridge…"
                className="input-neon"
                style={{ minHeight: 56, resize: 'vertical', fontSize: '0.78rem' }}
              />
              <button
                className="btn-ghost"
                style={{ padding: '0.55rem 0.95rem', fontSize: '0.78rem', marginTop: '0.7rem' }}
                disabled={!mockupB64 || busy}
                onClick={runStep2}
              >
                Convert to sketch →
              </button>
            </Card>
          )}

          {/* Card 3 — Sketch + measurement */}
          <Card num={mode === 'full' ? 3 : 2} title="Tube sketch & length"
                sub="Centerlines extracted, then measured" state={c3State}>
            <Preview b64={bwB64} placeholder="Run the previous step to generate the sketch"
                     loading={busy && c3State === 'active' && !bwB64} />
            {bwB64 && (
              <a href={`data:image/png;base64,${bwB64}`} download="neon_bw_sketch.png" style={dlStyle}>
                ↓ Download sketch
              </a>
            )}
            <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '0.95rem 0' }} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem' }}>
              <div>
                <Label required>Width (inches)</Label>
                <input type="number" step="0.5" min="1" value={width}
                       onChange={e => setWidth(e.target.value)}
                       className="input-neon" style={{ fontSize: '0.78rem' }} />
              </div>
              <div>
                <Label optional>GT length (m)</Label>
                <input type="number" step="0.01" value={gt}
                       onChange={e => setGt(e.target.value)} placeholder="optional"
                       className="input-neon" style={{ fontSize: '0.78rem' }} />
              </div>
            </div>
            <button
              className="btn-ghost"
              style={{ padding: '0.55rem 0.95rem', fontSize: '0.78rem', marginTop: '0.7rem' }}
              disabled={!bwB64 || busy}
              onClick={runStep3}
            >
              Measure LOC →
            </button>
          </Card>
        </div>

        {/* Action row */}
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {mode === 'full' ? (
            <>
              <button className="btn-neon" disabled={busy || !logo}
                      onClick={runFullPipeline} style={{ padding: '0.85rem 1.5rem' }}>
                {busy ? 'Running…' : 'Run full pipeline →'}
              </button>
              <button className="btn-ghost" disabled={busy || !logo}
                      onClick={runStep1} style={{ padding: '0.6rem 1.1rem', fontSize: '0.82rem' }}>
                Step 1 — Generate mockup
              </button>
            </>
          ) : (
            <button className="btn-neon" disabled={busy || !mockupFile}
                    onClick={runBwOnly} style={{ padding: '0.85rem 1.5rem' }}>
              {busy ? 'Running…' : 'Convert & measure →'}
            </button>
          )}
          {statusMsg && (
            <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}
                  className={busy ? 'status-pulse' : ''}>
              {statusMsg}
            </span>
          )}
        </div>

        {error && (
          <div style={{
            marginTop: '1rem',
            padding: '0.75rem 1rem',
            background: '#fef2f2',
            border: '1px solid var(--red)',
            borderRadius: 6,
            color: 'var(--red)',
            fontSize: '0.85rem',
            whiteSpace: 'pre-wrap',
          }}>
            ⚠ {error}
          </div>
        )}

        {measurement && <Results m={measurement} />}
      </div>
    </div>
  );
}

/* ── COMPONENTS ─────────────────────────────────────────────────────── */

function Card({ num, title, sub, state, children }: {
  num: number; title: string; sub: string; state: CardState; children: React.ReactNode;
}) {
  const border =
    state === 'active' ? 'var(--pink)' :
    state === 'done'   ? 'var(--green)' :
    state === 'err'    ? 'var(--red)'   :
    'var(--border)';
  const bgRing =
    state === 'active' ? 'var(--pink-soft)' :
    state === 'done'   ? '#ecfdf5' :
    state === 'err'    ? '#fef2f2' :
    'transparent';
  const numBg =
    state === 'active' ? 'var(--pink)' :
    state === 'done'   ? 'var(--green)' :
    state === 'err'    ? 'var(--red)' :
    'var(--bg-2)';
  const numColor = state ? '#fff' : 'var(--text-muted)';

  return (
    <div style={{
      background: '#fff',
      border: `1px solid ${border}`,
      borderRadius: 12,
      padding: '1.25rem',
      boxShadow: state === 'active' ? `0 0 0 3px ${bgRing}` : 'var(--shadow-sm)',
      transition: 'all 0.2s',
    }}>
      <div style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: 28, height: 28, borderRadius: '50%',
        background: numBg, color: numColor,
        fontFamily: 'Space Mono, monospace', fontWeight: 700, fontSize: '0.75rem',
        marginBottom: '0.7rem',
      }}>{num}</div>
      <div style={{
        fontSize: '0.62rem', color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: '0.2rem',
      }}>{title}</div>
      <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: '0.85rem' }}>{sub}</div>
      {children}
    </div>
  );
}

function Label({ required, optional, children }: {
  required?: boolean; optional?: boolean; children?: React.ReactNode;
}) {
  return (
    <label style={{
      display: 'block', fontSize: '0.66rem', color: 'var(--text-muted)',
      textTransform: 'uppercase', letterSpacing: '0.08em',
      margin: '0.6rem 0 0.3rem',
    }}>
      {children}
      {required && <span style={{ color: 'var(--red)', marginLeft: 3 }}>*</span>}
      {optional && (
        <span style={{
          marginLeft: 5, fontSize: '0.6rem', color: 'var(--text-muted)',
          background: 'var(--bg-1)', border: '1px solid var(--border)',
          padding: '1px 5px', borderRadius: 3, textTransform: 'lowercase',
          letterSpacing: 'normal',
        }}>optional</span>
      )}
    </label>
  );
}

function Preview({ src, b64, placeholder, loading }: {
  src?: string | null; b64?: string | null; placeholder: string; loading?: boolean;
}) {
  const url = b64 ? `data:image/png;base64,${b64}` : src;
  return (
    <div style={{
      width: '100%', minHeight: 130, background: 'var(--bg-1)',
      border: '1px dashed var(--border-md)', borderRadius: 6,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      overflow: 'hidden', position: 'relative', marginTop: '0.6rem',
    }}>
      {url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={url} alt="preview" style={{ maxWidth: '100%', maxHeight: 260, objectFit: 'contain' }} />
      ) : (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', textAlign: 'center', padding: '1rem' }}>
          {placeholder}
        </div>
      )}
      {loading && (
        <div style={{
          position: 'absolute', inset: 0,
          background: 'rgba(255,255,255,0.92)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--pink)', fontSize: '0.82rem', fontWeight: 600,
        }} className="status-pulse">
          Generating…
        </div>
      )}
    </div>
  );
}

const dlStyle: React.CSSProperties = {
  fontSize: '0.7rem', color: 'var(--text-dim)',
  background: 'var(--bg-1)', border: '1px solid var(--border)',
  padding: '4px 9px', borderRadius: 4, textDecoration: 'none',
  display: 'inline-block', marginTop: '0.45rem', fontWeight: 500,
};

function modeBtn(active: boolean): React.CSSProperties {
  return {
    padding: '0.55rem 1.25rem',
    borderRadius: 999,
    background: active ? 'var(--text)' : 'transparent',
    color: active ? '#fff' : 'var(--text-dim)',
    border: 'none',
    cursor: 'pointer',
    fontSize: '0.82rem',
    fontWeight: 600,
    transition: 'all 0.15s',
  };
}

function Results({ m }: { m: MeasurementResult }) {
  const tier = m.tier || 'UNKNOWN';
  const production = m.estimated_price ?? Math.max(25, Math.round(m.measured_m * 10));
  const total      = m.total_price ?? (production + (m.shipping_cost ?? 0));

  return (
    <div className="card" style={{ padding: '1.75rem', marginTop: '1.75rem' }}>
      <div style={{
        fontFamily: 'Space Mono, monospace', fontSize: '0.7rem',
        color: 'var(--pink)', letterSpacing: '0.18em', textTransform: 'uppercase',
        marginBottom: '0.4rem',
      }}>
        Measurement results
      </div>
      <h3 style={{
        fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.7rem',
        letterSpacing: '0.04em', marginBottom: '1.25rem',
      }}>
        Cut-ready geometry
      </h3>

      {/* Headline figures */}
      <div style={{
        padding: '1.25rem 1.5rem', marginBottom: '1.25rem',
        background: 'linear-gradient(135deg, #ecfdf5 0%, #f0fdfa 100%)',
        border: '1px solid #a7f3d0', borderRadius: 10,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1.5rem',
        flexWrap: 'wrap',
      }}>
        <div>
          <div style={resultsLabel}>Tube length</div>
          <div style={{ fontFamily: 'Space Mono, monospace', fontSize: '1.7rem', fontWeight: 700 }}>
            {m.measured_m?.toFixed(2)}<span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginLeft: 4, fontWeight: 400 }}>m</span>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={resultsLabel}>Breakeven price</div>
          <div style={{ fontFamily: 'Space Mono, monospace', fontSize: '2.1rem', fontWeight: 700, color: 'var(--green)' }}>
            ${total.toFixed(2)}
          </div>
        </div>
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(155px, 1fr))',
        gap: '0.6rem', marginBottom: '1rem',
      }}>
        <Metric label="Measured LOC" value={m.measured_m?.toFixed(4)} unit="m" />
        <Metric label="Quality tier" value={tier} valueColor={TIER_COLOR[tier] ?? '#888'} />
        <Metric label="Confidence" value={(m.confidence * 100).toFixed(1)} unit="%" />
        <Metric label="Tube width" value={m.tube_width_mm?.toFixed(1)} unit="mm" />
        <Metric label="Pixels / inch" value={m.px_per_inch?.toFixed(1)} />
        <Metric label="Paths [S/A/F]" value={`${m.n_paths} [${m.n_straight_segs}/${m.n_arc_segs}/${m.n_freeform_segs}]`} />
        <Metric label="Uncertainty" value={`[${m.loc_low_m?.toFixed(2)} – ${m.loc_high_m?.toFixed(2)}] m`} />
        <Metric label="Area-based" value={m.area_m?.toFixed(4)} unit="m" />
        <Metric label="Bias / risk" value={`${m.bias_direction} (${m.overcount_risk?.toFixed(2)})`} />
        <Metric label="Overcount ratio" value={m.overcount_ratio?.toFixed(3)} />
        {m.error_pct != null && (
          <Metric label="Error vs GT" value={(m.error_pct >= 0 ? '+' : '') + m.error_pct.toFixed(2)} unit="%" />
        )}
        <Metric label="Runtime" value={m.elapsed_s?.toFixed(1)} unit="s" />
      </div>

      <Label>Reasoning log</Label>
      <pre style={{
        background: 'var(--dark)', border: '1px solid var(--border)', borderRadius: 6,
        padding: '0.85rem', fontSize: '0.75rem', lineHeight: 1.7,
        whiteSpace: 'pre-wrap', maxHeight: 240, overflowY: 'auto', color: '#c8c8d8',
        fontFamily: 'Space Mono, monospace',
      }}>
        {(m.reasoning || []).join('\n')}
      </pre>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '1.25rem' }}>
        {m.overlay_b64 && (
          <div style={{ flex: 1, minWidth: 220 }}>
            <Label>Ridge & path overlay</Label>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`data:image/png;base64,${m.overlay_b64}`} alt="overlay"
                 style={{ maxWidth: '100%', maxHeight: 320, borderRadius: 6, border: '1px solid var(--border)' }} />
          </div>
        )}
        {m.ridge_b64 && (
          <div style={{ flex: 1, minWidth: 220 }}>
            <Label>Frangi ridge map</Label>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`data:image/png;base64,${m.ridge_b64}`} alt="ridge"
                 style={{ maxWidth: '100%', maxHeight: 320, borderRadius: 6, border: '1px solid var(--border)' }} />
          </div>
        )}
      </div>
    </div>
  );
}

const resultsLabel: React.CSSProperties = {
  fontSize: '0.65rem', color: 'var(--text-muted)',
  letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '0.3rem',
};

function Metric({ label, value, unit, valueColor }: {
  label: string; value: string | number | undefined; unit?: string; valueColor?: string;
}) {
  return (
    <div style={{
      background: 'var(--bg-1)', border: '1px solid var(--border)',
      borderRadius: 6, padding: '0.75rem 0.9rem',
    }}>
      <div style={{
        fontSize: '0.6rem', color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.3rem',
      }}>{label}</div>
      <div style={{
        fontSize: '1.2rem', fontWeight: 700, color: valueColor ?? 'var(--text)',
        fontFamily: 'Space Mono, monospace', lineHeight: 1.05,
      }}>
        {value ?? '—'}
        {unit && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: 4, fontWeight: 400 }}>{unit}</span>}
      </div>
    </div>
  );
}

function b64ToBlob(b64: string, mime: string): Blob {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return new Blob([arr], { type: mime });
}
