'use client';
import { useEffect, useRef } from 'react';

interface MorphingBlobProps {
  color?: string;
  size?: number;
  position?: { top?: string; left?: string; right?: string; bottom?: string };
  opacity?: number;
  speed?: number;
}

export default function MorphingBlob({
  color = '#ff2d78',
  size = 400,
  position = { top: '20%', left: '10%' },
  opacity = 0.15,
  speed = 1,
}: MorphingBlobProps) {
  const blobRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    const blob = blobRef.current;
    if (!blob) return;

    let time = 0;

    const animate = () => {
      time += 0.01 * speed;
      
      // Generate organic blob shape using border-radius
      const r1 = 30 + Math.sin(time) * 10;
      const r2 = 70 + Math.cos(time * 0.8) * 10;
      const r3 = 30 + Math.sin(time * 1.2) * 15;
      const r4 = 70 + Math.cos(time * 0.6) * 15;
      
      const r5 = 60 + Math.cos(time * 0.9) * 10;
      const r6 = 40 + Math.sin(time * 1.1) * 10;
      const r7 = 60 + Math.cos(time * 0.7) * 15;
      const r8 = 40 + Math.sin(time * 0.5) * 15;
      
      blob.style.borderRadius = `${r1}% ${r2}% ${r3}% ${r4}% / ${r5}% ${r6}% ${r7}% ${r8}%`;
      blob.style.transform = `
        translate(
          ${Math.sin(time * 0.5) * 20}px,
          ${Math.cos(time * 0.3) * 20}px
        )
        rotate(${Math.sin(time * 0.2) * 5}deg)
        scale(${1 + Math.sin(time * 0.4) * 0.1})
      `;
      
      frameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(frameRef.current);
    };
  }, [speed]);

  return (
    <div
      ref={blobRef}
      style={{
        position: 'absolute',
        width: size,
        height: size,
        background: `radial-gradient(circle at 30% 30%, ${color} 0%, transparent 70%)`,
        filter: `blur(60px)`,
        opacity,
        pointerEvents: 'none',
        transition: 'border-radius 0.5s ease',
        ...position,
      }}
    />
  );
}