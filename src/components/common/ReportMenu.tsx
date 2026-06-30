/**
 * ReportMenu — dropdown menu of available reports for a given model + record.
 *
 * Fetches Report records from wcapi where model_name matches.
 * Groups by category. Click opens the report (print route or future handler).
 *
 * Usage:
 *   <ReportMenu modelName="invoice" recordId={42} />
 *   <ReportMenu modelName="order" recordId={15} />
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getRecords } from '@/api/wcapi';

interface ReportRecord {
  id: number;
  name: string;
  description: string;
  output_type: string;
  category: string;
  sort_order: number;
  data: { template?: string; route?: string; [k: string]: unknown };
}

interface ReportMenuProps {
  modelName: string;
  recordId: number | string;
  parentModel?: string; // for QA reports — the parent model
}

const CATEGORY_LABELS: Record<string, string> = {
  report: 'Reports',
  statement: 'Statements',
  list: 'Lists',
  summary: 'Summaries',
  letter: 'Letters & Email',
  label: 'Labels',
  export: 'Exports',
  utility: 'Utilities',
};

const OUTPUT_ICONS: Record<string, string> = {
  print: '🖨',
  email: '✉',
  export: '📊',
  label: '🏷',
  json: '{}',
  api: '→',
  merge: '📄',
};

export default function ReportMenu({ modelName, recordId, parentModel }: ReportMenuProps) {
  const navigate = useNavigate();
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [open, setOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Fetch reports for this model
  useEffect(() => {
    if (loaded || !modelName) return;
    (async () => {
      try {
        const res = await getRecords('report', { model_name: modelName, ordering: 'sort_order' }) as any;
        setReports((res?.results || []) as ReportRecord[]);
      } catch { /* no reports available */ }
      setLoaded(true);
    })();
  }, [modelName, loaded]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Group by category
  const grouped = useMemo(() => {
    const groups: Record<string, ReportRecord[]> = {};
    reports.forEach((r) => {
      const cat = r.category || 'report';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(r);
    });
    return groups;
  }, [reports]);

  const handleSelect = useCallback((report: ReportRecord) => {
    setOpen(false);
    const route = report.data?.route;
    if (route) {
      // Replace {id}, {parent_model}, {parent_id} placeholders
      const resolved = route
        .replace('{id}', String(recordId))
        .replace('{parent_model}', parentModel || modelName)
        .replace('{parent_id}', String(recordId));
      navigate(resolved);
      return;
    }
    // Fallback — alert with report info (templates not yet built)
    alert(`Report: ${report.name}\nTemplate: ${report.data?.template || 'not configured'}\nOutput: ${report.output_type}\n\nThis report template is not yet built.`);
  }, [recordId, parentModel, modelName, navigate]);

  if (!reports.length) return null;

  return (
    <div ref={menuRef} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors"
      >
        🖨 Reports
        <span className="text-[10px] text-gray-400">({reports.length})</span>
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, zIndex: 50, marginTop: 4,
          background: 'white', border: '1px solid #ddd', borderRadius: 8,
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)', width: 320, maxHeight: 400,
          overflowY: 'auto',
        }}
          className="dark:bg-gray-800 dark:border-gray-700"
        >
          <div style={{ padding: '8px 12px', borderBottom: '1px solid #eee', fontSize: 12, fontWeight: 700, color: '#666' }}
            className="dark:border-gray-700 dark:text-gray-400">
            Reports for {modelName}
          </div>
          {Object.entries(grouped).map(([cat, items]) => (
            <div key={cat}>
              <div style={{ padding: '6px 12px', fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.06em', background: '#f8f9fa' }}
                className="dark:bg-gray-900 dark:text-gray-500">
                {CATEGORY_LABELS[cat] || cat}
              </div>
              {items.map((r) => (
                <button
                  key={r.id}
                  onClick={() => handleSelect(r)}
                  style={{ display: 'flex', alignItems: 'flex-start', gap: 8, width: '100%', padding: '8px 12px', border: 'none', background: 'transparent', cursor: 'pointer', textAlign: 'left', fontSize: 12 }}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>{OUTPUT_ICONS[r.output_type] || '📋'}</span>
                  <div>
                    <div style={{ fontWeight: 600, color: '#333' }} className="dark:text-gray-200">{r.name}</div>
                    {r.description && <div style={{ fontSize: 11, color: '#888', marginTop: 2 }} className="dark:text-gray-500">{r.description}</div>}
                  </div>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
