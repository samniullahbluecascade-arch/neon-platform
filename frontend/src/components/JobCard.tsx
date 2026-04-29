'use client';
import Link from 'next/link';
import type { Job } from '@/lib/types';
import TierBadge from './TierBadge';

const STATUS_COLOR: Record<string, string> = {
  pending:    '#6b7280',
  processing: '#ff2d78',
  done:       '#00ff9d',
  failed:     '#ff3b3b',
};

export default function JobCard({ job }: { job: Job }) {
  const color = STATUS_COLOR[job.status] ?? 'var(--border)';
  const isProcessing = job.status === 'processing' || job.status === 'pending';

  return (
    <Link href={`/jobs/${job.id}`} style={{ textDecoration: 'none' }}>
      <div
        className="card"
        style={{
          display: 'grid',
          gridTemplateColumns: '3px 1fr auto',
          gap: '1rem',
          padding: '1rem',
          alignItems: 'center',
          cursor: 'pointer',
          borderLeft: `3px solid ${color}`,
          borderLeftColor: color,
          boxShadow: isProcessing ? `inset 3px 0 12px ${color}30` : undefined,
        }}
      >
        {/* Color stripe handled via borderLeft; first column is spacer */}
        <div /> {/* spacer for grid */}

        {/* Main info */}
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.3rem' }}>
            <span style={{
              fontFamily: 'Space Mono, monospace',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              flexShrink: 0,
            }}>
              #{job.id.slice(0, 8)}
            </span>
            <span
              style={{
                color: 'var(--text)',
                fontSize: '0.9rem',
                fontWeight: 500,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {job.filename || 'Unnamed'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span
              className={isProcessing ? 'status-pulse' : ''}
              style={{ fontSize: '0.72rem', color, fontFamily: 'Space Mono, monospace', letterSpacing: '0.06em', textTransform: 'uppercase' }}
            >
              {job.status}
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              {job.width_inches}&quot; wide
            </span>
            {job.input_format && (
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{job.input_format}</span>
            )}
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              {new Date(job.created_at).toLocaleString()}
            </span>
          </div>
        </div>

        {/* Result */}
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          {job.measured_m != null ? (
            <div>
              <div style={{
                fontFamily: 'Space Mono, monospace',
                fontSize: '1.2rem',
                fontWeight: 700,
                color: 'var(--text)',
              }}>
                {job.measured_m.toFixed(2)}
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: '3px' }}>m</span>
              </div>
              {job.tier_result && <TierBadge tier={job.tier_result} />}
            </div>
          ) : (
            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>—</span>
          )}
        </div>
      </div>
    </Link>
  );
}
