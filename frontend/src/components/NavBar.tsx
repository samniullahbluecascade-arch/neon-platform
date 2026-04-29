'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

const TIER_COLORS: Record<string, string> = {
  free:       '#6b7280',
  pro:        '#00d4ff',
  enterprise: '#ffb300',
};

export default function NavBar() {
  const { user, logout } = useAuth();
  const path = usePathname();

  const link = (href: string, label: string) => (
    <Link
      href={href}
      style={{
        fontSize: '0.8rem',
        fontWeight: 500,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        color: path === href ? 'var(--text)' : 'var(--text-dim)',
        textDecoration: 'none',
        transition: 'color 0.15s',
        paddingBottom: '2px',
        borderBottom: path === href ? '1px solid var(--pink)' : '1px solid transparent',
      }}
    >
      {label}
    </Link>
  );

  return (
    <nav style={{
      position: 'sticky',
      top: 0,
      zIndex: 100,
      background: 'rgba(7, 7, 14, 0.88)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border)',
      padding: '0 2rem',
      height: '56px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '1rem',
    }}>
      {/* Logo */}
      <Link href="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.5rem', letterSpacing: '0.05em', color: 'var(--text)' }}>
          NEON
        </span>
        <span style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.5rem', letterSpacing: '0.05em' }} className="neon-pink">
          PLATFORM
        </span>
      </Link>

      {/* Nav links */}
      {user ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          {link('/dashboard', 'Dashboard')}
          {link('/studio', 'Studio')}
          {link('/pricing', 'Pricing')}

          {/* Tier badge */}
          <span style={{
            fontSize: '0.65rem',
            fontFamily: 'Space Mono, monospace',
            fontWeight: 700,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: TIER_COLORS[user.tier] ?? 'var(--text-dim)',
            border: `1px solid ${TIER_COLORS[user.tier] ?? 'var(--border)'}`,
            padding: '2px 8px',
            borderRadius: '100px',
          }}>
            {user.tier}
          </span>

          {link('/profile', user.email.split('@')[0])}

          <button className="btn-ghost" onClick={logout} style={{ padding: '0.4rem 0.9rem', fontSize: '0.75rem' }}>
            Sign out
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Link href="/pricing" style={{ color: 'var(--text-dim)', fontSize: '0.85rem', textDecoration: 'none' }}>
            Pricing
          </Link>
          <Link href="/login"><button className="btn-ghost" style={{ padding: '0.4rem 1rem', fontSize: '0.8rem' }}>Login</button></Link>
          <Link href="/register"><button className="btn-neon" style={{ padding: '0.4rem 1rem', fontSize: '0.8rem' }}>Get started</button></Link>
        </div>
      )}
    </nav>
  );
}
