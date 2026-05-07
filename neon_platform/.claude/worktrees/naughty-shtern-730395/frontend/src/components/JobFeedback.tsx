'use client';
import { useEffect, useState } from 'react';
import { getFeedback, submitFeedback, type JobFeedback } from '@/lib/feedback';

interface Props {
  jobId: string;
}

export default function JobFeedbackWidget({ jobId }: Props) {
  const [existing, setExisting] = useState<JobFeedback | null>(null);
  const [rating, setRating]     = useState(0);
  const [hover, setHover]       = useState(0);
  const [comment, setComment]   = useState('');
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    setExisting(getFeedback(jobId));
  }, [jobId]);

  const send = () => {
    if (rating < 1) return;
    const fb = submitFeedback(jobId, rating, comment);
    setExisting(fb);
    setSubmitted(true);
  };

  // Already-rated state
  if (existing && !submitted) {
    return (
      <div className="card" style={{
        padding: '1.5rem',
        marginBottom: '1.5rem',
        borderColor: 'rgba(255,179,0,0.35)',
        background: 'linear-gradient(135deg, rgba(255,179,0,0.04) 0%, transparent 100%)',
      }}>
        <div style={{
          fontSize: '0.7rem',
          color: 'var(--text-muted)',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          marginBottom: '0.6rem',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem',
        }}>
          <span>Your Feedback</span>
          <span style={{ color: '#ffb300' }}>★ Submitted</span>
        </div>
        <StarRow rating={existing.rating} size={20} />
        {existing.comment && (
          <div style={{
            marginTop: '0.8rem',
            fontSize: '0.85rem',
            color: 'var(--text-dim)',
            fontStyle: 'italic',
            lineHeight: 1.6,
          }}>
            “{existing.comment}”
          </div>
        )}
        <div style={{
          marginTop: '0.8rem',
          fontSize: '0.7rem',
          color: 'var(--text-muted)',
          fontFamily: 'Space Mono, monospace',
        }}>
          {new Date(existing.submittedAt).toLocaleString()} · stored locally
        </div>
      </div>
    );
  }

  // Just-submitted thank-you
  if (submitted) {
    return (
      <div className="card" style={{
        padding: '1.5rem',
        marginBottom: '1.5rem',
        borderColor: '#00ff9d',
        background: 'rgba(0,255,157,0.05)',
        textAlign: 'center',
      }}>
        <div style={{
          fontFamily: 'Bebas Neue, sans-serif',
          fontSize: '1.4rem',
          letterSpacing: '0.06em',
          color: '#00ff9d',
          marginBottom: '0.4rem',
        }}>
          THANK YOU FOR YOUR FEEDBACK
        </div>
        <div style={{ fontSize: '0.82rem', color: 'var(--text-dim)' }}>
          Your rating helps us tune the pipeline.
        </div>
      </div>
    );
  }

  // Collection form
  const showStar = (i: number) => (hover || rating) >= i;
  return (
    <div className="card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
      <div style={{
        fontSize: '0.72rem',
        color: 'var(--text-muted)',
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
        marginBottom: '0.8rem',
      }}>
        Rate This Measurement
      </div>

      <div
        style={{ display: 'flex', gap: '0.4rem', marginBottom: '1rem' }}
        onMouseLeave={() => setHover(0)}
      >
        {[1, 2, 3, 4, 5].map(i => (
          <button
            key={i}
            onMouseEnter={() => setHover(i)}
            onClick={() => setRating(i)}
            aria-label={`Rate ${i} stars`}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '0.2rem',
              fontSize: '2rem',
              lineHeight: 1,
              color: showStar(i) ? '#ffb300' : 'var(--bg-2)',
              textShadow: showStar(i) ? '0 0 14px rgba(255,179,0,0.6)' : undefined,
              transition: 'all 0.15s',
              transform: showStar(i) ? 'scale(1.05)' : 'scale(1)',
            }}
          >
            {showStar(i) ? '★' : '☆'}
          </button>
        ))}
        {rating > 0 && (
          <span style={{
            alignSelf: 'center',
            marginLeft: '0.6rem',
            fontSize: '0.78rem',
            color: 'var(--text-dim)',
            fontFamily: 'Space Mono, monospace',
          }}>
            {['','Poor','Fair','Good','Great','Excellent'][rating]}
          </span>
        )}
      </div>

      <textarea
        className="input-neon"
        value={comment}
        onChange={e => setComment(e.target.value)}
        placeholder="Tell us about the measurement accuracy, speed, or anything else… (optional)"
        style={{ minHeight: '70px', resize: 'vertical', fontSize: '0.85rem', marginBottom: '0.8rem' }}
      />

      <button
        className="btn-neon"
        disabled={rating < 1}
        onClick={send}
        style={{
          padding: '0.55rem 1.2rem',
          fontSize: '0.8rem',
          opacity: rating < 1 ? 0.5 : 1,
          cursor: rating < 1 ? 'not-allowed' : 'pointer',
        }}
      >
        Submit Feedback →
      </button>
      <span style={{
        marginLeft: '0.8rem',
        fontSize: '0.7rem',
        color: 'var(--text-muted)',
        fontFamily: 'Space Mono, monospace',
      }}>
        Stored locally for now · backend coming soon
      </span>
    </div>
  );
}

function StarRow({ rating, size }: { rating: number; size: number }) {
  return (
    <div style={{ display: 'inline-flex', gap: '2px' }}>
      {[1, 2, 3, 4, 5].map(i => (
        <span
          key={i}
          style={{
            fontSize: `${size}px`,
            color: i <= rating ? '#ffb300' : 'var(--bg-2)',
            textShadow: i <= rating ? '0 0 8px rgba(255,179,0,0.5)' : undefined,
          }}
        >
          {i <= rating ? '★' : '☆'}
        </span>
      ))}
    </div>
  );
}
