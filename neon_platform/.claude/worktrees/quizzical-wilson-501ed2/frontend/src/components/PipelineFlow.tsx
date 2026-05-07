'use client';
import { useEffect, useRef, useState } from 'react';

interface PipelineNode {
  id: string;
  label: string;
  icon?: string;
}

interface PipelineFlowProps {
  nodes: PipelineNode[];
  activeNode?: number;
  onNodeClick?: (index: number) => void;
}

export default function PipelineFlow({
  nodes,
  activeNode = 0,
  onNodeClick,
}: PipelineFlowProps) {
  const [flowOffset, setFlowOffset] = useState(0);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    const animate = () => {
      setFlowOffset(prev => (prev + 1) % 20);
      frameRef.current = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(frameRef.current);
  }, []);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 0,
      flexWrap: 'wrap',
      justifyContent: 'center',
    }}>
      {nodes.map((node, i) => (
        <div key={node.id} style={{ display: 'flex', alignItems: 'center' }}>
          {/* Node */}
          <div
            onClick={() => onNodeClick?.(i)}
            style={{
              position: 'relative',
              width: 80,
              height: 80,
              borderRadius: '50%',
              background: i <= activeNode
                ? `linear-gradient(135deg, var(--pink) 0%, var(--cyan) 100%)`
                : 'var(--bg-2)',
              border: `2px solid ${i <= activeNode ? 'var(--pink)' : 'var(--border-md)'}`,
              boxShadow: i <= activeNode
                ? `0 0 20px rgba(255, 45, 120, 0.4), 0 0 40px rgba(255, 45, 120, 0.2)`
                : 'none',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              transform: i === activeNode ? 'scale(1.1)' : 'scale(1)',
            }}
          >
            {node.icon && (
              <span style={{ fontSize: '1.5rem' }}>{node.icon}</span>
            )}
            <span style={{
              fontSize: '0.6rem',
              fontWeight: 600,
              letterSpacing: '0.05em',
              color: i <= activeNode ? '#fff' : 'var(--text-dim)',
              marginTop: node.icon ? '0.25rem' : 0,
            }}>
              {node.label}
            </span>
            
            {/* Pulse ring for active node */}
            {i === activeNode && (
              <div
                style={{
                  position: 'absolute',
                  inset: -4,
                  borderRadius: '50%',
                  border: '2px solid var(--pink)',
                  animation: 'pulse-ring 1.5s ease-out infinite',
                }}
              />
            )}
          </div>
          
          {/* Connector line */}
          {i < nodes.length - 1 && (
            <div style={{
              position: 'relative',
              width: 60,
              height: 4,
              margin: '0 0.5rem',
            }}>
              {/* Background line */}
              <div style={{
                position: 'absolute',
                inset: 0,
                background: 'var(--border)',
                borderRadius: 2,
              }} />
              
              {/* Active fill */}
              <div style={{
                position: 'absolute',
                left: 0,
                top: 0,
                bottom: 0,
                width: i < activeNode ? '100%' : i === activeNode ? '50%' : '0%',
                background: 'linear-gradient(90deg, var(--pink), var(--cyan))',
                borderRadius: 2,
                boxShadow: '0 0 10px var(--pink)',
                transition: 'width 0.3s ease',
              }} />
              
              {/* Flowing dots */}
              {i < activeNode && (
                <div
                  style={{
                    position: 'absolute',
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: 'var(--cyan)',
                    boxShadow: '0 0 10px var(--cyan)',
                    top: -2,
                    left: `${flowOffset * 3}%`,
                    transition: 'left 0.05s linear',
                  }}
                />
              )}
            </div>
          )}
        </div>
      ))}
      
      <style>{`
        @keyframes pulse-ring {
          0% { transform: scale(1); opacity: 1; }
          100% { transform: scale(1.3); opacity: 0; }
        }
      `}</style>
    </div>
  );
}