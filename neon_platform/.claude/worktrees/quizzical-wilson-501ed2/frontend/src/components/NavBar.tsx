'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

const TIER_COLORS: Record<string, string> = {
  free:       '#8a8a9a',
  starter:    '#0891b2',
  business:   '#e91e63',
  enterprise: '#d97706',
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
          fontSize: '0.85rem',
          fontWeight: 500,
          color: active ? 'var(--text)' : 'var(--text-dim)',
          textDecoration: 'none',
          transition: 'color 0.15s',
          paddingBottom: '2px',
          borderBottom: active ? '2px solid var(--pink)' : '2px solid transparent',
        }}
      >
        {label}
      </Link>
    );
  };

  return (
    <nav style={{
      position: 'sticky',
      top: 0,
      zIndex: 100,
      background: 'rgba(255, 255, 255, 0.88)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border)',
      padding: '0 2rem',
      height: '64px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '1rem',
    }}>
      {/* Logo */}
      <Link href="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center' }}>
        <span style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.6rem', letterSpacing: '0.04em', color: 'var(--text)' }}>
          Neon
        </span>
        <span style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.6rem', letterSpacing: '0.04em' }} className="neon-pink">
          izer
        </span>
      </Link>

      {/* Right side */}
      {user ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.75rem' }}>
          {link('/dashboard', 'Quick Measure')}
          {link('/studio', 'Studio')}
          {link('/pricing', 'Pricing')}

          {/* Tier badge */}
          <span style={{
            fontSize: '0.62rem',
            fontFamily: 'Space Mono, monospace',
            fontWeight: 700,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: TIER_COLORS[user.tier] ?? 'var(--text-muted)',
            border: `1px solid ${TIER_COLORS[user.tier] ?? 'var(--border-md)'}`,
            padding: '3px 10px',
            borderRadius: '999px',
          }}>
            {user.tier}
          </span>

          {link('/profile', user.email.split('@')[0])}

          <button className="btn-ghost" onClick={logout} style={{ padding: '0.4rem 0.9rem', fontSize: '0.78rem' }}>
            Sign out
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <Link href="/pricing" style={{ color: 'var(--text-dim)', fontSize: '0.85rem', textDecoration: 'none', fontWeight: 500 }}>
            Pricing
          </Link>
          <Link href="/login"><button className="btn-ghost" style={{ padding: '0.45rem 1rem', fontSize: '0.8rem' }}>Log in</button></Link>
          <Link href="/register"><button className="btn-neon" style={{ padding: '0.45rem 1rem', fontSize: '0.8rem' }}>Start free</button></Link>
        </div>
      )}
    </nav>
  );
}
