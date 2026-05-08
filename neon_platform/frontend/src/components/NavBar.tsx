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
      <Link
        href={href}
        style={{
          color: active ? 'var(--text)' : 'var(--text-2)',
          fontWeight: 500,
          fontSize: '0.875rem',
          letterSpacing: '0.01em',
          paddingBottom: 2,
          borderBottom: active ? '2px solid var(--pink)' : '2px solid transparent',
          transition: 'color 0.2s',
        }}
      >
        {label}
      </Link>
    );
  };

  return (
    <nav
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        background: 'rgba(255,255,255,0.92)',
        borderBottom: '1px solid var(--border)',
        boxShadow: '0 1px 0 rgba(0,0,0,0.06)',
      }}
    >
      <div className="wrapper" style={{
        display: 'flex',
        alignItems: 'center',
        gap: 40,
        height: 64,
      }}>
        <Link href="/" className="nav-logo" style={{ marginRight: 'auto' }}>
          <span className="logo-dot" />
          Neonizer
        </Link>

        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
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
          <div className="nav-links" style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
            <Link href="/studio" style={{ color: path === '/studio' ? 'var(--text)' : 'var(--text-2)', fontWeight: 500, fontSize: '0.875rem' }}>Studio</Link>
            <Link href="/pricing" style={{ color: path === '/pricing' ? 'var(--text)' : 'var(--text-2)', fontWeight: 500, fontSize: '0.875rem' }}>Pricing</Link>
            <Link href="/login" style={{ color: 'var(--text-2)', fontWeight: 500, fontSize: '0.875rem' }}>Login</Link>
            <Link href="/register">
              <button className="nav-cta">Start free →</button>
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}
