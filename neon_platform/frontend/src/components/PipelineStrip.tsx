'use client';

const IconCheck = ({ size = 11 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12l4 4 10-10" />
  </svg>
);

export type Phase = 'idle' | 'drawing' | 'tracing' | 'pricing' | 'done' | 'error';

const STEPS_FULL: { key: Exclude<Phase, 'idle' | 'done' | 'error'>; label: string }[] = [
  { key: 'drawing', label: 'Step 1 · Neon mockup' },
  { key: 'tracing', label: 'Step 2 · Tube length (LOC)' },
  { key: 'pricing', label: 'Step 3 · Your quote' },
];

const STEPS_BW: { key: Exclude<Phase, 'idle' | 'done' | 'error'>; label: string }[] = [
  { key: 'drawing', label: 'Step 1 · B&W cut sheet' },
  { key: 'tracing', label: 'Step 2 · Tube length (LOC)' },
  { key: 'pricing', label: 'Step 3 · Your quote' },
];

export default function PipelineStrip({
  phase,
  timings,
  pipelineMode = 'full',
}: {
  phase: Phase;
  /** Optional ms timings to display next to completed steps */
  timings?: Partial<Record<Exclude<Phase, 'idle' | 'done' | 'error'>, number>>;
  /** `bw` = mockup-only path (Sketch & quote only) */
  pipelineMode?: 'full' | 'bw';
}) {
  const STEPS = pipelineMode === 'bw' ? STEPS_BW : STEPS_FULL;
  const order = STEPS.map(s => s.key);
  const activeIdx =
    phase === 'idle' ? -1 :
    phase === 'done' ? order.length :
    phase === 'error' ? -1 :
    order.indexOf(phase);

  return (
    <div
      style={{
        display: 'flex',
        gap: 4,
        padding: 8,
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
      }}
    >
      {STEPS.map((step, i) => {
        const state =
          phase === 'error'         ? (i === 0 ? 'error' : 'idle') :
          phase === 'done'          ? 'done' :
          i <  activeIdx            ? 'done' :
          i === activeIdx           ? 'active' :
          'idle';

        const t = timings?.[step.key];

        return (
          <div
            key={step.key}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 12px',
              borderRadius: 6,
              background:
                state === 'active' ? 'var(--pink-dim)' :
                state === 'done'   ? 'rgba(22,163,74,0.06)' :
                state === 'error'  ? 'var(--red-dim)' :
                'var(--bg)',
              border: `1px solid ${
                state === 'active' ? 'rgba(232,23,93,0.3)' :
                state === 'done'   ? 'rgba(22,163,74,0.25)' :
                state === 'error'  ? 'rgba(220,38,38,0.3)' :
                'var(--border)'
              }`,
              transition: 'all 0.35s cubic-bezier(0.16,1,0.3,1)',
            }}
          >
            <Indicator state={state} />
            <div style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              color:
                state === 'active' ? 'var(--pink)' :
                state === 'done'   ? '#15803D' :
                state === 'error'  ? 'var(--red)' :
                'var(--text-3)',
              letterSpacing: '0.01em',
              flex: 1,
              minWidth: 0,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {step.label}
            </div>
            {t != null && state === 'done' && (
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.62rem',
                color: '#15803D',
                fontVariantNumeric: 'tabular-nums',
              }}>
                {(t / 1000).toFixed(1)}s
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function Indicator({ state }: { state: 'idle' | 'active' | 'done' | 'error' }) {
  if (state === 'done') {
    return (
      <div style={{
        width: 16, height: 16, borderRadius: '50%',
        background: '#15803D', color: '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        <IconCheck size={11} />
      </div>
    );
  }
  if (state === 'active') {
    return (
      <div style={{
        width: 10, height: 10, borderRadius: '50%',
        background: 'var(--pink)', flexShrink: 0,
        animation: 'ping-pulse 1.4s ease-in-out infinite',
      }} />
    );
  }
  if (state === 'error') {
    return (
      <div style={{
        width: 10, height: 10, borderRadius: '50%',
        background: 'var(--red)', flexShrink: 0,
      }} />
    );
  }
  return (
    <div style={{
      width: 10, height: 10, borderRadius: '50%',
      background: 'var(--text-3)', opacity: 0.35, flexShrink: 0,
    }} />
  );
}
