'use client';
import { useEffect, useRef, useState, useCallback } from 'react';

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  color: string;
  life: number;
  maxLife: number;
  vx: number;
  vy: number;
}

const COLORS = ['#ff2d78', '#00d4ff', '#00ff9d', '#ffb300', '#ff3b3b'];

export default function ExplosionParticles() {
  const particlesRef = useRef<Particle[]>([]);
  const frameRef = useRef<number>(0);
  const [, forceUpdate] = useState({});
  const containerRef = useRef<HTMLDivElement>(null);

  const explode = useCallback((x: number, y: number, count: number = 20) => {
    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 * i) / count + Math.random() * 0.5;
      const speed = Math.random() * 8 + 4;
      const particle: Particle = {
        id: Date.now() + Math.random(),
        x,
        y,
        size: Math.random() * 6 + 3,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        life: 0,
        maxLife: Math.random() * 40 + 30,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
      };
      particlesRef.current.push(particle);
    }
    forceUpdate({});
  }, []);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      // Only explode on button clicks
      if (target.closest('button') || target.closest('.btn-neon') || target.closest('.btn-ghost')) {
        explode(e.clientX, e.clientY, 25);
      }
    };

    const animate = () => {
      particlesRef.current = particlesRef.current.filter(p => {
        p.life++;
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.15; // gravity
        p.vx *= 0.98; // friction
        return p.life < p.maxLife;
      });

      forceUpdate({});
      frameRef.current = requestAnimationFrame(animate);
    };

    window.addEventListener('click', handleClick);
    frameRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('click', handleClick);
      cancelAnimationFrame(frameRef.current);
    };
  }, [explode]);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 9998,
      }}
    >
      {particlesRef.current.map(p => (
        <div
          key={p.id}
          style={{
            position: 'absolute',
            left: p.x,
            top: p.y,
            width: p.size,
            height: p.size,
            borderRadius: '50%',
            background: p.color,
            boxShadow: `0 0 ${p.size * 3}px ${p.color}, 0 0 ${p.size * 6}px ${p.color}`,
            opacity: 1 - p.life / p.maxLife,
            transform: `scale(${1 - (p.life / p.maxLife) * 0.8})`,
          }}
        />
      ))}
    </div>
  );
}