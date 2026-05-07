'use client';
import { useRef, useState, ReactNode, useCallback } from 'react';

interface Draggable3DProps {
  children: ReactNode;
  className?: string;
  rotationSensitivity?: number;
}

export default function Draggable3D({
  children,
  className = '',
  rotationSensitivity = 1,
}: Draggable3DProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [rotation, setRotation] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const lastMouseRef = useRef({ x: 0, y: 0 });

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    lastMouseRef.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging) return;

    const deltaX = e.clientX - lastMouseRef.current.x;
    const deltaY = e.clientY - lastMouseRef.current.y;

    setRotation(prev => ({
      x: prev.x + deltaY * rotationSensitivity * 0.5,
      y: prev.y + deltaX * rotationSensitivity * 0.5,
    }));

    lastMouseRef.current = { x: e.clientX, y: e.clientY };
  }, [isDragging, rotationSensitivity]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Touch support
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    setIsDragging(true);
    lastMouseRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!isDragging) return;

    const deltaX = e.touches[0].clientX - lastMouseRef.current.x;
    const deltaY = e.touches[0].clientY - lastMouseRef.current.y;

    setRotation(prev => ({
      x: prev.x + deltaY * rotationSensitivity * 0.5,
      y: prev.y + deltaX * rotationSensitivity * 0.5,
    }));

    lastMouseRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  }, [isDragging, rotationSensitivity]);

  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  return (
    <div
      ref={containerRef}
      className={`draggable-3d ${className}`}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      style={{
        cursor: isDragging ? 'grabbing' : 'grab',
        transformStyle: 'preserve-3d',
        perspective: 1000,
        userSelect: 'none',
      }}
    >
      <div
        style={{
          transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`,
          transformStyle: 'preserve-3d',
          transition: isDragging ? 'none' : 'transform 0.3s ease-out',
        }}
      >
        {children}
      </div>
    </div>
  );
}