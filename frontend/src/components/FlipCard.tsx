'use client';
import { useState, ReactNode } from 'react';

interface FlipCardProps {
  front: ReactNode;
  back: ReactNode;
  className?: string;
}

export default function FlipCard({ front, back, className = '' }: FlipCardProps) {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <div
      className={`flip-card ${className}`}
      onClick={() => setIsFlipped(!isFlipped)}
      style={{
        perspective: '1000px',
        width: '100%',
        height: '100%',
        cursor: 'pointer',
      }}
    >
      <div
        className="flip-card-inner"
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          transition: 'transform 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
          transformStyle: 'preserve-3d',
          transform: isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
        }}
      >
        {/* Front */}
        <div
          className="flip-card-front"
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            backfaceVisibility: 'hidden',
            borderRadius: 'inherit',
          }}
        >
          {front}
        </div>
        {/* Back */}
        <div
          className="flip-card-back"
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            backfaceVisibility: 'hidden',
            transform: 'rotateY(180deg)',
            borderRadius: 'inherit',
          }}
        >
          {back}
        </div>
      </div>
    </div>
  );
}