/**
 * Feedback / ratings client.
 *
 * Today: localStorage only. No backend persistence.
 * Tomorrow: swap getDistribution() / submitFeedback() to real API calls
 *           — rest of the codebase stays unchanged.
 */

export interface RatingDistribution {
  /** Counts indexed by star rating: [0★, 1★, 2★, 3★, 4★, 5★]. Index 0 unused. */
  counts: [number, number, number, number, number, number];
  total: number;
  average: number;
}

export interface JobFeedback {
  jobId: string;
  rating: number;     // 1..5
  comment: string;
  submittedAt: string; // ISO
}

export interface Testimonial {
  rating: number;
  text: string;
  author: string;
  role: string;
}

// ─── Mocked aggregate (driven by client-supplied target distribution) ────────
// Distribution: 80% 5★ / 10% 4★ / 0% 3★ / 5% 2★ / 5% 1★
const MOCK_PCT = [0, 0.05, 0.05, 0.0, 0.10, 0.80] as const;
const MOCK_TOTAL = 0; // 0 → "no real reviews yet" — bars show distribution shape only

export function getDistribution(): RatingDistribution {
  // counts[i] = round(MOCK_PCT[i] * fakeBase). fakeBase chosen so star ratios round cleanly.
  const fakeBase = 200;
  const counts: RatingDistribution['counts'] = [
    0,
    Math.round(MOCK_PCT[1] * fakeBase),
    Math.round(MOCK_PCT[2] * fakeBase),
    Math.round(MOCK_PCT[3] * fakeBase),
    Math.round(MOCK_PCT[4] * fakeBase),
    Math.round(MOCK_PCT[5] * fakeBase),
  ];
  // Average from percentages (independent of fakeBase) — clean math
  const average =
    1 * MOCK_PCT[1] + 2 * MOCK_PCT[2] + 3 * MOCK_PCT[3] +
    4 * MOCK_PCT[4] + 5 * MOCK_PCT[5];

  return { counts, total: MOCK_TOTAL, average };
}

export function getDistributionPercents(): [number, number, number, number, number, number] {
  return [0, MOCK_PCT[1] * 100, MOCK_PCT[2] * 100, MOCK_PCT[3] * 100, MOCK_PCT[4] * 100, MOCK_PCT[5] * 100];
}

// ─── Per-job feedback (localStorage) ─────────────────────────────────────────
const KEY = 'neon_job_feedback_v1';

function readAll(): Record<string, JobFeedback> {
  if (typeof window === 'undefined') return {};
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}');
  } catch {
    return {};
  }
}

export function getFeedback(jobId: string): JobFeedback | null {
  return readAll()[jobId] ?? null;
}

export function submitFeedback(jobId: string, rating: number, comment: string): JobFeedback {
  const all = readAll();
  const fb: JobFeedback = {
    jobId,
    rating,
    comment: comment.trim(),
    submittedAt: new Date().toISOString(),
  };
  all[jobId] = fb;
  if (typeof window !== 'undefined') {
    localStorage.setItem(KEY, JSON.stringify(all));
  }
  return fb;
}

// ─── Empty testimonials list (real reviews land here later) ──────────────────
export function getTestimonials(): Testimonial[] {
  return [];
}
