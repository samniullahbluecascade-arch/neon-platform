'use client';
import { useEffect, useState, useRef, useCallback } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { jobs as jobsApi, mediaUrl } from '@/lib/api';
import type { Job } from '@/lib/types';
import { TIER_CONFIG } from '@/lib/types';
import NavBar from '@/components/NavBar';
import TierBadge from '@/components/TierBadge';

const STATUS_COLOR: Record<string, string> = {
  pending:    '#6b7280',
  processing: '#ff2d78',
  done:       '#00ff9d',
  failed:     '#ff3b3b',
};

const fmt = (v: number | null, decimals = 2, unit = '') =>
  v == null ? '—' : `${v.toFixed(decimals)}${unit ? ' ' + unit : ''}`;

export default function JobDetailPage() {
  const { id }    = useParams<{ id: string }>();
  const router    = useRouter();
  const { user, loading } = useAuth();

  const [job,     setJob]     = useState<Job | null>(null);
  const [error,   setError]   = useState('');
  const [overlay, setOverlay] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const j = await jobsApi.get(id);
      setJob(j);
      if (j.status === 'done' || j.status === 'failed') {
        if (pollRef.current) clearInterval(pollRef.current);
      }
    } catch {
      setError('Job not found');
      if (pollRef.current) clearInterval(pollRef.current);
    }
  }, [id]);

  useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [user, loading, router]);

  useEffect(() => {
    if (!user) return;
    load();
    pollRef.current = setInterval(load, 2500);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [user, load]);

  if (loading || !user) return null;

  if (error) return (
    <div style={{ minHeight: '100vh' }}>
      <NavBar />
      <div style={{ padding: '4rem', textAlign: 'center' }}>
        <div style={{ color: 'var(--red)', fontFamily: 'Space Mono, monospace' }}>{error}</div>
        <Link href="/dashboard"><button className="btn-ghost" style={{ marginTop: '1.5rem' }}>← Dashboard</button></Link>
      </div>
    </div>
  );

  if (!job) return (
    <div style={{ minHeight: '100vh' }}>
      <NavBar />
      <div style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-muted)' }} className="status-pulse">
        Loading job…
      </div>
    </div>
  );

  const statusColor   = STATUS_COLOR[job.status] ?? 'var(--text-muted)';
  const isActive      = job.status === 'pending' || job.status === 'processing';
  const tierCfg       = job.tier_result ? TIER_CONFIG[job.tier_result as keyof typeof TIER_CONFIG] : null;
  const mockupUrl     = mediaUrl(job.mockup_url);
  const bwUrl         = mediaUrl(job.bw_url);
  const overlayUrl    = mediaUrl(job.overlay_url);
  const ridgeUrl      = mediaUrl(job.ridge_url);

  return (
    <div style={{ minHeight: '100vh' }}>
      <NavBar />

      <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '2rem' }}>
        {/* Breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
          <Link href="/dashboard" style={{ color: 'var(--text-muted)', textDecoration: 'none', fontSize: '0.82rem' }}>Dashboard</Link>
          <span style={{ color: 'var(--text-muted)' }}>/</span>
          <span style={{ color: 'var(--text-dim)', fontSize: '0.82rem', fontFamily: 'Space Mono, monospace' }}>
            {job.id.slice(0, 8)}…
          </span>
        </div>

        {/* Job header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1.5rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
              <h1 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '2rem', letterSpacing: '0.05em' }}>
                {job.filename || 'Measurement'}
              </h1>
              <span
                className={isActive ? 'status-pulse' : ''}
                style={{ fontFamily: 'Space Mono, monospace', fontSize: '0.72rem', color: statusColor, letterSpacing: '0.1em', textTransform: 'uppercase', border: `1px solid ${statusColor}`, padding: '2px 8px', borderRadius: '100px' }}
              >
                {job.status}
              </span>
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontFamily: 'Space Mono, monospace' }}>
              {job.id} · {new Date(job.created_at).toLocaleString()}
            </div>
          </div>

          {job.tier_result && <TierBadge tier={job.tier_result} size="lg" />}
        </div>

        {/* Processing state */}
        {isActive && (
          <div className="card" style={{ padding: '3rem', textAlign: 'center', marginBottom: '2rem', borderColor: 'rgba(255,45,120,0.25)' }}>
            <div style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '2rem', letterSpacing: '0.08em', marginBottom: '0.5rem' }} className="status-pulse neon-pink">
              MEASURING…
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              V8 pipeline running. Page polls every 2.5s.
            </div>
          </div>
        )}

        {/* Failed state */}
        {job.status === 'failed' && (
          <div className="card" style={{ padding: '1.5rem', marginBottom: '2rem', borderColor: 'var(--red)' }}>
            <div style={{ color: 'var(--red)', fontFamily: 'Space Mono, monospace', fontSize: '0.82rem', marginBottom: '0.5rem' }}>PIPELINE FAILED</div>
            <div style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>{job.error_message || 'Unknown error'}</div>
          </div>
        )}

        {/* Main result */}
        {job.status === 'done' && job.measured_m != null && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>

            {/* LOC result card */}
            <div className="card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                Tube Length (LOC)
              </div>
              <div style={{
                fontFamily: 'Space Mono, monospace',
                fontSize: 'clamp(3rem, 6vw, 5rem)',
                fontWeight: 700,
                lineHeight: 1,
                color: tierCfg?.color ?? 'var(--text)',
                textShadow: tierCfg ? `0 0 20px ${tierCfg.color}60` : undefined,
                marginBottom: '0.5rem',
              }}>
                {job.measured_m.toFixed(2)}
                <span style={{ fontSize: '1.5rem', color: 'var(--text-muted)', marginLeft: '0.3rem' }}>m</span>
              </div>

              {(job.loc_low_m != null && job.loc_high_m != null) && (
                <div style={{ fontFamily: 'Space Mono, monospace', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                  {job.loc_low_m.toFixed(2)} – {job.loc_high_m.toFixed(2)} m range
                </div>
              )}

              {job.confidence != null && (
                <div style={{ marginTop: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Confidence</span>
                    <span style={{ fontFamily: 'Space Mono, monospace', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      {(job.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div style={{ height: '4px', background: 'var(--bg-2)', borderRadius: '2px' }}>
                    <div style={{
                      height: '100%',
                      width: `${job.confidence * 100}%`,
                      background: tierCfg?.color ?? 'var(--pink)',
                      borderRadius: '2px',
                      boxShadow: `0 0 8px ${tierCfg?.color ?? 'var(--pink)'}`,
                    }} />
                  </div>
                </div>
              )}

              {job.error_pct != null && (
                <div style={{ marginTop: '0.75rem', fontFamily: 'Space Mono, monospace', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Δ {job.error_pct.toFixed(1)}% vs ground truth
                </div>
              )}

              {job.estimated_price != null && (
                <div style={{
                  marginTop: '1.25rem',
                  padding: '0.75rem 1rem',
                  background: 'rgba(0,255,157,0.06)',
                  border: '1px solid rgba(0,255,157,0.2)',
                  borderRadius: '6px',
                }}>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.3rem' }}>
                    Estimated Sign Price
                  </div>
                  <div style={{
                    fontFamily: 'Space Mono, monospace',
                    fontSize: '1.8rem',
                    fontWeight: 700,
                    color: '#00ff9d',
                    textShadow: '0 0 16px rgba(0,255,157,0.4)',
                  }}>
                    ${job.estimated_price.toFixed(0)}
                  </div>
                </div>
              )}
            </div>

            {/* Stats grid */}
            <div className="card" style={{ padding: '1.5rem' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '1rem' }}>
                Measurement Details
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                {[
                  { label: 'Tube OD',   val: fmt(job.tube_width_mm, 1, 'mm') },
                  { label: 'PPI',       val: fmt(job.px_per_inch, 1) },
                  { label: 'Area est.', val: fmt(job.area_m, 2, 'm') },
                  { label: 'Overcount', val: fmt(job.overcount_ratio, 2) },
                  { label: 'Paths',     val: job.n_paths ?? '—' },
                  { label: 'Elapsed',   val: fmt(job.elapsed_s, 1, 's') },
                  { label: 'Straight',  val: job.n_straight_segs ?? '—' },
                  { label: 'Arc',       val: job.n_arc_segs ?? '—' },
                  { label: 'Freeform',  val: job.n_freeform_segs ?? '—' },
                  { label: 'Physics',   val: job.physics_ok == null ? '—' : job.physics_ok ? '✓ OK' : '✗ Warn' },
                  { label: 'Format',    val: job.input_format || '—' },
                  { label: 'Width',     val: `${job.width_inches}"` },
                ].map(s => (
                  <div key={s.label}>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{s.label}</div>
                    <div style={{ fontFamily: 'Space Mono, monospace', fontSize: '0.82rem', color: 'var(--text)', marginTop: '2px' }}>{String(s.val)}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Generated images (mockup + B&W) */}
        {(mockupUrl || bwUrl) && (
          <div style={{ display: 'grid', gridTemplateColumns: mockupUrl && bwUrl ? '1fr 1fr' : '1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
            {mockupUrl && (
              <div className="card" style={{ padding: '1rem', overflow: 'hidden' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
                  Neon Mockup
                </div>
                <div style={{ position: 'relative', borderRadius: '4px', overflow: 'hidden', background: 'var(--bg-0)', height: '320px' }}>
                  <Image src={mockupUrl} alt="Neon mockup" fill style={{ objectFit: 'contain' }} unoptimized />
                </div>
              </div>
            )}
            {bwUrl && (
              <div className="card" style={{ padding: '1rem', overflow: 'hidden' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
                  B&W Tube Sketch
                </div>
                <div style={{ position: 'relative', borderRadius: '4px', overflow: 'hidden', background: 'var(--bg-0)', height: '320px' }}>
                  <Image src={bwUrl} alt="B&W tube sketch" fill style={{ objectFit: 'contain' }} unoptimized />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Overlay images */}
        {(overlayUrl || ridgeUrl) && (
          <div style={{ display: 'grid', gridTemplateColumns: ridgeUrl ? '2fr 1fr' : '1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
            {overlayUrl && (
              <div className="card" style={{ padding: '1rem', overflow: 'hidden' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
                  Ridge Overlay
                  <button
                    onClick={() => setOverlay(!overlay)}
                    style={{ float: 'right', background: 'none', border: 'none', color: 'var(--pink)', cursor: 'pointer', fontSize: '0.72rem' }}
                  >
                    {overlay ? 'collapse' : 'fullscreen'}
                  </button>
                </div>
                <div style={{
                  position: 'relative',
                  borderRadius: '4px',
                  overflow: 'hidden',
                  background: 'var(--bg-0)',
                  height: overlay ? '80vh' : '320px',
                  transition: 'height 0.3s ease',
                }}>
                  <Image
                    src={overlayUrl}
                    alt="Ridge overlay"
                    fill
                    style={{ objectFit: 'contain' }}
                    unoptimized
                  />
                </div>
              </div>
            )}
            {ridgeUrl && (
              <div className="card" style={{ padding: '1rem', overflow: 'hidden' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Ridge Map</div>
                <div style={{ position: 'relative', borderRadius: '4px', overflow: 'hidden', background: 'var(--bg-0)', height: '320px' }}>
                  <Image src={ridgeUrl} alt="Ridge map" fill style={{ objectFit: 'contain' }} unoptimized />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Reasoning */}
        {job.reasoning?.length > 0 && (
          <div className="card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '1rem' }}>
              Pipeline Reasoning
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {job.reasoning.map((r, i) => (
                <div key={i} style={{
                  fontFamily: 'Space Mono, monospace',
                  fontSize: '0.75rem',
                  color: 'var(--text-dim)',
                  padding: '0.3rem 0',
                  borderBottom: i < job.reasoning.length - 1 ? '1px solid var(--border)' : 'none',
                }}>
                  <span style={{ color: 'var(--pink)', marginRight: '0.6rem' }}>{String(i + 1).padStart(2, '0')}</span>
                  {r}
                </div>
              ))}
            </div>
          </div>
        )}

        <Link href="/dashboard"><button className="btn-ghost">← Back to Dashboard</button></Link>
      </div>
    </div>
  );
}
