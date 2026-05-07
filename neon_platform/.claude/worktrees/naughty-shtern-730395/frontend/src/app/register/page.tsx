'use client';
import { useState, FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { auth } from '@/lib/api';

export default function RegisterPage() {
  const router = useRouter();

  const [email,  setEmail]  = useState('');
  const [pw1,    setPw1]    = useState('');
  const [pw2,    setPw2]    = useState('');
  const [error,  setError]  = useState('');
  const [loading, setLoading] = useState(false);
  const [done,   setDone]   = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (pw1 !== pw2) { setError('Passwords do not match'); return; }
    if (pw1.length < 8) { setError('Password must be 8+ characters'); return; }

    setLoading(true);
    setError('');
    try {
      await auth.register(email, pw1, pw2);  // api sends: {email, password, password2}
      setDone(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed');
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
    }}>
      <div style={{
        position: 'fixed',
        top: '35%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '600px',
        height: '400px',
        background: 'radial-gradient(ellipse, rgba(0,212,255,0.08) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div style={{ width: '100%', maxWidth: '400px', position: 'relative' }}>
        <Link href="/" style={{ textDecoration: 'none', display: 'block', textAlign: 'center', marginBottom: '2.5rem' }}>
          <span style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '2rem', color: 'var(--text)' }}>NEON </span>
          <span style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '2rem' }} className="neon-pink">PLATFORM</span>
        </Link>

        <div className="card" style={{ padding: '2.5rem' }}>
          {done ? (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>✉</div>
              <h2 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.6rem', letterSpacing: '0.06em', marginBottom: '0.75rem' }}>
                CHECK YOUR EMAIL
              </h2>
              <p style={{ color: 'var(--text-dim)', fontSize: '0.88rem', lineHeight: 1.6, marginBottom: '1.5rem' }}>
                Verification link sent to <strong style={{ color: 'var(--text)' }}>{email}</strong>.
                Confirm your email then sign in.
              </p>
              <button className="btn-neon" onClick={() => router.push('/login')} style={{ width: '100%' }}>
                GO TO LOGIN →
              </button>
            </div>
          ) : (
            <>
              <h1 style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.8rem', letterSpacing: '0.06em', marginBottom: '0.5rem' }}>
                CREATE ACCOUNT
              </h1>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '2rem' }}>
                Free tier — 10 measurements/month.
              </p>

              <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.4rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Email</label>
                  <input className="input-neon" type="email" required placeholder="you@studio.com" value={email} onChange={e => setEmail(e.target.value)} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.4rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Password</label>
                  <input className="input-neon" type="password" required placeholder="8+ characters" value={pw1} onChange={e => setPw1(e.target.value)} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.4rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Confirm Password</label>
                  <input className="input-neon" type="password" required placeholder="repeat password" value={pw2} onChange={e => setPw2(e.target.value)} />
                </div>

                {error && <div style={{ color: 'var(--red)', fontSize: '0.82rem', fontFamily: 'Space Mono, monospace' }}>⚠ {error}</div>}

                <button className="btn-neon" type="submit" disabled={loading} style={{ width: '100%', marginTop: '0.5rem' }}>
                  {loading ? <span className="status-pulse">CREATING…</span> : 'CREATE ACCOUNT →'}
                </button>
              </form>
            </>
          )}
        </div>

        <p style={{ textAlign: 'center', marginTop: '1.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Already have an account?{' '}
          <Link href="/login" style={{ color: 'var(--pink)', textDecoration: 'none' }}>Sign in</Link>
        </p>
      </div>
    </div>
  );
}
