'use client';
import { useEffect, useRef } from 'react';

export default function WaveDistortion() {
  const containerRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let time = 0;

    const animate = () => {
      time += 0.02;
      
      // Create wave distortion using CSS custom properties
      const waveX = Math.sin(time) * 2;
      const waveY = Math.cos(time * 0.8) * 2;
      const waveScale = 1 + Math.sin(time * 0.5) * 0.002;
      
      container.style.setProperty('--wave-x', `${waveX}px`);
      container.style.setProperty('--wave-y', `${waveY}px`);
      container.style.setProperty('--wave-scale', `${waveScale}`);
      
      frameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
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
        zIndex: 1,
        background: `
          radial-gradient(ellipse 100% 50% at 50% 100%, 
            rgba(255, 45, 120, 0.03) 0%, 
            transparent 60%
          )
        `,
        filter: 'url(#wave-distortion)',
      }}
    >
      {/* SVG Filter for wave distortion */}
      <svg style={{ position: 'absolute', width: 0, height: 0 }}>
        <defs>
          <filter id="wave-distortion">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.01"
              numOctaves="3"
              result="noise"
            />
            <feDisplacementMap
              in="SourceGraphic"
              in2="noise"
              scale="3"
              xChannelSelector="R"
              yChannelSelector="G"
            />
          </filter>
        </defs>
      </svg>
      
      {/* Heat haze overlay */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `
            repeating-linear-gradient(
              0deg,
              transparent 0px,
              transparent 2px,
              rgba(255, 45, 120, 0.01) 2px,
              rgba(255, 45, 120, 0.01) 4px
            )
          `,
          animation: 'heat-haze 8s ease-in-out infinite',
        }}
      />
      
      <style>{`
        @keyframes heat-haze {
          0%, 100% { transform: translateY(0) scaleY(1); }
          50% { transform: translateY(-2px) scaleY(1.002); }
        }
      `}</style>
    </div>
  );
}