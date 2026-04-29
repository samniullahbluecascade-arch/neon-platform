'use client';
import { useMemo } from 'react';

interface LetterRevealProps {
  text: string;
  className?: string;
  letterClassName?: string;
  delay?: number;
  stagger?: number;
}

export default function LetterReveal({
  text,
  className = '',
  letterClassName = '',
  delay = 0,
  stagger = 0.05,
}: LetterRevealProps) {
  const letters = useMemo(() => text.split(''), [text]);

  return (
    <span className={className}>
      {letters.map((letter, i) => (
        <span
          key={i}
          className={`letter-3d ${letterClassName}`}
          style={{
            animationDelay: `${delay + i * stagger}s`,
            display: letter === ' ' ? 'inline' : 'inline-block',
            whiteSpace: 'pre',
          }}
        >
          {letter}
        </span>
      ))}
    </span>
  );
}