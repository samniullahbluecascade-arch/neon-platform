'use client';
import { useRef, useState, ReactNode } from 'react';

interface HolographicEffectProps {
  children: ReactNode;
  className?: string;
  intensity?: number;
}

export default function HolographicEffect({
  children,
  className = '',
  intensity = 1,
}: HolographicEffectProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [angle, setAngle] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setAngle({ x, y });
  };

  return (
    <div
      ref={containerRef}
      className={`holographic ${className}`}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {children}
      {/* Holographic overlay */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: isHovered
            ? `linear-gradient(
                ${angle.x * 3.6}deg,
                transparent 0%,
                rgba(255, 0, 128, ${0.15 * intensity}) 10%,
                rgba(255, 128, 0, ${0.12 * intensity}) 20%,
                rgba(255, 255, 0, ${0.1 * intensity}) 30%,
                rgba(0, 255, 128, ${0.12 * intensity}) 40%,
                rgba(0, 128, 255, ${0.15 * intensity}) 50%,
                rgba(128, 0, 255, ${0.12 * intensity}) 60%,
                rgba(255, 0, 128, ${0.1 * intensity}) 70%,
                transparent 100%
              )`
            : 'transparent',
          mixBlendMode: 'overlay',
          pointerEvents: 'none',
          transition: 'background 0.1s ease',
          borderRadius: 'inherit',
        }}
      />
      {/* Shimmer streak */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `linear-gradient(
            105deg,
            transparent 40%,
            rgba(255, 255, 255, ${isHovered ? 0.15 : 0}) 45%,
            rgba(255, 255, 255, ${isHovered ? 0.25 : 0}) 50%,
            rgba(255, 255, 255, ${isHovered ? 0.15 : 0}) 55%,
            transparent 60%
          )`,
          transform: `translateX(${isHovered ? (angle.x - 50) * 2 : -100}%)`,
          pointerEvents: 'none',
          transition: 'transform 0.05s ease',
          borderRadius: 'inherit',
        }}
      />
    </div>
  );
}