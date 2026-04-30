'use client';
import { useState } from 'react';
import Link from 'next/link';
import NavBar from '@/components/NavBar';
import SynthwaveBackground from '@/components/SynthwaveBackground';
import TiltCard from '@/components/TiltCard';
import LetterReveal from '@/components/LetterReveal';
import FlipCard from '@/components/FlipCard';
import HolographicEffect from '@/components/HolographicEffect';
import PressButton from '@/components/PressButton';
import NeonBorder from '@/components/NeonBorder';
import ConstellationParticles from '@/components/ConstellationParticles';
import WaveDistortion from '@/components/WaveDistortion';
import MorphingBlob from '@/components/MorphingBlob';
import PipelineFlow from '@/components/PipelineFlow';
import ScrollReveal from '@/components/ScrollReveal';

const FEATURES = [
  { icon: '◈', label: 'Neon Precision Pipeline', desc: 'Frangi+DoG ridge extraction with Bézier/arc geometry. Physics-validated.' },
  { icon: '◉', label: '±5% Accuracy', desc: 'GLASS_CUT tier achieves glass-ready precision on clean BW files.' },
  { icon: '◇', label: 'Any Format', desc: 'PNG, JPG, SVG, CDR. Handles glow, transparent, BW signs automatically.' },
  { icon: '△', label: 'Instant Quote', desc: 'Upload → measure → LOC range in seconds. No manual tracing.' },
];

const STEPS = [
  { n: '01', title: 'UPLOAD', desc: 'Drop your sign image. We auto-detect the format.' },
  { n: '02', title: 'PROCESS', desc: 'V8 engine extracts ridge paths and measures geometry.' },
  { n: '03', title: 'VALIDATE', desc: 'Physics checks verify tube OD, LOC/inch, resolution.' },
  { n: '04', title: 'QUOTE', desc: 'Get measured_m ± confidence band. Cut or quote.' },
];

const PIPELINE_NODES = [
  { id: 'upload', label: 'Upload', icon: '📤' },
  { id: 'detect', label: 'Detect', icon: '🔍' },
  { id: 'measure', label: 'Measure', icon: '📏' },
  { id: 'validate', label: 'Validate', icon: '✓' },
  { id: 'quote', label: 'Quote', icon: '💰' },
];

export default function LandingPage() {
  const [activePipelineNode, setActivePipelineNode] = useState(2);

  return (
    <div style={{ minHeight: '100vh' }}>
      {/* Global particle effects */}
      <ConstellationParticles />
      <WaveDistortion />
      
      <NavBar />

      {/* Hero */}
      <section style={{
        position: 'relative',
        minHeight: '88vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '6rem 2rem 4rem',
        overflow: 'hidden',
      }}>
        {/* Synthwave 3D Background with parallax */}
        <SynthwaveBackground />
        
        {/* Morphing blobs */}
        <MorphingBlob color="#ff2d78" size={500} position={{ top: '10%', left: '5%' }} opacity={0.1} speed={0.8} />
        <MorphingBlob color="#00d4ff" size={400} position={{ top: '60%', right: '10%' }} opacity={0.08} speed={1.2} />
        <MorphingBlob color="#00ff9d" size={300} position={{ bottom: '20%', left: '20%' }} opacity={0.06} speed={1} />

        <div className="fade-up" style={{ position: 'relative', zIndex: 1 }}>
          <div style={{
            fontFamily: 'Space Mono, monospace',
            fontSize: '0.72rem',
            letterSpacing: '0.2em',
            color: 'var(--pink)',
            textTransform: 'uppercase',
            marginBottom: '1.5rem',
          }}>
            <LetterReveal text="Neon Precision Studio" delay={0.2} stagger={0.03} />
          </div>

          <h1 style={{
            fontFamily: 'Bebas Neue, sans-serif',
            fontSize: 'clamp(5rem, 14vw, 12rem)',
            lineHeight: 0.9,
            letterSpacing: '0.02em',
            color: 'var(--text)',
            marginBottom: '0.2rem',
          }}>
            <LetterReveal text="MEASURE" delay={0.4} stagger={0.04} />
          </h1>
          <h1 style={{
            fontFamily: 'Bebas Neue, sans-serif',
            fontSize: 'clamp(5rem, 14vw, 12rem)',
            lineHeight: 0.9,
            letterSpacing: '0.02em',
            marginBottom: '0.2rem',
          }} className="neon-pink animate-flicker">
            <LetterReveal text="YOUR NEON" delay={0.7} stagger={0.04} letterClassName="neon-pink" />
          </h1>
          <h1 style={{
            fontFamily: 'Bebas Neue, sans-serif',
            fontSize: 'clamp(5rem, 14vw, 12rem)',
            lineHeight: 0.9,
            letterSpacing: '0.02em',
            color: 'var(--text)',
            marginBottom: '2.5rem',
          }}>
            <LetterReveal text="IN SECONDS." delay={1} stagger={0.04} />
          </h1>

          <p style={{
            fontSize: 'clamp(1rem, 2vw, 1.15rem)',
            color: 'var(--text-dim)',
            maxWidth: '520px',
            lineHeight: 1.7,
            marginBottom: '2.5rem',
          }} className="fade-up-1">
            AI-powered tube length measurement for neon sign manufacturers.
            Upload an image, get LOC in meters with cut-ready accuracy.
          </p>

          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }} className="fade-up-2">
            <Link href="/register">
              <PressButton depth={8}>
                <span style={{ padding: '0.9rem 2.2rem', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'linear-gradient(135deg, #ff2d78 0%, #ff6b3d 100%)', borderRadius: '4px', color: '#fff', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                  Start for Free →
                </span>
              </PressButton>
            </Link>
            <Link href="/pricing">
              <NeonBorder color="#00d4ff" speed={2}>
                <button style={{ padding: '0.9rem 2.2rem', fontSize: '0.9rem', background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontWeight: 500, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                  View Plans
                </button>
              </NeonBorder>
            </Link>
          </div>
        </div>
      </section>

      {/* Stat bar */}
      <div className="fade-up-1" style={{
        borderTop: '1px solid var(--border)',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-1)',
        padding: '1.5rem 2rem',
        display: 'flex',
        justifyContent: 'center',
        gap: '4rem',
        flexWrap: 'wrap',
      }}>
        {[
          { val: '≤5%',   label: 'Glass-cut error' },
          { val: 'Data First',  label: 'Architecture' },
          { val: 'Extreme',    label: 'Precisioned Pipeline' },
          { val: '<5s',   label: 'Avg. measure time' },
        ].map(s => (
          <div key={s.label} style={{ textAlign: 'center' }}>
            <div style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '2rem', color: 'var(--pink)', letterSpacing: '0.05em' }}>{s.val}</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Features with 3D Tilt Cards */}
      <section style={{ padding: '6rem 2rem', maxWidth: '1100px', margin: '0 auto' }}>
        <ScrollReveal animation="fade-up">
          <h2 style={{
            fontFamily: 'Bebas Neue, sans-serif',
            fontSize: 'clamp(2.5rem, 5vw, 4rem)',
            letterSpacing: '0.05em',
            marginBottom: '3rem',
          }}>
            BUILT FOR <span className="neon-cyan">GLASS CUTTERS</span>
          </h2>
        </ScrollReveal>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.5rem' }}>
          {FEATURES.map((f, i) => (
            <ScrollReveal key={f.label} animation="fade-up" delay={i * 0.1}>
              <TiltCard
                className="card"
                maxTilt={12}
                scale={1.02}
              >
                <HolographicEffect intensity={0.8}>
                  <div style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <span style={{ fontSize: '1.6rem', color: 'var(--pink)' }}>{f.icon}</span>
                    <div style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.3rem', letterSpacing: '0.06em' }}>{f.label}</div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', lineHeight: 1.6 }}>{f.desc}</div>
                  </div>
                </HolographicEffect>
              </TiltCard>
            </ScrollReveal>
          ))}
        </div>
      </section>

      {/* Flip Cards Demo Section */}
      <section style={{ padding: '4rem 2rem', maxWidth: '1100px', margin: '0 auto' }}>
        <ScrollReveal animation="fade-up">
          <h2 style={{
            fontFamily: 'Bebas Neue, sans-serif',
            fontSize: 'clamp(2rem, 4vw, 3rem)',
            letterSpacing: '0.05em',
            marginBottom: '2rem',
            textAlign: 'center',
          }}>
            <span className="neon-pink">CLICK</span> TO REVEAL
          </h2>
        </ScrollReveal>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
          {[
            { front: '⚡', back: 'Lightning fast processing with GPU acceleration' },
            { front: '🎯', back: 'Pixel-perfect accuracy for glass cutting' },
            { front: '🔒', back: 'Enterprise-grade security & data protection' },
          ].map((card, i) => (
            <ScrollReveal key={i} animation="zoom" delay={i * 0.1}>
              <div style={{ height: '180px' }}>
                <FlipCard
                  front={
                    <div style={{
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'var(--bg-2)',
                      borderRadius: '8px',
                      fontSize: '3rem',
                    }}>
                      {card.front}
                    </div>
                  }
                  back={
                    <div style={{
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'linear-gradient(135deg, var(--bg-2) 0%, rgba(255, 45, 120, 0.1) 100%)',
                      borderRadius: '8px',
                      padding: '1rem',
                      textAlign: 'center',
                      fontSize: '0.9rem',
                      color: 'var(--text-dim)',
                    }}>
                      {card.back}
                    </div>
                  }
                />
              </div>
            </ScrollReveal>
          ))}
        </div>
      </section>

      {/* How it works - Pipeline Steps */}
      <section style={{
        padding: '6rem 2rem',
        background: 'var(--bg-1)',
        borderTop: '1px solid var(--border)',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
          <ScrollReveal animation="fade-up">
            <h2 style={{
              fontFamily: 'Bebas Neue, sans-serif',
              fontSize: 'clamp(2.5rem, 5vw, 4rem)',
              letterSpacing: '0.05em',
              marginBottom: '3rem',
              textAlign: 'center',
            }}>
              HOW IT <span className="neon-pink">WORKS</span>
            </h2>
          </ScrollReveal>
          
          {/* Interactive Pipeline Flow */}
          <ScrollReveal animation="fade-up" delay={0.2}>
            <div style={{ marginBottom: '3rem' }}>
              <PipelineFlow
                nodes={PIPELINE_NODES}
                activeNode={activePipelineNode}
                onNodeClick={setActivePipelineNode}
              />
            </div>
          </ScrollReveal>
          
          {/* Pipeline visualization */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'flex-start', 
            gap: '1rem', 
            flexWrap: 'wrap',
            justifyContent: 'center',
          }}>
            {STEPS.map((s, i) => (
              <ScrollReveal key={s.n} animation="slide-left" delay={i * 0.1}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
                  <TiltCard
                    className="card"
                    maxTilt={8}
                    scale={1.01}
                  >
                    <div style={{ 
                      padding: '1.5rem', 
                      textAlign: 'center',
                      minWidth: '160px',
                    }}>
                      <div style={{
                        fontFamily: 'Space Mono, monospace',
                        fontSize: '0.7rem',
                        color: 'var(--pink)',
                        letterSpacing: '0.15em',
                        marginBottom: '0.6rem',
                      }}>{s.n}</div>
                      <div style={{
                        fontFamily: 'Bebas Neue, sans-serif',
                        fontSize: '1.8rem',
                        letterSpacing: '0.06em',
                        marginBottom: '0.6rem',
                      }}>{s.title}</div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', lineHeight: 1.6 }}>{s.desc}</div>
                    </div>
                  </TiltCard>
                  {i < STEPS.length - 1 && (
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      height: '120px',
                      flexShrink: 0,
                    }}>
                      <div className="flow-line" style={{ width: '40px', flex: 'none' }} />
                    </div>
                  )}
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '8rem 2rem', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
        {/* Background glow */}
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '600px',
          height: '400px',
          background: 'radial-gradient(ellipse at center, rgba(255,45,120,0.15) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />
        
        <MorphingBlob color="#00d4ff" size={300} position={{ top: '20%', right: '15%' }} opacity={0.1} speed={1.5} />
        
        <ScrollReveal animation="fade-up">
          <h2 style={{
            fontFamily: 'Bebas Neue, sans-serif',
            fontSize: 'clamp(3rem, 6vw, 5rem)',
            letterSpacing: '0.04em',
            marginBottom: '1rem',
            position: 'relative',
          }}>
            <LetterReveal text="READY TO " delay={0} stagger={0.03} />
            <span className="neon-pink">
              <LetterReveal text="CUT GLASS" delay={0.3} stagger={0.03} letterClassName="neon-pink" />
            </span>
            <LetterReveal text="?" delay={0.6} stagger={0.03} />
          </h2>
        </ScrollReveal>
        
        <ScrollReveal animation="fade-up" delay={0.2}>
          <p style={{ color: 'var(--text-dim)', marginBottom: '2rem', fontSize: '1rem', position: 'relative' }}>
            Free tier — 20 mockup generations + measurements/month. No card required.
          </p>
        </ScrollReveal>
        
        <ScrollReveal animation="zoom" delay={0.3}>
          <Link href="/register">
            <button className="btn-neon glow-rotate" style={{ padding: '1rem 2.8rem', fontSize: '1rem', position: 'relative' }}>
              Create Free Account →
            </button>
          </Link>
        </ScrollReveal>
      </section>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: '1.5rem 2rem',
        textAlign: 'center',
        color: 'var(--text-muted)',
        fontSize: '0.78rem',
        fontFamily: 'Space Mono, monospace',
      }}>
        <span className="gradient-text">NEON PLATFORM</span> — Neon Preciosion Studio 
      </footer>
    </div>
  );
}