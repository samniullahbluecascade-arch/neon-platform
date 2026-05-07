import { TIER_CONFIG } from '@/lib/types';

interface Props {
  tier: keyof typeof TIER_CONFIG | string | null;
  size?: 'sm' | 'lg';
}

export default function TierBadge({ tier, size = 'sm' }: Props) {
  if (!tier) return null;
  const cfg = TIER_CONFIG[tier as keyof typeof TIER_CONFIG];
  if (!cfg) return null;

  return (
    <span
      className="badge"
      title={cfg.desc}
      style={{
        color: cfg.color,
        border: `1px solid ${cfg.color}`,
        background: `${cfg.color}18`,
        fontSize: size === 'lg' ? '0.8rem' : '0.65rem',
        padding: size === 'lg' ? '0.3rem 0.8rem' : '0.2rem 0.6rem',
        boxShadow: `0 0 8px ${cfg.color}40`,
      }}
    >
      {cfg.label}
    </span>
  );
}
