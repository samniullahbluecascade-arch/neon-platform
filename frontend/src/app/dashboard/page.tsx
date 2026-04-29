'use client';
import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { jobs as jobsApi } from '@/lib/api';
import type { Job } from '@/lib/types';
import NavBar from '@/components/NavBar';
import UploadForm from '@/components/UploadForm';
import JobCard from '@/components/JobCard';


export default function DashboardPage() {
  const router        = useRouter();
  const { user, loading } = useAuth();
  const [jobList, setJobList]     = useState<Job[]>([]);
  const [fetching, setFetching]   = useState(true);
  const [statusFilter, setStatus] = useState('');

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

  const limit     = user.tier_limits.jobs_per_month;
  const usedPct   = limit >= 99999 ? 0 : (user.jobs_used_this_month / limit) * 100;
  const remaining = user.jobs_remaining;

  return (
    <div style={{ minHeight: '100vh' }}>
      <NavBar />

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '2rem', marginBottom: '2.5rem', flexWrap: 'wrap' }}>
          <div>
            <h1 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '2.8rem', letterSpacing: '0.05em', lineHeight: 1 }}>
              DASHBOARD
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.4rem' }}>
              {user.email}
            </p>
          </div>

          {/* Usage meter */}
          <div className="card" style={{ padding: '1.25rem 1.5rem', minWidth: '220px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.6rem' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                Monthly Usage
              </span>
              <span style={{ fontFamily: 'Space Mono, monospace', fontSize: '0.82rem', color: 'var(--text)' }}>
                {user.jobs_used_this_month} / {limit >= 99999 ? '∞' : limit}
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
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
              {remaining === 0
                ? <span style={{ color: 'var(--red)' }}>Limit reached — <a href="/pricing" style={{ color: 'var(--pink)' }}>upgrade</a></span>
                : `${remaining} remaining`}
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
            {remaining === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
                <div style={{ color: 'var(--red)', fontFamily: 'Space Mono, monospace', fontSize: '0.8rem', marginBottom: '1rem' }}>
                  Monthly limit reached
                </div>
                <a href="/pricing"><button className="btn-neon" style={{ width: '100%' }}>Upgrade Plan →</button></a>
              </div>
            ) : (
              <UploadForm />
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
                <div style={{ fontSize: '0.85rem' }}>Upload a sign image to get started.</div>
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
