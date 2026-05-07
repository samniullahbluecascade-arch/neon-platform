'use client';
import { useEffect, useRef, useState } from 'react';

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

const COLORS = ['#ff2d78', '#00d4ff', '#00ff9d', '#ffb300'];

export default function CursorParticleTrail() {
  const particlesRef = useRef<Particle[]>([]);
  const mouseRef = useRef({ x: 0, y: 0 });
  const lastMouseRef = useRef({ x: 0, y: 0 });
  const frameRef = useRef<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const [, forceUpdate] = useState({});

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const dx = e.clientX - lastMouseRef.current.x;
      const dy = e.clientY - lastMouseRef.current.y;
      const speed = Math.sqrt(dx * dx + dy * dy);

      // Create particles based on mouse speed
      if (speed > 2) {
        const count = Math.min(Math.floor(speed / 3), 3);
        for (let i = 0; i < count; i++) {
          const particle: Particle = {
            id: Date.now() + Math.random(),
            x: e.clientX + (Math.random() - 0.5) * 10,
            y: e.clientY + (Math.random() - 0.5) * 10,
            size: Math.random() * 4 + 2,
            color: COLORS[Math.floor(Math.random() * COLORS.length)],
            life: 0,
            maxLife: Math.random() * 30 + 20,
            vx: (Math.random() - 0.5) * 2,
            vy: (Math.random() - 0.5) * 2 - 1,
          };
          particlesRef.current.push(particle);
        }
      }

      lastMouseRef.current = { x: e.clientX, y: e.clientY };
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };

    const animate = () => {
      particlesRef.current = particlesRef.current.filter(p => {
        p.life++;
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.02; // gravity
        return p.life < p.maxLife;
      });

      forceUpdate({});
      frameRef.current = requestAnimationFrame(animate);
    };

    window.addEventListener('mousemove', handleMouseMove);
    frameRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(frameRef.current);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 9999,
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
            boxShadow: `0 0 ${p.size * 2}px ${p.color}, 0 0 ${p.size * 4}px ${p.color}`,
            opacity: 1 - p.life / p.maxLife,
            transform: `scale(${1 - p.life / p.maxLife * 0.5})`,
            transition: 'opacity 0.1s, transform 0.1s',
          }}
        />
      ))}
    </div>
  );
}