'use client';
import { useState, useRef, DragEvent, ChangeEvent } from 'react';
import { jobs } from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function UploadForm() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [file, setFile]           = useState<File | null>(null);
  const [dragOver, setDragOver]   = useState(false);
  const [width, setWidth]         = useState('');
  const [height, setHeight]       = useState('');
  const [format, setFormat]       = useState('');
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');

  const accept = (f: File) => {
    if (!f.type.match(/image\//) && !f.name.match(/\.(svg|cdr)$/i)) {
      setError('Supported: PNG, JPG, SVG, CDR');
      return;
    }
    setFile(f);
    setError('');
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) accept(f);
  };

  const onFile = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) accept(f);
  };

  const submit = async () => {
    if (!file) { setError('Select an image first'); return; }
    const w = parseFloat(width);
    if (!w || w <= 0) { setError('Enter sign width in inches'); return; }

    setLoading(true);
    setError('');
    try {
      const form = new FormData();
      form.append('image', file);
      form.append('width_inches', String(w));
      if (height) form.append('height_inches', height);
      if (format) form.append('force_format', format);

      const res = await jobs.create(form);
      router.push(`/jobs/${res.job_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed');
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Drop zone */}
      <div
        className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
        style={{ padding: '3rem 2rem', textAlign: 'center' }}
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <input ref={fileRef} type="file" accept="image/*,.svg,.cdr" style={{ display: 'none' }} onChange={onFile} />

        {file ? (
          <div>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🖼</div>
            <div style={{ color: 'var(--text)', fontWeight: 600, marginBottom: '0.25rem' }}>{file.name}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              {(file.size / 1024).toFixed(0)} KB — click to change
            </div>
          </div>
        ) : (
          <div>
            <div style={{
              fontFamily: 'Bebas Neue, sans-serif',
              fontSize: '1.6rem',
              letterSpacing: '0.1em',
              color: 'var(--text-dim)',
              marginBottom: '0.5rem',
            }}>
              DROP SIGN IMAGE HERE
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
              PNG · JPG · SVG · CDR — or click to browse
            </div>
          </div>
        )}
      </div>

      {/* Measurement inputs */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.4rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            Width (inches) *
          </label>
          <input
            className="input-neon"
            type="number"
            min="0"
            step="0.5"
            placeholder="e.g. 24"
            value={width}
            onChange={e => setWidth(e.target.value)}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.4rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            Height (inches)
          </label>
          <input
            className="input-neon"
            type="number"
            min="0"
            step="0.5"
            placeholder="optional"
            value={height}
            onChange={e => setHeight(e.target.value)}
          />
        </div>
      </div>

      {/* Force format */}
      <div>
        <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.4rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Image Type (auto-detect if blank)
        </label>
        <select
          className="input-neon"
          value={format}
          onChange={e => setFormat(e.target.value)}
          style={{ cursor: 'pointer' }}
        >
          <option value="">Auto-detect</option>
          <option value="bw">Black &amp; White</option>
          <option value="transparent">Transparent</option>
          <option value="colored">Colored / Glow</option>
        </select>
      </div>

      {error && (
        <div style={{ color: 'var(--red)', fontSize: '0.82rem', fontFamily: 'Space Mono, monospace' }}>
          ⚠ {error}
        </div>
      )}

      <button className="btn-neon" onClick={submit} disabled={loading} style={{ width: '100%', padding: '0.85rem' }}>
        {loading ? (
          <span className="status-pulse">MEASURING…</span>
        ) : (
          'MEASURE SIGN →'
        )}
      </button>
    </div>
  );
}
