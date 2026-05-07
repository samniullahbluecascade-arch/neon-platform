'use client';
import { useEffect, useRef, useState } from 'react';

/**
 * Auto-looping cinematic of the full pipeline:
 *   1. LOGO     — flat black silhouette of an "OPEN" coffee cup logo
 *   2. DESIGN   — colored neon mockup wash + soft halo (Gemini phase)
 *   3. CRAFTING — neon tube traced over the design (path-draw animation)
 *   4. LOC      — measurement readout ticks up (V8 pipeline)
 *
 * Pure SVG + CSS — no external libs. Pauses when off-screen.
 */

type Stage = 'logo' | 'design' | 'craft' | 'loc';

const SEQ: { stage: Stage; dur: number }[] = [
  { stage: 'logo',   dur: 1600 },
  { stage: 'design', dur: 1600 },
  { stage: 'craft',  dur: 4800 },
  { stage: 'loc',    dur: 3600 },
];

// Final measured length (m) — matches the price formula max(25, 10*m)
const TARGET_M = 2.34;
const TARGET_PRICE = Math.max(25, Math.round(TARGET_M * 10));

// ─── SVG path data (coffee cup + steam) ──────────────────────────────────────
// Each path uses stroke-linecap=round so it reads as a real bent neon tube.
const PATHS = {
  cupBody:
    'M 110 150 L 110 250 Q 110 280 140 280 L 240 280 Q 270 280 270 250 L 270 150 Z',
  handle:
    'M 270 175 Q 320 175 320 215 Q 320 255 270 255',
  steam1: 'M 145 130 Q 130 105 145 80 Q 160 55 145 30',
  steam2: 'M 190 130 Q 175 105 190 80 Q 205 55 190 30',
  steam3: 'M 235 130 Q 220 105 235 80 Q 250 55 235 30',
};

// Order matters — visual draw sequence. pathLength=100 normalises every
// path so stroke-dasharray / stroke-dashoffset use a known length and the
// tube fully closes (no trailing gap from underestimated path length).
const TUBES: { d: string; color: string; delay: number }[] = [
  { d: PATHS.cupBody, color: '#ff2d78', delay: 0    },
  { d: PATHS.handle,  color: '#ff2d78', delay: 700  },
  { d: PATHS.steam1,  color: '#00d4ff', delay: 1200 },
  { d: PATHS.steam2,  color: '#00d4ff', delay: 1400 },
  { d: PATHS.steam3,  color: '#00d4ff', delay: 1600 },
];

export default function NeonPipelineAnimation() {
  const [stage, setStage] = useState<Stage>('logo');
  const [visible, setVisible] = useState(false);
  const [counter, setCounter] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);

  // Pause off-screen
  useEffect(() => {
    if (!wrapRef.current) return;
    const obs = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting),
      { threshold: 0.15 },
    );
    obs.observe(wrapRef.current);
    return () => obs.disconnect();
  }, []);

  // Stage cycler — only runs while visible
  useEffect(() => {
    if (!visible) return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let idx = 0;
    const tick = () => {
      const cur = SEQ[idx];
      setStage(cur.stage);
      timer = setTimeout(() => {
        idx = (idx + 1) % SEQ.length;
        tick();
      }, cur.dur);
    };
    tick();
    return () => { if (timer) clearTimeout(timer); };
  }, [visible]);

  // LOC counter tick-up when stage hits 'loc'
  useEffect(() => {
    if (stage !== 'loc') { setCounter(0); return; }
    let raf = 0;
    const start = performance.now();
    const dur = 1400;
    const animate = (now: number) => {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      setCounter(eased * TARGET_M);
      if (t < 1) raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [stage]);

  const stageIdx = SEQ.findIndex(s => s.stage === stage);
  const showCraft = stage === 'craft' || stage === 'loc';
  const showLoc   = stage === 'loc';
  const showDesign = stage === 'design' || showCraft;

  return (
    <section style={{ padding: '5rem 2rem', maxWidth: '1100px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
        <div style={{
          fontFamily: 'Space Mono, monospace',
          fontSize: '0.72rem',
          letterSpacing: '0.2em',
          color: 'var(--pink)',
          textTransform: 'uppercase',
          marginBottom: '0.6rem',
        }}>
          End-to-End Pipeline · Live Demo
        </div>
        <h2 style={{
          fontFamily: 'Bebas Neue, sans-serif',
          fontSize: 'clamp(2.5rem, 5vw, 4rem)',
          letterSpacing: '0.05em',
        }}>
          FROM LOGO TO <span className="neon-cyan">CUT-READY GLASS</span>
        </h2>
      </div>

      <div ref={wrapRef} className="card" style={{
        padding: '2rem',
        position: 'relative',
        overflow: 'hidden',
        background: 'linear-gradient(180deg, #0a0a14 0%, #07070e 100%)',
      }}>
        {/* Stage progress strip */}
        <div style={{
          display: 'flex',
          gap: '0.75rem',
          marginBottom: '1.5rem',
          flexWrap: 'wrap',
        }}>
          {SEQ.map((s, i) => {
            const active = i === stageIdx;
            const past   = i < stageIdx;
            const color  = active ? '#ff2d78' : past ? '#00ff9d' : 'var(--border)';
            const labels = ['LOGO', 'DESIGN', 'CRAFTING', 'LOC + PRICE'];
            return (
              <div key={s.stage} style={{
                flex: 1,
                minWidth: '120px',
                padding: '0.55rem 0.75rem',
                border: `1px solid ${color}`,
                borderRadius: '4px',
                background: active ? `${color}15` : 'transparent',
                transition: 'all 0.4s ease',
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.62rem',
                  fontFamily: 'Space Mono, monospace',
                  letterSpacing: '0.12em',
                  color,
                  textTransform: 'uppercase',
                }}>
                  <span style={{
                    display: 'inline-block',
                    width: '8px', height: '8px', borderRadius: '50%',
                    background: color,
                    boxShadow: active ? `0 0 8px ${color}` : undefined,
                    animation: active ? 'pulse 1.4s infinite' : undefined,
                  }} />
                  0{i + 1} · {labels[i]}
                </div>
              </div>
            );
          })}
        </div>

        {/* Stage caption */}
        <div style={{
          textAlign: 'center',
          minHeight: '24px',
          marginBottom: '1rem',
          fontSize: '0.78rem',
          fontFamily: 'Space Mono, monospace',
          color: 'var(--text-dim)',
          letterSpacing: '0.05em',
        }}>
          {stage === 'logo'   && 'Client uploads brand logo / sign sketch.'}
          {stage === 'design' && 'Gemini renders photorealistic colored neon mockup.'}
          {stage === 'craft'  && 'V8 extracts tube centerlines and traces the glass path.'}
          {stage === 'loc'    && `LOC measured · price computed · cut-ready.`}
        </div>

        {/* Scene */}
        <div style={{
          position: 'relative',
          aspectRatio: '16 / 9',
          maxHeight: '440px',
          margin: '0 auto',
          borderRadius: '6px',
          background: 'radial-gradient(ellipse at center, #0d0d18 0%, #050509 80%)',
          overflow: 'hidden',
        }}>
          <svg
            viewBox="0 0 600 400"
            style={{ width: '100%', height: '100%', display: 'block' }}
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              {/* Soft glow filter for tubes */}
              <filter id="np-glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="4" result="blur1" />
                <feGaussianBlur stdDeviation="10" in="SourceGraphic" result="blur2" />
                <feMerge>
                  <feMergeNode in="blur2" />
                  <feMergeNode in="blur1" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              {/* Subtle grid pattern (background) */}
              <pattern id="np-grid" width="30" height="30" patternUnits="userSpaceOnUse">
                <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#1a1a26" strokeWidth="0.5" />
              </pattern>
            </defs>

            <rect width="600" height="400" fill="url(#np-grid)" opacity="0.6" />

            {/* Scene group — centered around viewBox center horizontally */}
            <g transform="translate(95, 30)">

              {/* STAGE 1 — Logo silhouette (visible when stage='logo' OR fading into design) */}
              <g style={{
                opacity: stage === 'logo' ? 1 : (stage === 'design' ? 0.35 : 0),
                transition: 'opacity 0.8s ease',
              }}>
                <path d={PATHS.cupBody} fill="#1c1c28" stroke="#2a2a38" strokeWidth="2" />
                <path d={PATHS.handle}  fill="none"     stroke="#2a2a38" strokeWidth="14" strokeLinecap="round" />
                <path d={PATHS.steam1}  fill="none"     stroke="#2a2a38" strokeWidth="6"  strokeLinecap="round" />
                <path d={PATHS.steam2}  fill="none"     stroke="#2a2a38" strokeWidth="6"  strokeLinecap="round" />
                <path d={PATHS.steam3}  fill="none"     stroke="#2a2a38" strokeWidth="6"  strokeLinecap="round" />
                {/* Filename plate */}
                <g transform="translate(125, 320)" style={{
                  opacity: stage === 'logo' ? 1 : 0,
                  transition: 'opacity 0.4s ease',
                }}>
                  <rect x="0" y="0" width="170" height="26" rx="4" fill="#0e0e16" stroke="#2a2a38" />
                  <text x="85" y="17" fill="#888" fontSize="11" fontFamily="Space Mono, monospace" textAnchor="middle">
                    cafe_logo.png
                  </text>
                </g>
              </g>

              {/* STAGE 2 — Colored mockup with halo (design phase) */}
              <g style={{
                opacity: showDesign ? 1 : 0,
                transition: 'opacity 0.8s ease',
              }}>
                {/* Soft colored fill underneath */}
                <path d={PATHS.cupBody} fill="rgba(255,45,120,0.12)" />
                <path d={PATHS.cupBody} fill="none" stroke="#ff2d78" strokeOpacity={showCraft ? 0 : 0.55} strokeWidth="3" style={{ transition: 'stroke-opacity 0.6s' }} />
                <path d={PATHS.handle}  fill="none" stroke="#ff2d78" strokeOpacity={showCraft ? 0 : 0.55} strokeWidth="14" strokeLinecap="round" style={{ transition: 'stroke-opacity 0.6s' }} />
                <path d={PATHS.steam1}  fill="none" stroke="#00d4ff" strokeOpacity={showCraft ? 0 : 0.45} strokeWidth="6"  strokeLinecap="round" style={{ transition: 'stroke-opacity 0.6s' }} />
                <path d={PATHS.steam2}  fill="none" stroke="#00d4ff" strokeOpacity={showCraft ? 0 : 0.45} strokeWidth="6"  strokeLinecap="round" style={{ transition: 'stroke-opacity 0.6s' }} />
                <path d={PATHS.steam3}  fill="none" stroke="#00d4ff" strokeOpacity={showCraft ? 0 : 0.45} strokeWidth="6"  strokeLinecap="round" style={{ transition: 'stroke-opacity 0.6s' }} />
              </g>

              {/* STAGE 3 — Crafted neon tubes (path-draw animation) */}
              <g style={{
                opacity: showCraft ? 1 : 0,
                transition: 'opacity 0.5s ease',
              }} filter="url(#np-glow)">
                {showCraft && TUBES.map((t, i) => {
                  const isCupOrHandle = t.d === PATHS.cupBody || t.d === PATHS.handle;
                  const draw = `np-draw 1.4s ${t.delay}ms cubic-bezier(0.7,0,0.3,1) forwards`;
                  // pathLength=100 normalises all paths to length 100 so a
                  // single keyframe (offset 100→0) completes the tube without
                  // any trailing uncovered segment.
                  return (
                    <g key={i}>
                      <path d={t.d} pathLength={100} fill="none" stroke={t.color}
                        strokeOpacity="0.25" strokeWidth={isCupOrHandle ? 22 : 14}
                        strokeLinecap="round" strokeLinejoin="round"
                        strokeDasharray="100" strokeDashoffset="100"
                        style={{ animation: draw }} />
                      <path d={t.d} pathLength={100} fill="none" stroke="#ffffff"
                        strokeOpacity="0.95" strokeWidth={isCupOrHandle ? 5 : 3}
                        strokeLinecap="round" strokeLinejoin="round"
                        strokeDasharray="100" strokeDashoffset="100"
                        style={{ animation: draw }} />
                      <path d={t.d} pathLength={100} fill="none" stroke={t.color}
                        strokeOpacity="0.55" strokeWidth={isCupOrHandle ? 14 : 8}
                        strokeLinecap="round" strokeLinejoin="round"
                        strokeDasharray="100" strokeDashoffset="100"
                        style={{ animation: `${draw}, np-flicker ${3 + i * 0.4}s ${1500 + t.delay}ms infinite` }} />
                    </g>
                  );
                })}
              </g>

              {/* Scan line — sweeps across during craft */}
              {stage === 'craft' && (
                <line
                  x1="0" y1="0" x2="0" y2="320"
                  stroke="#00ff9d"
                  strokeOpacity="0.55"
                  strokeWidth="1.5"
                  style={{ animation: 'np-scan 2.4s ease-in-out infinite' }}
                />
              )}

              {/* Measurement callouts (LOC stage only) */}
              {showLoc && (
                <g style={{ animation: 'np-fadein 0.5s ease forwards' }}>
                  {/* Dimension line under cup */}
                  <line x1="105" y1="305" x2="275" y2="305" stroke="#00ff9d" strokeWidth="1" strokeDasharray="3 3" />
                  <line x1="105" y1="298" x2="105" y2="312" stroke="#00ff9d" strokeWidth="1" />
                  <line x1="275" y1="298" x2="275" y2="312" stroke="#00ff9d" strokeWidth="1" />
                  <text x="190" y="325" fill="#00ff9d" fontSize="11" fontFamily="Space Mono, monospace" textAnchor="middle">
                    {counter.toFixed(2)} m · LOC
                  </text>
                </g>
              )}
            </g>

            {/* Right-side readout panel (LOC stage) */}
            {showLoc && (
              <g style={{ animation: 'np-fadein 0.5s 0.2s ease both' }}>
                <rect x="430" y="80" width="150" height="220" rx="6" fill="#0a0a14" stroke="#00ff9d" strokeOpacity="0.4" />
                <text x="445" y="105" fill="#888" fontSize="9" fontFamily="Space Mono, monospace" letterSpacing="2">RESULT</text>
                <line x1="445" y1="113" x2="565" y2="113" stroke="#222" />

                <text x="445" y="138" fill="#666" fontSize="9" fontFamily="Space Mono, monospace">TUBE LENGTH</text>
                <text x="445" y="165" fill="#fff" fontSize="22" fontFamily="Space Mono, monospace" fontWeight="700">
                  {counter.toFixed(2)}<tspan fill="#666" fontSize="12"> m</tspan>
                </text>

                <text x="445" y="195" fill="#666" fontSize="9" fontFamily="Space Mono, monospace">TIER</text>
                <text x="445" y="215" fill="#00ff9d" fontSize="14" fontFamily="Bebas Neue, sans-serif" letterSpacing="1.5">GLASS_CUT</text>

                <text x="445" y="245" fill="#666" fontSize="9" fontFamily="Space Mono, monospace">ESTIMATED PRICE</text>
                <text x="445" y="278" fill="#00ff9d" fontSize="26" fontFamily="Space Mono, monospace" fontWeight="700"
                      style={{ filter: 'drop-shadow(0 0 6px rgba(0,255,157,0.55))' }}>
                  ${TARGET_PRICE}
                </text>
              </g>
            )}
          </svg>
        </div>

        {/* Footer caption */}
        <div style={{
          marginTop: '1.25rem',
          textAlign: 'center',
          fontSize: '0.7rem',
          color: 'var(--text-muted)',
          fontFamily: 'Space Mono, monospace',
          letterSpacing: '0.05em',
        }}>
          ⚡ Auto-loops · representative of the real Studio + Quick Measure pipeline
        </div>
      </div>

      {/* Local keyframes */}
      <style jsx>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50%      { opacity: 0.45; }
        }
        @keyframes np-fadein {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes np-scan {
          0%   { transform: translateX(0px);   opacity: 0; }
          10%  { opacity: 0.6; }
          50%  { transform: translateX(370px); opacity: 0.6; }
          90%  { opacity: 0.6; }
          100% { transform: translateX(370px); opacity: 0; }
        }
        @keyframes np-flicker {
          0%, 100% { opacity: 0.55; }
          47%      { opacity: 0.55; }
          48%      { opacity: 0.30; }
          49%      { opacity: 0.55; }
          70%      { opacity: 0.55; }
          71%      { opacity: 0.40; }
          72%      { opacity: 0.55; }
        }
        @keyframes np-draw {
          to { stroke-dashoffset: 0; }
        }
      `}</style>
    </section>
  );
}
