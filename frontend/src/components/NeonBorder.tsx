'use client';
import { useRef, useState, ReactNode, useEffect } from 'react';

interface NeonBorderProps {
  children: ReactNode;
  className?: string;
  color?: string;
  animated?: boolean;
  speed?: number;
}

export default function NeonBorder({
  children,
  className = '',
  color = '#ff2d78',
  animated = true,
  speed = 3,
}: NeonBorderProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 50, y: 50 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setMousePos({ x, y });
  };

  return (
    <div
      ref={containerRef}
      className={`neon-border ${className}`}
      onMouseMove={handleMouseMove}
      style={{
        position: 'relative',
        padding: '1px',
        borderRadius: 'inherit',
      }}
    >
      {/* Animated border gradient */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: 'inherit',
          padding: '2px',
          background: animated
            ? `conic-gradient(
                from ${speed * 0}deg at ${mousePos.x}% ${mousePos.y}%,
                transparent 0deg,
                ${color} 60deg,
                transparent 120deg,
                ${color} 180deg,
                transparent 240deg,
                ${color} 300deg,
                transparent 360deg
              )`
            : color,
          animation: animated ? `neon-border-spin ${10 / speed}s linear infinite` : 'none',
          WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
          WebkitMaskComposite: 'xor',
          maskComposite: 'exclude',
          filter: `drop-shadow(0 0 4px ${color}) drop-shadow(0 0 8px ${color})`,
        }}
      />
      {/* Glow effect */}
      <div
        style={{
          position: 'absolute',
          inset: -4,
          borderRadius: 'inherit',
          background: `radial-gradient(circle at ${mousePos.x}% ${mousePos.y}%, ${color}40 0%, transparent 50%)`,
          pointerEvents: 'none',
          opacity: 0.6,
        }}
      />
      {/* Content */}
      <div style={{ position: 'relative', zIndex: 1, borderRadius: 'inherit' }}>
        {children}
      </div>
    </div>
  );
}