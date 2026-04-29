'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { auth as authApi, billing } from '@/lib/api';
import NavBar from '@/components/NavBar';

const TIER_COLOR: Record<string, string> = { free: '#6b7280', pro: '#00d4ff', enterprise: '#ffb300' };

export default function ProfilePage() {
  const router = useRouter();
  const { user, loading, refresh } = useAuth();

  const [fullName, setFullName] = useState('');
  const [company,  setCompany]  = useState('');
  const [saving,   setSaving]   = useState(false);
  const [saveMsg,  setSaveMsg]  = useState('');
  const [apiKey,   setApiKey]   = useState('');
  const [showKey,  setShowKey]  = useState(false);
  const [rotating, setRotating] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.push('/login');
    if (user) {
      setFullName(user.full_name ?? '');
      setCompany(user.company ?? '');
      setApiKey(user.api_key);
    }
  }, [user, loading, router]);

  const saveProfile = async () => {
    setSaving(true);
    setSaveMsg('');
    try {
      await authApi.update({ full_name: fullName, company });
      await refresh();
      setSaveMsg('Saved.');
    } catch {
      setSaveMsg('Save failed.');
    }
    setSaving(false);
  };

  const rotateKey = async () => {
    if (!confirm('Rotate API key? All existing integrations using the current key will stop working.')) return;
    setRotating(true);
    try {
      const r = await authApi.rotateApiKey();
      setApiKey(r.api_key);
      await refresh();
    } catch {}
    setRotating(false);
  };

  const openPortal = async () => {
    try {
      const r = await billing.portal(`${window.location.origin}/profile`);
      window.location.href = r.portal_url;
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Portal unavailable');
    }
  };

  if (loading || !user) return null;

  const accent = TIER_COLOR[user.tier] ?? 'var(--text-muted)';

  return (
    <div style={{ minHeight: '100vh' }}>
      <NavBar />

      <div style={{ maxWidth: '720px', margin: '0 auto', padding: '3rem 2rem' }}>
        <h1 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '2.8rem', letterSpacing: '0.05em', marginBottom: '2rem' }}>
          PROFILE
        </h1>

        {/* Account tier */}
        <div className="card" style={{ padding: '1.5rem', marginBottom: '1.5rem', borderColor: accent, boxShadow: `0 0 12px ${accent}20` }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.3rem' }}>Account Tier</div>
              <div style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '2rem', color: accent, letterSpacing: '0.06em' }}>
                {user.tier.toUpperCase()}
              </div>
              <div style={{ fontFamily: 'Space Mono, monospace', fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                {user.jobs_used_this_month} jobs used this month
              </div>
            </div>
            {user.tier !== 'enterprise' && (
              <button className="btn-neon" onClick={() => router.push('/pricing')} style={{ flexShrink: 0 }}>
                Upgrade Plan →
              </button>
            )}
          </div>
        </div>

        {/* Profile form */}
        <div className="card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h2 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.2rem', letterSpacing: '0.06em', marginBottom: '1.25rem' }}>
            ACCOUNT INFO
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.4rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Email</label>
              <input className="input-neon" value={user.email} disabled style={{ opacity: 0.5, cursor: 'not-allowed' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.4rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Full Name</label>
              <input className="input-neon" value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Your name" />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.4rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Company</label>
              <input className="input-neon" value={company} onChange={e => setCompany(e.target.value)} placeholder="Neon Sign Studio" />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1.25rem' }}>
            <button className="btn-neon" onClick={saveProfile} disabled={saving} style={{ flexShrink: 0 }}>
              {saving ? <span className="status-pulse">SAVING…</span> : 'Save Changes'}
            </button>
            {saveMsg && <span style={{ fontSize: '0.82rem', color: saveMsg === 'Saved.' ? 'var(--green)' : 'var(--red)', fontFamily: 'Space Mono, monospace' }}>{saveMsg}</span>}
          </div>
        </div>

        {/* API Key */}
        <div className="card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h2 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.2rem', letterSpacing: '0.06em', marginBottom: '0.5rem' }}>
            API KEY
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginBottom: '1.25rem', lineHeight: 1.6 }}>
            Use this key to authenticate direct API requests. Pass as <code style={{ fontFamily: 'Space Mono, monospace', color: 'var(--cyan)' }}>Authorization: Bearer &lt;api_key&gt;</code>.
          </p>

          <div style={{ position: 'relative', marginBottom: '1rem' }}>
            <input
              className="input-neon"
              readOnly
              value={showKey ? apiKey : '•'.repeat(Math.min(apiKey.length, 40))}
              style={{ paddingRight: '7rem', fontFamily: 'Space Mono, monospace', fontSize: '0.78rem', letterSpacing: '0.04em' }}
            />
            <button
              onClick={() => setShowKey(!showKey)}
              style={{
                position: 'absolute',
                right: '0.5rem',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'none',
                border: 'none',
                color: 'var(--pink)',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontFamily: 'Space Mono, monospace',
              }}
            >
              {showKey ? 'hide' : 'reveal'}
            </button>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button
              className="btn-ghost"
              onClick={() => { navigator.clipboard.writeText(apiKey); }}
              style={{ fontSize: '0.78rem', padding: '0.5rem 1rem' }}
            >
              Copy Key
            </button>
            <button
              className="btn-ghost"
              onClick={rotateKey}
              disabled={rotating}
              style={{ fontSize: '0.78rem', padding: '0.5rem 1rem', color: 'var(--amber)', borderColor: 'rgba(255,179,0,0.3)' }}
            >
              {rotating ? <span className="status-pulse">ROTATING…</span> : '⟳ Rotate Key'}
            </button>
          </div>
        </div>

        {/* Billing */}
        {user.tier !== 'free' && (
          <div className="card" style={{ padding: '1.5rem' }}>
            <h2 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.2rem', letterSpacing: '0.06em', marginBottom: '0.5rem' }}>
              BILLING
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginBottom: '1.25rem' }}>
              Manage your subscription, invoices, and payment method via Stripe.
            </p>
            <button className="btn-ghost" onClick={openPortal}>Open Billing Portal →</button>
          </div>
        )}
      </div>
    </div>
  );
}
