'use client';
import { useEffect, useState, useRef, useCallback, ChangeEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { studio, MeasurementResult } from '@/lib/api';
import NavBar from '@/components/NavBar';

type Tab  = 'mockup' | 'quote';
type Mode = 'full' | 'bw-only';
type SignType = 'standard' | 'outdoor' | 'rgb';

const MARKUP_RATE    = 0.40;

const SIGN_TYPE_MULTIPLIERS: Record<SignType, number> = {
  standard: 10,
  outdoor: 20,
  rgb: 15,
};

const SIGN_TYPE_LABELS: Record<SignType, string> = {
  standard: 'Standard Indoor',
  outdoor: 'Outdoor Sign',
  rgb: 'RGB Sign',
};

// Subtype options match keys in v8_generate.py OUTDOOR_SUBTYPE_CLAUSES / INDOOR_SUBTYPE_CLAUSES.
const SUBTYPE_OPTIONS_OUTDOOR: { value: string; label: string }[] = [
  { value: 'facade_storefront', label: 'Facade storefront' },
  { value: 'pole_sign',         label: 'Pole sign' },
  { value: 'monument_sign',     label: 'Monument sign' },
  { value: 'wayfinding_sign',   label: 'Wayfinding sign' },
  { value: 'blade_sign',        label: 'Blade / projection sign' },
  { value: 'standalone_sign',   label: 'Standalone sign' },
  { value: 'subway_sign',       label: 'Subway / transit sign' },
];

const SUBTYPE_OPTIONS_INDOOR: { value: string; label: string }[] = [
  { value: 'living_room',           label: 'Living room' },
  { value: 'cafe_bar',              label: 'Cafe bar' },
  { value: 'restaurant_booth',      label: 'Restaurant booth' },
  { value: 'bedroom',               label: 'Bedroom' },
  { value: 'studio_office',         label: 'Studio / office' },
  { value: 'retail_store_interior', label: 'Retail interior' },
  { value: 'barbershop',            label: 'Barbershop' },
  { value: 'tattoo_parlor',         label: 'Tattoo parlor' },
  { value: 'gym',                   label: 'Gym' },
];

const subtypeOptionsFor = (s: SignType) =>
  s === 'outdoor' ? SUBTYPE_OPTIONS_OUTDOOR : SUBTYPE_OPTIONS_INDOOR;

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

  const [mode, setMode]  = useState<Mode>('full');
  const [tab,  setTab]   = useState<Tab>('mockup');

  // Inputs
  const [logo, setLogo]             = useState<File | null>(null);
  const [bg,   setBg]               = useState<File | null>(null);
  const [mockupFile, setMockupFile] = useState<File | null>(null);
  const [extra, setExtra]           = useState('');
  const [neonColor, setNeonColor]   = useState(COLOR_OPTIONS[0]);
  const [width, setWidth]           = useState('24');
  const [signType, setSignType]     = useState<SignType>('standard');
  const [subtype, setSubtype]       = useState<string>('auto');
  const [uvNeon, setUvNeon]         = useState(false);
  const [uvPart, setUvPart]         = useState('');
  const [gt, setGt]                 = useState('');

  // Outputs
  const [mockupB64, setMockupB64]     = useState<string | null>(null);
  const [bwB64, setBwB64]             = useState<string | null>(null);
  const [measurement, setMeasurement] = useState<MeasurementResult | null>(null);

  // Pipeline state
  const [busy,  setBusy]   = useState(false);
  const [error, setError]  = useState('');

  useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [user, loading, router]);

  if (loading || !user) return null;

  const reset = () => {
    setMockupB64(null);
    setBwB64(null);
    setMeasurement(null);
    setError('');
    setTab('mockup');
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

  const costPerMetre = () => SIGN_TYPE_MULTIPLIERS[signType];

  const composedExtra = () => {
    const parts: string[] = [];
    if (extra.trim()) parts.push(extra.trim());
    parts.push(`Preferred neon color: ${neonColor.name} (${neonColor.hex}).`);
    parts.push(`Sign type: ${SIGN_TYPE_LABELS[signType]}.`);
    return parts.join(' ');
  };



  const runFullPipeline = async () => {
    if (!logo) { setError('Upload a sign design first.'); return; }
    const w = widthNum();
    if (!w) { setError('Enter a valid sign width (in inches).'); return; }
    setMockupB64(null); setBwB64(null); setMeasurement(null);
    setBusy(true); setError('');
    try {
      const fd = new FormData();
      fd.append('logo', logo);
      if (bg) fd.append('background', bg);
      if (composedExtra()) fd.append('additional', composedExtra());
      if (uvText()) fd.append('uv', uvText());
      fd.append('width_inches', String(w));
      fd.append('sign_type', signType);
      if (subtype && subtype !== 'auto') fd.append('subtype', subtype);
      if (gt) fd.append('ground_truth_m', gt);
      const r = await studio.fullPipeline(fd);
      setMockupB64(r.mockup_b64);
      setBwB64(r.bw_b64);
      setMeasurement(r.measurement);
      setTab('mockup');
    } catch (e: unknown) {
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
    try {
      const fd = new FormData();
      fd.append('mockup', mockupFile);
      if (composedExtra()) fd.append('additional', composedExtra());
      if (uvText()) fd.append('uv', uvText());
      fd.append('width_inches', String(w));
      fd.append('sign_type', signType);
      if (subtype && subtype !== 'auto') fd.append('subtype', subtype);
      if (gt) fd.append('ground_truth_m', gt);
      const r = await studio.bwOnlyPipeline(fd);
      setBwB64(r.bw_b64);
      setMeasurement(r.measurement);
      setTab('mockup');
    } catch (e: unknown) {
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
        <div style={{ marginBottom: 20, maxWidth: 920, marginLeft: 'auto', marginRight: 'auto' }}>
          <div className="section-tag">The studio</div>
          <h1 className="section-title">Upload. Configure. Generate.</h1>
          <p className="section-sub" style={{ marginBottom: 0 }}>
            {mode === 'full'
              ? 'One flow: colored mockup, black-and-white cut sheet, tube length, and quote — in order.'
              : 'Upload a finished colored mockup: we produce the cut sheet, measure tube length, and show your quote.'}
          </p>
        </div>

        {/* Single condensed workspace */}
        <div className="lux-glass-panel" style={{
          maxWidth: 920,
          margin: '0 auto',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          overflow: 'hidden',
        }}>
          <div style={{ padding: '20px 22px 16px', borderBottom: '1px solid var(--border)' }}>
            <div style={{
              display: 'inline-flex',
              background: 'var(--bg)',
              border: '1px solid var(--border)',
              borderRadius: 999,
              padding: 4,
            }}>
              <ModeBtn active={mode === 'full'}    onClick={() => { setMode('full');    reset(); }}>Full pipeline</ModeBtn>
              <ModeBtn active={mode === 'bw-only'} onClick={() => { setMode('bw-only'); reset(); }}>Sketch &amp; quote only</ModeBtn>
            </div>
          </div>

          <div style={{ padding: 22 }}>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)',
              gap: 22,
              alignItems: 'start',
            }}>
              {/* LEFT — upload, options, run */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {/* Upload Section */}
            <div style={{ marginBottom: 18 }}>
              <div className="panel-label" style={{ marginBottom: 10 }}>1. Upload {mode === 'full' ? 'Design' : 'Mockup'}</div>
              <label style={{
                display: 'block',
                position: 'relative',
                border: '2px dashed var(--border)',
                borderRadius: 8,
                padding: '20px',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'border-color 0.2s',
              }}>
                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp,.bmp"
                  onChange={mode === 'full' ? onLogo : onMockupFile}
                  style={{ position: 'absolute', inset: 0, opacity: 0, cursor: 'pointer' }}
                />
                {inputPreview ? (
                  <img src={inputPreview} alt="preview" style={{
                    maxWidth: '100%',
                    maxHeight: 120,
                    objectFit: 'contain',
                    margin: '0 auto',
                    borderRadius: 6,
                  }} />
                ) : (
                  <div>
                    <div style={{ fontSize: '1.5rem', marginBottom: 8 }}>↑</div>
                    <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-2)' }}>
                      Drop {mode === 'full' ? 'your sign design' : 'colored mockup'} here
                    </p>
                    <p style={{ margin: '4px 0 0', fontSize: '0.7rem', color: 'var(--text-3)' }}>
                      PNG, JPG, WEBP, BMP
                    </p>
                  </div>
                )}
              </label>
            </div>

            {/* Configuration Section */}
            <div style={{ marginBottom: 16 }}>
              <div className="panel-label" style={{ marginBottom: 10 }}>2. Width, sign type and color</div>
              
              <div style={{ display: 'grid', gap: 12 }}>
                {/* Width & Sign Type Row */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-3)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Width (inches)
                    </label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <input
                        type="number"
                        min={1}
                        max={240}
                        placeholder="24"
                        value={width}
                        onChange={e => setWidth(e.target.value)}
                        style={{
                          flex: 1,
                          padding: '10px 12px',
                          background: 'var(--bg)',
                          border: '1px solid var(--border)',
                          borderRadius: 6,
                          color: 'var(--text)',
                          fontSize: '0.9rem',
                        }}
                      />
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-3)' }}>in</span>
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-3)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Sign type (quote rate)
                    </label>
                    <select
                      value={signType}
                      onChange={e => {
                        setSignType(e.target.value as SignType);
                        setSubtype('auto');  // reset subtype pool changed
                      }}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        background: 'var(--bg)',
                        border: '1px solid var(--border)',
                        borderRadius: 6,
                        color: 'var(--text)',
                        fontSize: '0.9rem',
                        cursor: 'pointer',
                      }}
                    >
                      <option value="standard">Standard indoor</option>
                      <option value="outdoor">Outdoor sign</option>
                      <option value="rgb">RGB sign</option>
                    </select>
                  </div>
                </div>

                {/* Subtype (environment / mount style) */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-3)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {signType === 'outdoor' ? 'Outdoor mount style' : 'Indoor scene'} <span style={{ color: 'var(--text-3)', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>(optional)</span>
                  </label>
                  <select
                    value={subtype}
                    onChange={e => setSubtype(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      background: 'var(--bg)',
                      border: '1px solid var(--border)',
                      borderRadius: 6,
                      color: 'var(--text)',
                      fontSize: '0.9rem',
                      cursor: 'pointer',
                    }}
                  >
                    <option value="auto">Auto (random)</option>
                    {subtypeOptionsFor(signType).map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>

                {/* Neon Color */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-3)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Neon Color
                  </label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{
                      width: 28,
                      height: 28,
                      borderRadius: '50%',
                      background: neonColor.hex,
                      boxShadow: `0 0 12px rgba(${neonColor.glow},0.7)`,
                      border: '2px solid var(--border)',
                    }} />
                    <select
                      value={neonColor.hex}
                      onChange={e => {
                        const c = COLOR_OPTIONS.find(c => c.hex === e.target.value);
                        if (c) setNeonColor(c);
                      }}
                      style={{
                        flex: 1,
                        padding: '10px 12px',
                        background: 'var(--bg)',
                        border: '1px solid var(--border)',
                        borderRadius: 6,
                        color: 'var(--text)',
                        fontSize: '0.9rem',
                        cursor: 'pointer',
                      }}
                    >
                      {COLOR_OPTIONS.map(c => <option key={c.hex} value={c.hex}>{c.name}</option>)}
                    </select>
                  </div>
                </div>

                {/* Background (Full mode only) */}
                {mode === 'full' && (
                  <div>
                    <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-3)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Background Image (Optional)
                    </label>
                    <label style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      padding: '10px 12px',
                      background: 'var(--bg)',
                      border: `1px solid ${bg ? 'rgba(0,229,200,0.4)' : 'var(--border)'}`,
                      borderRadius: 6,
                      cursor: 'pointer',
                    }}>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={e => setBg(e.target.files?.[0] ?? null)}
                        style={{ display: 'none' }}
                      />
                      <span style={{ fontSize: '1rem' }}>🖼</span>
                      <span style={{ fontSize: '0.85rem', color: bg ? 'var(--text)' : 'var(--text-3)' }}>
                        {bg ? bg.name : 'Upload background (PNG, JPG, WEBP)'}
                      </span>
                      {bg && <span style={{ marginLeft: 'auto', color: 'var(--cyan)' }}>✓</span>}
                    </label>
                  </div>
                )}

                {/* UV Checkbox */}
                <div
                  onClick={() => setUvNeon(!uvNeon)}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 10,
                    padding: '12px',
                    background: uvNeon ? 'rgba(255,180,0,0.08)' : 'var(--bg)',
                    border: `1px solid ${uvNeon ? 'rgba(255,180,0,0.3)' : 'var(--border)'}`,
                    borderRadius: 6,
                    cursor: 'pointer',
                  }}
                >
                  <div style={{
                    width: 18,
                    height: 18,
                    borderRadius: 4,
                    border: `2px solid ${uvNeon ? 'var(--amber)' : 'var(--border)'}`,
                    background: uvNeon ? 'var(--amber)' : 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    marginTop: 2,
                  }}>
                    {uvNeon && <span style={{ color: '#000', fontSize: '0.75rem' }}>✓</span>}
                  </div>
                  <div>
                    <strong style={{ fontSize: '0.85rem', color: 'var(--text)' }}>
                      Includes UV Printed Part
                      <span style={{
                        marginLeft: 8,
                        fontSize: '0.6rem',
                        fontWeight: 700,
                        color: 'var(--amber)',
                        background: 'rgba(255,180,0,0.15)',
                        padding: '2px 6px',
                        borderRadius: 4,
                      }}>UV PRINT</span>
                    </strong>
                    <p style={{ margin: '4px 0 0', fontSize: '0.75rem', color: 'var(--text-3)' }}>
                      Check if your sign has UV-printed components (acrylic backing, printed panel, etc.)
                    </p>
                  </div>
                </div>

                {/* UV Part Field */}
                {uvNeon && (
                  <div>
                    <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 600, color: 'var(--amber)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Which part is UV printed?
                    </label>
                    <input
                      type="text"
                      value={uvPart}
                      onChange={e => setUvPart(e.target.value)}
                      placeholder="e.g. Acrylic backboard, front panel graphic, logo insert..."
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        background: 'rgba(255,180,0,0.04)',
                        border: '1px solid rgba(255,180,0,0.25)',
                        borderRadius: 6,
                        color: 'var(--text)',
                        fontSize: '0.85rem',
                      }}
                    />
                  </div>
                )}

                {/* Additional Instructions */}
                <div>
                  <div className="panel-label" style={{ marginBottom: 10, marginTop: 4 }}>3. Extras (optional)</div>
                  <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-3)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Additional Instructions
                  </label>
                  <textarea
                    value={extra}
                    onChange={e => setExtra(e.target.value)}
                    placeholder="Any custom requirements... e.g. 'Wall-mounted with black acrylic backboard'"
                    style={{
                      width: '100%',
                      height: 80,
                      padding: '10px 12px',
                      background: 'var(--bg)',
                      border: '1px solid var(--border)',
                      borderRadius: 6,
                      color: 'var(--text)',
                      fontSize: '0.85rem',
                      resize: 'vertical',
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={mode === 'full' ? runFullPipeline : runBwOnly}
              disabled={busy || (mode === 'full' ? !logo : !mockupFile)}
              style={{
                width: '100%',
                padding: '14px 20px',
                background: busy ? 'var(--surface-2)' : '#9beaf8',
                color: busy ? 'var(--text-3)' : '#000000',
                border: 'none',
                borderRadius: 8,
                fontSize: '0.9rem',
                fontWeight: 600,
                cursor: busy ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
              }}
            >
              {busy ? (
                <span>Working...</span>
              ) : (
                <><span>✦</span> Generate {mode === 'full' ? 'Mockup & Quote' : 'Quote'}</>
              )}
            </button>

            {error && (
              <div style={{
                marginTop: 12,
                padding: '10px 13px',
                background: 'var(--red-dim)',
                border: '1px solid rgba(220,38,38,0.3)',
                borderRadius: 8,
                color: 'var(--red)',
                fontSize: '0.82rem',
                display: 'flex',
                alignItems: 'flex-start',
                gap: 8,
              }}>
                <span>!</span><span>{error}</span>
              </div>
            )}
              </div>

          {/* RIGHT — Results */}
          <div style={{
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: 18,
          }}>
            <div className="panel-label" style={{ marginBottom: 12 }}>Results</div>

            {/* Results Display */}
            <div>
              {busy && !(mode === 'full' ? mockupB64 : bwB64) ? (
                <GeneratingAnimation mode={mode} />
              ) : (mode === 'full' ? mockupB64 : bwB64) ? (
                <div style={{
                  background: '#020209',
                  minHeight: 200,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  position: 'relative',
                  overflow: 'hidden',
                  borderRadius: 8,
                }}>
                  <div style={{
                    position: 'absolute',
                    inset: 0,
                    background: 'radial-gradient(ellipse at center, rgba(232,23,93,0.10) 0%, transparent 60%)',
                    pointerEvents: 'none',
                  }} />
                  <img
                    src={`data:image/png;base64,${mode === 'full' ? mockupB64 : bwB64}`}
                    alt={mode === 'full' ? "mockup" : "sketch"}
                    style={{ maxWidth: '100%', maxHeight: 280, position: 'relative', zIndex: 1 }}
                  />
                </div>
              ) : (
                <div style={{
                  padding: 40,
                  textAlign: 'center',
                  color: 'var(--text-3)',
                  fontSize: '0.85rem',
                  background: 'var(--bg)',
                  borderRadius: 8,
                }}>
                  Click <strong style={{ color: 'var(--text-2)' }}>Generate</strong> to see results.
                </div>
              )}

              {(mode === 'full' ? mockupB64 : bwB64) && (
                <a
                  href={`data:image/png;base64,${mode === 'full' ? mockupB64 : bwB64}`}
                  download={mode === 'full' ? "neon_mockup.png" : "cut_sheet.png"}
                  style={{
                    display: 'block',
                    marginTop: 12,
                    padding: '10px 14px',
                    background: 'var(--surface-2)',
                    borderRadius: 6,
                    textAlign: 'center',
                    fontSize: '0.8rem',
                    fontWeight: 500,
                    color: 'var(--text-2)',
                    textDecoration: 'none',
                  }}
                >
                  ↓ Download {mode === 'full' ? 'mockup' : 'cut sheet'}
                </a>
              )}

              {measurement && (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: 8,
                  marginTop: 12,
                }}>
                  <Detail label="Tube length" value={`${measurement.measured_m.toFixed(2)} m`} />
                  <Detail label="Sign quality" value={TIER_LABELS[measurement.tier] ?? measurement.tier} variant={measurement.tier === 'GLASS_CUT' ? 'green' : undefined} />
                  <Detail label="Confidence" value={`${(measurement.confidence * 100).toFixed(0)}%`} />
                  <Detail label="Processing time" value={`${measurement.elapsed_s?.toFixed(1) ?? '—'} s`} />
                </div>
              )}

              <QuoteTab
                measurement={measurement}
                loading={busy}
                uvNeon={uvNeon}
                signType={signType}
              />
            </div>

          </div>
            </div>
          </div>
        </div>
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

function Detail({ label, value, variant }: {
  label: string; value: string; variant?: 'amber' | 'green';
}) {
  const bgColor = variant === 'green' ? 'rgba(0,229,200,0.1)' : variant === 'amber' ? 'rgba(255,180,0,0.1)' : 'var(--bg)';
  const borderColor = variant === 'green' ? 'rgba(0,229,200,0.3)' : variant === 'amber' ? 'rgba(255,180,0,0.3)' : 'var(--border)';
  const valueColor = variant === 'green' ? 'var(--cyan)' : variant === 'amber' ? 'var(--amber)' : 'var(--text)';

  return (
    <div style={{
      padding: '10px 12px',
      background: bgColor,
      border: `1px solid ${borderColor}`,
      borderRadius: 6,
    }}>
      <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: '0.9rem', fontWeight: 600, color: valueColor }}>{value}</div>
    </div>
  );
}

function QuoteTab({ measurement, loading, uvNeon, signType }: {
  measurement: MeasurementResult | null; loading: boolean; uvNeon: boolean; signType: SignType;
}) {
  if (!measurement || loading) return null;

  const len           = measurement.measured_m;
  const costPerMetre  = SIGN_TYPE_MULTIPLIERS[signType];
  const rawMaterial   = len * costPerMetre;
  const markupAmount  = rawMaterial * MARKUP_RATE;
  const subtotal      = rawMaterial + markupAmount;
  const shipping      = measurement.shipping_cost ?? 0;
  const uvSurcharge   = uvNeon ? Math.max(15, len * 5) : 0;
  const total         = subtotal + shipping + uvSurcharge;

  return (
    <div style={{
      background: 'var(--bg)',
      borderRadius: 8,
      marginTop: 12,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 20px', border: '1px solid var(--border)', borderRadius: 8, background: 'var(--surface)' }}>
        <span style={{ color: 'var(--text)', fontSize: '1rem', fontWeight: 700 }}>Total Quote</span>
        <span style={{ color: 'var(--cyan)', fontSize: '1.25rem', fontWeight: 700 }}>${total.toFixed(2)}</span>
      </div>
    </div>
  );
}

/* ─── Fancy Generating Animation ─────────────────────────────── */

const LOADING_MESSAGES = [
  { text: 'Analyzing your design…', icon: '🔍' },
  { text: 'Tracing neon tube paths…', icon: '✨' },
  { text: 'Bending the glass tubes…', icon: '🌟' },
  { text: 'Mixing neon gas colors…', icon: '🌈' },
  { text: 'Mounting on the wall…', icon: '🔨' },
  { text: 'Adjusting the glow…', icon: '💡' },
  { text: 'Perfecting the lighting…', icon: '🌃' },
  { text: 'Adding the final touches…', icon: '🎨' },
  { text: 'Almost there…', icon: '🚀' },
];

function GeneratingAnimation({ mode }: { mode: Mode }) {
  const [msgIdx, setMsgIdx] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [fade, setFade] = useState(true);

  useEffect(() => {
    const timer = setInterval(() => setElapsed(s => s + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const cycle = setInterval(() => {
      setFade(false);
      setTimeout(() => {
        setMsgIdx(i => (i + 1) % LOADING_MESSAGES.length);
        setFade(true);
      }, 300);
    }, 5000);
    return () => clearInterval(cycle);
  }, []);

  const msg = LOADING_MESSAGES[msgIdx];
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  const timeStr = mins > 0 ? `${mins}m ${secs.toString().padStart(2, '0')}s` : `${secs}s`;

  return (
    <div style={{
      padding: '44px 24px',
      textAlign: 'center',
      background: 'linear-gradient(180deg, rgba(232,23,93,0.04) 0%, var(--surface) 100%)',
      borderRadius: 8,
      border: '1px solid var(--border)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Animated neon ring */}
      <div style={{
        width: 64,
        height: 64,
        margin: '0 auto 20px',
        borderRadius: '50%',
        position: 'relative',
      }}>
        <div style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          border: '3px solid rgba(232,23,93,0.15)',
        }} />
        <div className="neon-ring-spin" style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          border: '3px solid transparent',
          borderTopColor: '#E8175D',
          borderRightColor: 'rgba(232,23,93,0.4)',
          filter: 'drop-shadow(0 0 6px rgba(232,23,93,0.6))',
        }} />
        <div className="neon-glow-pulse" style={{
          position: 'absolute',
          inset: -8,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(232,23,93,0.15) 0%, transparent 70%)',
        }} />
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.5rem',
          transition: 'opacity 0.3s ease',
          opacity: fade ? 1 : 0,
        }}>
          {msg.icon}
        </div>
      </div>

      {/* Cycling message */}
      <div style={{
        fontSize: '0.92rem',
        fontWeight: 600,
        color: 'var(--text)',
        marginBottom: 6,
        transition: 'opacity 0.3s ease',
        opacity: fade ? 1 : 0,
        minHeight: '1.4em',
      }}>
        {msg.text}
      </div>

      <p style={{
        margin: '0 0 16px',
        fontSize: '0.75rem',
        color: 'var(--text-3)',
      }}>
        Crafting your {mode === 'full' ? 'neon mockup' : 'cut sheet'} — stay on this page
      </p>

      {/* Elapsed timer */}
      <div style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '6px 14px',
        background: 'rgba(232,23,93,0.08)',
        border: '1px solid rgba(232,23,93,0.2)',
        borderRadius: 20,
        fontSize: '0.72rem',
        fontWeight: 600,
        fontFamily: 'var(--font-mono)',
        color: 'var(--pink, #E8175D)',
        fontVariantNumeric: 'tabular-nums',
      }}>
        <span className="timer-blink" style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: '#E8175D',
        }} />
        {timeStr}
      </div>
    </div>
  );
}
