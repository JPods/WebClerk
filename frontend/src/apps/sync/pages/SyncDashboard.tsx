/**
 * Sync App Dashboard — hub for connections, bundles, and data conversion.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '@/api/axios';
import { getUI } from '@/utils/contactUI';

type Counts = Record<string, number>;

const MODEL_LINKS: { label: string; model: string; description: string }[] = [
  { label: 'Connections', model: 'sync.Connection', description: 'API, SFTP, internal, and webhook connections' },
  { label: 'Bundles', model: 'sync.Bundle', description: 'Inbound and outbound data exchanges' },
  { label: 'Conversion Projects', model: 'conversion.ConversionProject', description: 'Data conversion pipelines (Alice + Claude)' },
];

const TOOLS: { label: string; path: string; description: string }[] = [
  { label: 'JSON Tree', path: '/json-tree', description: 'View, edit, and post JSON bundles' },
  { label: 'databrowser', path: '/databrowser', description: 'Browse and edit any model' },
];

const STAT_MODELS = ['sync.Connection', 'sync.Bundle'];

export default function SyncDashboard() {
  const active = getUI<string>('theme.active', 'dark');
  const baseFontSize = getUI<number>(`theme.${active}.font.size`, 13);
  const navigate = useNavigate();
  const [counts, setCounts] = useState<Counts>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all(
      STAT_MODELS.map(m =>
        apiClient.get(`/wcapi/get/?model_name=${m}&limit=1`)
          .then(r => [m, r.data?.data?.total ?? 0] as [string, number])
          .catch(() => [m, 0] as [string, number])
      )
    ).then(pairs => {
      setCounts(Object.fromEntries(pairs));
      setLoading(false);
    });
  }, []);

  const goDb = (model: string) => navigate(`/${model}`);

  return (
    <div data-wc="sync-dashboard" style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      <h1 style={{ fontSize: baseFontSize + 9, fontWeight: 700, marginBottom: 4 }}>Sync &amp; Integration</h1>
      <p style={{ fontSize: baseFontSize, color: 'var(--db-text-muted)', marginBottom: 24 }}>
        Connections, bundles, data conversion, and external system integration.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 28 }}>
        {STAT_MODELS.map(m => {
          const label = m.split('.').pop() || m;
          return (
            <div key={m} onClick={() => goDb(m)}
              style={{ background: 'var(--db-surface-alt)', borderRadius: 8, padding: '14px 16px', cursor: 'pointer', transition: 'background 150ms' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--db-border)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'var(--db-surface-alt)')}>
              <div style={{ fontSize: baseFontSize + 11, fontWeight: 700 }}>{loading ? '...' : (counts[m] ?? 0).toLocaleString()}</div>
              <div style={{ fontSize: baseFontSize - 1, color: 'var(--db-text-muted)' }}>{label}s</div>
            </div>
          );
        })}
      </div>

      <h2 style={{ fontSize: baseFontSize + 2, fontWeight: 600, marginBottom: 10, borderBottom: '1px solid var(--db-border)', paddingBottom: 6 }}>Tools</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12, marginBottom: 28 }}>
        {TOOLS.map(t => (
          <div key={t.label} onClick={() => navigate(t.path)}
            style={{ border: '1px solid var(--db-border)', borderRadius: 8, padding: '14px 16px', cursor: 'pointer', transition: 'border-color 150ms' }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#60a5fa')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--db-border)')}>
            <div style={{ fontSize: baseFontSize + 1, fontWeight: 600 }}>{t.label}</div>
            <div style={{ fontSize: baseFontSize - 1, color: 'var(--db-text-muted)', marginTop: 2 }}>{t.description}</div>
          </div>
        ))}
      </div>

      <h2 style={{ fontSize: baseFontSize + 2, fontWeight: 600, marginBottom: 10, borderBottom: '1px solid var(--db-border)', paddingBottom: 6 }}>Data</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
        {MODEL_LINKS.map(m => (
          <div key={m.model} onClick={() => goDb(m.model)}
            style={{ border: '1px solid var(--db-border)', borderRadius: 8, padding: '12px 16px', cursor: 'pointer', transition: 'border-color 150ms' }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#60a5fa')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--db-border)')}>
            <div style={{ fontSize: baseFontSize + 1, fontWeight: 600 }}>{m.label}</div>
            <div style={{ fontSize: baseFontSize - 1, color: 'var(--db-text-muted)', marginTop: 2 }}>{m.description}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
