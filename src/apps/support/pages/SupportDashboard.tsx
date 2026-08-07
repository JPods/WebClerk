/**
 * Support & Accounting Dashboard — combined hub.
 *
 * Operations: actions, quality, documents, settings, connections, bundles.
 * Accounting: journal status, GL balance, aging, pending inventory.
 * Tools: Kanban, Gantt, JSON Tree.
 */
import React, { useEffect, useState, lazy, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '@/api/axios';

const AccountingDashboard = lazy(() => import('@/pages/admin/AccountingDashboard'));

type Counts = Record<string, number>;

const MODEL_LINKS: { label: string; model: string; description: string }[] = [
  { label: 'Actions', model: 'action', description: 'Tasks, to-dos, follow-ups, and assignments' },
  { label: 'Quality', model: 'support.Quality', description: 'Inspections, NCRs, corrective actions' },
  { label: 'Documents', model: 'docs.Document', description: 'Files, attachments, and templates' },
  { label: 'Settings', model: 'setting', description: 'System and user configuration' },
  { label: 'Reports', model: 'core.Report', description: 'Output forms and report templates' },
  { label: 'Connections', model: 'sync.Connection', description: 'API, SFTP, internal, and webhook connections' },
  { label: 'Bundles', model: 'sync.Bundle', description: 'Inbound and outbound data exchanges' },
  { label: 'Conversion Projects', model: 'conversion.ConversionProject', description: 'Data conversion pipelines (Alice + Claude)' },
];

const TOOLS: { label: string; path: string; description: string }[] = [
  { label: 'Kanban', path: '/kanban', description: 'Visual task board' },
  { label: 'Gantt', path: '/gantt', description: 'Project timeline view' },
  { label: 'JSON Tree', path: '/json-tree', description: 'View, edit, and post JSON bundles' },
];

const STAT_MODELS = ['action', 'docs.Document', 'setting', 'sync.Connection', 'sync.Bundle'];

export default function SupportDashboard() {
  const navigate = useNavigate();
  const [counts, setCounts] = useState<Counts>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all(
      STAT_MODELS.map(m =>
        apiClient.get(`/wcapi/get/?model_name=${m}&limit=1`)
          .then(r => [m, r.data?.data?.total ?? r.data?.data?.count ?? 0] as [string, number])
          .catch(() => [m, 0] as [string, number])
      )
    ).then(pairs => {
      setCounts(Object.fromEntries(pairs));
      setLoading(false);
    });
  }, []);

  const goDb = (model: string) => navigate(`/${model}`);

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Support &amp; Accounting</h1>
      <p style={{ fontSize: 13, color: '#64748b', marginBottom: 24 }}>
        Actions, quality, documents, settings, reports, and financial health.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 28 }}>
        {STAT_MODELS.map(m => {
          const label = m.split('.').pop() || m;
          return (
            <div key={m} onClick={() => goDb(m)}
              style={{ background: '#f1f5f9', borderRadius: 8, padding: '14px 16px', cursor: 'pointer', transition: 'background 150ms' }}
              onMouseEnter={e => (e.currentTarget.style.background = '#e2e8f0')}
              onMouseLeave={e => (e.currentTarget.style.background = '#f1f5f9')}>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{loading ? '...' : (counts[m] ?? 0).toLocaleString()}</div>
              <div style={{ fontSize: 12, color: '#64748b' }}>{label.charAt(0).toUpperCase() + label.slice(1)}s</div>
            </div>
          );
        })}
      </div>

      <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10, borderBottom: '1px solid #e2e8f0', paddingBottom: 6 }}>Tools</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12, marginBottom: 28 }}>
        {TOOLS.map(t => (
          <div key={t.label} onClick={() => navigate(t.path)}
            style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: '14px 16px', cursor: 'pointer', transition: 'border-color 150ms' }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#60a5fa')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = '#e2e8f0')}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{t.label}</div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{t.description}</div>
          </div>
        ))}
      </div>

      <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10, borderBottom: '1px solid #e2e8f0', paddingBottom: 6 }}>Data</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
        {MODEL_LINKS.map(m => (
          <div key={m.model} onClick={() => goDb(m.model)}
            style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: '12px 16px', cursor: 'pointer', transition: 'border-color 150ms' }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#60a5fa')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = '#e2e8f0')}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{m.label}</div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{m.description}</div>
          </div>
        ))}
      </div>

      <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10, marginTop: 28, borderBottom: '1px solid #e2e8f0', paddingBottom: 6 }}>Accounting</h2>
      <Suspense fallback={<div style={{ padding: 16, color: '#94a3b8', fontSize: 13 }}>Loading accounting...</div>}>
        <AccountingDashboard />
      </Suspense>
    </div>
  );
}
