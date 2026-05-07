'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { billing } from '@/lib/api';
import type { Plan } from '@/lib/types';
import { useAuth } from '@/context/AuthContext';
import NavBar from '@/components/NavBar';
import PaymentMethodPicker from '@/components/PaymentMethodPicker';

const FEATURES: Record<string, string[]> = {
  free:       ['20 requests/month', '2000 px max width', 'Standard accuracy', 'REST API access'],
  starter:    ['200 requests/month', '4000 px max width', 'Standard accuracy', 'All formats supported', 'Email support'],
  business:   ['600 requests/month', '8000 px max width', 'ML correction enabled', 'Priority processing', 'All formats supported'],
  enterprise: ['1,500 requests/month', 'No resolution limit', 'ML correction enabled', 'SLA guarantee', 'Dedicated support', 'Custom integrations'],
};

const ACCENT: Record<string, string> = { free: '#6b7280', starter: '#00d4ff', business: '#ff2d78', enterprise: '#ffb300' };

export default function PricingPage() {
  const router      = useRouter();
  const { user }    = useAuth();
  const [plans, setPlans]     = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [picking, setPicking] = useState<Plan | null>(null);

  useEffect(() => {
    billing.plans().then(setPlans).finally(() => setLoading(false));
  }, []);

  const upgrade = (plan: Plan) => {
    if (!user) { router.push('/login'); return; }
    if (plan.tier_key === 'free') return;
    setPicking(plan);
  };

  return (
    <div style={{ minHeight: '100vh' }}>
      <NavBar />

      <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '4rem 2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
          <h1 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: 'clamp(3rem, 6vw, 5rem)', letterSpacing: '0.04em', marginBottom: '1rem' }}>
            SIMPLE <span className="neon-pink">PRICING</span>
          </h1>
          <p style={{ color: 'var(--text-dim)', fontSize: '1rem', maxWidth: '500px', margin: '0 auto', lineHeight: 1.6 }}>
            Start free. Scale when you need. No hidden fees.
          </p>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)' }} className="status-pulse">Loading plans…</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
            {plans.map(plan => {
              const accent    = ACCENT[plan.tier_key] ?? 'var(--pink)';
              const isCurrent = user?.tier === plan.tier_key;
              const features  = FEATURES[plan.tier_key] ?? [];
              const isFree    = plan.tier_key === 'free';
              const isEnt     = plan.tier_key === 'enterprise';

              return (
                <div
                  key={plan.id}
                  className={`card ${isEnt ? 'enterprise-card' : ''}`}
                  style={{
                    padding: '2rem',
                    borderColor: isEnt ? '#ffb300' : (isCurrent ? accent : undefined),
                    boxShadow: isEnt
                      ? '0 0 32px rgba(255,179,0,0.18), inset 0 0 32px rgba(255,179,0,0.04)'
                      : (isCurrent ? `0 0 20px ${accent}30` : undefined),
                    background: isEnt
                      ? 'linear-gradient(135deg, rgba(255,179,0,0.06) 0%, transparent 50%, rgba(255,140,0,0.04) 100%)'
                      : undefined,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '1.25rem',
                    position: 'relative',
                    transform: isEnt ? 'translateY(-6px)' : undefined,
                  }}
                >
                  {/* Premium ribbon for Enterprise */}
                  {isEnt && (
                    <div style={{
                      position: 'absolute',
                      top: '-12px',
                      left: '50%',
                      transform: 'translateX(-50%)',
                      background: 'linear-gradient(90deg, #ffb300 0%, #ffd84d 50%, #ffb300 100%)',
                      backgroundSize: '200% 100%',
                      animation: 'gold-shimmer 3s linear infinite',
                      color: '#1a0f00',
                      fontSize: '0.62rem',
                      fontWeight: 800,
                      fontFamily: 'Space Mono, monospace',
                      letterSpacing: '0.18em',
                      padding: '4px 14px',
                      borderRadius: '99px',
                      boxShadow: '0 0 16px rgba(255,179,0,0.5)',
                      whiteSpace: 'nowrap',
                      zIndex: 2,
                    }}>
                      ★ PREMIUM
                    </div>
                  )}
                  {isCurrent && (
                    <div style={{
                      position: 'absolute',
                      top: '-1px',
                      right: '1.5rem',
                      background: accent,
                      color: '#000',
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      fontFamily: 'Space Mono, monospace',
                      letterSpacing: '0.1em',
                      padding: '2px 10px',
                      borderRadius: '0 0 4px 4px',
                    }}>
                      CURRENT
                    </div>
                  )}

                  <div>
                    <div style={{
                      fontFamily: 'Bebas Neue, sans-serif',
                      fontSize: '1.6rem',
                      letterSpacing: '0.06em',
                      color: accent,
                      marginBottom: '0.25rem',
                    }}>
                      {plan.name.toUpperCase()}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                      {plan.description}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontFamily: 'Space Mono, monospace', fontSize: '2.5rem', fontWeight: 700, color: 'var(--text)' }}>
                      {plan.price_usd_cents === 0 ? '$0' : `$${(plan.price_usd_cents / 100).toFixed(0)}`}
                    </span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginLeft: '0.3rem' }}>/month</span>
                  </div>

                  <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {features.map(f => (
                      <li key={f} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.85rem', color: 'var(--text-dim)' }}>
                        <span style={{ color: accent, flexShrink: 0 }}>✓</span>
                        {f}
                      </li>
                    ))}
                  </ul>

                  <div style={{ marginTop: 'auto' }}>
                    {isCurrent ? (
                      <button className="btn-ghost" disabled style={{ width: '100%', opacity: 0.5 }}>Current plan</button>
                    ) : isFree ? (
                      <Link href="/register" style={{ display: 'block' }}>
                        <button className="btn-ghost" style={{ width: '100%' }}>Get Started Free</button>
                      </Link>
                    ) : (
                      <button
                        className="btn-neon"
                        style={{ width: '100%', background: accent, boxShadow: `0 0 16px ${accent}50` }}
                        onClick={() => upgrade(plan)}
                      >
                        Upgrade to {plan.name} →
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div style={{ textAlign: 'center', marginTop: '3rem', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
          Questions?{' '}
          <a href="mailto:support@neonplatform.com" style={{ color: 'var(--pink)', textDecoration: 'none' }}>
            Contact support
          </a>
          {user && (
            <>
              {' · '}
              <button
                onClick={async () => {
                  try {
                    const r = await billing.portal(`${window.location.origin}/profile`);
                    window.location.href = r.portal_url;
                  } catch {}
                }}
                style={{ background: 'none', border: 'none', color: 'var(--pink)', cursor: 'pointer', fontSize: '0.82rem' }}
              >
                Manage billing
              </button>
            </>
          )}
        </div>
      </div>

      {picking && <PaymentMethodPicker plan={picking} onClose={() => setPicking(null)} />}

      <style jsx global>{`
        @keyframes gold-shimmer {
          0%   { background-position: 0% 50%; }
          100% { background-position: 200% 50%; }
        }
        .enterprise-card::before {
          content: '';
          position: absolute;
          inset: -1px;
          border-radius: inherit;
          padding: 1px;
          background: linear-gradient(135deg, #ffb300 0%, #ffd84d 25%, #ff8c00 50%, #ffd84d 75%, #ffb300 100%);
          background-size: 300% 300%;
          animation: gold-shimmer 5s linear infinite;
          -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
          -webkit-mask-composite: xor;
                  mask-composite: exclude;
          pointer-events: none;
          z-index: 0;
        }
        .enterprise-card > * {
          position: relative;
          z-index: 1;
        }
      `}</style>
    </div>
  );
}
