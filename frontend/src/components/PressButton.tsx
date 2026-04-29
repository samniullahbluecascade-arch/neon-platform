'use client';
import { useState, ReactNode, useRef } from 'react';

interface PressButtonProps {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
  depth?: number;
}

export default function PressButton({
  children,
  onClick,
  className = '',
  depth = 6,
}: PressButtonProps) {
  const [isPressed, setIsPressed] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);

  return (
    <button
      ref={buttonRef}
      className={`press-btn ${className}`}
      onClick={onClick}
      onMouseDown={() => setIsPressed(true)}
      onMouseUp={() => setIsPressed(false)}
      onMouseLeave={() => setIsPressed(false)}
      style={{
        position: 'relative',
        transform: isPressed
          ? `translateY(${depth}px) translateZ(0)`
          : 'translateY(0) translateZ(0)',
        boxShadow: isPressed
          ? `0 ${depth / 2}px ${depth}px rgba(0, 0, 0, 0.3), inset 0 ${depth / 3}px ${depth / 2}px rgba(0, 0, 0, 0.2)`
          : `0 ${depth}px ${depth * 2}px rgba(0, 0, 0, 0.25), 0 ${depth / 2}px ${depth}px rgba(255, 45, 120, 0.2)`,
        transition: 'transform 0.1s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.1s cubic-bezier(0.4, 0, 0.2, 1)',
        transformStyle: 'preserve-3d',
        cursor: 'pointer',
      }}
    >
      {/* Button face */}
      <span
        style={{
          display: 'block',
          transform: isPressed ? `translateY(${-depth / 2}px)` : 'translateY(0)',
          transition: 'transform 0.1s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        {children}
      </span>
      {/* Bottom edge (3D depth effect) */}
      <span
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: `${depth}px`,
          background: 'linear-gradient(to bottom, rgba(180, 20, 80, 1), rgba(120, 15, 55, 1))',
          borderRadius: 'inherit',
          transform: `translateY(${isPressed ? 0 : depth}px) translateZ(-${depth}px)`,
          transition: 'transform 0.1s cubic-bezier(0.4, 0, 0.2, 1)',
          zIndex: -1,
        }}
      />
    </button>
  );
}