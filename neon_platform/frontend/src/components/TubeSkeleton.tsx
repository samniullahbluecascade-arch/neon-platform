'use client';

/**
 * Animated tube-drawing placeholder shown in the output preview while the API
 * generates a real image. The path strokes in glowing pink, holds, then fades
 * out as the dasharray inverts — looping continuously.
 *
 * `variant`:
 *   - `mockup`  : pink tube draw (matches the rendered neon mockup it replaces)
 *   - `sketch`  : white-on-near-black tube draw (matches the b/w sketch output)
 */

const SHAPES = {
  mockup: 'M 40 60 Q 40 30 70 30 L 200 30 Q 230 30 230 60 L 230 110 Q 230 140 200 140 L 70 140 Q 40 140 40 110 Z',
  sketch: 'M 40 90 L 40 30 L 80 30 L 80 90 L 40 90 M 110 90 L 110 30 L 150 30 L 150 90 M 110 60 L 145 60 M 180 90 L 180 30 L 220 30 L 220 90 M 180 60 L 215 60',
};

export default function TubeSkeleton({
  variant = 'mockup',
  caption,
}: {
  variant?: 'mockup' | 'sketch';
  caption?: string;
}) {
  const isMockup = variant === 'mockup';

  return (
    <div style={{
      width: '100%',
      minHeight: 280,
      background: '#020209',
      backgroundImage:
        'linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),' +
        'linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)',
      backgroundSize: '24px 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
      overflow: 'hidden',
      padding: 16,
    }}>
      {/* Atmospheric radial */}
      <div style={{
        position: 'absolute',
        inset: 0,
        background: isMockup
          ? 'radial-gradient(ellipse at center, rgba(232,23,93,0.12) 0%, transparent 65%)'
          : 'radial-gradient(ellipse at center, rgba(255,255,255,0.04) 0%, transparent 65%)',
        pointerEvents: 'none',
      }} />

      <svg
        viewBox="0 0 270 170"
        style={{
          width: '70%',
          maxWidth: 380,
          position: 'relative',
          zIndex: 1,
        }}
      >
        <path
          d={SHAPES[variant]}
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={5.5}
          style={{
            stroke: isMockup ? '#E8175D' : 'rgba(255,255,255,0.85)',
            filter: isMockup
              ? 'drop-shadow(0 0 6px #E8175D) drop-shadow(0 0 16px rgba(232,23,93,0.55))'
              : 'drop-shadow(0 0 4px rgba(255,255,255,0.5))',
            strokeDasharray: 700,
            animation: 'tube-skeleton-draw 2.6s cubic-bezier(0.45,0,0.55,1) infinite',
          }}
        />
      </svg>

      {/* Caption */}
      {caption && (
        <div style={{
          position: 'absolute',
          bottom: 16,
          left: 0,
          right: 0,
          textAlign: 'center',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.7rem',
          color: 'rgba(255,255,255,0.5)',
          letterSpacing: '0.08em',
        }}>
          {caption}
        </div>
      )}

      <style jsx>{`
        @keyframes tube-skeleton-draw {
          0%   { stroke-dashoffset: 700; opacity: 0.25; }
          35%  { stroke-dashoffset: 0;   opacity: 1;    }
          65%  { stroke-dashoffset: 0;   opacity: 1;    }
          100% { stroke-dashoffset: -700; opacity: 0.25; }
        }
      `}</style>
    </div>
  );
}
