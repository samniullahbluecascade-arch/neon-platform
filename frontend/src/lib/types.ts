export interface User {
  id: string;
  email: string;
  full_name: string;
  company: string;
  avatar_url: string;
  tier: 'free' | 'starter' | 'business' | 'enterprise';
  jobs_used_this_month: number;
  jobs_remaining: number;
  tier_limits: { jobs_per_month: number; max_width_px: number; ml_correction: boolean };
  api_key: string;
  email_verified: boolean;
  created_at: string;
}

export interface Job {
  id: string;
  status: 'pending' | 'processing' | 'done' | 'failed';
  filename: string;
  width_inches: number;
  height_inches: number | null;
  measured_m: number | null;
  tier_result: 'GLASS_CUT' | 'QUOTE' | 'ESTIMATE' | 'MARGINAL' | 'FAIL' | null;
  confidence: number | null;
  tube_width_mm: number | null;
  px_per_inch: number | null;
  loc_low_m: number | null;
  loc_high_m: number | null;
  area_m: number | null;
  overcount_ratio: number | null;
  n_paths: number | null;
  n_straight_segs: number | null;
  n_arc_segs: number | null;
  n_freeform_segs: number | null;
  error_pct: number | null;
  elapsed_s: number | null;
  reasoning: string[];
  physics_ok: boolean | null;
  input_format: string;
  estimated_price: number | null;
  error_message: string;
  overlay_b64: string | null;
  ridge_b64: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface Plan {
  id: number;
  name: string;
  tier_key: string;
  stripe_price_id: string;
  price_usd_cents: number;
  jobs_per_month: number;
  ml_correction: boolean;
  max_width_px: number;
  description: string;
  sort_order: number;
}

export const TIER_CONFIG = {
  GLASS_CUT: { color: '#00ff9d', label: 'Glass Cut',  desc: '≤5% error — cut-ready' },
  QUOTE:     { color: '#00d4ff', label: 'Quote',      desc: '≤10% error — quote-ready' },
  ESTIMATE:  { color: '#ffb300', label: 'Estimate',   desc: '≤20% error' },
  MARGINAL:  { color: '#ff8c00', label: 'Marginal',   desc: '≤35% error' },
  FAIL:      { color: '#ff3b3b', label: 'Failed',     desc: '>35% error' },
} as const;
