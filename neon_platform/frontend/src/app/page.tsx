'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import NavBar from '@/components/NavBar';

type Tab = 'mockup' | 'quote';

type Sample = { word: string; color: string; glow: string };
const SIGN_OPTIONS: Sample[] = [
  { word: 'OPEN',    color: '#FF1464', glow: '255,20,100' },
  { word: 'COFFEE',  color: '#FFB400', glow: '255,180,0' },
  { word: 'LOVE ♡',  color: '#FF1464', glow: '255,20,100' },
  { word: 'BAR',     color: '#00E5C8', glow: '0,229,200' },
  { word: 'BOLT ⚡', color: '#FFB400', glow: '255,180,0' },
];

const COLOR_OPTIONS = [
  { hex: '#E8175D', glow: '232,23,93',  name: 'Hot Pink' },
  { hex: '#FF4500', glow: '255,69,0',   name: 'Red Orange' },
  { hex: '#D97706', glow: '217,119,6',  name: 'Warm Amber' },
  { hex: '#0891B2', glow: '8,145,178',  name: 'Neon Cyan' },
  { hex: '#16A34A', glow: '22,163,74',  name: 'Electric Green' },
  { hex: '#7C3AED', glow: '124,58,237', name: 'Ultra Violet' },
  { hex: '#111827', glow: '17,24,39',   name: 'Pure White' },
  { hex: '#DB2777', glow: '219,39,119', name: 'Soft Pink' },
];

export default function LandingPage() {
  // Hero (small) frame state
  const [smTab, setSmTab]                 = useState<Tab>('mockup');
  const [smColor, setSmColor]             = useState(COLOR_OPTIONS[0]);
  const [smWidth, setSmWidth]             = useState('');
  const [smBgName, setSmBgName]           = useState('');
  const [smUv, setSmUv]                   = useState(false);

  // Demo (big) section state
  const [bigTab, setBigTab]               = useState<Tab>('mockup');
  const [bigColor, setBigColor]           = useState(COLOR_OPTIONS[0]);
  const [bigWidth, setBigWidth]           = useState('');
  const [bigBg, setBigBg]                 = useState<File | null>(null);
  const [bigUv, setBigUv]                 = useState(false);
  const [bigUvPart, setBigUvPart]         = useState('');
  const [bigSign, setBigSign]             = useState<Sample>(SIGN_OPTIONS[0]);

  // Scroll-reveal observer
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;
    const els = document.querySelectorAll('.reveal');
    const obs = new IntersectionObserver(
      entries => {
        entries.forEach(en => {
          if (en.isIntersecting) {
            en.target.classList.add('in');
            obs.unobserve(en.target);
          }
        });
      },
      { threshold: 0.18, rootMargin: '0px 0px -10% 0px' }
    );
    els.forEach(el => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  return (
    <div>
      <NavBar />

      {/* ───────── HERO ───────── */}
      <section>
        <div className="wrapper hero">
          <div className="hero-left">
            <div className="hero-badge">
              <span className="badge-dot" />
              Live measurement engine
            </div>

            <h1 className="hero-headline">
              Turn any artwork into<br />
              a <span className="accent">neon sign quote</span><br />
              in 60 seconds.
            </h1>

            <p className="hero-sub">
              Drop in a logo or mockup. Neonizer&rsquo;s AI traces every tube,
              counts every bend, and builds a production quote — automatically.
              No back-and-forth. No guesswork.
            </p>

            <div className="hero-actions">
              <Link href="/register"><button className="btn-primary">Start for free →</button></Link>
              <Link href="/studio">
                <button className="btn-secondary">
                  <span className="play-icon">▶</span>
                  Watch demo
                </button>
              </Link>
            </div>

            <div className="trust-chips">
              <div className="trust-chip">
                <CheckIcon />
                No credit card
              </div>
              <div className="trust-chip">
                <CheckIcon />
                20 free quotes / month
              </div>
              <div className="trust-chip">
                <CheckIcon />
                Cancel anytime
              </div>
            </div>
          </div>

          {/* App Preview Frame */}
          <div className="app-frame">
            <div className="frame-bar">
              <div className="dot-r" /><div className="dot-y" /><div className="dot-g" />
              <div className="frame-url">neonizer.app / studio</div>
            </div>
            <div className="frame-body">
              {/* Input panel */}
              <div className="frame-input">
                <div className="upload-zone">
                  <div className="upload-icon-wrap">↑</div>
                  <p>Drop your design</p>
                  <span>PNG · JPG · SVG · CDR</span>
                </div>
                <div className="instruction-box-frame">
                  <div className="instr-header">
                    <span className="instr-badge">AI Instructions</span>
                    <span className="ai-dot" />
                  </div>
                  <textarea className="instr-textarea" placeholder="e.g. Outdoor, warm white, wall-mounted..." />

                  {/* Color + Width + BG */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 0.8fr 1fr', gap: 5, marginBottom: 7 }}>
                    <div style={{ position: 'relative' }}>
                      <span style={{
                        position: 'absolute', left: 7, top: '50%', transform: 'translateY(-50%)',
                        width: 10, height: 10, borderRadius: '50%',
                        background: smColor.hex,
                        boxShadow: `0 0 5px rgba(${smColor.glow},0.8)`,
                        pointerEvents: 'none',
                      }} />
                      <select
                        value={smColor.hex}
                        onChange={e => {
                          const c = COLOR_OPTIONS.find(c => c.hex === e.target.value);
                          if (c) setSmColor(c);
                        }}
                        style={{
                          width: '100%', appearance: 'none', WebkitAppearance: 'none',
                          background: 'rgba(0,0,0,0.03)', border: '1px solid var(--border-2)',
                          borderRadius: 6, padding: '5px 18px 5px 22px',
                          color: 'var(--text)', fontFamily: 'var(--font-body)',
                          fontSize: '0.6rem', fontWeight: 500, outline: 'none', cursor: 'pointer',
                        }}>
                        {COLOR_OPTIONS.slice(0, 7).map(c => (
                          <option key={c.hex} value={c.hex}>{c.name}</option>
                        ))}
                      </select>
                      <span style={{
                        position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)',
                        fontSize: '0.45rem', color: 'var(--text-3)', pointerEvents: 'none',
                      }}>▼</span>
                    </div>

                    <div style={{ position: 'relative' }}>
                      <input type="number" placeholder="24" min={1} max={240}
                        value={smWidth}
                        onChange={e => setSmWidth(e.target.value)}
                        style={{
                          width: '100%',
                          background: 'rgba(0,0,0,0.03)',
                          border: '1px solid var(--border-2)',
                          borderRadius: 6, padding: '5px 22px 5px 8px',
                          color: 'var(--text)', fontFamily: 'var(--font-mono)',
                          fontSize: '0.62rem', fontWeight: 500, outline: 'none',
                          MozAppearance: 'textfield' as React.CSSProperties['MozAppearance'],
                          fontVariantNumeric: 'tabular-nums',
                        }} />
                      <span style={{
                        position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)',
                        fontSize: '0.52rem', fontWeight: 600, color: 'var(--text-3)',
                        pointerEvents: 'none', fontFamily: 'var(--font-mono)',
                      }}>in</span>
                    </div>

                    <label style={{ position: 'relative', overflow: 'hidden', cursor: 'pointer' }}>
                      <input type="file" accept="image/*"
                        onChange={e => {
                          const f = e.target.files?.[0];
                          if (f) setSmBgName(f.name.length > 12 ? f.name.slice(0, 10) + '…' : f.name);
                        }}
                        style={{ position: 'absolute', inset: 0, opacity: 0, cursor: 'pointer', zIndex: 2 }} />
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: 5,
                        background: 'rgba(0,0,0,0.02)',
                        border: `1px dashed ${smBgName ? 'rgba(0,229,200,0.4)' : 'var(--border-2)'}`,
                        borderRadius: 6, padding: '5px 8px',
                        transition: 'all 0.2s',
                      }}>
                        <span style={{ fontSize: '0.65rem', color: 'var(--cyan)' }}>🖼</span>
                        <span style={{
                          fontSize: '0.6rem',
                          color: smBgName ? 'var(--cyan)' : 'var(--text-3)',
                          fontWeight: 500,
                          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                        }}>
                          {smBgName || 'Background'}
                        </span>
                      </div>
                    </label>
                  </div>

                  {/* UV checkbox */}
                  <div onClick={() => setSmUv(!smUv)} style={{
                    display: 'flex', alignItems: 'flex-start', gap: 7,
                    padding: '7px 9px',
                    background: smUv ? 'var(--amber-dim)' : 'rgba(0,0,0,0.02)',
                    border: `1px solid ${smUv ? 'rgba(255,180,0,0.4)' : 'var(--border-2)'}`,
                    borderRadius: 6, cursor: 'pointer', marginBottom: 7,
                    transition: 'all 0.2s',
                  }}>
                    <div style={{
                      width: 13, height: 13, borderRadius: 3,
                      border: `1.5px solid ${smUv ? 'var(--amber)' : 'var(--border-2)'}`,
                      background: smUv ? 'var(--amber)' : 'transparent',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0, marginTop: 1,
                      boxShadow: smUv ? '0 0 8px rgba(255,180,0,0.4)' : 'none',
                      transition: 'all 0.18s',
                    }}>
                      {smUv && <span style={{ fontSize: '0.5rem', fontWeight: 900, color: '#000', lineHeight: 1 }}>✓</span>}
                    </div>
                    <div>
                      <div style={{ fontSize: '0.62rem', fontWeight: 600, color: 'var(--text)', lineHeight: 1.2, marginBottom: 1 }}>
                        UV Printed Part
                      </div>
                      <div style={{ fontSize: '0.56rem', color: 'var(--text-3)', lineHeight: 1.3 }}>
                        Sign includes a UV-printed component
                      </div>
                    </div>
                  </div>

                  {smUv && (
                    <div style={{ marginBottom: 7 }}>
                      <textarea
                        placeholder="Which part? e.g. acrylic backboard…"
                        style={{
                          width: '100%',
                          background: 'rgba(255,180,0,0.04)',
                          border: '1px solid rgba(255,180,0,0.25)',
                          borderRadius: 6, padding: '6px 8px',
                          color: 'var(--text)', fontFamily: 'var(--font-body)',
                          fontSize: '0.62rem', resize: 'none', height: 38, outline: 'none',
                        }}
                      />
                    </div>
                  )}

                  <button className="gen-btn">Generate →</button>
                </div>
              </div>

              {/* Output panel */}
              <div className="frame-output">
                <div className="output-tabs-sm">
                  <button className={`tab-sm ${smTab === 'mockup' ? 'active' : ''}`} onClick={() => setSmTab('mockup')}>Mockup</button>
                  <button className={`tab-sm ${smTab === 'quote' ? 'active' : ''}`}  onClick={() => setSmTab('quote')}>Quote</button>
                </div>

                {smTab === 'mockup' && (
                  <>
                    <div className="neon-preview-box">
                      <span className="neon-sign-text">OPEN</span>
                    </div>
                    <div className="output-meta-sm">
                      <div className="meta-pill"><span className="label">Tube length</span><span className="value">3.12 m</span></div>
                      <div className="meta-pill highlight"><span className="label">Quote</span><span className="value">$184.50</span></div>
                      <div className="meta-pill"><span className="label">Tolerance</span><span className="value">±4.8%</span></div>
                      <div className="meta-pill"><span className="label">Tier</span><span className="value">GLASS-CUT</span></div>
                    </div>
                  </>
                )}

                {smTab === 'quote' && (
                  <div style={{ padding: 12, fontSize: '0.72rem' }}>
                    <QRow label="Tube length" value="3.12 m" />
                    <QRow label="Cost / metre" value="$42.00" />
                    <QRow label="Markup" value="40%" />
                    <QRow label="Total quote" value="$184.50" total />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ───────── STATS BAR ───────── */}
      <div className="stats-bar reveal">
        <div className="wrapper">
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-value">12<span>,</span>400<span>+</span></div>
              <div className="stat-label">Signs measured</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">≤<span>5</span>%</div>
              <div className="stat-label">Cutting tolerance</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">&lt;<span>5</span>s</div>
              <div className="stat-label">Per measurement</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">120<span>+</span></div>
              <div className="stat-label">Sign manufacturers</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">$1<span>.</span>2<span>M</span></div>
              <div className="stat-label">In quotes generated</div>
            </div>
          </div>
        </div>
      </div>

      {/* ───────── 3-STAGE VISUAL ───────── */}
      <section className="section">
        <div className="wrapper">
          <div className="stages-header reveal">
            <div className="section-tag">From artwork to production</div>
            <h2 className="section-title">Three stages, one upload.</h2>
            <p className="section-sub">
              Watch your customer&rsquo;s logo become a photoreal mockup, then a precise cut sheet,
              then a ready-to-send quote.
            </p>
          </div>

          <div className="stages-grid">
            <div className="stage-card reveal" data-delay="1">
              <div className="stage-visual" style={{ flexDirection: 'column', gap: 6 }}>
                <span style={{ fontSize: '2.5rem' }}>🖼</span>
                <span style={{
                  fontSize: '0.7rem', fontFamily: 'var(--font-mono)',
                  color: 'var(--text-3)', letterSpacing: '0.05em',
                }}>customer_logo.png</span>
              </div>
              <div className="stage-body">
                <div className="stage-num">01 — SOURCE</div>
                <div className="title">Customer artwork</div>
                <p>Whatever they sent — JPG, PNG, SVG, or CDR. Neonizer detects the format automatically.</p>
              </div>
            </div>

            <div className="stage-card reveal" data-delay="2">
              <div className="stage-visual neon-bg">OPEN</div>
              <div className="stage-body">
                <div className="stage-num">02 — MOCKUP</div>
                <div className="title">Photoreal neon render</div>
                <p>AI shows exactly how the finished sign will glow — the exact image your customer signs off on.</p>
              </div>
            </div>

            <div className="stage-card reveal" data-delay="3">
              <div className="stage-visual sketch-bg">
                <div className="sketch-lines">
                  <Stage3SketchSvg />
                </div>
              </div>
              <div className="stage-body">
                <div className="stage-num">03 — MEASURED</div>
                <div className="title">Cut-ready geometry</div>
                <p>Every path traced, every bend counted, total length confirmed. Send straight to your bender.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ───────── DEMO / TOOLBOX ───────── */}
      <section className="demo-section">
        <div className="wrapper">
          <div className="reveal" style={{ marginBottom: 56 }}>
            <div className="section-tag">The studio</div>
            <h2 className="section-title">Upload. Instruct. Generate.</h2>
            <p className="section-sub">
              The instruction toolbox is your control room. Tell the AI exactly what you need —
              mounting style, glow color, weatherproofing, size — and it adapts the output.
            </p>
          </div>

          <div className="demo-layout">
            {/* LEFT — Upload + Instruction toolbox */}
            <div className="big-input-panel reveal" data-delay="1">
              <div>
                <div className="panel-label">1. Upload your artwork</div>
                <div className="big-upload">
                  <div className="big-upload-icon">↑</div>
                  <h4>Drop your sign design here</h4>
                  <p>Or click to browse your files</p>
                  <div className="format-chips">
                    <span className="fmt">PNG</span>
                    <span className="fmt">JPG</span>
                    <span className="fmt">SVG</span>
                    <span className="fmt">CDR</span>
                  </div>
                </div>
              </div>

              <div>
                <div className="panel-label">2. Set your instructions</div>
                <div className="big-instr-box">
                  <div className="big-instr-header">
                    <div className="instr-title">
                      <span>AI Instruction Toolbox</span>
                      <span className="badge">Active</span>
                    </div>
                    <div className="ai-status">
                      <span className="status-dot" />
                      Ready
                    </div>
                  </div>

                  <div className="big-instr-body">
                    <textarea
                      className="big-instr-textarea"
                      placeholder="Describe any custom requirements… e.g. 'Make it suitable for outdoor use, warm white glow, approximately 36 inches wide, wall-mounted with a black acrylic backboard.'"
                    />

                    <div className="toolbox-row">
                      <div className="toolbox-field">
                        <label>Neon Color</label>
                        <div className="color-select-wrap">
                          <span className="color-swatch" style={{
                            background: bigColor.hex,
                            boxShadow: `0 0 8px rgba(${bigColor.glow},0.7)`,
                          }} />
                          <select
                            className="color-select"
                            value={bigColor.hex}
                            onChange={e => {
                              const c = COLOR_OPTIONS.find(c => c.hex === e.target.value);
                              if (c) setBigColor(c);
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
                            value={bigWidth}
                            onChange={e => setBigWidth(e.target.value)}
                          />
                          <span className="width-unit">in</span>
                        </div>
                      </div>

                      <div className="toolbox-field">
                        <label>Background Image</label>
                        <div className="bg-upload-zone" style={{
                          borderColor: bigBg ? 'rgba(0,229,200,0.4)' : undefined,
                        }}>
                          <input
                            type="file" accept="image/*"
                            onChange={e => setBigBg(e.target.files?.[0] ?? null)}
                          />
                          <div className="bg-upload-icon">🖼</div>
                          <div className="bg-upload-text">
                            <p>{bigBg ? 'Background set ✓' : 'Upload background'}</p>
                            <span>PNG · JPG · WEBP</span>
                          </div>
                        </div>
                        {bigBg && (
                          <div className="bg-file-name visible">
                            <span>✓</span>
                            <span>{bigBg.name.length > 22 ? bigBg.name.slice(0, 20) + '…' : bigBg.name}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* UV Coating */}
                    <div
                      className={`uv-checkbox-wrap ${bigUv ? 'checked' : ''}`}
                      onClick={() => setBigUv(!bigUv)}
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

                    <div className={`uv-part-field ${bigUv ? 'visible' : ''}`}>
                      <label className="toolbox-field" style={{ gap: 6, display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'var(--amber)' }}>
                          Which part is UV printed?
                        </span>
                        <div style={{ position: 'relative' }}>
                          <textarea
                            value={bigUvPart}
                            onChange={e => setBigUvPart(e.target.value)}
                            placeholder="e.g. Acrylic backboard, front panel graphic, logo insert…"
                            style={{
                              height: 60,
                              background: 'rgba(126, 218, 243, 0.04)',
                              border: '1px solid rgba(255,180,0,0.25)',
                              borderRadius: 8,
                              padding: '10px 12px',
                              margin: 0,
                              resize: 'none',
                              width: '100%',
                              color: 'var(--text)',
                              fontFamily: 'var(--font-body)',
                              fontSize: '0.82rem',
                              outline: 'none',
                            }}
                          />
                        </div>
                      </label>
                    </div>

                    <button className="big-gen-btn">
                      <span>✦</span> Generate mockup &amp; quote
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* RIGHT — Outputs */}
            <div className="reveal" data-delay="2">
              <div className="panel-label" style={{ marginBottom: 12 }}>3. Your outputs</div>
              <div className="big-output-panel">
                <div className="big-tabs">
                  <button className={`big-tab ${bigTab === 'mockup' ? 'active' : ''}`} onClick={() => setBigTab('mockup')}>✦ Neon Mockup</button>
                  <button className={`big-tab ${bigTab === 'quote' ? 'active' : ''}`}  onClick={() => setBigTab('quote')}>$ Cost Quote</button>
                </div>

                {bigTab === 'mockup' && (
                  <>
                    <div className="sign-selector">
                      {SIGN_OPTIONS.map(s => (
                        <button key={s.word}
                          className={`sign-opt ${bigSign.word === s.word ? 'active' : ''}`}
                          onClick={() => setBigSign(s)}
                        >
                          {s.word}
                        </button>
                      ))}
                    </div>
                    <div className="mockup-display">
                      <span
                        key={bigSign.word}
                        className="big-neon-sign"
                        style={{
                          color: bigSign.color,
                          textShadow:
                            `0 0 7px ${bigSign.color}, 0 0 15px ${bigSign.color},` +
                            ` 0 0 30px rgba(${bigSign.glow},0.8),` +
                            ` 0 0 60px rgba(${bigSign.glow},0.4),` +
                            ` 0 0 100px rgba(${bigSign.glow},0.2)`,
                        }}
                      >
                        {bigSign.word}
                      </span>
                    </div>
                    <div className="output-details">
                      <div className="detail-card"><div className="d-label">Tube length</div><div className="d-value">3.12 m</div></div>
                      <div className="detail-card"><div className="d-label">Tolerance</div><div className="d-value">±4.8%</div></div>
                      <div className="detail-card amber"><div className="d-label">Quote</div><div className="d-value">$184.50</div></div>
                      <div className="detail-card"><div className="d-label">Tier</div><div className="d-value">GLASS-CUT</div></div>
                      <div className="detail-card green"><div className="d-label">Confidence</div><div className="d-value">High</div></div>
                      <div className="detail-card"><div className="d-label">Sign width</div><div className="d-value">24 in</div></div>
                    </div>
                  </>
                )}

                {bigTab === 'quote' && (
                  <div className="quote-display">
                    <div className="quote-row"><span className="q-label">Tube length</span><span className="q-value">3.12 m</span></div>
                    <div className="quote-row"><span className="q-label">Cost per metre</span><span className="q-value">$42.00</span></div>
                    <div className="quote-row"><span className="q-label">Raw material cost</span><span className="q-value">$131.04</span></div>
                    <div className="quote-row"><span className="q-label">Labour estimate</span><span className="q-value">~2.5 hrs</span></div>
                    <div className="quote-row"><span className="q-label">Markup applied</span><span className="q-value">40%</span></div>
                    <div className="quote-row"><span className="q-label">Shipping Cost</span><span className="q-value">+$18.00</span></div>
                    <div className="quote-row total"><span className="q-label">Total customer quote</span><span className="q-value">$184.50</span></div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ───────── FEATURES ───────── */}
      <section className="section">
        <div className="wrapper">
          <div className="reveal">
            <div className="section-tag">Everything you need</div>
            <h2 className="section-title">Built for neon shops, end to end.</h2>
            <p className="section-sub">
              Neonizer isn&rsquo;t a single tool — it&rsquo;s a full production workflow.
              Mockup, measure, price, and deliver, all from one platform.
            </p>
          </div>

          <div className="features-grid">
            <div className="feature-card reveal" data-delay="1">
              <div className="feature-icon">✦</div>
              <h3>AI Neon Mockup</h3>
              <p>Drop in a flat brand logo and Neonizer renders a photoreal LED neon mockup — the exact look your customer is signing off on.</p>
            </div>
            <div className="feature-card reveal" data-delay="2">
              <div className="feature-icon cyan">◎</div>
              <h3>Tube Extraction</h3>
              <p>Centerlines pulled straight from your mockup. Every path traced, every bend counted. Send the cut sheet to your bender as-is.</p>
            </div>
            <div className="feature-card reveal" data-delay="3">
              <div className="feature-icon amber">$</div>
              <h3>Breakeven Pricing</h3>
              <p>Tube length × your cost per metre × your markup. Set it once, every quote uses it. Know your margin before you send anything.</p>
            </div>
            <div className="feature-card reveal" data-delay="1">
              <div className="feature-icon">⬡</div>
              <h3>Instruction Toolbox</h3>
              <p>Guide the AI with custom instructions and preset chips — outdoor, RGB, double-sided, wall-mount. The output adapts to your spec.</p>
            </div>
            <div className="feature-card reveal" data-delay="2">
              <div className="feature-icon cyan">{'{ }'}</div>
              <h3>REST API</h3>
              <p>One POST request. Everything you see in the dashboard, also as JSON. Bake Neonizer into your existing shop software or CRM.</p>
            </div>
            <div className="feature-card reveal" data-delay="3">
              <div className="feature-icon amber">⚡</div>
              <h3>Always On, Sub-5s</h3>
              <p>Quote a wedding sign at 11 pm. Process 200 in a morning. Same &lt;5 second speed, 24/7. No queue, no downtime.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ───────── HOW IT WORKS ───────── */}
      <section className="section" style={{ paddingTop: 0 }}>
        <div className="wrapper">
          <div className="reveal" style={{ textAlign: 'center', marginBottom: 0 }}>
            <div className="section-tag" style={{ justifyContent: 'center' }}>The process</div>
            <h2 className="section-title">Four steps, one send.</h2>
          </div>

          <div className="steps-grid">
            <div className="step-item reveal" data-delay="1">
              <div className="step-num">01</div>
              <h4>Upload</h4>
              <p>Drop in your sign image. Format is detected automatically.</p>
            </div>
            <div className="step-item reveal" data-delay="2">
              <div className="step-num">02</div>
              <h4>Instruct</h4>
              <p>Set your specs in the toolbox — or use the quick-select chips.</p>
            </div>
            <div className="step-item reveal" data-delay="3">
              <div className="step-num">03</div>
              <h4>Generate</h4>
              <p>AI traces every tube, renders the mockup, and measures geometry in under 5 seconds.</p>
            </div>
            <div className="step-item reveal" data-delay="4">
              <div className="step-num">04</div>
              <h4>Quote</h4>
              <p>Receive your mockup and final quote. Send it, bend it, done.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ───────── CTA ───────── */}
      <section className="cta-section">
        <div className="wrapper">
          <div className="cta-inner reveal">
            <h2>Quote your first sign<br />in <span style={{ color: 'var(--pink)' }}>60 seconds.</span></h2>
            <p>Free forever — 20 measurements every month, no credit card required. Join 120+ sign manufacturers already quoting faster.</p>
            <div className="cta-actions">
              <Link href="/register">
                <button className="btn-primary" style={{ fontSize: '1rem', padding: '15px 32px' }}>
                  Create your free account →
                </button>
              </Link>
              <Link href="/pricing">
                <button className="btn-secondary">View pricing</button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ───────── FOOTER ───────── */}
      <footer className="footer">
        <div className="wrapper">
          <div className="footer-grid">
            <div className="footer-brand">
              <div className="nav-logo">
                <span className="logo-dot" />
                Neonizer
              </div>
              <p>Precision tube-length measurement and instant quoting for neon sign manufacturers. Built for the shop floor.</p>
            </div>
            <div className="footer-col">
              <h5>Product</h5>
              <ul>
                <li><Link href="/studio">Studio</Link></li>
                <li><Link href="/dashboard">Quick Measure</Link></li>
                <li><Link href="/pricing">Pricing</Link></li>
                <li><Link href="#">API</Link></li>
              </ul>
            </div>
            <div className="footer-col">
              <h5>Resources</h5>
              <ul>
                <li><Link href="#">Documentation</Link></li>
                <li><Link href="#">Tutorials</Link></li>
                <li><Link href="#">Blog</Link></li>
                <li><Link href="#">FAQ</Link></li>
              </ul>
            </div>
            <div className="footer-col">
              <h5>Company</h5>
              <ul>
                <li><Link href="#">About</Link></li>
                <li><Link href="#">Contact</Link></li>
                <li><Link href="#">Status</Link></li>
                <li><Link href="#">Terms</Link></li>
              </ul>
            </div>
          </div>
          <div className="footer-bottom">
            <span>© 2026 Neonizer. All rights reserved.</span>
            <span>Built for neon manufacturers.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

/* ─── helpers ─────────────────────────────────────────────────── */

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4.5 7l1.8 1.8 3-3.3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function QRow({ label, value, total }: { label: string; value: string; total?: boolean }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between',
      padding: total ? '8px 0' : '6px 0',
      borderBottom: total ? 'none' : '1px solid var(--border)',
      color: total ? 'var(--text)' : 'var(--text-2)',
      fontWeight: total ? 700 : 400,
    }}>
      <span style={{ color: total ? 'var(--text)' : undefined }}>{label}</span>
      <span style={{
        fontFamily: 'var(--font-mono)',
        color: total ? 'var(--amber)' : 'var(--text)',
        fontVariantNumeric: 'tabular-nums',
      }}>{value}</span>
    </div>
  );
}

function Stage3SketchSvg() {
  return (
    <svg viewBox="0 0 100 70" fill="none">
      <rect x="5" y="10" width="3" height="50" rx="1.5" fill="white" opacity="0.7" />
      <rect x="5" y="10" width="18" height="3" rx="1.5" fill="white" opacity="0.7" />
      <rect x="5" y="33" width="18" height="3" rx="1.5" fill="white" opacity="0.7" />
      <rect x="5" y="57" width="18" height="3" rx="1.5" fill="white" opacity="0.7" />
      <rect x="28" y="10" width="3" height="50" rx="1.5" fill="white" opacity="0.7" />
      <rect x="40" y="10" width="3" height="50" rx="1.5" fill="white" opacity="0.7" />
      <path d="M43 10 C43 10 57 10 57 30 C57 50 43 50 43 50" stroke="white" strokeWidth="3" strokeLinecap="round" fill="none" opacity="0.7" />
      <rect x="65" y="10" width="3" height="50" rx="1.5" fill="white" opacity="0.7" />
      <path d="M68 10 L83 60" stroke="white" strokeWidth="3" strokeLinecap="round" opacity="0.7" />
      <path d="M68 60 L83 10" stroke="white" strokeWidth="3" strokeLinecap="round" opacity="0.7" />
      <line x1="2" y1="65" x2="88" y2="65" stroke="rgba(255,20,100,0.6)" strokeWidth="0.8" strokeDasharray="3,2" />
      <text x="44" y="69" fill="rgba(255,20,100,0.8)" fontSize="4" fontFamily="monospace" textAnchor="middle">3.12 m · ±5%</text>
    </svg>
  );
}
