'use client';
import { useEffect, useState, useCallback, useRef, DragEvent, ChangeEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { jobs as jobsApi } from '@/lib/api';
import type { Job } from '@/lib/types';
import NavBar from '@/components/NavBar';
import JobCard from '@/components/JobCard';

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [jobList, setJobList] = useState<Job[]>([]);
  const [fetching, setFetching] = useState(true);
  const [statusFilter, setStatus] = useState('');

  // Upload state
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [width, setWidth] = useState('');
  const [height, setHeight] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const fetchJobs = useCallback(async () => {
    try {
      setJobList(await jobsApi.list(statusFilter || undefined));
    } catch {}
    setFetching(false);
  }, [statusFilter]);

  useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [user, loading, router]);

  useEffect(() => {
    if (user) { setFetching(true); fetchJobs(); }
  }, [user, fetchJobs]);

  if (loading || !user) return null;

  const limit = user.tier_limits.jobs_per_month;
  const usedPct = (user.jobs_used_this_month / limit) * 100;

  const accept = (f: File) => {
    if (!f.type.match(/image\//)) {
      setError('Supported: PNG, JPG images');
      return;
    }
    setFile(f);
    setError('');
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) accept(f);
  };

  const onFile = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) accept(f);
  };

  const submit = async () => {
    if (!file) { setError('Select an image first'); return; }
    const w = parseFloat(width);
    if (!w || w <= 0) { setError('Enter sign width in inches'); return; }

    setSubmitting(true);
    setError('');
    try {
      const form = new FormData();
      form.append('image', file);
      form.append('width_inches', String(w));
      if (height) form.append('height_inches', height);
      form.append('force_format', 'bw');

      const res = await jobsApi.create(form);
      router.push(`/jobs/${res.job_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed');
      setSubmitting(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh' }}>
      <NavBar />

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '2rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          <div>
            <h1 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '2.8rem', letterSpacing: '0.05em', lineHeight: 1 }}>
              QUICK MEASURE
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.4rem' }}>
              B&W Sketch → LOC Measurement → Price
            </p>
          </div>

          {/* Usage meter */}
          <div className="card" style={{ padding: '1.25rem 1.5rem', minWidth: '220px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.6rem' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                Monthly Usage
              </span>
              <span style={{ fontFamily: 'Space Mono, monospace', fontSize: '0.82rem', color: 'var(--text)' }}>
                {user.jobs_used_this_month} / {limit}
              </span>
            </div>
            <div style={{ height: '4px', background: 'var(--bg-2)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${Math.min(usedPct, 100)}%`,
                background: usedPct > 80 ? 'var(--red)' : 'var(--pink)',
                borderRadius: '2px',
                boxShadow: `0 0 8px ${usedPct > 80 ? 'var(--red)' : 'var(--pink)'}`,
                transition: 'width 0.4s',
              }} />
            </div>
          </div>
        </div>

        {/* Upload + Jobs layout */}
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 400px) 1fr', gap: '2rem', alignItems: 'start' }}>

          {/* Upload panel */}
          <div className="card" style={{ padding: '1.5rem', position: 'sticky', top: '72px' }}>
            <h2 style={{
              fontFamily: 'Bebas Neue, sans-serif',
              fontSize: '1.4rem',
              letterSpacing: '0.06em',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}>
              <span className="neon-pink">⬆</span> NEW MEASUREMENT
            </h2>

            {user.jobs_remaining === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
                <div style={{ color: 'var(--red)', fontFamily: 'Space Mono, monospace', fontSize: '0.8rem', marginBottom: '1rem' }}>
                  Monthly limit reached
                </div>
                <a href="/pricing"><button className="btn-neon" style={{ width: '100%' }}>Upgrade Plan →</button></a>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {/* Drop zone */}
                <div
                  className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
                  style={{ padding: '3rem 2rem', textAlign: 'center' }}
                  onClick={() => fileRef.current?.click()}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={onDrop}
                >
                  <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={onFile} />

                  {file ? (
                    <div>
                      <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🖼</div>
                      <div style={{ color: 'var(--text)', fontWeight: 600, marginBottom: '0.25rem' }}>{file.name}</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        {(file.size / 1024).toFixed(0)} KB — click to change
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div style={{
                        fontFamily: 'Bebas Neue, sans-serif',
                        fontSize: '1.6rem',
                        letterSpacing: '0.1em',
                        color: 'var(--text-dim)',
                        marginBottom: '0.5rem',
                      }}>
                        DROP YOUR NEON SIGN SKETCH HERE
                      </div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                        PNG · JPG — Black &amp; White tube sketch — or click to browse
                      </div>
                    </div>
                  )}
                </div>

                {/* Measurement inputs */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.4rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                      Width (inches) *
                    </label>
                    <input
                      className="input-neon"
                      type="number"
                      min="0"
                      step="0.5"
                      placeholder="e.g. 24"
                      value={width}
                      onChange={e => setWidth(e.target.value)}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.4rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                      Height (inches)
                    </label>
                    <input
                      className="input-neon"
                      type="number"
                      min="0"
                      step="0.5"
                      placeholder="optional"
                      value={height}
                      onChange={e => setHeight(e.target.value)}
                    />
                  </div>
                </div>

                {error && (
                  <div style={{ color: 'var(--red)', fontSize: '0.82rem', fontFamily: 'Space Mono, monospace' }}>
                    ⚠ {error}
                  </div>
                )}

                <button className="btn-neon" onClick={submit} disabled={submitting} style={{ width: '100%', padding: '0.85rem' }}>
                  {submitting ? (
                    <span className="status-pulse">MEASURING…</span>
                  ) : (
                    'MEASURE SIGN →'
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Job list */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', gap: '1rem' }}>
              <h2 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.4rem', letterSpacing: '0.06em' }}>
                JOB HISTORY
              </h2>
              <select
                className="input-neon"
                style={{ width: 'auto', padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                value={statusFilter}
                onChange={e => { setStatus(e.target.value); }}
              >
                <option value="">All</option>
                <option value="done">Done</option>
                <option value="processing">Processing</option>
                <option value="pending">Pending</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            {fetching ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '2rem 0' }} className="status-pulse">
                Loading jobs…
              </div>
            ) : jobList.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '4rem 2rem',
                color: 'var(--text-muted)',
                border: '1px dashed var(--border)',
                borderRadius: '6px',
              }}>
                <div style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.4rem', marginBottom: '0.5rem', letterSpacing: '0.06em' }}>
                  NO JOBS YET
                </div>
                <div style={{ fontSize: '0.85rem' }}>Upload a B&W sign sketch to get started.</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {jobList.map(j => <JobCard key={j.id} job={j} />)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
