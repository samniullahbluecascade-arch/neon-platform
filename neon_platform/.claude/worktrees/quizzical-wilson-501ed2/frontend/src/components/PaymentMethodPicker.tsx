'use client';
import { useState } from 'react';
import type { Plan } from '@/lib/types';
import { billing } from '@/lib/api';

interface Props {
  plan: Plan;
  onClose: () => void;
}

type Method = {
  id: string;
  name: string;
  group: 'card' | 'wallet' | 'pk';
  hint?: string;
  emoji: string;
  color: string;
  /** Where the click flows. 'stripe' → Stripe Checkout; 'manual' → instructions modal. */
  flow: 'stripe' | 'manual';
};

const METHODS: Method[] = [
  // International — Stripe-backed
  { id: 'card',     name: 'Card',         group: 'card',   hint: 'Visa · Mastercard · Amex',  emoji: '💳', color: '#00d4ff', flow: 'stripe' },
  { id: 'paypal',   name: 'PayPal',       group: 'card',   hint: 'via Stripe',                emoji: '🅿️', color: '#0070ba', flow: 'stripe' },
  { id: 'apple',    name: 'Apple Pay',    group: 'wallet', hint: 'via Stripe',                emoji: '',  color: '#ffffff', flow: 'stripe' },
  { id: 'google',   name: 'Google Pay',   group: 'wallet', hint: 'via Stripe',                emoji: 'G', color: '#fbbc04', flow: 'stripe' },
  { id: 'klarna',   name: 'Klarna',       group: 'wallet', hint: 'Pay later · via Stripe',    emoji: 'K', color: '#ffa8cd', flow: 'stripe' },

  // Local Pakistan — manual flow
  { id: 'jazzcash', name: 'JazzCash',     group: 'pk',     hint: 'Mobile wallet',  emoji: 'J', color: '#ee2526', flow: 'manual' },
  { id: 'easypaisa',name: 'EasyPaisa',    group: 'pk',     hint: 'Mobile wallet',  emoji: 'E', color: '#52ae30', flow: 'manual' },
  { id: 'nayapay',  name: 'NayaPay',      group: 'pk',     hint: 'Digital bank',   emoji: 'N', color: '#3a86ff', flow: 'manual' },
  { id: 'sadapay',  name: 'SadaPay',      group: 'pk',     hint: 'Digital bank',   emoji: 'S', color: '#ff6b35', flow: 'manual' },
  { id: 'paypak',   name: 'PayPak',       group: 'pk',     hint: '1Link domestic', emoji: 'P', color: '#00a651', flow: 'manual' },
  { id: 'bank',     name: 'Bank Transfer',group: 'pk',     hint: 'IBFT · any bank',emoji: '🏦', color: '#9ca3af', flow: 'manual' },
];

const GROUPS: { key: Method['group']; label: string }[] = [
  { key: 'card',   label: 'Cards & Online' },
  { key: 'wallet', label: 'Wallets' },
  { key: 'pk',     label: 'Pakistan — Local' },
];

// Merchant details for local PK manual flow — replace with real values in
// production. Kept here as a single source of truth for the instructions modal.
const PK_INSTRUCTIONS: Record<string, { account: string; title: string; extra?: string }> = {
  jazzcash:  { title: 'JazzCash',     account: '+92 300 0000000', extra: 'Send via JazzCash app · use plan name as reference' },
  easypaisa: { title: 'EasyPaisa',    account: '+92 345 0000000', extra: 'Send via EasyPaisa app · use plan name as reference' },
  nayapay:   { title: 'NayaPay',      account: '@neonplatform',   extra: 'Send via NayaPay handle' },
  sadapay:   { title: 'SadaPay',      account: 'PK00SADA0000000000', extra: 'IBAN transfer' },
  paypak:    { title: 'PayPak (1Link)', account: 'Visit any ATM · Bill Payment · Biller: Neon Platform', extra: 'Domestic 1Link transfer' },
  bank:      { title: 'Bank Transfer (IBFT)', account: 'Bank: Meezan · Title: Neon Platform · IBAN: PK00MEZN0000000000', extra: 'Any Pakistan bank via IBFT' },
};

export default function PaymentMethodPicker({ plan, onClose }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [pkSelection, setPkSelection] = useState<string | null>(null);

  const startStripe = async (methodId: string) => {
    setBusy(methodId);
    try {
      const res = await billing.checkout(
        plan.id,
        `${window.location.origin}/dashboard?upgraded=1`,
        `${window.location.origin}/pricing`,
      );
      window.location.href = res.checkout_url;
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Checkout failed');
      setBusy(null);
    }
  };

  // Local-PK instructions sub-modal
  if (pkSelection) {
    const cfg = PK_INSTRUCTIONS[pkSelection];
    const m = METHODS.find(x => x.id === pkSelection)!;
    const usd = (plan.price_usd_cents / 100).toFixed(0);
    return (
      <Backdrop onClose={onClose}>
        <div className="card" style={{ maxWidth: '460px', width: '100%', padding: '1.75rem', borderColor: m.color }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <Tile method={m} small />
            <div>
              <div style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.4rem', letterSpacing: '0.04em' }}>
                {cfg.title}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{m.hint}</div>
            </div>
          </div>

          <div style={{
            padding: '1rem',
            background: 'var(--bg-2)',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            marginBottom: '1rem',
          }}>
            <Row label="Plan"   value={`${plan.name}  ·  $${usd}/mo`} />
            <Row label="Send to" value={cfg.account} mono />
            <Row label="Reference" value={`PLAN-${plan.tier_key.toUpperCase()}`} mono />
            {cfg.extra && <Row label="Note" value={cfg.extra} small />}
          </div>

          <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: '1rem', lineHeight: 1.6 }}>
            Send the exact amount to the account above using <b>{cfg.title}</b>.
            Use <b>PLAN-{plan.tier_key.toUpperCase()}</b> as the payment reference.
            Once sent, email a screenshot to <a href="mailto:billing@neonplatform.com" style={{ color: 'var(--pink)' }}>billing@neonplatform.com</a> —
            your tier upgrades within one business day.
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button className="btn-ghost" onClick={() => setPkSelection(null)} style={{ padding: '0.5rem 1rem', fontSize: '0.78rem' }}>
              ← Back
            </button>
            <button
              className="btn-neon"
              style={{ padding: '0.5rem 1.1rem', fontSize: '0.78rem', background: m.color, boxShadow: `0 0 12px ${m.color}50` }}
              onClick={() => {
                window.location.href = `mailto:billing@neonplatform.com?subject=Payment Sent — PLAN-${plan.tier_key.toUpperCase()}&body=Hi, I sent payment for the ${plan.name} plan via ${cfg.title}. Reference: PLAN-${plan.tier_key.toUpperCase()}. Screenshot attached.`;
              }}
            >
              I&apos;ve Sent Payment →
            </button>
          </div>
        </div>
      </Backdrop>
    );
  }

  // Method picker
  return (
    <Backdrop onClose={onClose}>
      <div className="card" style={{ maxWidth: '760px', width: '100%', padding: '1.75rem', maxHeight: '90vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '1.25rem', gap: '1rem' }}>
          <div>
            <div style={{ fontFamily: 'Bebas Neue, sans-serif', fontSize: '1.6rem', letterSpacing: '0.05em', marginBottom: '0.2rem' }}>
              CHOOSE PAYMENT METHOD
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Upgrading to <span className="neon-pink" style={{ fontWeight: 700 }}>{plan.name}</span> · ${(plan.price_usd_cents / 100).toFixed(0)}/mo
            </div>
          </div>
          <button onClick={onClose} className="btn-ghost" style={{ padding: '0.3rem 0.7rem', fontSize: '0.7rem' }}>
            Cancel
          </button>
        </div>

        {GROUPS.map(g => {
          const items = METHODS.filter(m => m.group === g.key);
          return (
            <div key={g.key} style={{ marginBottom: '1.25rem' }}>
              <div style={{
                fontSize: '0.62rem', color: 'var(--text-muted)',
                letterSpacing: '0.15em', textTransform: 'uppercase',
                marginBottom: '0.6rem',
              }}>
                {g.label}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '0.6rem' }}>
                {items.map(m => (
                  <button
                    key={m.id}
                    disabled={busy !== null}
                    onClick={() => m.flow === 'stripe' ? startStripe(m.id) : setPkSelection(m.id)}
                    style={{
                      background: 'var(--bg-2)',
                      border: `1px solid ${m.color}40`,
                      borderRadius: '6px',
                      padding: '0.85rem 0.7rem',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'flex-start',
                      gap: '0.3rem',
                      textAlign: 'left',
                      color: 'var(--text)',
                      opacity: busy && busy !== m.id ? 0.4 : 1,
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = m.color; e.currentTarget.style.boxShadow = `0 0 10px ${m.color}30`; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = `${m.color}40`; e.currentTarget.style.boxShadow = 'none'; }}
                  >
                    <Tile method={m} />
                    {busy === m.id && (
                      <span className="status-pulse" style={{ fontSize: '0.65rem', color: m.color }}>redirecting…</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          );
        })}

        <div style={{
          marginTop: '1rem',
          padding: '0.7rem 1rem',
          background: 'rgba(255,179,0,0.06)',
          border: '1px solid rgba(255,179,0,0.2)',
          borderRadius: '6px',
          fontSize: '0.72rem',
          color: 'var(--text-dim)',
          lineHeight: 1.6,
        }}>
          <span style={{ color: '#ffb300' }}>★</span>{' '}
          International methods process instantly via secure Stripe checkout.
          Local Pakistan methods require a 1-business-day manual confirmation.
        </div>
      </div>
    </Backdrop>
  );
}

function Tile({ method, small }: { method: Method; small?: boolean }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.5rem',
      width: '100%',
    }}>
      <div style={{
        width: small ? '32px' : '28px',
        height: small ? '32px' : '28px',
        borderRadius: '6px',
        background: `${method.color}22`,
        border: `1px solid ${method.color}66`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'Bebas Neue, sans-serif',
        fontSize: small ? '1rem' : '0.85rem',
        color: method.color,
        fontWeight: 700,
        flexShrink: 0,
      }}>
        {method.emoji}
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{
          fontSize: small ? '0.85rem' : '0.78rem',
          fontWeight: 600,
          color: 'var(--text)',
          letterSpacing: '0.02em',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {method.name}
        </div>
        {method.hint && (
          <div style={{
            fontSize: '0.62rem',
            color: 'var(--text-muted)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {method.hint}
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value, mono, small }: { label: string; value: string; mono?: boolean; small?: boolean }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
      gap: '1rem', padding: '0.3rem 0',
      borderBottom: '1px solid var(--border)',
    }}>
      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{label}</span>
      <span style={{
        fontSize: small ? '0.72rem' : '0.82rem',
        color: 'var(--text)',
        fontFamily: mono ? 'Space Mono, monospace' : undefined,
        textAlign: 'right',
        wordBreak: 'break-all',
      }}>
        {value}
      </span>
    </div>
  );
}

function Backdrop({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.78)',
        backdropFilter: 'blur(6px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '1.5rem',
      }}
    >
      <div onClick={e => e.stopPropagation()} style={{ width: '100%', display: 'flex', justifyContent: 'center' }}>
        {children}
      </div>
    </div>
  );
}
