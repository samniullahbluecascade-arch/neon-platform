'use client';
import { useEffect, useRef, useState } from 'react';

interface GlowPoint {
  id: number;
  x: number;
  y: number;
  life: number;
}

export default function CursorEffects() {
  const cursorRef = useRef<HTMLDivElement>(null);
  const trailRef = useRef<HTMLDivElement>(null);
  const glowPointsRef = useRef<GlowPoint[]>([]);
  const frameRef = useRef<number>(0);
  const [, forceUpdate] = useState({});
  const mouseRef = useRef({ x: -100, y: -100 });
  const lastGlowRef = useRef(0);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
      
      // Update cursor position
      if (cursorRef.current) {
        cursorRef.current.style.left = `${e.clientX}px`;
        cursorRef.current.style.top = `${e.clientY}px`;
      }
      
      // Update trail position with slight delay
      if (trailRef.current) {
        setTimeout(() => {
          if (trailRef.current) {
            trailRef.current.style.left = `${e.clientX}px`;
            trailRef.current.style.top = `${e.clientY}px`;
          }
        }, 50);
      }
      
      // Create glow points periodically
      const now = Date.now();
      if (now - lastGlowRef.current > 100) {
        glowPointsRef.current.push({
          id: now + Math.random(),
          x: e.clientX,
          y: e.clientY,
          life: 0,
        });
        lastGlowRef.current = now;
      }
    };

    const animate = () => {
      // Update glow points
      glowPointsRef.current = glowPointsRef.current.filter(p => {
        p.life++;
        return p.life < 30;
      });
      forceUpdate({});
      frameRef.current = requestAnimationFrame(animate);
    };

    // Hide default cursor
    document.body.style.cursor = 'none';
    
    window.addEventListener('mousemove', handleMouseMove);
    frameRef.current = requestAnimationFrame(animate);

    return () => {
      document.body.style.cursor = 'auto';
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(frameRef.current);
    };
  }, []);

  return (
    <>
      {/* Custom cursor */}
      <div
        ref={cursorRef}
        style={{
          position: 'fixed',
          left: -100,
          top: -100,
          pointerEvents: 'none',
          zIndex: 99999,
          transform: 'translate(-50%, -50%)',
        }}
      >
        {/* Inner dot */}
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: '#ff2d78',
            boxShadow: '0 0 10px #ff2d78, 0 0 20px #ff2d78',
          }}
        />
      </div>
      
      {/* Cursor trail ring */}
      <div
        ref={trailRef}
        style={{
          position: 'fixed',
          left: -100,
          top: -100,
          pointerEvents: 'none',
          zIndex: 99998,
          transform: 'translate(-50%, -50%)',
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            border: '1px solid rgba(255, 45, 120, 0.5)',
            boxShadow: '0 0 10px rgba(255, 45, 120, 0.3)',
            transition: 'all 0.15s ease-out',
          }}
        />
      </div>
      
      {/* Glow marks left behind */}
      {glowPointsRef.current.map(p => (
        <div
          key={p.id}
          style={{
            position: 'fixed',
            left: p.x,
            top: p.y,
            pointerEvents: 'none',
            zIndex: 99997,
            transform: 'translate(-50%, -50%)',
          }}
        >
          <div
            style={{
              width: 20 - p.life * 0.5,
              height: 20 - p.life * 0.5,
              borderRadius: '50%',
              background: `radial-gradient(circle, rgba(255, 45, 120, ${0.3 - p.life * 0.01}) 0%, transparent 70%)`,
              opacity: 1 - p.life / 30,
            }}
          />
        </div>
      ))}
    </>
  );
}