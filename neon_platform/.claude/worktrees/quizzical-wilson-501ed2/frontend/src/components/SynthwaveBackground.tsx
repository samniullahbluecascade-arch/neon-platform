'use client';
import { useEffect, useRef, useMemo, useState } from 'react';

interface ParticleConfig {
  left: string;
  size: number;
  duration: number;
  delay: number;
  color: string;
}

const COLORS = ['#ff2d78', '#00d4ff', '#00ff9d', '#ffb300'];

function rand(min: number, max: number) { return Math.random() * (max - min) + min; }

export default function SynthwaveBackground() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mousePosition, setMousePosition] = useState({ x: 0.5, y: 0.5 });
  const [scrollY, setScrollY] = useState(0);

  // Mouse parallax tracking
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({
        x: e.clientX / window.innerWidth,
        y: e.clientY / window.innerHeight,
      });
    };

    const handleScroll = () => {
      setScrollY(window.scrollY);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('scroll', handleScroll, { passive: true });
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  // Stable particle config
  const particles = useMemo<ParticleConfig[]>(
    () => Array.from({ length: 48 }, () => ({
      left: `${rand(0, 100)}%`,
      size: rand(2, 6),
      duration: rand(10, 25),
      delay: rand(0, 15),
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
    })),
    []
  );

  // Parallax offsets for different layers
  const cube1Parallax = {
    x: (mousePosition.x - 0.5) * 40,
    y: (mousePosition.y - 0.5) * 30 - scrollY * 0.1,
  };

  const cube2Parallax = {
    x: (mousePosition.x - 0.5) * -25,
    y: (mousePosition.y - 0.5) * -20 - scrollY * 0.15,
  };

  const orb1Parallax = {
    x: (mousePosition.x - 0.5) * 60,
    y: (mousePosition.y - 0.5) * 40,
  };

  const orb2Parallax = {
    x: (mousePosition.x - 0.5) * -45,
    y: (mousePosition.y - 0.5) * -35,
  };

  const orb3Parallax = {
    x: (mousePosition.x - 0.5) * 30,
    y: (mousePosition.y - 0.5) * 25,
  };

  return (
    <div ref={containerRef} style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
      {/* Synthwave grid floor */}
      <div className="grid-floor" />

      {/* Mouse spotlight */}
      <div 
        className="mouse-glow" 
        style={{
          '--mx': `${mousePosition.x * 100}%`,
          '--my': `${mousePosition.y * 100}%`,
        } as React.CSSProperties}
      />

      {/* Floating glow orbs with parallax */}
      <div
        className="orb"
        style={{
          top: '12%',
          left: '15%',
          width: '320px',
          height: '320px',
          background: 'radial-gradient(circle, #ff2d78 0%, transparent 70%)',
          animationDelay: '0s',
          transform: `translate(${orb1Parallax.x}px, ${orb1Parallax.y}px)`,
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
          transform: `translate(${orb2Parallax.x}px, ${orb2Parallax.y}px)`,
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
          transform: `translate(${orb3Parallax.x}px, ${orb3Parallax.y}px)`,
        }}
      />

      {/* Spinning wireframe cube — top right with parallax */}
      <div
        className="cube-wrap"
        style={{
          position: 'absolute',
          top: '18%',
          right: '12%',
          width: '180px',
          height: '180px',
          opacity: 0.85,
          transform: `translate(${cube1Parallax.x}px, ${cube1Parallax.y}px)`,
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

      {/* Smaller cube — bottom left with parallax */}
      <div
        className="cube-wrap"
        style={{
          position: 'absolute',
          bottom: '20%',
          left: '8%',
          width: '110px',
          height: '110px',
          opacity: 0.7,
          transform: `translate(${cube2Parallax.x}px, ${cube2Parallax.y}px)`,
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

      {/* Third cube — center-left */}
      <div
        className="cube-wrap"
        style={{
          position: 'absolute',
          top: '45%',
          left: '5%',
          width: '80px',
          height: '80px',
          opacity: 0.5,
          transform: `translate(${(mousePosition.x - 0.5) * 50}px, ${(mousePosition.y - 0.5) * 40}px)`,
        }}
      >
        <div
          className="cube-3d"
          style={{
            width: '80px',
            height: '80px',
            animationDuration: '30s',
          }}
        >
          <div className="face" style={{ transform: 'translateZ(40px)', borderColor: 'rgba(0,255,157,0.5)', boxShadow: '0 0 20px rgba(0,255,157,0.25), inset 0 0 20px rgba(0,255,157,0.06)' }} />
          <div className="face" style={{ transform: 'rotateY(180deg) translateZ(40px)', borderColor: 'rgba(0,255,157,0.5)', boxShadow: '0 0 20px rgba(0,255,157,0.25), inset 0 0 20px rgba(0,255,157,0.06)' }} />
          <div className="face" style={{ transform: 'rotateY(-90deg) translateZ(40px)', borderColor: 'rgba(0,255,157,0.5)', boxShadow: '0 0 20px rgba(0,255,157,0.25), inset 0 0 20px rgba(0,255,157,0.06)' }} />
          <div className="face" style={{ transform: 'rotateY(90deg) translateZ(40px)', borderColor: 'rgba(0,255,157,0.5)', boxShadow: '0 0 20px rgba(0,255,157,0.25), inset 0 0 20px rgba(0,255,157,0.06)' }} />
          <div className="face" style={{ transform: 'rotateX(90deg) translateZ(40px)', borderColor: 'rgba(0,255,157,0.5)', boxShadow: '0 0 20px rgba(0,255,157,0.25), inset 0 0 20px rgba(0,255,157,0.06)' }} />
          <div className="face" style={{ transform: 'rotateX(-90deg) translateZ(40px)', borderColor: 'rgba(0,255,157,0.5)', boxShadow: '0 0 20px rgba(0,255,157,0.25), inset 0 0 20px rgba(0,255,157,0.06)' }} />
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

      {/* Vignette overlay */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse at center, transparent 40%, rgba(7,7,14,0.8) 100%)',
          pointerEvents: 'none',
        }}
      />
    </div>
  );
}