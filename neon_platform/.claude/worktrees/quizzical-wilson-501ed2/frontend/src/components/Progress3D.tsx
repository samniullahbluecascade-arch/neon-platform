'use client';
import { useEffect, useRef, useState } from 'react';

interface Progress3DProps {
  value: number;
  max?: number;
  label?: string;
  color?: string;
  height?: number;
  animated?: boolean;
}

export default function Progress3D({
  value,
  max = 100,
  label,
  color = '#ff2d78',
  height = 24,
  animated = true,
}: Progress3DProps) {
  const barRef = useRef<HTMLDivElement>(null);
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    if (animated) {
      const duration = 1000;
      const startTime = Date.now();
      const startValue = displayValue;
      
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        setDisplayValue(startValue + (value - startValue) * eased);
        
        if (progress < 1) {
          requestAnimationFrame(animate);
        }
      };
      
      animate();
    } else {
      setDisplayValue(value);
    }
  }, [value, animated]);

  const percentage = (displayValue / max) * 100;

  return (
    <div style={{ width: '100%' }}>
      {label && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: '0.5rem',
          fontSize: '0.75rem',
          color: 'var(--text-dim)',
        }}>
          <span>{label}</span>
          <span style={{ color, fontFamily: 'Space Mono, monospace' }}>
            {Math.round(displayValue)}%
          </span>
        </div>
      )}
      
      {/* 3D Cylindrical Progress Bar */}
      <div
        ref={barRef}
        style={{
          position: 'relative',
          width: '100%',
          height,
          background: 'var(--bg-0)',
          borderRadius: height / 2,
          overflow: 'hidden',
          boxShadow: `
            inset 0 2px 4px rgba(0, 0, 0, 0.4),
            inset 0 -1px 0 rgba(255, 255, 255, 0.05)
          `,
        }}
      >
        {/* Progress fill */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            height: '100%',
            width: `${percentage}%`,
            background: `linear-gradient(
              180deg,
              ${color}dd 0%,
              ${color} 50%,
              ${color}99 100%
            )`,
            borderRadius: height / 2,
            boxShadow: `
              0 0 10px ${color}80,
              0 0 20px ${color}40,
              inset 0 1px 0 rgba(255, 255, 255, 0.3),
              inset 0 -1px 0 rgba(0, 0, 0, 0.2)
            `,
            transition: 'width 0.1s ease-out',
          }}
        >
          {/* Highlight */}
          <div
            style={{
              position: 'absolute',
              top: 2,
              left: 4,
              right: 4,
              height: '30%',
              background: 'linear-gradient(180deg, rgba(255,255,255,0.3) 0%, transparent 100%)',
              borderRadius: height / 2,
            }}
          />
        </div>
        
        {/* Glass overlay */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(180deg, rgba(255,255,255,0.05) 0%, transparent 50%, rgba(0,0,0,0.1) 100%)',
            borderRadius: height / 2,
            pointerEvents: 'none',
          }}
        />
      </div>
    </div>
  );
}