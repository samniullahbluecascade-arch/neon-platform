'use client';
import { useEffect, useRef, useState, ReactNode } from 'react';

interface ScrollRevealProps {
  children: ReactNode;
  className?: string;
  animation?: 'fade-up' | 'fade-in' | 'slide-left' | 'slide-right' | 'zoom' | 'flip';
  delay?: number;
  duration?: number;
  threshold?: number;
}

export default function ScrollReveal({
  children,
  className = '',
  animation = 'fade-up',
  delay = 0,
  duration = 0.6,
  threshold = 0.1,
}: ScrollRevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(element);
        }
      },
      { threshold }
    );

    observer.observe(element);

    return () => observer.disconnect();
  }, [threshold]);

  const getAnimationStyles = (): React.CSSProperties => {
    const base: React.CSSProperties = {
      opacity: isVisible ? 1 : 0,
      transition: `all ${duration}s cubic-bezier(0.4, 0, 0.2, 1) ${delay}s`,
    };

    switch (animation) {
      case 'fade-up':
        return {
          ...base,
          transform: isVisible ? 'translateY(0)' : 'translateY(40px)',
        };
      case 'fade-in':
        return base;
      case 'slide-left':
        return {
          ...base,
          transform: isVisible ? 'translateX(0)' : 'translateX(60px)',
        };
      case 'slide-right':
        return {
          ...base,
          transform: isVisible ? 'translateX(0)' : 'translateX(-60px)',
        };
      case 'zoom':
        return {
          ...base,
          transform: isVisible ? 'scale(1)' : 'scale(0.8)',
        };
      case 'flip':
        return {
          ...base,
          transform: isVisible ? 'rotateX(0)' : 'rotateX(-30deg)',
          transformOrigin: 'bottom',
          perspective: 1000,
        };
      default:
        return base;
    }
  };

  return (
    <div
      ref={ref}
      className={className}
      style={getAnimationStyles()}
    >
      {children}
    </div>
  );
}