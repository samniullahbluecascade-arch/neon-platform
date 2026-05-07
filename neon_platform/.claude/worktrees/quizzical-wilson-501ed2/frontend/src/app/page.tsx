'use client';
import { useState, useMemo } from 'react';
import Link from 'next/link';
import NavBar from '@/components/NavBar';

type Sample = {
  name: string;
  color: 'pink' | 'cyan' | 'green' | 'amber';
  length: number;
  tier: 'GLASS-CUT' | 'QUOTE' | 'ESTIMATE';
  svg: React.ReactNode;
};

const SAMPLES: Sample[] = [
  {
    name: 'OPEN', color: 'pink', length: 2.34, tier: 'GLASS-CUT',
    svg: (
      <svg viewBox="0 0 320 120" style={{ width: '70%', maxHeight: '78%' }}>
        <path className="tube-glow tube-draw" d="M 30 30 Q 15 30 15 60 Q 15 90 30 90 Q 60 90 60 60 Q 60 30 30 30 Z" />
        <path className="tube-glow tube-draw" d="M 80 90 L 80 30 L 105 30 Q 120 30 120 45 Q 120 60 105 60 L 80 60" />
        <path className="tube-glow tube-draw" d="M 175 30 L 140 30 L 140 90 L 175 90 M 140 60 L 170 60" />
        <path className="tube-glow tube-draw" d="M 195 90 L 195 30 L 235 90 L 235 30" />
      </svg>
    ),
  },
  {
    name: 'COFFEE', color: 'amber', length: 3.12, tier: 'GLASS-CUT',
    svg: (
      <svg viewBox="0 0 280 160" style={{ width: '60%', maxHeight: '80%' }}>
        <path className="tube-glow amber tube-draw" d="M 60 70 L 60 130 Q 60 140 70 140 L 150 140 Q 160 140 160 130 L 160 70 Z" />
        <path className="tube-glow amber tube-draw" d="M 160 85 Q 195 85 195 110 Q 195 130 160 130" />
        <path className="tube-glow amber tube-draw" d="M 85 60 Q 75 45 85 30 Q 95 15 85 0" />
        <path className="tube-glow amber tube-draw" d="M 110 60 Q 100 45 110 30 Q 120 15 110 0" />
        <path className="tube-glow amber tube-draw" d="M 135 60 Q 125 45 135 30 Q 145 15 135 0" />
      </svg>
    ),
  },
  {
    name: 'HEART', color: 'pink', length: 1.85, tier: 'GLASS-CUT',
    svg: (
      <svg viewBox="0 0 200 180" style={{ width: '60%', maxHeight: '80%' }}>
        <path className="tube-glow tube-draw" d="M 100 160 L 30 90 Q 5 65 30 40 Q 55 15 80 40 L 100 60 L 120 40 Q 145 15 170 40 Q 195 65 170 90 Z" />
      </svg>
    ),
  },
  {
    name: 'BOLT', color: 'cyan', length: 1.42, tier: 'QUOTE',
    svg: (
      <svg viewBox="0 0 160 200" style={{ width: '50%', maxHeight: '85%' }}>
        <path className="tube-glow cyan tube-draw" d="M 100 10 L 30 110 L 75 110 L 60 190 L 130 80 L 90 80 Z" />
      </svg>
    ),
  },
];

export default function LandingPage() {
  const [activeIdx, setActiveIdx] = useState(1);
  const [widthIn, setWidthIn] = useState(24);

  const sample = SAMPLES[activeIdx];
  const measuredM = useMemo(() => sample.length * (widthIn / 24), [sample.length, widthIn]);
  const price = Math.max(25, Math.round(measuredM * 10 * 1.4));
  const tierColor = sample.tier === 'GLASS-CUT' ? 'var(--green)' : sample.tier === 'QUOTE' ? 'var(--cyan)' : 'var(--amber)';

  return (
    <div style={{ minHeight: '100vh' }}>
      <NavBar />

      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <section style={{
        padding: '4rem 2rem 5rem',
        position: 'relative',
        overflow: 'hidden',
        background:
          'radial-gradient(ellipse 800px 500px at 0% 0%, var(--pink-soft) 0%, transparent 55%),' +
          'radial-gradient(ellipse 600px 400px at 100% 30%, var(--cyan-soft) 0%, transparent 55%)',
      }}>
        <div style={{
          maxWidth: '1240px', margin: '0 auto',
          display: 'grid', gridTemplateColumns: '1.05fr 1fr', gap: '4rem', alignItems: 'center',
        }} className="hero-grid">

          <div className="fade-up">
            <div className="pill" style={{ marginBottom: '1.5rem' }}>Live measurement engine</div>
            <h1 style={{
              fontFamily: 'Bebas Neue, sans-serif',
              fontSize: 'clamp(2.6rem, 5.5vw, 4.6rem)',
              letterSpacing: '0.02em',
              lineHeight: 1.02,
              marginBottom: '1.25rem',
            }}>
              Quote any neon sign<br />
              in <span className="neon-pink">60 seconds.</span>
            </h1>
            <p style={{
              color: 'var(--text-dim)',
              fontSize: '1.1rem',
              lineHeight: 1.6,
              marginBottom: '2rem',
              maxWidth: '540px',
            }}>
              Drop in a logo, mockup, or sketch. Neonizer measures every tube down to the bend, then
              prices it for you. Stop tracing, stop emailing leads back and forth — just quote and bend.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.75rem' }}>
              <Link href="/register">
                <button className="btn-neon" style={{ padding: '0.95rem 1.8rem', fontSize: '0.95rem' }}>
                  Start for free →
                </button>
              </Link>
              <Link href="/dashboard">
                <button className="btn-ghost" style={{ padding: '0.9rem 1.7rem', fontSize: '0.9rem' }}>
                  Watch a demo
                </button>
              </Link>
            </div>
            <div style={{ display: 'flex', gap: '1.25rem', fontSize: '0.78rem', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
              <span><span style={{ color: 'var(--green)' }}>●</span> No credit card</span>
              <span><span style={{ color: 'var(--green)' }}>●</span> 20 free measurements / month</span>
              <span><span style={{ color: 'var(--green)' }}>●</span> Cancel anytime</span>
            </div>
          </div>

          {/* Live demo panel */}
          <div className="fade-up-2" style={{
            background: '#fff',
            border: '1px solid var(--border)',
            borderRadius: '18px',
            boxShadow: 'var(--shadow-xl)',
            overflow: 'hidden',
          }}>
            <div style={{
              padding: '0.75rem 1.1rem',
              borderBottom: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              background: 'var(--bg-1)',
            }}>
              <div style={{ display: 'flex', gap: '5px' }}>
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#ff5f57' }} />
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#ffbd2e' }} />
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#28c840' }} />
              </div>
              <div style={{
                fontFamily: 'Space Mono, monospace', fontSize: '0.65rem',
                letterSpacing: '0.18em', color: 'var(--text-muted)', textTransform: 'uppercase',
              }}>neonizer.app / measure</div>
              <div style={{ width: 42 }} />
            </div>

            <div className="dark-screen" key={activeIdx} style={{
              aspectRatio: '5 / 3',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              borderRadius: 0,
            }}>
              {sample.svg}
            </div>

            <div style={{
              padding: '1rem 1.1rem',
              display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem',
              borderBottom: '1px solid var(--border)',
            }}>
              <Stat label="Tube length" value={measuredM.toFixed(2)} unit="m" />
              <Stat label="Breakeven" value={`$${price.toFixed(2)}`} valueColor="var(--green)" />
              <Stat label="Quality tier" value={sample.tier} valueColor={tierColor} small />
            </div>

            <div style={{ padding: '0.95rem 1.1rem 1.1rem', display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
              <div>
                <div style={demoCtrlLabel}>Try a sample</div>
                <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.45rem' }}>
                  {SAMPLES.map((s, i) => (
                    <button
                      key={s.name}
                      onClick={() => setActiveIdx(i)}
                      style={{
                        flex: 1,
                        padding: '0.55rem',
                        background: i === activeIdx ? 'var(--pink-soft)' : '#fff',
                        border: `1px solid ${i === activeIdx ? 'var(--pink)' : 'var(--border)'}`,
                        borderRadius: 6,
                        cursor: 'pointer',
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        color: i === activeIdx ? 'var(--pink-deep)' : 'var(--text-dim)',
                        transition: 'all 0.15s',
                      }}
                    >
                      {s.name}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div style={demoCtrlLabel}>Sign width</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.7rem', marginTop: '0.45rem' }}>
                  <input
                    type="range" min={12} max={48} value={widthIn}
                    onChange={e => setWidthIn(parseInt(e.target.value))}
                    style={{ flex: 1, accentColor: 'var(--pink)' }}
                  />
                  <div style={{ fontFamily: 'Space Mono, monospace', fontSize: '0.85rem', fontWeight: 700, minWidth: 60, textAlign: 'right' }}>
                    {widthIn} in
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SOCIAL PROOF ─────────────────────────────────────────────────── */}
      <div style={{
        borderTop: '1px solid var(--border)',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-1)',
        padding: '1.5rem 2rem',
      }}>
        <div style={{
          maxWidth: '1100px', margin: '0 auto',
          display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: '2rem', alignItems: 'center',
        }}>
          {[
            ['12,400+', 'Signs measured'],
            ['≤5%', 'Cutting tolerance'],
            ['<5s', 'Per measurement'],
            ['120+', 'Sign manufacturers'],
            ['$1.2M', 'In quotes generated'],
          ].map(([v, l]) => (
            <div key={l} style={{ textAlign: 'center' }}>
              <div style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '2rem', color: 'var(--pink)', letterSpacing: '0.03em', lineHeight: 1 }}>{v}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginTop: '0.4rem' }}>{l}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── BEFORE / DURING / AFTER ──────────────────────────────────────── */}
      <section style={sectionStyle}>
        <div style={containerStyle}>
          <SectionHead
            eyebrow="From sketch to quote"
            title={<>See <span className="neon-pink">how it transforms</span> your artwork</>}
            sub="Three stages, one upload. Watch your customer's logo turn into a photoreal mockup, then a clean tube sketch, then a measured cutting plan."
          />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1.25rem' }} className="ba-grid">
            {/* 1. Source */}
            <BACard step="01 — Source" title="Customer artwork" desc="Whatever they sent you — JPG, PNG, SVG, or CDR.">
              <div style={{ ...baScreen, background: '#fff', backgroundImage: 'none' }}>
                <svg viewBox="0 0 200 150" style={{ width: '80%' }}>
                  <text x="100" y="85" textAnchor="middle" fontFamily="Bebas Neue" fontSize="42" fill="#0a0a14" letterSpacing="2">OPEN</text>
                  <text x="100" y="115" textAnchor="middle" fontFamily="DM Sans" fontSize="11" fill="#8a8a9a">customer logo.png</text>
                </svg>
              </div>
            </BACard>

            {/* 2. Mockup */}
            <BACard step="02 — Mockup" title="Photoreal neon render" desc="AI shows exactly how the finished sign will glow.">
              <div className="dark-screen" style={baScreenInner}>
                <svg viewBox="0 0 200 150" style={{ width: '85%' }}>
                  <path className="tube-glow" strokeWidth={5} d="M 30 50 Q 30 35 45 35 L 65 35 Q 80 35 80 50 L 80 90 Q 80 105 65 105 L 45 105 Q 30 105 30 90 Z" />
                  <path className="tube-glow" strokeWidth={5} d="M 95 35 L 95 105 M 95 35 L 130 105 M 130 35 L 130 105" />
                  <path className="tube-glow" strokeWidth={5} d="M 145 50 Q 145 35 160 35 L 175 35 Q 180 35 180 40 L 180 50 Q 180 60 170 60 L 155 60 Q 145 60 145 70 L 145 100 Q 145 105 150 105 L 175 105" />
                </svg>
              </div>
            </BACard>

            {/* 3. Measured */}
            <BACard step="03 — Measured" title="Cut-ready geometry" desc="Every path traced, every bend counted, length confirmed.">
              <div className="dark-screen" style={baScreenInner}>
                <svg viewBox="0 0 200 150" style={{ width: '85%' }}>
                  <path className="tube-glow" strokeWidth={5} strokeOpacity={0.4} d="M 30 50 Q 30 35 45 35 L 65 35 Q 80 35 80 50 L 80 90 Q 80 105 65 105 L 45 105 Q 30 105 30 90 Z" />
                  <path className="tube-glow" strokeWidth={5} strokeOpacity={0.4} d="M 95 35 L 95 105 M 95 35 L 130 105 M 130 35 L 130 105" />
                  <path className="tube-glow" strokeWidth={5} strokeOpacity={0.4} d="M 145 50 Q 145 35 160 35 L 175 35 Q 180 35 180 40 L 180 50 Q 180 60 170 60 L 155 60 Q 145 60 145 70 L 145 100 Q 145 105 150 105 L 175 105" />
                  <path d="M 30 50 Q 30 35 45 35 L 65 35 Q 80 35 80 50 L 80 90 Q 80 105 65 105 L 45 105 Q 30 105 30 90 Z" fill="none" stroke="#fff" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M 95 35 L 95 105 M 95 35 L 130 105 M 130 35 L 130 105" fill="none" stroke="#fff" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M 145 50 Q 145 35 160 35 L 175 35 Q 180 35 180 40 L 180 50 Q 180 60 170 60 L 155 60 Q 145 60 145 70 L 145 100 Q 145 105 150 105 L 175 105" fill="none" stroke="#fff" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="30" cy="50" r="2.5" fill="var(--pink)" />
                  <circle cx="80" cy="90" r="2.5" fill="var(--pink)" />
                  <circle cx="95" cy="35" r="2.5" fill="var(--pink)" />
                  <circle cx="130" cy="105" r="2.5" fill="var(--pink)" />
                  <circle cx="145" cy="50" r="2.5" fill="var(--pink)" />
                  <circle cx="175" cy="105" r="2.5" fill="var(--pink)" />
                  <line x1="20" y1="125" x2="180" y2="125" stroke="rgba(255,255,255,0.5)" strokeWidth={2} strokeDasharray="4 4" strokeLinecap="round" />
                  <text x="100" y="140" textAnchor="middle" fontFamily="Space Mono" fontSize="9" fill="#fff">2.34 m  ·  ±5%  ·  GLASS-CUT</text>
                </svg>
              </div>
            </BACard>
          </div>
        </div>
      </section>

      {/* ── BENTO GRID ───────────────────────────────────────────────────── */}
      <section style={{ ...sectionStyle, background: 'var(--bg-1)', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
        <div style={containerStyle}>
          <SectionHead
            eyebrow="Built for neon shops"
            title={<>Everything you need to <span className="neon-pink">price &amp; produce</span></>}
            sub="Neonizer isn't a single tool — it's a workshop. Mockup generation, tube extraction, breakeven pricing, and an API to wire it into your stack."
          />

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(6, 1fr)',
            gridAutoRows: 'minmax(180px, auto)',
            gap: '1rem',
          }} className="bento-grid">
            {/* Big AI mockup tile */}
            <BentoCell span={3} rowSpan>
              <BentoEyebrow>AI Mockup</BentoEyebrow>
              <div style={{ ...bentoTitle, fontSize: '2rem' }}>From flat logo<br />to glowing neon.</div>
              <div style={bentoDesc}>Drop in a flat brand logo and Neonizer renders a photoreal LED neon mockup — the exact look your customer is signing off on.</div>
              <div className="dark-screen" style={bentoVisual}>
                <svg viewBox="0 0 200 120" style={{ width: '70%' }}>
                  <path className="tube-glow" strokeWidth={6} d="M 25 70 Q 25 45 45 45 L 75 45 Q 95 45 95 65 L 95 85 Q 95 95 85 95 L 35 95 Q 25 95 25 85 Z" />
                  <path className="tube-glow" strokeWidth={6} d="M 110 45 L 110 95 M 110 45 L 145 95 M 145 45 L 145 95" />
                  <path className="tube-glow" strokeWidth={6} d="M 160 95 L 160 65 Q 160 45 175 45" />
                </svg>
              </div>
            </BentoCell>

            {/* Tube extraction */}
            <BentoCell span={3}>
              <BentoEyebrow>Tube extraction</BentoEyebrow>
              <div style={bentoTitle}>Black-and-white sketch in one pass.</div>
              <div style={bentoDesc}>Centerlines pulled straight from your mockup. Send it to your bender as-is.</div>
              <div style={{ ...bentoVisual, background: '#fff', backgroundImage: 'none' }}>
                <svg viewBox="0 0 200 60" style={{ width: '70%' }}>
                  <path d="M 15 30 Q 15 15 30 15 L 60 15 M 75 15 L 75 45 M 75 15 L 105 45 M 105 15 L 105 45 M 120 15 L 150 15 Q 165 15 165 30 Q 165 45 150 45 L 120 45" fill="none" stroke="#0a0a14" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </BentoCell>

            {/* Breakeven pricing */}
            <BentoCell span={3}>
              <BentoEyebrow>Breakeven pricing</BentoEyebrow>
              <div style={bentoTitle}>Know your margin before you quote.</div>
              <div style={bentoDesc}>Tube length × your cost per metre × your markup. Set it once, every quote uses it.</div>
              <div style={{
                marginTop: '1rem',
                padding: '0.85rem 1rem',
                background: 'linear-gradient(135deg, #ecfdf5, #f0fdfa)',
                border: '1px solid #a7f3d0',
                borderRadius: 8,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Quote</span>
                  <span style={{ fontFamily: 'Space Mono, monospace', fontSize: '1.5rem', fontWeight: 700, color: 'var(--green)' }}>$184.50</span>
                </div>
              </div>
            </BentoCell>

            {/* REST API */}
            <BentoCell span={3}>
              <BentoEyebrow>REST API</BentoEyebrow>
              <div style={bentoTitle}>Bake it into your shop.</div>
              <div style={bentoDesc}>One POST. Everything you see in the dashboard, also as JSON.</div>
              <pre style={{
                flex: 1, marginTop: '1rem',
                background: 'var(--dark)',
                borderRadius: 8, padding: '1rem',
                fontFamily: 'Space Mono, monospace', fontSize: '0.72rem',
                color: '#c8c8d8', lineHeight: 1.7, overflowX: 'auto',
              }}>
{`# Measure a sign image
`}<span style={{ color: '#f472b6' }}>POST</span>{` /v1/measure
{
  `}<span style={{ color: '#34d399' }}>{`"image"`}</span>{`: ...,
  `}<span style={{ color: '#34d399' }}>{`"width_in"`}</span>{`: 24
}`}
              </pre>
            </BentoCell>

            {/* Formats */}
            <BentoCell span={2}>
              <BentoEyebrow>File formats</BentoEyebrow>
              <div style={bentoTitle}>Bring anything.</div>
              <div style={{ flex: 1, marginTop: '1rem', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem', alignContent: 'center' }}>
                {['PNG', 'JPG', 'SVG', 'CDR'].map(f => (
                  <div key={f} style={{
                    padding: '0.7rem',
                    border: '1px solid var(--border)', borderRadius: 6,
                    textAlign: 'center', fontFamily: 'Space Mono, monospace', fontSize: '0.78rem',
                    color: 'var(--text-dim)', background: 'var(--bg-1)',
                  }}>{f}</div>
                ))}
              </div>
            </BentoCell>

            {/* ML accuracy */}
            <BentoCell span={2}>
              <BentoEyebrow>ML boost</BentoEyebrow>
              <div style={bentoTitle}>±5% on clean sketches.</div>
              <div style={bentoDesc}>Optional ML correction layer learns from your shop's past jobs and tightens accuracy over time.</div>
            </BentoCell>

            {/* 24/7 */}
            <BentoCell span={2}>
              <BentoEyebrow>Always on</BentoEyebrow>
              <div style={bentoTitle}>24 / 7, sub-5 second runs.</div>
              <div style={bentoDesc}>Quote a wedding sign at 11pm. Quote 200 in a morning. Same speed.</div>
            </BentoCell>
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS (FLOW CHART) ────────────────────────────────────── */}
      <section style={sectionStyle} id="how">
        <div style={containerStyle}>
          <SectionHead
            eyebrow="Process"
            title={<>How it <span className="neon-pink">works</span></>}
            sub="Four steps from a customer's image to a quote you can send."
          />
          <div style={{ display: 'flex', alignItems: 'stretch', gap: '0.5rem', flexWrap: 'wrap', marginTop: '3rem' }} className="steps-row">
            <StepNode num="01" title="Upload" desc="Drop in your sign image. The format is detected automatically." />
            <StepArrow />
            <StepNode num="02" title="Process" desc="Our pipeline traces every tube path and measures the geometry." />
            <StepArrow />
            <StepNode num="03" title="Validate" desc="Physics checks confirm tube diameter, length-per-inch and image resolution." />
            <StepArrow />
            <StepNode num="04" title="Quote" desc="Receive a cut-ready length and a confidence band. Bend it, or quote the customer." />
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section style={{
        ...sectionStyle, textAlign: 'center',
        background: 'linear-gradient(135deg, #fdf2f7 0%, #f0fdfa 100%)',
      }}>
        <div style={containerStyle}>
          <h2 style={{
            fontFamily: 'Bebas Neue, sans-serif',
            fontSize: 'clamp(2.1rem, 4.5vw, 3.2rem)',
            letterSpacing: '0.03em', marginBottom: '0.85rem', lineHeight: 1.05,
          }}>
            Quote your first sign in <span className="neon-pink">60 seconds.</span>
          </h2>
          <p style={{ color: 'var(--text-dim)', fontSize: '1.05rem', maxWidth: '620px', margin: '0 auto 2rem', lineHeight: 1.6 }}>
            Free forever — 20 measurements every month, no credit card required.
          </p>
          <Link href="/register">
            <button className="btn-neon" style={{ padding: '0.95rem 1.8rem', fontSize: '0.95rem' }}>
              Create your free account →
            </button>
          </Link>
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────────────────── */}
      <footer style={{
        background: 'var(--dark)', color: '#c8c8d8',
        padding: '4rem 2rem 2rem',
      }}>
        <div style={{
          maxWidth: '1180px', margin: '0 auto',
          display: 'grid', gridTemplateColumns: '1.3fr 1fr 1fr 1fr 1fr', gap: '3rem',
          marginBottom: '3rem',
        }} className="footer-grid">
          <div>
            <div style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.6rem', letterSpacing: '0.04em', marginBottom: '0.85rem' }}>
              <span style={{ color: '#fff' }}>Neon</span><span style={{ color: 'var(--pink)' }}>izer</span>
            </div>
            <div style={{ color: 'rgba(255,255,255,0.55)', fontSize: '0.85rem', lineHeight: 1.6, maxWidth: 280 }}>
              Precision tube-length measurement and instant quoting for neon sign manufacturers.
            </div>
          </div>
          <FooterCol heading="Product" links={[
            ['Studio', '/studio'], ['Quick Measure', '/dashboard'], ['Pricing', '/pricing'], ['API', '#'],
          ]} />
          <FooterCol heading="Resources" links={[
            ['Documentation', '#'], ['Tutorials', '#'], ['Blog', '#'], ['FAQ', '#'],
          ]} />
          <FooterCol heading="Company" links={[
            ['About', '#'], ['Contact', '#'], ['Status', '#'],
          ]} />
          <FooterCol heading="Legal" links={[
            ['Terms', '#'], ['Privacy', '#'], ['Security', '#'],
          ]} />
        </div>
        <div style={{
          maxWidth: '1180px', margin: '0 auto',
          borderTop: '1px solid rgba(255,255,255,0.1)',
          paddingTop: '1.5rem',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          flexWrap: 'wrap', gap: '1rem',
          color: 'rgba(255,255,255,0.45)', fontFamily: 'Space Mono, monospace', fontSize: '0.75rem',
        }}>
          <span>© 2026 Neonizer. All rights reserved.</span>
          <span>Built for neon manufacturers.</span>
        </div>
      </footer>

      {/* ── RESPONSIVE OVERRIDES ─────────────────────────────────────────── */}
      <style jsx global>{`
        @media (max-width: 1000px) {
          .hero-grid { grid-template-columns: 1fr !important; gap: 3rem !important; }
          .ba-grid   { grid-template-columns: 1fr !important; }
          .bento-grid { grid-template-columns: repeat(2, 1fr) !important; }
          .footer-grid { grid-template-columns: 1fr 1fr !important; gap: 2rem !important; }
        }
        @media (max-width: 720px) {
          .steps-row { flex-direction: column !important; gap: 0.25rem !important; }
          .step-arrow { transform: rotate(90deg); padding: 0.4rem 0; }
          .footer-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}

/* ── HELPERS ────────────────────────────────────────────────────────── */
const sectionStyle: React.CSSProperties = { padding: '5rem 2rem' };
const containerStyle: React.CSSProperties = { maxWidth: '1180px', margin: '0 auto' };

const demoCtrlLabel: React.CSSProperties = {
  fontSize: '0.62rem', color: 'var(--text-muted)',
  letterSpacing: '0.12em', textTransform: 'uppercase',
};

const baScreen: React.CSSProperties = {
  aspectRatio: '4 / 3', borderRadius: 0,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  padding: '1.5rem',
};
const baScreenInner: React.CSSProperties = {
  ...baScreen,
  borderRadius: 0,
};

const bentoTitle: React.CSSProperties = {
  fontFamily: 'Bebas Neue, sans-serif',
  fontSize: '1.55rem', letterSpacing: '0.04em',
  marginBottom: '0.5rem',
};
const bentoDesc: React.CSSProperties = {
  color: 'var(--text-dim)', fontSize: '0.88rem', lineHeight: 1.55,
};
const bentoVisual: React.CSSProperties = {
  flex: 1, marginTop: '1rem', borderRadius: 8,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  overflow: 'hidden', minHeight: 140, padding: '1rem',
};

function Stat({ label, value, unit, valueColor, small }: {
  label: string; value: string; unit?: string; valueColor?: string; small?: boolean;
}) {
  return (
    <div>
      <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
        {label}
      </div>
      <div style={{
        fontFamily: 'Space Mono, monospace',
        fontSize: small ? '0.85rem' : '1.25rem',
        fontWeight: 700,
        color: valueColor ?? 'var(--text)',
        letterSpacing: small ? '0.05em' : 'normal',
      }}>
        {value}{unit && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: 3, fontWeight: 400 }}>{unit}</span>}
      </div>
    </div>
  );
}

function SectionHead({ eyebrow, title, sub }: { eyebrow: string; title: React.ReactNode; sub: string }) {
  return (
    <div style={{ textAlign: 'center', maxWidth: 720, margin: '0 auto 3rem' }}>
      <div style={{
        fontFamily: 'Space Mono, monospace', fontSize: '0.7rem',
        color: 'var(--pink)', letterSpacing: '0.18em', textTransform: 'uppercase',
        marginBottom: '0.85rem',
      }}>{eyebrow}</div>
      <h2 style={{
        fontFamily: 'Bebas Neue, sans-serif',
        fontSize: 'clamp(2.1rem, 4.5vw, 3.2rem)',
        letterSpacing: '0.03em', marginBottom: '0.85rem', lineHeight: 1.05,
      }}>{title}</h2>
      <p style={{ color: 'var(--text-dim)', fontSize: '1.05rem', maxWidth: 620, margin: '0 auto', lineHeight: 1.6 }}>
        {sub}
      </p>
    </div>
  );
}

function BACard({ step, title, desc, children }: { step: string; title: string; desc: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid var(--border)',
      borderRadius: 14, overflow: 'hidden', boxShadow: 'var(--shadow)',
    }}>
      {children}
      <div style={{ padding: '1rem 1.25rem', borderTop: '1px solid var(--border)' }}>
        <div style={{ fontFamily: 'Space Mono, monospace', fontSize: '0.65rem', color: 'var(--pink)', letterSpacing: '0.18em', marginBottom: '0.35rem' }}>{step}</div>
        <div style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.2rem', letterSpacing: '0.04em' }}>{title}</div>
        <div style={{ color: 'var(--text-dim)', fontSize: '0.83rem', lineHeight: 1.5, marginTop: '0.3rem' }}>{desc}</div>
      </div>
    </div>
  );
}

function BentoCell({ span, rowSpan, children }: { span: number; rowSpan?: boolean; children: React.ReactNode }) {
  return (
    <div style={{
      gridColumn: `span ${span}`,
      gridRow: rowSpan ? 'span 2' : undefined,
      background: '#fff', border: '1px solid var(--border)', borderRadius: 14,
      padding: rowSpan ? '2rem' : '1.6rem',
      transition: 'border-color 0.2s, box-shadow 0.2s, transform 0.2s',
      display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative',
    }}
    onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--pink)'; e.currentTarget.style.boxShadow = 'var(--shadow)'; e.currentTarget.style.transform = 'translateY(-2px)'; }}
    onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = ''; e.currentTarget.style.transform = ''; }}
    >
      {children}
    </div>
  );
}

function BentoEyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontFamily: 'Space Mono, monospace', fontSize: '0.62rem',
      color: 'var(--pink)', letterSpacing: '0.18em', textTransform: 'uppercase',
      marginBottom: '0.7rem',
    }}>{children}</div>
  );
}

function StepNode({ num, title, desc }: { num: string; title: string; desc: string }) {
  return (
    <div className="card" style={{
      flex: '1 1 180px',
      padding: '1.75rem 1.25rem 1.5rem',
      textAlign: 'center', position: 'relative',
    }}>
      <div style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: 42, height: 42, borderRadius: '50%',
        background: 'var(--pink)', color: '#fff',
        fontFamily: 'Space Mono, monospace', fontSize: '0.8rem', fontWeight: 700,
        marginBottom: '0.95rem',
        boxShadow: '0 4px 14px rgba(233,30,99,0.3)',
        position: 'relative', zIndex: 1,
      }}>{num}</div>
      <div style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.4rem', letterSpacing: '0.05em', marginBottom: '0.45rem' }}>{title}</div>
      <div style={{ color: 'var(--text-dim)', fontSize: '0.85rem', lineHeight: 1.55 }}>{desc}</div>
    </div>
  );
}

function StepArrow() {
  return (
    <div className="step-arrow" aria-hidden style={{
      flex: '0 0 32px', display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: 'var(--pink)', alignSelf: 'center',
    }}>
      <svg width={44} height={14} viewBox="0 0 44 14" fill="none">
        <line x1={0} y1={7} x2={34} y2={7} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeDasharray="4 5" />
        <path d="M32 1L42 7L32 13" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      </svg>
    </div>
  );
}

function FooterCol({ heading, links }: { heading: string; links: [string, string][] }) {
  return (
    <div>
      <h4 style={{
        fontFamily: 'Space Mono, monospace', fontSize: '0.7rem',
        letterSpacing: '0.18em', textTransform: 'uppercase',
        color: 'rgba(255,255,255,0.55)', marginBottom: '1rem',
      }}>{heading}</h4>
      <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
        {links.map(([label, href]) => (
          <li key={label}>
            <Link href={href} style={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.88rem', textDecoration: 'none' }}>
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
