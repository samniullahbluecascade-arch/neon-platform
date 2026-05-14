'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

const TIER_COLOR: Record<string, string> = {
  free:       '#9CA3AF',
  starter:    '#0891B2',
  business:   '#E8175D',
  enterprise: '#D97706',
};

export default function NavBar() {
  const { user, logout } = useAuth();
  const path = usePathname();

  const link = (href: string, label: string) => {
    const active = path === href;
    return (
      <Link href={href} className={`lux-nav-link${active ? ' is-active' : ''}`}>
        {label}
      </Link>
    );
  };

  return (
    <nav className="lux-nav">
      <div className="wrapper lux-nav-inner">
        <Link href="/" className="nav-logo lux-nav-brand" style={{ marginRight: 'auto' }}>
          <span className="logo-dot" />
          Neonizer
        </Link>

        {user ? (
          <div className="lux-nav-links" style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            {link('/dashboard', 'Quick Measure')}
            {link('/studio', 'Studio')}
            {link('/pricing', 'Pricing')}

            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.62rem',
              fontWeight: 700,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              color: TIER_COLOR[user.tier] ?? 'var(--text-3)',
              border: `1px solid ${TIER_COLOR[user.tier] ?? 'var(--border-2)'}`,
              padding: '3px 10px',
              borderRadius: 999,
            }}>
              {user.tier}
            </span>

            {link('/profile', user.email.split('@')[0])}

            <button
              onClick={logout}
              className="btn-secondary"
              style={{ padding: '7px 14px', fontSize: '0.78rem' }}
            >
              Sign out
            </button>
          </div>
        ) : (
          <div className="nav-links lux-nav-links">
            <Link href="/studio" className={`lux-nav-link${path === '/studio' ? ' is-active' : ''}`}>Studio</Link>
            <Link href="/pricing" className={`lux-nav-link${path === '/pricing' ? ' is-active' : ''}`}>Pricing</Link>
            <Link href="/login" className="lux-nav-link">Login</Link>
            <Link href="/register">
              <button className="nav-cta lux-nav-cta">Start free →</button>
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}
