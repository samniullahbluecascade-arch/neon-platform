'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import FlipCard from './FlipCard';
import ScrollReveal from './ScrollReveal';
import {
  getDistribution,
  getDistributionPercents,
  getTestimonials,
} from '@/lib/feedback';

// ─── Star row ────────────────────────────────────────────────────────────────
function Stars({ rating, size = 16, glow = false }: { rating: number; size?: number; glow?: boolean }) {
  const full  = Math.floor(rating);
  const half  = rating - full >= 0.5;
  return (
    <span style={{ display: 'inline-flex', gap: '2px', lineHeight: 1 }}>
      {[1, 2, 3, 4, 5].map(i => {
        const filled = i <= full;
        const isHalf = !filled && i === full + 1 && half;
        return (
          <span
            key={i}
            style={{
              fontSize: `${size}px`,
              color: filled || isHalf ? '#ffb300' : 'var(--bg-2)',
              textShadow: glow && (filled || isHalf) ? '0 0 8px rgba(255,179,0,0.5)' : undefined,
              filter: isHalf ? 'drop-shadow(0 0 0 #ffb300)' : undefined,
            }}
          >
            {isHalf ? '★' : (filled ? '★' : '☆')}
          </span>
        );
      })}
    </span>
  );
}

// ─── Distribution bar ────────────────────────────────────────────────────────
function DistributionBar({ stars, percent, animate }: { stars: number; percent: number; animate: boolean }) {
  const color = stars >= 4 ? '#ffb300' : stars === 3 ? '#00d4ff' : '#ff8c00';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
      <div style={{
        width: '38px',
        fontFamily: 'Space Mono, monospace',
        fontSize: '0.78rem',
        color: 'var(--text-dim)',
        display: 'flex', alignItems: 'center', gap: '2px',
      }}>
        {stars}<span style={{ color: '#ffb300', fontSize: '0.78rem' }}>★</span>
      </div>
      <div style={{
        flex: 1,
        height: '8px',
        background: 'var(--bg-2)',
        border: '1px solid var(--border)',
        borderRadius: '99px',
        overflow: 'hidden',
        position: 'relative',
      }}>
        <div style={{
          height: '100%',
          width: animate ? `${percent}%` : '0%',
          background: `linear-gradient(90deg, ${color}aa 0%, ${color} 100%)`,
          borderRadius: '99px',
          boxShadow: percent > 0 ? `0 0 10px ${color}80` : undefined,
          transition: 'width 1.6s cubic-bezier(0.22, 1, 0.36, 1)',
        }} />
      </div>
      <div style={{
        width: '48px',
        textAlign: 'right',
        fontFamily: 'Space Mono, monospace',
        fontSize: '0.78rem',
        color: 'var(--text-dim)',
      }}>
        {percent.toFixed(0)}%
      </div>
    </div>
  );
}

// ─── Component ───────────────────────────────────────────────────────────────
export default function RatingsShowcase() {
  const dist        = getDistribution();
  const percents    = getDistributionPercents();
  const testimonials = getTestimonials();

  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.2 },
    );
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);

  // Average counter animation
  const [counter, setCounter] = useState(0);
  useEffect(() => {
    if (!visible) return;
    let raf = 0;
    const start = performance.now();
    const dur = 1200;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      setCounter(eased * dist.average);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [visible, dist.average]);

  return (
    <section
      ref={ref}
      style={{
        padding: '6rem 2rem',
        maxWidth: '1100px',
        margin: '0 auto',
      }}
    >
      <ScrollReveal animation="fade-up">
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <div style={{
            fontFamily: 'Space Mono, monospace',
            fontSize: '0.72rem',
            letterSpacing: '0.2em',
            color: 'var(--pink)',
            textTransform: 'uppercase',
            marginBottom: '0.6rem',
          }}>
            Client Satisfaction
          </div>
          <h2 style={{
            fontFamily: 'Bebas Neue, sans-serif',
            fontSize: 'clamp(2.5rem, 5vw, 4rem)',
            letterSpacing: '0.05em',
          }}>
            TRUSTED BY <span className="neon-pink">NEON SHOPS</span>
          </h2>
        </div>
      </ScrollReveal>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(260px, 1fr) 1.4fr',
        gap: '2rem',
        alignItems: 'stretch',
      }}>
        {/* Left: Avg rating + stars */}
        <ScrollReveal animation="slide-right">
          <div className="card" style={{
            padding: '2.5rem 2rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.85rem',
            textAlign: 'center',
            position: 'relative',
            overflow: 'hidden',
          }}>
            {/* gold radial backdrop */}
            <div style={{
              position: 'absolute', inset: 0,
              background: 'radial-gradient(ellipse at center, rgba(255,179,0,0.10) 0%, transparent 65%)',
              pointerEvents: 'none',
            }} />
            <div style={{
              fontFamily: 'Space Mono, monospace',
              fontSize: '0.65rem',
              letterSpacing: '0.18em',
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              position: 'relative',
            }}>
              Average Rating
            </div>
            <div style={{
              fontFamily: 'Bebas Neue, sans-serif',
              fontSize: 'clamp(4rem, 8vw, 6rem)',
              lineHeight: 1,
              color: '#ffb300',
              textShadow: '0 0 24px rgba(255,179,0,0.45)',
              letterSpacing: '0.02em',
              position: 'relative',
            }}>
              {counter.toFixed(2)}
            </div>
            <div style={{ position: 'relative' }}>
              <Stars rating={dist.average} size={26} glow />
            </div>
            <div style={{
              fontSize: '0.78rem',
              color: 'var(--text-dim)',
              fontFamily: 'Space Mono, monospace',
              letterSpacing: '0.05em',
              position: 'relative',
            }}>
              {dist.total > 0
                ? `${dist.total.toLocaleString()} verified reviews`
                : 'Early access · projected satisfaction'}
            </div>
          </div>
        </ScrollReveal>

        {/* Right: distribution bars */}
        <ScrollReveal animation="slide-left">
          <div className="card" style={{ padding: '2rem' }}>
            <div style={{
              display: 'flex',
              alignItems: 'baseline',
              justifyContent: 'space-between',
              marginBottom: '1.5rem',
              flexWrap: 'wrap',
              gap: '0.5rem',
            }}>
              <div style={{
                fontSize: '0.72rem',
                letterSpacing: '0.12em',
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
              }}>
                Rating Distribution
              </div>
              <div style={{
                fontSize: '0.7rem',
                color: 'var(--text-dim)',
                fontFamily: 'Space Mono, monospace',
              }}>
                Click a tile below to read a review
              </div>
            </div>
            {[5, 4, 3, 2, 1].map(s => (
              <DistributionBar
                key={s}
                stars={s}
                percent={percents[s]}
                animate={visible}
              />
            ))}
          </div>
        </ScrollReveal>
      </div>

      {/* Testimonials row */}
      <ScrollReveal animation="fade-up" delay={0.2}>
        <div style={{
          marginTop: '2rem',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '1rem',
        }}>
          {testimonials.length === 0 ? (
            <div className="card" style={{
              gridColumn: '1 / -1',
              padding: '2.5rem 2rem',
              textAlign: 'center',
              borderStyle: 'dashed',
            }}>
              <div style={{
                fontFamily: 'Bebas Neue, sans-serif',
                fontSize: '1.4rem',
                letterSpacing: '0.06em',
                marginBottom: '0.5rem',
              }}>
                NO PUBLIC REVIEWS YET
              </div>
              <div style={{
                color: 'var(--text-dim)',
                fontSize: '0.85rem',
                marginBottom: '1.25rem',
                lineHeight: 1.6,
              }}>
                Real client reviews land here as users rate their measurements.
                <br />
                Be among the first.
              </div>
              <Link href="/register">
                <button className="btn-ghost" style={{ padding: '0.6rem 1.4rem', fontSize: '0.78rem' }}>
                  Try a measurement →
                </button>
              </Link>
            </div>
          ) : (
            testimonials.map((t, i) => (
              <div key={i} style={{ height: '180px' }}>
                <FlipCard
                  front={
                    <div className="card" style={{
                      height: '100%',
                      padding: '1.5rem',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '0.5rem',
                    }}>
                      <Stars rating={t.rating} size={18} glow />
                      <div style={{
                        fontFamily: 'Bebas Neue, sans-serif',
                        fontSize: '1.2rem',
                        letterSpacing: '0.04em',
                      }}>{t.author}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{t.role}</div>
                      <div style={{
                        fontSize: '0.65rem',
                        color: 'var(--pink)',
                        letterSpacing: '0.1em',
                        textTransform: 'uppercase',
                      }}>
                        Click to read →
                      </div>
                    </div>
                  }
                  back={
                    <div className="card" style={{
                      height: '100%',
                      padding: '1.5rem',
                      background: 'linear-gradient(135deg, var(--bg-2) 0%, rgba(255,179,0,0.08) 100%)',
                      display: 'flex',
                      alignItems: 'center',
                      fontSize: '0.85rem',
                      color: 'var(--text-dim)',
                      lineHeight: 1.6,
                      fontStyle: 'italic',
                    }}>
                      “{t.text}”
                    </div>
                  }
                />
              </div>
            ))
          )}
        </div>
      </ScrollReveal>
    </section>
  );
}
