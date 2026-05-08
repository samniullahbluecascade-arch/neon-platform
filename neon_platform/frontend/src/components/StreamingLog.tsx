'use client';
import { useEffect, useRef, useState } from 'react';

/**
 * Streaming log feed shown while the pipeline runs.
 * Lines are simulated on a schedule (we don't get real-time API events),
 * paced to roughly match the actual pipeline duration. When `done` flips
 * true, a final "Done · ready to cut" line appends.
 *
 * Looks like a build log. Engineer-credible loading state.
 */

const SCHEDULE_FULL: { at: number; line: string }[] = [
  { at: 200,  line: 'Reading sign artwork…' },
  { at: 1100, line: 'Calling render engine · vision-pro' },
  { at: 4200, line: 'Mockup ready · 1024×768' },
  { at: 4500, line: 'Tube extraction · centerline pass' },
  { at: 6300, line: 'Bézier path fit · 14 paths · 22 bends' },
  { at: 6800, line: 'Length · within 5%' },
  { at: 7400, line: 'Pricing · cost × markup + outdoor' },
];

const SCHEDULE_BW: { at: number; line: string }[] = [
  { at: 200,  line: 'Reading colored mockup…' },
  { at: 800,  line: 'Tube extraction · centerline pass' },
  { at: 2400, line: 'Bézier path fit · paths · bends' },
  { at: 2900, line: 'Length · within 5%' },
  { at: 3500, line: 'Pricing · cost × markup + outdoor' },
];

export default function StreamingLog({
  active,
  done,
  mode = 'full',
  error,
}: {
  active: boolean;
  done: boolean;
  mode?: 'full' | 'bw';
  error?: string | null;
}) {
  const [lines, setLines] = useState<string[]>([]);
  const timeouts = useRef<ReturnType<typeof setTimeout>[]>([]);
  const startedAt = useRef<number>(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    timeouts.current.forEach(clearTimeout);
    timeouts.current = [];

    if (!active) return;

    setLines([]);
    startedAt.current = Date.now();

    const schedule = mode === 'bw' ? SCHEDULE_BW : SCHEDULE_FULL;

    schedule.forEach(({ at, line }) => {
      const id = setTimeout(() => {
        setLines(prev => [...prev, line]);
      }, at);
      timeouts.current.push(id);
    });

    return () => timeouts.current.forEach(clearTimeout);
  }, [active, mode]);

  useEffect(() => {
    if (!done) return;
    const elapsed = ((Date.now() - startedAt.current) / 1000).toFixed(1);
    setLines(prev => [...prev, `Done · ${elapsed}s · ready to cut`]);
  }, [done]);

  useEffect(() => {
    if (!error) return;
    setLines(prev => [...prev, `Failed · ${error}`]);
  }, [error]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines]);

  if (!active && lines.length === 0) return null;

  return (
    <div style={{
      background: '#0F1117',
      borderTop: '1px solid var(--border)',
      padding: 14,
      maxHeight: 160,
      overflowY: 'auto',
      fontFamily: 'var(--font-mono)',
      fontSize: '0.72rem',
      lineHeight: 1.7,
      color: 'rgba(255,255,255,0.55)',
      fontVariantNumeric: 'tabular-nums',
    }} ref={scrollRef}>
      {lines.map((l, i) => {
        const isFinal  = l.startsWith('Done');
        const isError  = l.startsWith('Failed');
        const isFresh  = i === lines.length - 1 && !done && !error;

        return (
          <div
            key={i}
            style={{
              display: 'flex',
              gap: 8,
              alignItems: 'baseline',
              color:
                isError ? '#FCA5A5' :
                isFinal ? '#86EFAC' :
                isFresh ? 'rgba(255,255,255,0.92)' :
                'rgba(255,255,255,0.45)',
              animation: isFresh ? 'log-line-in 0.3s ease both' : undefined,
            }}
          >
            <span style={{ color: isError ? '#F87171' : isFinal ? '#4ADE80' : '#E8175D', flexShrink: 0 }}>
              {isError ? '×' : isFinal ? '✓' : '→'}
            </span>
            <span>{l}</span>
          </div>
        );
      })}
      {active && !done && !error && (
        <div style={{
          display: 'flex',
          gap: 8,
          alignItems: 'baseline',
          color: 'rgba(255,255,255,0.35)',
        }}>
          <span style={{ color: '#E8175D' }}>→</span>
          <span style={{ display: 'inline-flex', gap: 3 }}>
            <span style={{ animation: 'log-dot 1.4s 0s ease-in-out infinite' }}>·</span>
            <span style={{ animation: 'log-dot 1.4s 0.2s ease-in-out infinite' }}>·</span>
            <span style={{ animation: 'log-dot 1.4s 0.4s ease-in-out infinite' }}>·</span>
          </span>
        </div>
      )}
      <style jsx>{`
        @keyframes log-line-in {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes log-dot {
          0%, 100% { opacity: 0.2; }
          50%      { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
