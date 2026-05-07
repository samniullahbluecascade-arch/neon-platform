'use client';
import { useEffect, useRef, useMemo } from 'react';

interface ParticleConfig {
  left:     string;
  size:     number;
  duration: number;
  delay:    number;
  color:    string;
}

const COLORS = ['#ff2d78', '#00d4ff', '#00ff9d'];

function rand(min: number, max: number) { return Math.random() * (max - min) + min; }

export default function HeroVisuals() {
  const heroRef = useRef<HTMLDivElement>(null);

  // Mouse-tracked spotlight
  useEffect(() => {
    const el = heroRef.current;
    if (!el) return;
    const onMove = (e: MouseEvent) => {
      const r = el.getBoundingClientRect();
      el.style.setProperty('--mx', `${e.clientX - r.left}px`);
      el.style.setProperty('--my', `${e.clientY - r.top}px`);
    };
    el.addEventListener('mousemove', onMove);
    return () => el.removeEventListener('mousemove', onMove);
  }, []);

  // Stable particle config (don't regenerate on re-render)
  const particles = useMemo<ParticleConfig[]>(
    () => Array.from({ length: 32 }, () => ({
      left:     `${rand(0, 100)}%`,
      size:     rand(2, 5),
      duration: rand(8, 18),
      delay:    rand(0, 12),
      color:    COLORS[Math.floor(Math.random() * COLORS.length)],
    })),
    []
  );

  return (
    <div ref={heroRef} style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
      {/* Synthwave grid floor */}
      <div className="grid-floor" />

      {/* Mouse spotlight */}
      <div className="mouse-glow" />

      {/* Floating glow orbs */}
      <div
        className="orb"
        style={{
          top: '12%',
          left: '15%',
          width: '320px',
          height: '320px',
          background: 'radial-gradient(circle, #ff2d78 0%, transparent 70%)',
          animationDelay: '0s',
        }}
      />
      <div
        className="orb"
        style={{
          top: '8%',
          right: '8%',
          width: '420px',
          height: '420px',
          background: 'radial-gradient(circle, #00d4ff 0%, transparent 70%)',
          animationDelay: '-8s',
          animationDuration: '28s',
        }}
      />
      <div
        className="orb"
        style={{
          bottom: '5%',
          left: '40%',
          width: '380px',
          height: '380px',
          background: 'radial-gradient(circle, #00ff9d 0%, transparent 70%)',
          animationDelay: '-15s',
          animationDuration: '32s',
        }}
      />

      {/* Spinning wireframe cube — top right */}
      <div
        className="cube-wrap"
        style={{
          position: 'absolute',
          top: '18%',
          right: '12%',
          width: '180px',
          height: '180px',
          opacity: 0.85,
        }}
      >
        <div className="cube-3d" style={{ width: '180px', height: '180px' }}>
          {/* 6 cube faces */}
          <div className="face" style={{ transform: 'translateZ(90px)' }} />
          <div className="face" style={{ transform: 'rotateY(180deg) translateZ(90px)' }} />
          <div className="face" style={{ transform: 'rotateY(-90deg) translateZ(90px)' }} />
          <div className="face" style={{ transform: 'rotateY(90deg) translateZ(90px)' }} />
          <div className="face" style={{ transform: 'rotateX(90deg) translateZ(90px)' }} />
          <div className="face" style={{ transform: 'rotateX(-90deg) translateZ(90px)' }} />
        </div>
      </div>

      {/* Smaller cube — bottom left */}
      <div
        className="cube-wrap"
        style={{
          position: 'absolute',
          bottom: '20%',
          left: '8%',
          width: '110px',
          height: '110px',
          opacity: 0.7,
        }}
      >
        <div
          className="cube-3d"
          style={{
            width: '110px',
            height: '110px',
            animationDirection: 'reverse',
            animationDuration: '18s',
          }}
        >
          <div className="face" style={{ transform: 'translateZ(55px)', borderColor: 'rgba(0,212,255,0.6)', boxShadow: '0 0 24px rgba(0,212,255,0.3), inset 0 0 24px rgba(0,212,255,0.08)' }} />
          <div className="face" style={{ transform: 'rotateY(180deg) translateZ(55px)', borderColor: 'rgba(0,212,255,0.6)', boxShadow: '0 0 24px rgba(0,212,255,0.3), inset 0 0 24px rgba(0,212,255,0.08)' }} />
          <div className="face" style={{ transform: 'rotateY(-90deg) translateZ(55px)', borderColor: 'rgba(0,212,255,0.6)', boxShadow: '0 0 24px rgba(0,212,255,0.3), inset 0 0 24px rgba(0,212,255,0.08)' }} />
          <div className="face" style={{ transform: 'rotateY(90deg) translateZ(55px)', borderColor: 'rgba(0,212,255,0.6)', boxShadow: '0 0 24px rgba(0,212,255,0.3), inset 0 0 24px rgba(0,212,255,0.08)' }} />
          <div className="face" style={{ transform: 'rotateX(90deg) translateZ(55px)', borderColor: 'rgba(0,212,255,0.6)', boxShadow: '0 0 24px rgba(0,212,255,0.3), inset 0 0 24px rgba(0,212,255,0.08)' }} />
          <div className="face" style={{ transform: 'rotateX(-90deg) translateZ(55px)', borderColor: 'rgba(0,212,255,0.6)', boxShadow: '0 0 24px rgba(0,212,255,0.3), inset 0 0 24px rgba(0,212,255,0.08)' }} />
        </div>
      </div>

      {/* Particles drifting up */}
      {particles.map((p, i) => (
        <div
          key={i}
          className="particle"
          style={{
            left: p.left,
            width: `${p.size}px`,
            height: `${p.size}px`,
            background: p.color,
            boxShadow: `0 0 ${p.size * 3}px ${p.color}`,
            animationDuration: `${p.duration}s`,
            animationDelay: `${-p.delay}s`,
          }}
        />
      ))}

      {/* Scanlines overlay */}
      <div className="scanlines" />
    </div>
  );
}
