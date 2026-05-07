'use client';
import { jsPDF } from 'jspdf';
import type { Job } from '@/lib/types';
import { TIER_CONFIG } from '@/lib/types';

interface Props {
  job: Job;
}

/**
 * Generates a branded PDF spec sheet for a completed measurement job.
 * Pure client-side — no backend involvement.
 */
export default function DownloadReceipt({ job }: Props) {
  if (job.status !== 'done' || job.measured_m == null) return null;
  const measuredM = job.measured_m; // type narrowing held in closure

  const onClick = () => {
    const doc = new jsPDF({ unit: 'mm', format: 'a4' });
    const W = doc.internal.pageSize.getWidth();   // ~210
    const M = 18;                                  // page margin
    let y = M;

    const pink   = [255, 45, 120] as const;
    const cyan   = [0, 212, 255] as const;
    const green  = [0, 200, 130] as const;
    const dark   = [25, 25, 35] as const;
    const muted  = [120, 120, 130] as const;

    // ─── Header bar ─────────────────────────────────────────────────────────
    doc.setFillColor(...dark);
    doc.rect(0, 0, W, 22, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(16);
    doc.text('NEON', M, 14);
    doc.setTextColor(...pink);
    doc.text('PLATFORM', M + 18, 14);
    doc.setTextColor(180, 180, 200);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.text('MEASUREMENT  ·  SPEC  SHEET', W - M, 14, { align: 'right' });
    y = 32;

    // ─── Job info row ───────────────────────────────────────────────────────
    doc.setTextColor(...muted);
    doc.setFontSize(8);
    doc.text('JOB ID', M, y);
    doc.text('CREATED', M + 70, y);
    doc.text('STATUS', W - M - 30, y);

    doc.setTextColor(40, 40, 50);
    doc.setFontSize(10);
    doc.setFont('courier', 'normal');
    doc.text(job.id.slice(0, 16) + '…', M, y + 5);
    doc.text(new Date(job.created_at).toLocaleString(), M + 70, y + 5);
    doc.setTextColor(...green);
    doc.setFont('helvetica', 'bold');
    doc.text(job.status.toUpperCase(), W - M - 30, y + 5);
    y += 16;

    // ─── Filename ───────────────────────────────────────────────────────────
    doc.setTextColor(...muted);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.text('FILENAME', M, y);
    doc.setTextColor(40, 40, 50);
    doc.setFontSize(11);
    doc.text(job.filename || 'measurement.png', M, y + 5);
    y += 14;

    // ─── Hero box: LOC + Price ──────────────────────────────────────────────
    const heroH = 38;
    doc.setDrawColor(...pink);
    doc.setLineWidth(0.4);
    doc.roundedRect(M, y, W - 2 * M, heroH, 2, 2, 'S');

    // LOC left
    doc.setTextColor(...muted);
    doc.setFontSize(8);
    doc.text('TUBE LENGTH (LOC)', M + 5, y + 7);
    doc.setTextColor(...dark);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(28);
    doc.text(`${measuredM.toFixed(2)} m`, M + 5, y + 22);
    if (job.loc_low_m != null && job.loc_high_m != null) {
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(...muted);
      doc.text(`range: ${job.loc_low_m.toFixed(2)} – ${job.loc_high_m.toFixed(2)} m`, M + 5, y + 30);
    }

    // Price right — single breakeven total
    if (job.estimated_price != null) {
      const total = job.total_price ?? (job.estimated_price + (job.shipping_cost ?? 0));
      doc.setTextColor(...muted);
      doc.setFontSize(8);
      doc.text('BREAKEVEN PRICE', W - M - 5, y + 7, { align: 'right' });
      doc.setTextColor(...green);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(28);
      doc.text(`$${total.toFixed(2)}`, W - M - 5, y + 22, { align: 'right' });
    }
    y += heroH + 10;

    // ─── Tier band ──────────────────────────────────────────────────────────
    if (job.tier_result) {
      const cfg = TIER_CONFIG[job.tier_result as keyof typeof TIER_CONFIG];
      if (cfg) {
        const hex = cfg.color.replace('#', '');
        const r = parseInt(hex.slice(0, 2), 16);
        const g = parseInt(hex.slice(2, 4), 16);
        const b = parseInt(hex.slice(4, 6), 16);
        doc.setFillColor(r, g, b);
        doc.rect(M, y, 4, 12, 'F');
        doc.setTextColor(...muted);
        doc.setFontSize(8);
        doc.text('TIER RESULT', M + 8, y + 5);
        doc.setTextColor(r, g, b);
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(13);
        doc.text(cfg.label.toUpperCase(), M + 8, y + 11);
        doc.setTextColor(...muted);
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(8);
        doc.text(cfg.desc, W - M - 5, y + 8, { align: 'right' });
        y += 18;
      }
    }

    // ─── Specs grid ─────────────────────────────────────────────────────────
    const fmt = (v: number | null | undefined, d = 2, u = '') =>
      v == null ? '—' : `${v.toFixed(d)}${u ? ' ' + u : ''}`;

    const cells: { label: string; value: string }[] = [
      { label: 'SIGN WIDTH',     value: `${job.width_inches}"` },
      { label: 'TUBE OD',        value: fmt(job.tube_width_mm, 1, 'mm') },
      { label: 'PIXELS / INCH',  value: fmt(job.px_per_inch, 1) },
      { label: 'AREA EST.',      value: fmt(job.area_m, 2, 'm') },
      { label: 'CONFIDENCE',     value: job.confidence != null ? `${(job.confidence * 100).toFixed(0)}%` : '—' },
      { label: 'OVERCOUNT',      value: fmt(job.overcount_ratio, 2) },
      { label: 'PATHS',          value: String(job.n_paths ?? '—') },
      { label: 'STRAIGHT SEGS',  value: String(job.n_straight_segs ?? '—') },
      { label: 'ARC SEGS',       value: String(job.n_arc_segs ?? '—') },
      { label: 'FREEFORM SEGS',  value: String(job.n_freeform_segs ?? '—') },
      { label: 'PHYSICS CHECK',  value: job.physics_ok == null ? '—' : (job.physics_ok ? 'OK' : 'WARN') },
      { label: 'ELAPSED',        value: fmt(job.elapsed_s, 1, 's') },
    ];

    doc.setTextColor(...dark);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.text('MEASUREMENT DETAILS', M, y);
    doc.setDrawColor(220, 220, 230);
    doc.line(M, y + 1.5, W - M, y + 1.5);
    y += 6;

    const cols  = 4;
    const cellW = (W - 2 * M) / cols;
    const cellH = 14;
    cells.forEach((c, i) => {
      const cx = M + (i % cols) * cellW;
      const cy = y + Math.floor(i / cols) * cellH;
      doc.setTextColor(...muted);
      doc.setFontSize(7);
      doc.setFont('helvetica', 'normal');
      doc.text(c.label, cx + 2, cy + 4);
      doc.setTextColor(...dark);
      doc.setFontSize(10);
      doc.setFont('courier', 'bold');
      doc.text(c.value, cx + 2, cy + 10);
    });
    y += Math.ceil(cells.length / cols) * cellH + 6;

    // ─── Reasoning ──────────────────────────────────────────────────────────
    if (job.reasoning && job.reasoning.length) {
      doc.setTextColor(...dark);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9);
      doc.text('PIPELINE REASONING', M, y);
      doc.setDrawColor(220, 220, 230);
      doc.line(M, y + 1.5, W - M, y + 1.5);
      y += 6;

      doc.setTextColor(60, 60, 70);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8.5);
      job.reasoning.forEach((r, i) => {
        const lines = doc.splitTextToSize(`${String(i + 1).padStart(2, '0')}. ${r}`, W - 2 * M - 4);
        if (y + lines.length * 4 > 280) {
          doc.addPage();
          y = M;
        }
        doc.text(lines, M, y);
        y += lines.length * 4 + 1;
      });
    }

    // ─── Footer on every page ──────────────────────────────────────────────
    const totalPages = doc.getNumberOfPages();
    for (let p = 1; p <= totalPages; p++) {
      doc.setPage(p);
      doc.setDrawColor(...cyan);
      doc.setLineWidth(0.3);
      doc.line(M, 285, W - M, 285);
      doc.setTextColor(...muted);
      doc.setFontSize(7);
      doc.setFont('helvetica', 'normal');
      doc.text('NEON PLATFORM  ·  Neon Precision Studio  ·  AI-powered LOC measurement', M, 290);
      doc.text(`page ${p} / ${totalPages}`, W - M, 290, { align: 'right' });
    }

    doc.save(`neon_spec_${job.id.slice(0, 8)}.pdf`);
  };

  return (
    <button
      onClick={onClick}
      className="btn-ghost"
      style={{
        padding: '0.55rem 1.1rem',
        fontSize: '0.78rem',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.4rem',
      }}
      title="Download branded PDF spec sheet"
    >
      <span style={{ color: '#ffb300' }}>⬇</span> Download Spec Sheet (PDF)
    </button>
  );
}
