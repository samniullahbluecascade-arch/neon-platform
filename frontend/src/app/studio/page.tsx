'use client';
import { useEffect, useState, ChangeEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { studio, MeasurementResult } from '@/lib/api';
import NavBar from '@/components/NavBar';

type Mode = 'full' | 'bw-only';
type CardState = '' | 'active' | 'done' | 'err';

const TIER_COLOR: Record<string, string> = {
  GLASS_CUT: '#00ff9d',
  QUOTE: '#00d4ff',
  ESTIMATE: '#ffb300',
  MARGINAL: '#ff8c00',
  FAIL: '#ff3b3b',
  UNKNOWN: '#888',
};

export default function StudioPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  const [mode, setMode] = useState<Mode>('full');

  const [logo, setLogo] = useState<File | null>(null);
  const [bg, setBg] = useState<File | null>(null);
  const [mockupFile, setMockupFile] = useState<File | null>(null);
  const [extra, setExtra] = useState('');
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

  const buildAdditional = () =>
    [extra.trim(), uvNeon ? UV_INSTRUCTION : ''].filter(Boolean).join('\n');

  const widthNum = () => {
    const w = parseFloat(width);
    return !w || w <= 0 ? null : w;
  };

  const runStep1 = async () => {
    if (!logo) { setError('Upload a logo first.'); return; }
    setBusy(true); setError(''); setStatusMsg('Phase 1 — calling Gemini for colored neon mockup…');
    setC2State('active');
    try {
      const fd = new FormData();
      fd.append('logo', logo);
      if (bg) fd.append('background', bg);
      const _addStep1 = buildAdditional();
      if (_addStep1) fd.append('additional', _addStep1);
      const r = await studio.generateMockup(fd);
      setMockupB64(r.image_b64);
      setC1State('done'); setC2State('done');
      setStatusMsg('Mockup ready. Click Convert to B&W.');
    } catch (e: unknown) {
      setC2State('err');
      setError(e instanceof Error ? e.message : 'Mockup generation failed');
    } finally { setBusy(false); }
  };

  const runStep2 = async () => {
    if (!mockupB64) { setError('Generate the mockup first.'); return; }
    setBusy(true); setError(''); setStatusMsg('Phase 2 — extracting tube centerlines via Gemini…');
    setC3State('active');
    try {
      const blob = b64ToBlob(mockupB64, 'image/png');
      const fd = new FormData();
      fd.append('mockup', blob, 'mockup.png');
      const r = await studio.generateBw(fd);
      setBwB64(r.image_b64);
      setStatusMsg('B&W ready. Enter width and Measure.');
    } catch (e: unknown) {
      setC3State('err');
      setError(e instanceof Error ? e.message : 'B&W conversion failed');
    } finally { setBusy(false); }
  };

  const runStep3 = async () => {
    if (!bwB64) { setError('Generate the B&W sketch first.'); return; }
    const w = widthNum();
    if (!w) { setError('Enter a valid sign width (inches).'); return; }
    setBusy(true); setError(''); setStatusMsg('Phase 3 — running V8 LOC pipeline…');
    try {
      const blob = b64ToBlob(bwB64, 'image/png');
      const fd = new FormData();
      fd.append('image', blob, 'bw_sketch.png');
      fd.append('real_width_inches', String(w));
      fd.append('force_format', 'bw');
      if (gt) fd.append('gt_m', gt);
      const r = await studio.measure(fd);
      setMeasurement(r);
      setC3State('done');
      setStatusMsg('Pipeline complete.');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Measurement failed');
    } finally { setBusy(false); }
  };

  const runFullPipeline = async () => {
    if (!logo) { setError('Upload a logo first.'); return; }
    const w = widthNum();
    if (!w) { setError('Enter a valid sign width (inches).'); return; }
    setBusy(true); setError(''); setStatusMsg('Running full pipeline (30–90s)…');
    setC2State('active'); setC3State('active');
    try {
      const fd = new FormData();
      fd.append('logo', logo);
      if (bg) fd.append('background', bg);
      const _addFull = buildAdditional();
      if (_addFull) fd.append('additional', _addFull);
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
    if (!mockupFile) { setError('Upload a colored mockup first.'); return; }
    const w = widthNum();
    if (!w) { setError('Enter a valid sign width (inches).'); return; }
    setBusy(true); setError(''); setStatusMsg('Running B&W-only pipeline (20–60s)…');
    setC3State('active');
    try {
      const fd = new FormData();
      fd.append('mockup', mockupFile);
      if (extra) fd.append('additional', extra);
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
      <div style={{ maxWidth: '1380px', margin: '0 auto', padding: '2rem' }}>
        <h1 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '2.8rem', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
          NEON SIGN STUDIO
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
          {mode === 'full'
            ? 'Logo → Neon Mockup → B&W Tube Sketch → LOC + Price'
            : 'Colored Mockup → B&W Tube Sketch → LOC + Price'}
        </p>

        {/* Mode toggle */}
        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', marginBottom: '1.5rem' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            Workflow:
          </span>
          <button
            className={mode === 'full' ? 'btn-neon' : 'btn-ghost'}
            style={{ padding: '0.4rem 0.9rem', fontSize: '0.75rem' }}
            onClick={() => { setMode('full'); reset(); }}
          >Full Pipeline</button>
          <button
            className={mode === 'bw-only' ? 'btn-neon' : 'btn-ghost'}
            style={{ padding: '0.4rem 0.9rem', fontSize: '0.75rem' }}
            onClick={() => { setMode('bw-only'); reset(); }}
          >B&amp;W from Mockup</button>
        </div>

        {/* 3-card grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: mode === 'bw-only' ? '1fr 1fr' : '1fr 1fr 1fr',
          gap: '1rem',
          marginBottom: '1.25rem',
        }}>
          {/* Card 1: Input */}
          <Card num={1} title={mode === 'full' ? 'Design Input' : 'Mockup Input'} sub={mode === 'full' ? 'Upload logo + optional background' : 'Upload colored mockup'} state={c1State}>
            {mode === 'full' ? (
              <>
                <Label required>Logo / Design Image</Label>
                <input type="file" accept=".png,.jpg,.jpeg,.webp,.bmp" onChange={onLogo} className="input-neon" style={{ padding: '0.4rem', cursor: 'pointer', fontSize: '0.78rem' }} />
                <Label optional>Background Environment</Label>
                <input type="file" accept=".png,.jpg,.jpeg,.webp,.bmp" onChange={onBg} className="input-neon" style={{ padding: '0.4rem', cursor: 'pointer', fontSize: '0.78rem' }} />
              </>
            ) : (
              <>
                <Label required>Colored Mockup Image</Label>
                <input type="file" accept=".png,.jpg,.jpeg,.webp,.bmp" onChange={onMockupFile} className="input-neon" style={{ padding: '0.4rem', cursor: 'pointer', fontSize: '0.78rem' }} />
              </>
            )}
            <Label optional>Additional Instructions</Label>
            <textarea
              value={extra} onChange={e => setExtra(e.target.value)}
              placeholder="e.g. electric blue lettering, neon flex tube only…"
              className="input-neon"
              style={{ minHeight: '54px', resize: 'vertical', fontSize: '0.78rem' }}
            />
            {mode === 'full' && (
              <label style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                marginTop: '0.7rem', cursor: 'pointer', userSelect: 'none',
              }}>
                <input
                  type="checkbox"
                  checked={uvNeon}
                  onChange={e => setUvNeon(e.target.checked)}
                  style={{ accentColor: '#ff2d78', width: '14px', height: '14px', cursor: 'pointer' }}
                />
                <span style={{
                  fontSize: '0.72rem', color: uvNeon ? '#ff2d78' : 'var(--text-muted)',
                  textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: uvNeon ? 700 : 400,
                  transition: 'color 0.15s',
                }}>
                  UV_NEON SIGN
                </span>
                {uvNeon && (
                  <span style={{
                    fontSize: '0.6rem', color: 'var(--text-dim)', background: 'rgba(255,45,120,0.08)',
                    border: '1px solid rgba(255,45,120,0.25)', padding: '1px 6px', borderRadius: '3px',
                  }}>
                    UV skip injected
                  </span>
                )}
              </label>
            )}
            <Preview src={inputPreview} placeholder="Input preview appears here" />
          </Card>

          {/* Card 2: Mockup (full mode only) */}
          {mode === 'full' && (
            <Card num={2} title="Colored Neon Mockup" sub="Gemini renders photorealistic LED neon sign" state={c2State}>
              <Preview b64={mockupB64} placeholder="Run Step 1 to generate mockup" loading={busy && c2State === 'active' && !mockupB64} />
              {mockupB64 && (
                <a href={`data:image/png;base64,${mockupB64}`} download="neon_mockup.png" style={dlStyle}>
                  ⬇ Download
                </a>
              )}
              <button
                className="btn-ghost"
                style={{ padding: '0.5rem 0.8rem', fontSize: '0.75rem', marginTop: '0.6rem' }}
                disabled={!mockupB64 || busy}
                onClick={runStep2}
              >
                Convert to B&amp;W →
              </button>
            </Card>
          )}

          {/* Card 3: B&W + measure */}
          <Card num={mode === 'full' ? 3 : 2} title="B&W Sketch + LOC" sub="Tube centerlines extracted then measured" state={c3State}>
            <Preview b64={bwB64} placeholder="Run previous step to generate B&W sketch" loading={busy && c3State === 'active' && !bwB64} />
            {bwB64 && (
              <a href={`data:image/png;base64,${bwB64}`} download="neon_bw_sketch.png" style={dlStyle}>
                ⬇ Download
              </a>
            )}
            <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '0.9rem 0' }} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem' }}>
              <div>
                <Label required>Width (inches)</Label>
                <input type="number" step="0.5" min="1" value={width} onChange={e => setWidth(e.target.value)} className="input-neon" style={{ fontSize: '0.78rem' }} />
              </div>
              <div>
                <Label optional>GT LOC (m)</Label>
                <input type="number" step="0.01" value={gt} onChange={e => setGt(e.target.value)} placeholder="optional" className="input-neon" style={{ fontSize: '0.78rem' }} />
              </div>
            </div>
            <button
              className="btn-ghost"
              style={{ padding: '0.5rem 0.8rem', fontSize: '0.75rem', marginTop: '0.6rem' }}
              disabled={!bwB64 || busy}
              onClick={runStep3}
            >
              Measure LOC →
            </button>
          </Card>
        </div>

        {/* Action row */}
        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {mode === 'full' ? (
            <>
              <button className="btn-neon" disabled={busy || !logo} onClick={runFullPipeline} style={{ padding: '0.7rem 1.4rem' }}>
                {busy ? 'RUNNING…' : '⚡ RUN FULL PIPELINE'}
              </button>
              <button className="btn-ghost" disabled={busy || !logo} onClick={runStep1} style={{ padding: '0.5rem 1rem', fontSize: '0.78rem' }}>
                Step 1 — Generate Mockup
              </button>
            </>
          ) : (
            <button className="btn-neon" disabled={busy || !mockupFile} onClick={runBwOnly} style={{ padding: '0.7rem 1.4rem' }}>
              {busy ? 'RUNNING…' : '⚡ CONVERT TO B&W & MEASURE'}
            </button>
          )}
          {statusMsg && <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }} className={busy ? 'status-pulse' : ''}>{statusMsg}</span>}
        </div>

        {error && (
          <div style={{ marginTop: '1rem', padding: '0.7rem 1rem', background: 'rgba(255,60,60,.08)', border: '1px solid var(--red)', borderRadius: '4px', color: 'var(--red)', fontSize: '0.82rem', whiteSpace: 'pre-wrap' }}>
            ⚠ {error}
          </div>
        )}

        {/* Results */}
        {measurement && <Results m={measurement} />}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
function Card({ num, title, sub, state, children }: {
  num: number; title: string; sub: string; state: CardState; children: React.ReactNode;
}) {
  const border =
    state === 'active' ? 'var(--pink)' :
    state === 'done' ? '#00ff9d' :
    state === 'err' ? 'var(--red)' :
    'var(--border)';
  const numBg =
    state === 'active' ? 'var(--pink)' :
    state === 'done' ? '#00ff9d' :
    state === 'err' ? 'var(--red)' :
    'var(--bg-2)';
  return (
    <div className="card" style={{ padding: '1.25rem', border: `1px solid ${border}`, transition: 'border-color 0.2s' }}>
      <div style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: '26px', height: '26px', borderRadius: '50%', background: numBg,
        color: state ? '#000' : 'var(--text-muted)', fontWeight: 700, fontSize: '0.75rem', marginBottom: '0.6rem',
      }}>{num}</div>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.2rem' }}>{title}</div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginBottom: '0.8rem' }}>{sub}</div>
      {children}
    </div>
  );
}

function Label({ required, optional, children }: { required?: boolean; optional?: boolean; children?: React.ReactNode }) {
  return (
    <label style={{ display: 'block', fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: '0.6rem 0 0.3rem' }}>
      {children}
      {required && <span style={{ color: 'var(--red)', marginLeft: '3px' }}>*</span>}
      {optional && <span style={{ marginLeft: '5px', fontSize: '0.62rem', color: 'var(--text-dim)', background: 'var(--bg-2)', border: '1px solid var(--border)', padding: '1px 5px', borderRadius: '3px' }}>optional</span>}
    </label>
  );
}

function Preview({ src, b64, placeholder, loading }: { src?: string | null; b64?: string | null; placeholder: string; loading?: boolean }) {
  const url = b64 ? `data:image/png;base64,${b64}` : src;
  return (
    <div style={{
      width: '100%', minHeight: '130px', background: '#000',
      border: '1px dashed var(--border)', borderRadius: '4px',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      overflow: 'hidden', position: 'relative', marginTop: '0.6rem',
    }}>
      {url ? (
        <img src={url} alt="preview" style={{ maxWidth: '100%', maxHeight: '260px', objectFit: 'contain' }} />
      ) : (
        <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem', textAlign: 'center', padding: '1rem' }}>{placeholder}</div>
      )}
      {loading && (
        <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.82)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--pink)', fontSize: '0.78rem' }} className="status-pulse">
          Generating…
        </div>
      )}
    </div>
  );
}

const dlStyle: React.CSSProperties = {
  fontSize: '0.68rem', color: 'var(--text-muted)', background: 'var(--bg-2)',
  border: '1px solid var(--border)', padding: '3px 8px', borderRadius: '3px',
  textDecoration: 'none', display: 'inline-block', marginTop: '0.4rem',
};

function Results({ m }: { m: MeasurementResult }) {
  const tier = m.tier || 'UNKNOWN';
  return (
    <div className="card" style={{ padding: '1.5rem', marginTop: '1.5rem' }}>
      <h3 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.4rem', letterSpacing: '0.06em', marginBottom: '1rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.6rem' }}>
        📊 LOC MEASUREMENT RESULTS
      </h3>
      {/* Estimated price */}
      <div style={{
        padding: '1rem 1.25rem', marginBottom: '1rem',
        background: 'rgba(0,255,157,0.06)', border: '1px solid rgba(0,255,157,0.2)', borderRadius: '6px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Estimated Sign Price</div>
          <div style={{ fontFamily: 'Space Mono, monospace', fontSize: '2rem', fontWeight: 700, color: '#00ff9d', textShadow: '0 0 16px rgba(0,255,157,0.4)' }}>
            ${Math.max(25, Math.round(m.measured_m * 10))}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Tube Length</div>
          <div style={{ fontFamily: 'Space Mono, monospace', fontSize: '1.6rem', fontWeight: 700, color: 'var(--text)' }}>
            {m.measured_m?.toFixed(2)}<span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginLeft: '3px' }}>m</span>
          </div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(155px, 1fr))', gap: '0.6rem', marginBottom: '1rem' }}>
        <Metric label="Measured LOC" value={m.measured_m?.toFixed(4)} unit="m" />
        <Metric label="Tier" value={tier} valueColor={TIER_COLOR[tier] ?? '#888'} />
        <Metric label="Confidence" value={(m.confidence * 100).toFixed(1)} unit="%" />
        <Metric label="Tube Width" value={m.tube_width_mm?.toFixed(1)} unit="mm" />
        <Metric label="px / inch" value={m.px_per_inch?.toFixed(1)} />
        <Metric label="Paths [S/A/F]" value={`${m.n_paths} [${m.n_straight_segs}/${m.n_arc_segs}/${m.n_freeform_segs}]`} />
        <Metric label="Uncertainty" value={`[${m.loc_low_m?.toFixed(2)} – ${m.loc_high_m?.toFixed(2)}] m`} />
        <Metric label="Area-based" value={m.area_m?.toFixed(4)} unit="m" />
        <Metric label="Bias / Risk" value={`${m.bias_direction} (${m.overcount_risk?.toFixed(2)})`} />
        <Metric label="Overcount Ratio" value={m.overcount_ratio?.toFixed(3)} />
        {m.error_pct != null && <Metric label="Error vs GT" value={(m.error_pct >= 0 ? '+' : '') + m.error_pct.toFixed(2)} unit="%" />}
        <Metric label="Elapsed" value={m.elapsed_s?.toFixed(1)} unit="s" />
      </div>

      <Label>Reasoning Log</Label>
      <pre style={{
        background: '#000', border: '1px solid var(--border)', borderRadius: '4px',
        padding: '0.7rem', fontSize: '0.72rem', lineHeight: 1.7, whiteSpace: 'pre-wrap',
        maxHeight: '220px', overflowY: 'auto', color: '#bbb',
      }}>
        {(m.reasoning || []).join('\n')}
      </pre>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '1rem' }}>
        {m.overlay_b64 && (
          <div style={{ flex: 1, minWidth: '220px' }}>
            <Label>Ridge + Path Overlay</Label>
            <img src={`data:image/png;base64,${m.overlay_b64}`} alt="overlay" style={{ maxWidth: '100%', maxHeight: '320px', borderRadius: '4px' }} />
          </div>
        )}
        {m.ridge_b64 && (
          <div style={{ flex: 1, minWidth: '220px' }}>
            <Label>Frangi Ridge Map</Label>
            <img src={`data:image/png;base64,${m.ridge_b64}`} alt="ridge" style={{ maxWidth: '100%', maxHeight: '320px', borderRadius: '4px' }} />
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value, unit, valueColor }: { label: string; value: string | number | undefined; unit?: string; valueColor?: string }) {
  return (
    <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: '4px', padding: '0.7rem 0.85rem' }}>
      <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>{label}</div>
      <div style={{ fontSize: '1.3rem', fontWeight: 700, color: valueColor ?? 'var(--text)', lineHeight: 1 }}>
        {value ?? '—'}{unit && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: '4px' }}>{unit}</span>}
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
