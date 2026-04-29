import type { User, Job, Plan } from './types';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

function token(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

async function tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem('refresh_token');
  if (!refresh) return false;
  try {
    const r = await fetch(`${BASE}/api/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });
    if (!r.ok) return false;
    const d = await r.json();
    localStorage.setItem('access_token', d.access);
    if (d.refresh) localStorage.setItem('refresh_token', d.refresh);
    return true;
  } catch {
    return false;
  }
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const hdrs: Record<string, string> = { ...(init.headers as Record<string, string>) };
  const t = token();
  if (t) hdrs['Authorization'] = `Bearer ${t}`;
  if (!(init.body instanceof FormData)) hdrs['Content-Type'] = 'application/json';
  // Skip ngrok browser interstitial on free tier
  hdrs['ngrok-skip-browser-warning'] = 'true';

  let r = await fetch(`${BASE}${path}`, { ...init, headers: hdrs });

  if (r.status === 401) {
    const ok = await tryRefresh();
    if (ok) {
      hdrs['Authorization'] = `Bearer ${localStorage.getItem('access_token')}`;
      r = await fetch(`${BASE}${path}`, { ...init, headers: hdrs });
    } else {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
      throw new Error('Session expired');
    }
  }

  if (!r.ok) {
    const err = await r.json().catch(() => ({ error: r.statusText }));
    throw new Error(err.error ?? err.detail ?? 'Request failed');
  }
  if (r.status === 204) return {} as T;
  return r.json();
}

export const auth = {
  register: (email: string, password: string, password2: string) =>
    req<{ message: string; id: string }>('/api/auth/register/', {
      method: 'POST',
      body: JSON.stringify({ email, password, password2 }),
    }),

  login: async (email: string, password: string) => {
    const d = await req<{ access: string; refresh: string }>('/api/auth/token/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem('access_token', d.access);
    localStorage.setItem('refresh_token', d.refresh);
    return d;
  },

  logout: async () => {
    const refresh = localStorage.getItem('refresh_token');
    await req('/api/auth/logout/', {
      method: 'POST',
      body: JSON.stringify({ refresh }),
    }).catch(() => {});
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  me:           () => req<User>('/api/auth/profile/'),
  update:       (data: Partial<User>) =>
    req<User>('/api/auth/profile/', { method: 'PATCH', body: JSON.stringify(data) }),
  rotateApiKey: () =>
    req<{ api_key: string }>('/api/auth/api-key/rotate/', { method: 'POST' }),
};

export const jobs = {
  list:   (status?: string) =>
    req<Job[]>(`/api/jobs/${status ? `?status=${status}` : ''}`),
  get:    (id: string) => req<Job>(`/api/jobs/${id}/`),
  create: (form: FormData) =>
    req<{ job_id: string; status: string; message: string }>('/api/jobs/create/', {
      method: 'POST',
      body: form,
    }),
};

export interface MeasurementResult {
  measured_m: number;
  tier: string;
  confidence: number;
  px_per_inch: number;
  tube_width_mm: number;
  gt_m: number | null;
  error_pct: number | null;
  n_paths: number;
  n_straight_segs: number;
  n_arc_segs: number;
  n_freeform_segs: number;
  physics_ok: boolean;
  reasoning: string[];
  source: string;
  elapsed_s: number;
  input_format: string;
  loc_low_m: number;
  loc_high_m: number;
  area_m: number;
  overcount_ratio: number;
  overcount_risk: number;
  bias_direction: string;
  tube_cv: number;
  tube_width_uncertain: boolean;
  overlay_b64: string;
  ridge_b64: string;
}

export const studio = {
  generateMockup: (form: FormData) =>
    req<{ image_b64: string }>('/api/generate_mockup/', { method: 'POST', body: form }),
  generateBw: (form: FormData) =>
    req<{ image_b64: string }>('/api/generate_bw/', { method: 'POST', body: form }),
  fullPipeline: (form: FormData) =>
    req<{ mockup_b64: string; bw_b64: string; measurement: MeasurementResult }>(
      '/api/full_pipeline/', { method: 'POST', body: form }),
  bwOnlyPipeline: (form: FormData) =>
    req<{ bw_b64: string; measurement: MeasurementResult }>(
      '/api/bw_only_pipeline/', { method: 'POST', body: form }),
  measure: (form: FormData) =>
    req<MeasurementResult>('/api/measure/', { method: 'POST', body: form }),
};

export const billing = {
  plans:    () => req<Plan[]>('/api/billing/plans/'),
  checkout: (plan_id: number, success_url?: string, cancel_url?: string) =>
    req<{ checkout_url: string }>('/api/billing/checkout/', {
      method: 'POST',
      body: JSON.stringify({ plan_id, success_url, cancel_url }),
    }),
  cancel:  () =>
    req<{ message: string; cancel_at: number }>('/api/billing/cancel/', { method: 'POST' }),
  portal:  (return_url?: string) =>
    req<{ portal_url: string }>('/api/billing/portal/', {
      method: 'POST',
      body: JSON.stringify({ return_url }),
    }),
};

export function mediaUrl(path: string | null): string | null {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  return `${BASE}${path}`;
}
