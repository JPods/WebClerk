/* LastChecked: 2026-07-19 | WhereUsed: DataBrowser route | WhoCreated: Bill+Claude */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createBlankRecord } from '../../tools/createBlankRecord';
import { useAppSelector } from '../../store/hooks';
import { useDataBrowser, numId, type FieldSpec } from '../../hooks/useDataBrowser';
import { dbLog } from '../../utils/dbLog';
import { getDetailViewPref } from '../../layout/MacTopBar';
import BehaviorField from '../../components/common/BehaviorField';
import FieldOrderDialog from '../../components/common/FieldOrderDialog';
import RelatedDialog from '../../components/common/RelatedDialog';
import ReportsDialog from '../../components/common/ReportsDialog';
import DataGrid from '../../components/common/DataGrid';
import type { RowColorRule } from '../../components/common/DataGrid';
import ToolbarIcon from '../../components/common/ToolbarIcon';
import { TB } from '../../components/common/toolbarActions';
import DedupPanel from '../../components/common/DedupPanel';
import './AdminWorkbench.css';

/** Maps DataBrowser model name → .tsx detail route (used for double-click new-tab). */
const APP_DETAIL_ROUTES: Record<string, string> = {
  order: '/order',
  invoice: '/invoice',
  proposal: '/proposal',
  purchase: '/purchase',
  workorder: '/work_order',
  work_order: '/work_order',
  receipt: '/receipt',
  requisition: '/requisition',
  payment: '/payment',
  customer: '/customer',
  item: '/item',
  contact: '/contact',
  action: '/action',
};

/** Lazy-loaded detail components for App mode inline rendering in the right panel. */
const APP_DETAIL_COMPONENTS: Record<string, React.LazyExoticComponent<React.ComponentType<any>>> = {
  contact: React.lazy(() => import('@/apps/core/models/contact/pages/ContactDetail')),
  customer: React.lazy(() => import('@/apps/orgs/models/customer/pages/CustomerDetail')),
  order: React.lazy(() => import('@/apps/transactions/models/order/pages/OrderDetail')),
  invoice: React.lazy(() => import('@/apps/transactions/models/invoice/pages/InvoiceDetail')),
  proposal: React.lazy(() => import('@/apps/transactions/models/proposal/pages/ProposalDetail')),
  purchase: React.lazy(() => import('@/apps/transactions/models/purchase/pages/PurchaseDetail')),
  item: React.lazy(() => import('@/apps/products/models/item/pages/ItemDetail')),
  action: React.lazy(() => import('@/apps/core/models/action/pages/ActionDetail')),
};

// ---------------------------------------------------------------------------
// SpawnLinks — related-window buttons for complex records
// ---------------------------------------------------------------------------

const SPAWN_CONFIG: Record<string, Array<{ label: string; target: string; filterKey: string }>> = {
  serial: [
    { label: 'History', target: 'serial_log', filterKey: 'serial_id' },
    { label: 'Q&A', target: 'question_answer', filterKey: 'refs__links__serial_id' },
    { label: 'Documents', target: 'document', filterKey: 'refs__links__serial_id' },
    { label: 'Actions', target: 'action', filterKey: 'refs__links__serial_id' },
    { label: 'Customer', target: 'contact', filterKey: 'id' },
    { label: 'Vendor', target: 'contact', filterKey: 'id' },
  ],
  item: [
    { label: 'Serials', target: 'serial', filterKey: 'item_id' },
    { label: 'XRefs', target: 'item_xref', filterKey: 'item_id' },
    { label: 'Org Items', target: 'org_item', filterKey: 'item_id' },
    { label: 'Documents', target: 'document', filterKey: 'refs__links__item_id' },
  ],
  invoice: [
    { label: 'Lines', target: 'invoice_line', filterKey: 'invoice_id' },
    { label: 'Payments', target: 'payment', filterKey: 'invoice_id' },
    { label: 'Customer', target: 'contact', filterKey: 'id' },
    { label: 'Documents', target: 'document', filterKey: 'refs__links__invoice_id' },
  ],
  order: [
    { label: 'Lines', target: 'order_line', filterKey: 'order_id' },
    { label: 'Customer', target: 'contact', filterKey: 'id' },
    { label: 'Documents', target: 'document', filterKey: 'refs__links__order_id' },
  ],
  contact: [
    { label: 'Orders', target: 'order', filterKey: 'customer_id' },
    { label: 'Invoices', target: 'invoice', filterKey: 'customer_id' },
    { label: 'Payments', target: 'payment', filterKey: 'invoice__customer_id' },
    { label: 'Serials', target: 'serial', filterKey: 'refs__links__customer_id' },
    { label: 'Actions', target: 'action', filterKey: 'refs__links__contact_id' },
    { label: 'Documents', target: 'document', filterKey: 'refs__links__contact_id' },
  ],
};

// ── HarvestBar — folder input + harvest button for StatementLine ──
const HarvestBar: React.FC<{ onComplete: () => void }> = ({ onComplete }) => {
  const [folder, setFolder] = React.useState(() => localStorage.getItem('db-harvest-folder') || '');
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<any>(null);

  const handleHarvest = async () => {
    if (!folder.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch('/api/transactions/statements/harvest/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ path: folder.trim() }),
      });
      const data = await res.json();
      setResult(data);
      localStorage.setItem('db-harvest-folder', folder.trim());
      if (data.lines_loaded > 0) onComplete();
    } catch (err: any) {
      setResult({ error: err.message || 'Harvest failed' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8, padding: '4px 8px',
      background: 'var(--db-surface-alt)', borderBottom: '1px solid var(--db-border)',
      fontSize: 12,
    }}>
      <span style={{ fontWeight: 600, color: 'var(--db-text-muted)', whiteSpace: 'nowrap' }}>Harvest:</span>
      <input
        type="text"
        value={folder}
        onChange={(e) => setFolder(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') handleHarvest(); }}
        placeholder="~/Taxes/2025 or drop folder path here"
        style={{
          flex: 1, padding: '3px 8px', fontSize: 12,
          background: 'var(--db-input-bg)', color: 'var(--db-text)',
          border: '1px solid var(--db-border)', borderRadius: 4,
        }}
      />
      <button
        onClick={handleHarvest}
        disabled={loading || !folder.trim()}
        style={{
          padding: '3px 12px', fontSize: 12, fontWeight: 600,
          background: loading ? 'var(--db-border)' : '#ea580c',
          color: '#fff', border: 'none', borderRadius: 4, cursor: loading ? 'wait' : 'pointer',
          whiteSpace: 'nowrap',
        }}
      >
        {loading ? 'Harvesting...' : 'Harvest'}
      </button>
      {result && !result.error && (
        <span style={{ color: 'var(--db-text-muted)', whiteSpace: 'nowrap' }}>
          {result.lines_loaded} loaded, {result.lines_skipped} skipped
          {result.missing?.length > 0 && (
            <span style={{ color: '#ef4444', marginLeft: 8 }}>
              ⚠ Missing: {result.missing.join(', ')}
            </span>
          )}
        </span>
      )}
      {result?.error && (
        <span style={{ color: '#ef4444' }}>{result.error}</span>
      )}
    </div>
  );
};

const SpawnLinks: React.FC<{ model: string; record: any; recordId: number }> = ({ model, record, recordId }) => {
  const links = SPAWN_CONFIG[model];
  if (!links || !links.length) return null;

  const openSpawn = (link: typeof links[0]) => {
    let filterValue = recordId;
    // For customer/vendor links, resolve the ID from refs
    if (link.label === 'Customer' && link.target === 'contact') {
      const refs = record.refs || {};
      filterValue = refs?.links?.customer_id || refs?.links?.contact?.[0] || recordId;
    } else if (link.label === 'Vendor' && link.target === 'contact') {
      const refs = record.refs || {};
      filterValue = refs?.links?.vendor_id || recordId;
    }
    window.open(`/admin-wb?model=${link.target}&${link.filterKey}=${filterValue}`, '_blank');
  };

  return (
    <div className="db-spawn-bar">
      <span className="db-spawn-label">Related:</span>
      {links.map((link) => (
        <button key={link.label} className="db-btn db-btn--small db-btn--ghost"
          onClick={() => openSpawn(link)}
          title={`Open ${link.label} in new DataBrowser window`}>
          {link.label} ↗
        </button>
      ))}
    </div>
  );
};

// ---------------------------------------------------------------------------
// BOM Panel — shows when viewing an Item with BOM children
// ---------------------------------------------------------------------------

const BOM_COLUMNS = ['item_ida', 'description', 'qty_plan', 'qty_actual', 'cost_avg', 'cost_last', 'cost_extended'];

const BOMPanel: React.FC<{ itemId: number; theme: any; fontSize: number }> = ({ itemId, theme, fontSize }) => {
  const [bomData, setBomData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [costBasis, setCostBasis] = useState('avg');
  const [buildQty, setBuildQty] = useState('1');

  const fetchBom = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(`/products/items/${itemId}/bom/expand/?qty=${buildQty}&cost_basis=${costBasis}`);
      if (resp.ok) {
        const data = await resp.json();
        setBomData(data?.data || data);
      } else {
        setBomData(null);
      }
    } catch { setBomData(null); }
    setLoading(false);
  }, [itemId, costBasis, buildQty]);

  useEffect(() => { fetchBom(); }, [fetchBom]);

  if (loading) return <div className="db-status-msg">Loading BOM...</div>;
  if (!bomData?.rows?.length) return null; // No BOM — hide panel

  return (
    <div className="db-bom-panel">
      <div className="db-bom-header">
        <span className="db-bom-title">Bill of Materials</span>
        <label className="db-bom-control">
          Qty: <input type="number" min="1" value={buildQty}
            onChange={(e) => setBuildQty(e.target.value)} className="db-bom-input" />
        </label>
        <label className="db-bom-control">
          Cost:
          <select value={costBasis} onChange={(e) => setCostBasis(e.target.value)} className="db-bom-input">
            <option value="avg">Average</option>
            <option value="last">Last Receipt</option>
            <option value="min">Min (conservative)</option>
            <option value="landed">Landed</option>
          </select>
        </label>
        <span className="db-bom-total">Total: ${(bomData.total_cost || 0).toFixed(2)}</span>
        <button className="db-btn db-btn--small db-btn--ghost" onClick={() => {
          window.open(`/admin-wb?model=bill_of_material&parent_id=${itemId}`, '_blank');
        }}>Open BOM ↗</button>
      </div>
      <DataGrid
        records={bomData.rows}
        columns={BOM_COLUMNS}
        treeColumn="item_ida"
        levelField="level"
        childFlag="is_subassembly"
        theme={theme}
        fontSize={fontSize - 1}
        hideToolbar
        numId={(v: unknown) => typeof v === 'number' ? v : null}
        onRowDoubleClicked={(row: any) => {
          if (row?.is_subassembly && row?.item_id) {
            window.open(`/admin-wb?model=item&id=${row.item_id}`, '_blank');
          }
        }}
      />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Theme tokens — kept for passing to child components (DataGrid, BehaviorField)
// that still use inline styles. AdminWorkbench itself uses CSS custom properties.
// ---------------------------------------------------------------------------

const themes = {
  dark: {
    bg: '#1e1e1e', surface: '#252526', surfaceAlt: '#2d2d2d',
    border: '#3c3c3c', borderLight: '#4d4d4d',
    text: '#d4d4d4', textMuted: '#888', textDim: '#666',
    accent: '#9cdcfe', accentGreen: '#4ec98c', accentGold: '#e8c870',
    accentRed: '#e05252', accentPurple: '#c8a8e8',
    btnBg: '#2d2d2d', btnPrimary: '#0e639c', btnSave: '#1a6b2e',
    btnDanger: '#6b1a1a', btnDangerBorder: '#964040', btnSaveBorder: '#2f8f45',
    inputBg: '#2a2a2a', inputBorder: '#555',
    rowHover: '#2a2d2e', rowActive: '#094771', rowChecked: '#3a3a1a',
    resizeHandle: '#4a9eff',
  },
  light: {
    bg: '#f8f9fa', surface: '#ffffff', surfaceAlt: '#f1f3f5',
    border: '#dee2e6', borderLight: '#e9ecef',
    text: '#212529', textMuted: '#6c757d', textDim: '#adb5bd',
    accent: '#0d6efd', accentGreen: '#198754', accentGold: '#fd7e14',
    accentRed: '#dc3545', accentPurple: '#6f42c1',
    btnBg: '#ffffff', btnPrimary: '#0d6efd', btnSave: '#198754',
    btnDanger: '#dc3545', btnDangerBorder: '#dc3545', btnSaveBorder: '#157347',
    inputBg: '#ffffff', inputBorder: '#ced4da',
    rowHover: '#f1f3f5', rowActive: '#cfe2ff', rowChecked: '#fff3cd',
    resizeHandle: '#0d6efd',
  },
};

type ThemeKey = keyof typeof themes;

// ---------------------------------------------------------------------------
// Btn helper — uses CSS classes from AdminWorkbench.css
// ---------------------------------------------------------------------------

const Btn: React.FC<{
  variant?: 'default' | 'primary' | 'save' | 'danger' | 'ghost';
  small?: boolean; disabled?: boolean; title?: string;
  onClick?: (e: React.MouseEvent) => void; children: React.ReactNode;
  // Legacy: accept and ignore `t` prop for backward compat during migration
  t?: any;
}> = ({ variant = 'default', small, disabled, title, onClick, children }) => (
  <button
    className={`db-btn ${small ? 'db-btn--small' : ''} ${variant !== 'default' ? `db-btn--${variant}` : ''}`}
    disabled={disabled} title={title} onClick={onClick}>{children}</button>
);

// ---------------------------------------------------------------------------
// MatchCandidatesPanel — full detail cards for dedup/merge review
// ---------------------------------------------------------------------------

type MatchPanelProps = {
  selectedRecord: any; selectedId: number | null; selectedModel: string;
  visibleFields: string[]; fieldBehaviors: Record<string, any>;
  detailFieldSpecs: any[]; detailRowSizes: Record<string, any>;
  theme: any; fontSize: number;
  onMerged: () => void; onDeleted: () => void;
};

function MatchCandidatesPanel({
  selectedRecord, selectedId, selectedModel, visibleFields, fieldBehaviors,
  detailFieldSpecs, detailRowSizes, theme, fontSize, onMerged, onDeleted,
}: MatchPanelProps) {
  const [candidateRecords, setCandidateRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const refs = selectedRecord?.refs as any;
  const candidates = refs?.contact;
  const isRisk = refs?.import === 'risk';

  // Fetch full records for each candidate
  useEffect(() => {
    if (!candidates || !Array.isArray(candidates) || candidates.length === 0) {
      setCandidateRecords([]);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const { getRecords } = await import('@/api/wcapi');
        const ids = candidates.map((c: any) => c.contact_id).filter(Boolean);
        if (ids.length === 0) { setCandidateRecords([]); return; }
        const res = await getRecords(selectedModel, { filters: { id__in: ids } });
        if (!cancelled) setCandidateRecords(res.results || []);
      } catch { if (!cancelled) setCandidateRecords([]); }
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, [selectedId, candidates?.length]);

  if ((!candidates || candidates.length === 0) && !isRisk) return null;

  const isDark = theme === (theme?.bg ? theme : null) || true; // fallback
  const cardBg = '#1e293b';
  const cardBorder = '#334155';
  const headerColor = '#94a3b8';

  // Pick display fields — shorter list for cards (skip large JSON fields)
  const cardFields = visibleFields.filter(f =>
    !['metadata', 'refs', 'prefs', 'actions', 'comments', 'config', 'password'].includes(f)
  ).slice(0, 12);

  const doMerge = async (candidateRecord: any, matchMeta: any) => {
    if (!confirm(`Merge into "${matchMeta?.name || candidateRecord.ida}"?\nThis updates the matched contact and deletes the risk record.`)) return;
    try {
      const { saveRecord: sr, deleteRecord: dr } = await import('@/api/wcapi');
      const rec = selectedRecord!;
      const config = rec.config || {};
      const orig = config.original_mac || {};
      const update: any = { id: candidateRecord.id };
      // Fill empty fields on the target from the risk record
      if (orig.first && !candidateRecord.name_first) update.name_first = orig.first;
      if (orig.last && !candidateRecord.name_last) update.name_last = orig.last;
      if (orig.org && !candidateRecord.company) update.company = orig.org;
      if (orig.title && !candidateRecord.title) update.title = orig.title;
      if (orig.dept && !candidateRecord.department) update.department = orig.dept;
      if (orig.addresses?.length && !candidateRecord.address_full) {
        const a = orig.addresses[0];
        update.address_full = [a.street, a.city, a.state, a.zip].filter(Boolean).join(', ');
      }
      if (orig.phones?.length && !candidateRecord.phone) {
        update.phone = orig.phones[0].number;
      }
      update.config = { ...(candidateRecord.config || {}), merged_from_risk: rec.ida, original_mac: orig };
      await sr(selectedModel, update);
      await dr(selectedModel, selectedId!);
      onMerged();
    } catch (e) { alert('Merge failed: ' + (e as Error).message); }
  };

  const doDelete = async () => {
    if (!confirm('Delete this risk record?')) return;
    try {
      const { deleteRecord: dr } = await import('@/api/wcapi');
      await dr(selectedModel, selectedId!);
      onDeleted();
    } catch (e) { alert('Delete failed: ' + (e as Error).message); }
  };

  return (
    <div style={{ marginTop: 12, borderTop: `1px solid ${cardBorder}`, paddingTop: 12 }}>
      {/* Header with delete button for risk records */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: headerColor, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {candidateRecords.length > 0 ? `Possible Matches (${candidateRecords.length})` : 'No Matches Found'}
        </span>
        {isRisk && (
          <button onClick={doDelete}
            style={{ padding: '4px 12px', fontSize: 11, fontWeight: 600, background: '#991b1b', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
            title="Delete this risk record — garbage">
            Delete
          </button>
        )}
      </div>

      {loading && <div style={{ fontSize: 11, color: '#6b7280', padding: 8 }}>Loading candidates...</div>}

      {/* Candidate detail cards */}
      {candidateRecords.map((rec, idx) => {
        const matchMeta = candidates?.find((c: any) => c.contact_id === rec.id) || {};
        return (
          <div key={rec.id} style={{
            background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 6,
            padding: 10, marginBottom: 10,
          }}>
            {/* Card header with merge/view buttons */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, paddingBottom: 6, borderBottom: `1px solid ${cardBorder}` }}>
              <div>
                <span style={{ fontWeight: 600, fontSize: 13, color: '#e2e8f0' }}>
                  {rec.attention || rec.name_first && rec.name_last ? `${rec.name_first || ''} ${rec.name_last || ''}`.trim() : rec.ida}
                </span>
                <span style={{ fontSize: 10, color: '#6b7280', marginLeft: 8 }}>#{rec.id}</span>
                {matchMeta.reason && (
                  <span style={{ fontSize: 10, color: '#f59e0b', marginLeft: 8 }}>
                    {matchMeta.reason} (score: {matchMeta.score})
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 4 }}>
                <button onClick={() => doMerge(rec, matchMeta)}
                  style={{ padding: '3px 10px', fontSize: 11, fontWeight: 600, background: '#166534', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
                  Merge
                </button>
                <button onClick={() => {
                  const route = APP_DETAIL_ROUTES[selectedModel];
                  if (route) window.open(`${route}/${rec.id}`, '_blank');
                }}
                  style={{ padding: '3px 8px', fontSize: 11, background: 'transparent', color: '#6b7280', border: `1px solid ${cardBorder}`, borderRadius: 4, cursor: 'pointer' }}>
                  Open
                </button>
              </div>
            </div>

            {/* Card body — detail fields in 2-column grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 8px', fontSize: 11 }}>
              {cardFields.map(f => {
                const val = rec[f];
                if (val === null || val === undefined || val === '' || val === false) return null;
                const display = typeof val === 'object' ? JSON.stringify(val).slice(0, 60) : String(val).slice(0, 60);
                return (
                  <React.Fragment key={f}>
                    <span style={{ color: '#6b7280', fontWeight: 500 }}>{f}</span>
                    <span style={{ color: '#e2e8f0', wordBreak: 'break-all' }}>{display}</span>
                  </React.Fragment>
                );
              }).filter(Boolean)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const AdminWorkbench: React.FC = () => {
  const { isAuthenticated, user } = useAppSelector((s) => s.auth);
  const navigate = useNavigate();
  const db = useDataBrowser(isAuthenticated);

  // --- Sprint projects for Apply-to-Selection dropdown ---
  const [sprintProjects, setSprintProjects] = useState<string[]>([]);
  useEffect(() => {
    (async () => {
      try {
        const { getRecords } = await import('@/api/wcapi');
        const res = await getRecords('action', {
          filters: { 'metadata__quality_type': 'sprint', status__in: ['open', 'in_progress'] },
          fields: ['project_name'],
          limit: 100,
          order_by: 'project_name',
        });
        const names = (res.results || []).map((r: any) => r.project_name).filter(Boolean);
        setSprintProjects([...new Set(names)] as string[]);
      } catch { /* sprints not available — dropdown will show empty */ }
    })();
  }, []);

  // --- Local UI state ---
  const [theme, setTheme] = useState<ThemeKey>(() => (localStorage.getItem('db-theme') as ThemeKey) || 'dark');
  const [baseFontSizeNum, setBaseFontSizeNum] = useState<number>(() => {
    try {
      const stored = localStorage.getItem('wc3_wcui_prefs');
      if (stored) { const p = JSON.parse(stored); if (p.font_size) return p.font_size; }
    } catch {}
    const legacy = localStorage.getItem('db-fontsize');
    return legacy === 'L' ? 16 : legacy === 'M' ? 14 : 12;
  });
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [modelFilterText, setModelFilterText] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveLayoutName, setSaveLayoutName] = useState('');
  const [showLayoutDialog, setShowLayoutDialog] = useState<'list' | 'detail' | null>(null);
  const [showRelatedDialog, setShowRelatedDialog] = useState<'list' | 'detail' | null>(null);
  const [showReportsDialog, setShowReportsDialog] = useState<'list' | 'detail' | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [showDupes, setShowDupes] = useState(false);
  const [showDedup, setShowDedup] = useState(false);
  const [dedupAllIds, setDedupAllIds] = useState<number[]>([]);
  const [dedupCurrentIds, setDedupCurrentIds] = useState<number[]>([]);
  const modelInputRef = useRef<HTMLInputElement>(null);
  const modelSelectRef = useRef<HTMLSelectElement>(null);

  // ── Draggable splitter between list and detail panes ──
  const [detailWidth, setDetailWidth] = useState<number>(() => {
    const saved = localStorage.getItem('db-detail-width');
    return saved ? parseInt(saved, 10) : 420;
  });
  const [splitterActive, setSplitterActive] = useState(false);
  const mainRef = useRef<HTMLDivElement>(null);

  const handleSplitterDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setSplitterActive(true);
    const startX = e.clientX;
    const startWidth = detailWidth;

    const onMove = (ev: MouseEvent) => {
      const delta = startX - ev.clientX;
      const newWidth = Math.max(280, Math.min(startWidth + delta, (mainRef.current?.clientWidth || 1200) - 200));
      setDetailWidth(newWidth);
    };
    const onUp = () => {
      setSplitterActive(false);
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      setDetailWidth((w) => { localStorage.setItem('db-detail-width', String(w)); return w; });
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [detailWidth]);
  const prefsSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const navLogBuffer = useRef<{ model: string; dt: number }[]>([]);
  const navLogTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const t = themes[theme];
  const baseFontSize = baseFontSizeNum;

  // Load UI preferences from wcuiPrefs on mount
  useEffect(() => {
    if (!isAuthenticated) return;
    import('@/utils/wcuiPrefs').then(({ loadWcuiFromServer, migrateLegacyPrefs, getWcuiPref }) => {
      migrateLegacyPrefs();
      loadWcuiFromServer().then(() => {
        const t = getWcuiPref('theme', 'dark');
        if (t === 'dark' || t === 'light') setTheme(t as ThemeKey);
        const fs = getWcuiPref('font_size', 12);
        if (typeof fs === 'number') setBaseFontSizeNum(fs);
      });
    });
  }, [isAuthenticated]);

  // Expose user ID for hooks that can't access Redux directly
  useEffect(() => {
    if (user?.id) (window as any).__WC_USER_ID = Number(user.id);
  }, [user?.id]);

  // Track navigation patterns — Alice watches for coaching opportunities
  useEffect(() => {
    if (!db.selectedModel || !user?.id) return;
    navLogBuffer.current.push({ model: db.selectedModel, dt: Date.now() });
    // Flush buffer every 30 seconds (batch, not per-click)
    if (navLogTimer.current) clearTimeout(navLogTimer.current);
    navLogTimer.current = setTimeout(async () => {
      const entries = navLogBuffer.current.splice(0);
      if (!entries.length) return;
      try {
        const { manageAction } = await import('@/api/wcapi');
        await manageAction('log_user_navigation', {
          contact_id: Number(user!.id),
          entries,
        });
      } catch { /* silent */ }
    }, 30000);
  }, [db.selectedModel, user?.id]);

  const toggleTheme = () => {
    const n = theme === 'dark' ? 'light' : 'dark';
    setTheme(n); localStorage.setItem('db-theme', n);
    import('@/utils/wcuiPrefs').then(m => m.setWcuiPref('theme', n));
  };
  const increaseFontSize = () => {
    setBaseFontSizeNum(s => { const n = Math.min(22, s + 2); import('@/utils/wcuiPrefs').then(m => m.setWcuiPref('font_size', n)); return n; });
  };
  const decreaseFontSize = () => {
    setBaseFontSizeNum(s => { const n = Math.max(8, s - 2); import('@/utils/wcuiPrefs').then(m => m.setWcuiPref('font_size', n)); return n; });
  };

  // Model filter — begins with, not contains
  const filteredModels = modelFilterText.trim()
    ? db.modelNames.filter((n) => n.toLowerCase().startsWith(modelFilterText.toLowerCase()))
    : db.modelNames;

  // Track highlighted index in model picker for keyboard navigation
  const [modelHighlight, setModelHighlight] = useState(0);

  // Reset highlight when filter changes
  React.useEffect(() => { setModelHighlight(0); }, [modelFilterText]);

  // inputStyle removed — use className="db-input" or "db-search" instead

  // Keyboard shortcuts: Cmd+Shift+M = model picker, Cmd+P / Cmd+Opt+P = reports
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.shiftKey && e.key.toLowerCase() === 'm') {
        e.preventDefault();
        setShowModelPicker((p) => { const next = !p; if (next) setTimeout(() => modelInputRef.current?.focus(), 50); return next; });
      }
      if (mod && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        e.stopPropagation();
        // Both Cmd+P and Cmd+Opt+P open the report selector in DataBrowser context
        setShowReportsDialog(db.selectedId ? 'detail' : 'list');
      }
    };
    window.addEventListener('keydown', handler, true);
    return () => window.removeEventListener('keydown', handler, true);
  }, [db.selectedId]);

  // Build fieldSpecs map from listFieldSpecs for DataGrid formatting
  const fieldSpecsMap = useMemo(() => {
    const m: Record<string, FieldSpec> = {};
    db.listFieldSpecs.forEach((s) => { m[s.field] = s; });
    return m;
  }, [db.listFieldSpecs]);

  // Context menu: delete column
  const handleDeleteColumn = useCallback((field: string) => {
    const updated = db.listFieldSpecs.filter((s) => s.field !== field);
    db.updateListLayout(updated);
  }, [db.listFieldSpecs, db.updateListLayout]);

  // Context menu: add column at position
  const handleAddColumn = useCallback((field: string, atIndex: number) => {
    const updated = [...db.listFieldSpecs];
    updated.splice(atIndex, 0, { field, visible: true });
    db.updateListLayout(updated);
  }, [db.listFieldSpecs, db.updateListLayout]);

  // Context menu: save current layout
  const handleSaveLayout = useCallback(() => {
    const name = db.activeViewName || 'default';
    db.saveView(name, db.listFieldSpecs, 'list');
  }, [db.activeViewName, db.listFieldSpecs, db.saveView]);

  // Context menu: save as new layout
  const handleSaveLayoutAs = useCallback(() => {
    const name = prompt('Layout name:');
    if (name?.trim()) db.saveView(name.trim(), db.listFieldSpecs, 'list');
  }, [db.listFieldSpecs, db.saveView]);

  // Context menu: load named view
  const handleLoadView = useCallback((viewName: string) => {
    const v = db.savedViews.find((sv) => sv.name === viewName);
    if (v) db.loadView(v);
  }, [db.savedViews, db.loadView]);

  return (
    <div data-wc="databrowser" className="db-root" data-theme={theme} style={{ fontSize: baseFontSize }}>

      {/* ═══ Header — model picker + search + global controls ═══ */}
      <header data-wc="db-header" className="db-header">
        <button data-wc="db-model-picker" className="db-btn db-model-picker-btn"
          onClick={() => { setShowModelPicker((p) => { const n = !p; if (n) setTimeout(() => modelInputRef.current?.focus(), 50); return n; }); }}
          title="Cmd/Ctrl+Shift+M">{db.modelLabel} <span className="db-model-count">({db.modelNames.length})</span></button>
        <input data-wc="db-search" className="db-search" type="text" placeholder="Search records..." value={db.searchTerm} onChange={(e) => db.setSearchTerm(e.target.value)} />
        <div className="db-layout-bar">
          <span data-wc="db-layouts-label" className="db-layout-label"
            onClick={(e) => {
              if (e.shiftKey && db.workbenchSettingId) {
                window.open(`/wcapi/get/?model_name=setting&id=${db.workbenchSettingId}&format=json`, '_blank');
              }
            }}
            title={db.workbenchSettingId ? `Setting #${db.workbenchSettingId} · Shift-click to inspect` : 'No setting loaded'}>
            Layouts {db.workbenchSettingId ? `#${db.workbenchSettingId}` : ''}
          </span>
          {db.savedViews.map((v) => (
            <button key={v.name} className={`db-layout-btn ${db.activeViewName === v.name ? 'db-layout-btn--active' : ''}`}
              onClick={(e) => { if (e.shiftKey) { db.deleteView(v.name); return; } db.loadView(v); }}
              title="Click to load. Shift-click to delete.">{v.name}</button>
          ))}
          <Btn small variant="save" onClick={() => { setShowSaveDialog(true); setSaveLayoutName(db.activeViewName || ''); }}>Save</Btn>
          {db.activeViewName && <Btn small onClick={() => db.saveView(db.activeViewName!)}>Update</Btn>}
          <Btn small variant="ghost" onClick={() => db.resetLayout()} title="Reset to default layout">Reset</Btn>
        </div>
        <div className="db-header-right">
          <button data-wc="db-font-size" className="db-font-toggle" onClick={decreaseFontSize} title="Decrease font size">A-</button>
          <button data-wc="db-font-size" className="db-font-toggle" onClick={increaseFontSize} title="Increase font size">A+</button>
          <button data-wc="db-theme-toggle" className="db-theme-toggle" onClick={toggleTheme}>{theme === 'dark' ? 'Light' : 'Dark'}</button>
        </div>
      </header>

      {/* Model picker */}
      {showModelPicker && (
        <div className="db-model-picker-panel">
          <div className="db-model-picker-col">
            <input ref={modelInputRef} className="db-input" type="text" placeholder="Type to filter (begins with)..." value={modelFilterText}
              onChange={(e) => setModelFilterText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') { setShowModelPicker(false); setModelFilterText(''); }
                if (e.key === 'ArrowDown') { e.preventDefault(); setModelHighlight((h) => Math.min(h + 1, filteredModels.length - 1)); }
                if (e.key === 'ArrowUp') { e.preventDefault(); setModelHighlight((h) => Math.max(h - 1, 0)); }
                if (e.key === 'Enter' && filteredModels.length) { db.handleSelectModel(filteredModels[modelHighlight]); setShowModelPicker(false); setModelFilterText(''); }
              }}
              autoFocus />
            <div className="db-model-picker-list" ref={modelSelectRef as any}>
              {filteredModels.map((n, i) => (
                <div key={n}
                  className={`db-model-picker-item ${i === modelHighlight ? 'db-row--active' : n === db.selectedModel ? 'db-model-picker-item--current' : ''}`}
                  onClick={() => { db.handleSelectModel(n); setShowModelPicker(false); setModelFilterText(''); }}
                  onMouseEnter={() => setModelHighlight(i)}
                  ref={i === modelHighlight ? (el) => el?.scrollIntoView({ block: 'nearest' }) : undefined}>
                  {n}
                </div>
              ))}
            </div>
            <div className="db-model-count">{filteredModels.length}/{db.modelNames.length} · Cmd/Ctrl+Shift+M</div>
          </div>
        </div>
      )}

      {/* Save layout */}
      {showSaveDialog && (
        <div className="db-save-dialog-bar">
          <span className="db-save-dialog-label">Save Layout:</span>
          <input className="db-input db-save-dialog-input" type="text" value={saveLayoutName} onChange={(e) => setSaveLayoutName(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && saveLayoutName.trim()) { db.saveView(saveLayoutName); setShowSaveDialog(false); } if (e.key === 'Escape') setShowSaveDialog(false); }}
            autoFocus placeholder="Layout name..." />
          <Btn variant="save" small onClick={() => { db.saveView(saveLayoutName); setShowSaveDialog(false); }} disabled={!saveLayoutName.trim()}>Save</Btn>
          <Btn small onClick={() => setShowSaveDialog(false)}>Cancel</Btn>
        </div>
      )}

      {/* Field config replaced by List Order / Form Order dialogs */}

      {/* ═══ Two-pane body ═══ */}
      <div className="db-main" ref={mainRef}>

        {/* List pane */}
        <div data-wc="db-list-pane" className="db-list-pane">
          {/* List toolbar — glass buttons */}
          <div data-wc="db-list-toolbar" className="db-list-toolbar" style={{ gap: 4 }}>
            <ToolbarIcon action={TB.filter} title="Filter" active={showFilters} onClick={() => setShowFilters(!showFilters)} />
            <ToolbarIcon action={TB.showAll} title="Show All (Shift+click clears selection)" onClick={(e) => {
              if (e?.shiftKey) { db.setSelectedRowIds(new Set()); }
              db.setSubsetMode('all'); db.setSearchTerm('');
            }} />
            <ToolbarIcon action={TB.showSubset} title="Show Selected" active={db.subsetMode === 'show'} onClick={() => db.setSubsetMode(db.subsetMode === 'show' ? 'all' : 'show')} />
            <ToolbarIcon action={TB.omit} title="Omit Selected" active={db.subsetMode === 'omit'} onClick={() => db.setSubsetMode(db.subsetMode === 'omit' ? 'all' : 'omit')} />
            <ToolbarIcon action={TB.sort} title="Sort" onClick={() => {}} />
            <ToolbarIcon action={TB.print} title="Reports" onClick={() => setShowReportsDialog(db.selectedId ? 'detail' : 'list')} />
            {/* Apply to Selection — bulk set field values on selected rows */}
            {db.selectedRowIds.size > 0 && (
              <select
                style={{ fontSize: 11, padding: '2px 4px', background: 'var(--db-surface-alt)', color: 'var(--db-text)', border: '1px solid var(--db-border)', borderRadius: 3, cursor: 'pointer' }}
                value=""
                title={`Apply to ${db.selectedRowIds.size} selected records`}
                onChange={async (e) => {
                  const val = e.target.value;
                  e.target.value = '';
                  if (!val) return;
                  const [field, ...rest] = val.split(':');
                  const newValue = rest.join(':');

                  if (field === '__set_field__') {
                    // Prompt for field name and value
                    const fieldName = prompt('Field name:');
                    if (!fieldName) return;
                    const fieldValue = prompt(`New value for "${fieldName}" on ${db.selectedRowIds.size} records:`);
                    if (fieldValue === null) return;
                    const ids = Array.from(db.selectedRowIds);
                    const { saveRecord: sr } = await import('@/api/wcapi');
                    let updated = 0;
                    for (const rid of ids) {
                      try { await sr(db.selectedModel, { id: rid, [fieldName]: fieldValue }); updated++; } catch (e) { console.error(e); }
                    }
                    db.fetchRecords();
                    console.log(`Updated ${updated}/${ids.length}: ${fieldName} = ${fieldValue}`);
                    return;
                  }

                  // Apply field:value to all selected
                  const ids = Array.from(db.selectedRowIds);
                  if (!confirm(`Set ${field} = "${newValue}" on ${ids.length} selected records?`)) return;
                  const { saveRecord: sr } = await import('@/api/wcapi');
                  let updated = 0;
                  for (const rid of ids) {
                    try { await sr(db.selectedModel, { id: rid, [field]: newValue }); updated++; } catch (e) { console.error(e); }
                  }
                  db.fetchRecords();
                  console.log(`Updated ${updated}/${ids.length}: ${field} = ${newValue}`);
                }}
              >
                <option value="">Apply to {db.selectedRowIds.size}...</option>
                {/* Dynamic select lists from field_access Setting */}
                {Object.entries(db.fieldBehaviors)
                  .filter(([, beh]) => beh.type === 'select' && beh.options?.length)
                  .map(([field, beh]) => (
                    <optgroup key={field} label={field}>
                      {beh.options.map((o: any) => (
                        <option key={o.value} value={`${field}:${o.value}`}>{o.label}</option>
                      ))}
                    </optgroup>
                  ))
                }
                {/* Fallback status options if no select behaviors loaded */}
                {!Object.values(db.fieldBehaviors).some((b: any) => b.type === 'select' && b.options?.length) && (
                  <optgroup label="status">
                    <option value="status:open">open</option>
                    <option value="status:in_progress">in_progress</option>
                    <option value="status:complete">complete</option>
                    <option value="status:on_hold">on_hold</option>
                    <option value="status:cancelled">cancelled</option>
                  </optgroup>
                )}
                {sprintProjects.length > 0 && (
                  <optgroup label="project_name">
                    {sprintProjects.map(p => (
                      <option key={p} value={`project_name:${p}`}>{p}</option>
                    ))}
                  </optgroup>
                )}
                <optgroup label="Custom">
                  <option value="__set_field__">Set any field...</option>
                </optgroup>
              </select>
            )}
            <ToolbarIcon action={TB.deleteSelection} danger title="Delete Selected" disabled={db.selectedRowIds.size === 0} onClick={async () => {
              const ids = Array.from(db.selectedRowIds);
              const n = ids.length;
              if (n > 0
                && confirm(`Delete ${n} selected ${db.modelLabel} records?`)
                && confirm(`CONFIRM: Permanently delete ${n} records. This cannot be undone.`)) {
                const { deleteRecord: dr } = await import('@/api/wcapi');
                let deleted = 0;
                for (const rid of ids) {
                  try { await dr(db.selectedModel, rid); deleted++; } catch (e) { console.error(`Failed to delete ${rid}:`, e); }
                }
                db.setSelectedRowIds(new Set());
                db.setSelectedId(null);
                db.setSelectedRecord(null);
                db.fetchRecords();
                console.log(`Deleted ${deleted}/${n} records`);
              }
            }} />
            <span className="db-separator">|</span>
            <Btn small variant="ghost" onClick={() => {
              dbLog('openDialog:list', { model: db.selectedModel, allFields: db.allFields.length, visibleList: db.visibleListFields, visibleDetail: db.visibleDetailFields.length, behaviors: Object.keys(db.fieldBehaviors).length });
              setShowLayoutDialog('list');
            }}>List Order</Btn>
            <Btn small variant="ghost" onClick={() => setShowRelatedDialog('list')}>Related</Btn>
            <span className="db-spacer" />
            <span className="db-pagination-info">{db.totalRecords}</span>
            <Btn small variant="ghost" disabled={db.page === 0} onClick={() => db.setPage((p) => p - 1)}>←</Btn>
            <span className="db-pagination-info">{db.page + 1}/{db.totalPages}</span>
            <Btn small variant="ghost" disabled={db.page >= db.totalPages - 1} onClick={() => db.setPage((p) => p + 1)}>→</Btn>
          </div>
          {/* Harvest bar — statement_line only */}
          {db.selectedModel === 'statement_line' && (
            <HarvestBar onComplete={() => db.fetchRecords()} />
          )}
          {db.recordsLoading && <div className="db-status-msg">Loading...</div>}
          {db.recordsError && <div className="db-status-msg db-status-msg--error">{db.recordsError}</div>}
          {!db.recordsLoading && (
            <DataGrid
              records={db.displayRecords}
              columns={db.visibleListFields}
              colWidths={{ ...db.specWidths, ...db.colWidths }}
              fieldSpecs={fieldSpecsMap}
              fieldBehaviors={db.fieldBehaviors}
              selectedId={db.selectedId}
              selectedRowIds={db.selectedRowIds}
              sort={db.sort}
              hideToolbar
              externalShowFilters={showFilters}
              externalShowDupes={showDupes}
              onFilterChange={async (filters) => {
                // Server-side column filtering — re-fetch with filters as query params
                if (Object.keys(filters).length === 0) {
                  db.fetchRecords();
                  return;
                }
                try {
                  const { getRecords } = await import('@/api/wcapi');
                  const params: Record<string, any> = { limit: 500, filters };
                  const res = await getRecords(db.selectedModel, params) as any;
                  const results = Array.isArray(res.results) ? res.results : [];
                  db.setRecords(results);
                  db.setTotalRecords(res.total ?? results.length);
                } catch (e) { console.error('Server filter failed:', e); }
              }}
              onSelectRecord={(id) => {
                // Both Admin and App mode: select the record in the right panel
                db.setSelectedId(id); db.setIsDirty(false);
              }}
              onRowDoubleClicked={(row) => {
                // Statement lines have no detail view — users look at their statement
                if (db.selectedModel === 'statement_line') return;
                const id = typeof row?.id === 'number' ? row.id : Number(row?.id);
                if (!id) return;
                const route = APP_DETAIL_ROUTES[db.selectedModel];
                if (route) { window.open(`${route}/${id}`, '_blank'); }
              }}
              onToggleRow={db.toggleRow}
              onSelectAll={db.selectAllRows}
              onClearSelection={() => db.setSelectedRowIds(new Set())}
              onSort={(field) => db.handleSort(field)}
              onColumnDrop={db.handleColumnDrop}
              onResizeStart={db.handleResizeStart}
              onCellEdit={async (rid, field, value) => {
                try {
                  const { saveRecord } = await import('@/api/wcapi');
                  await saveRecord(db.selectedModel, { id: rid, [field]: value });
                  db.fetchRecords();
                } catch (e) { console.error('Inline edit failed:', e); }
              }}
              numId={numId}
              theme={t}
              fontSize={baseFontSize}
              /* Column context menu — wc2 right-click pattern */
              allFields={db.allFields}
              namedViews={db.savedViews}
              onDeleteColumn={handleDeleteColumn}
              onAddColumn={handleAddColumn}
              onSaveLayout={handleSaveLayout}
              onSaveLayoutAs={handleSaveLayoutAs}
              onLoadView={handleLoadView}
            />
          )}
        </div>

        {/* Draggable splitter */}
        {(showDedup || (!showDedup && (db.selectedRecord || (db.selectedModel && db.totalRecords === 0 && !db.recordsLoading)))) && (
          <div className={`db-splitter${splitterActive ? ' db-splitter--active' : ''}`} onMouseDown={handleSplitterDown} />
        )}

        {/* Dedup panel — replaces detail pane when active */}
        {showDedup && db.selectedModel && (
          <div className="db-detail-pane db-detail-pane--app" style={{ width: detailWidth }}>
            <DedupPanel
              model={db.selectedModel}
              onMergeComplete={async () => {
                // Refresh the list from fresh dedup scan
                try {
                  const { manageAction } = await import('@/api/wcapi');
                  const res = await manageAction('find_duplicates', { model: db.selectedModel, match_fields: ['name_first+name_last'], limit: 500 }) as any;
                  const groups = res?.groups || [];
                  const records = groups.flatMap((g: any) =>
                    g.records.map((r: any) => ({ id: r.id, ida: r.ida, ...r.fields }))
                  );
                  db.setRecords(records);
                  db.setTotalRecords(records.length);
                } catch { db.fetchRecords(); }
              }}
              onClose={() => { setShowDedup(false); db.fetchRecords(); }}
            />
          </div>
        )}

        {/* Detail pane — show when record selected OR when list is empty (so Add button is accessible) */}
        {!showDedup && (db.selectedRecord || (db.selectedModel && db.totalRecords === 0 && !db.recordsLoading)) && (() => {
          const viewPref = getDetailViewPref();
          const AppDetailComponent = viewPref === 'app' ? APP_DETAIL_COMPONENTS[db.selectedModel] : null;
          return (
        <div data-wc="db-detail-pane" className={`db-detail-pane ${viewPref === 'app' && AppDetailComponent ? 'db-detail-pane--app' : ''}`} style={{ width: detailWidth }}>
          {/* Detail toolbar — record-focused glass buttons */}
          <div data-wc="db-detail-toolbar" className="db-list-toolbar" style={{ gap: 6 }}>
            <ToolbarIcon action={TB.addRecord} title="Add New Record" onClick={async () => {
              try {
                const blank = createBlankRecord(db.selectedModel, db.allFields);
                // Apply installation defaults from Setting.prefs.defaults
                if (db.fieldDefaults) {
                  Object.entries(db.fieldDefaults).forEach(([k, v]) => {
                    if (v !== '' && v != null) {
                      // Handle offset patterns: dt_due_offset_days → compute dt_due
                      if (k.endsWith('_offset_days')) {
                        const targetField = k.replace('_offset_days', '');
                        blank[targetField] = Date.now() + (Number(v) * 86400000);
                      } else {
                        blank[k] = v;
                      }
                    }
                  });
                }
                const { saveRecord: sr } = await import('@/api/wcapi');
                const result = await sr(db.selectedModel, blank) as any;
                if (result?.id) { db.fetchRecords(); db.setSelectedId(result.id); }
                else { alert('Add failed — no ID returned. Check console.'); }
              } catch (err: any) {
                console.error('[AddRecord] error:', err);
                alert('Add failed: ' + (err?.message || JSON.stringify(err)));
              }
            }} />
            <ToolbarIcon action={TB.save} title="Save" disabled={!db.isDirty} onClick={() => db.handleSaveRecord()} />
            <ToolbarIcon action={TB.discard} title="Discard Changes" disabled={!db.isDirty} onClick={() => { db.setIsDirty(false); db.setSelectedId(db.selectedId); }} />
            <ToolbarIcon action={TB.deleteRecord} danger title="Delete Record" disabled={!db.selectedId} onClick={() => { if (db.selectedId) db.handleDeleteRecord(); }} />
            <ToolbarIcon action={TB.print} title="Print / Reports for this record" disabled={!db.selectedId} onClick={() => setShowReportsDialog('detail')} />
            <span className="db-separator">|</span>
            <span className="db-detail-model-label">{db.modelLabel}</span>
            {db.selectedId && <span className="db-detail-id">#{db.selectedId}</span>}
            {db.isDirty && <span className="db-unsaved-badge">UNSAVED</span>}
            <span className="db-spacer" />
            {viewPref !== 'app' && (
              <Btn small variant="ghost" onClick={() => {
                dbLog('openDialog:detail', { model: db.selectedModel, allFields: db.allFields.length, visibleDetail: db.visibleDetailFields, behaviors: Object.keys(db.fieldBehaviors).length });
                setShowLayoutDialog('detail');
              }}>Form Order</Btn>
            )}
          </div>
          <div className="db-detail-body">
            {/* App mode: render the model's Detail.tsx component inline */}
            {viewPref === 'app' && AppDetailComponent && db.selectedId ? (
              <React.Suspense fallback={<div style={{ padding: 20, textAlign: 'center', color: '#888' }}>Loading...</div>}>
                <AppDetailComponent
                  modeProp="edit"
                  recordId={db.selectedId}
                  id={db.selectedId}
                  dataProp={db.selectedRecord}
                  hideBreadcrumb
                  inline
                  onSaved={() => db.fetchRecords()}
                  onCancelInline={() => { db.setSelectedId(null); }}
                />
              </React.Suspense>
            ) : db.selectedRecord ? (
              /* Admin mode: DataBrowser field grid */
              <div className="db-detail-grid">
                {db.visibleDetailFields
                  .filter((f) => Object.prototype.hasOwnProperty.call(db.selectedRecord!, f))
                  .map((f) => (
                    <BehaviorField key={f} name={f} value={db.selectedRecord![f]} behavior={db.fieldBehaviors[f] || {}}
                      onChange={(v) => db.updateField(f, v)} record={db.selectedRecord as Record<string, unknown>}
                      fontSize={baseFontSize} theme={t} rowSize={db.detailRowSizes[f]}
                      typeHint={db.detailFieldSpecs.find(s => s.field === f)?.typeHint}
                      error={db.validationErrors[f]} />
                  ))}
              </div>
            ) : null}

            {/* BOM panel — show when viewing an Item (Admin mode only) */}
            {viewPref !== 'app' && db.selectedRecord && db.selectedModel === 'item' && db.selectedId && (
              <BOMPanel itemId={db.selectedId} theme={t} fontSize={baseFontSize} />
            )}

            {/* Match candidates panel — full detail cards for each candidate */}
            <MatchCandidatesPanel
              selectedRecord={db.selectedRecord}
              selectedId={db.selectedId}
              selectedModel={db.selectedModel}
              visibleFields={db.visibleDetailFields}
              fieldBehaviors={db.fieldBehaviors}
              detailFieldSpecs={db.detailFieldSpecs}
              detailRowSizes={db.detailRowSizes}
              theme={t}
              fontSize={baseFontSize}
              onMerged={() => {
                db.fetchRecords();
                // Auto-advance
                const curIdx = (db as any).records?.findIndex?.((r: any) => numId(r.id) === db.selectedId) ?? -1;
                const next = (db as any).records?.[curIdx + 1] || (db as any).records?.[curIdx - 1];
                if (next) db.setSelectedId(numId(next.id));
              }}
              onDeleted={() => {
                db.fetchRecords();
                const curIdx = (db as any).records?.findIndex?.((r: any) => numId(r.id) === db.selectedId) ?? -1;
                const next = (db as any).records?.[curIdx + 1] || (db as any).records?.[curIdx - 1];
                if (next) db.setSelectedId(numId(next.id));
              }}
            />

            {/* Spawn links — show related windows for complex records */}
            {db.selectedRecord && db.selectedId && (
              <SpawnLinks model={db.selectedModel} record={db.selectedRecord} recordId={db.selectedId} />
            )}
          </div>
        </div>
          );
        })()}
      </div>

      {/* Related dialog */}
      <RelatedDialog
        open={showRelatedDialog !== null}
        model={db.selectedModel}
        selectedRecord={showRelatedDialog === 'detail' ? db.selectedRecord : null}
        selectedRowIds={db.selectedRowIds}
        theme={t}
        fontSize={baseFontSize}
        onClose={() => setShowRelatedDialog(null)}
      />

      {/* Reports dialog */}
      <ReportsDialog
        open={showReportsDialog !== null}
        model={db.selectedModel}
        context={showReportsDialog || 'list'}
        selectedId={showReportsDialog === 'detail' ? db.selectedId : null}
        theme={t}
        fontSize={baseFontSize}
        onClose={() => setShowReportsDialog(null)}
        onExecuteReport={async (report) => {
          const config = report.config as any || {};
          if (config.action === 'open_dedup_panel') {
            setShowReportsDialog(null);
            setShowDedup(true);
            // Load dedup records into the list
            try {
              const { manageAction } = await import('@/api/wcapi');
              const res = await manageAction('find_duplicates', {
                model: db.selectedModel,
                match_fields: config.match_fields || ['name_first+name_last'],
                limit: 500,
              }) as any;
              const groups = res?.groups || [];
              const records = groups.flatMap((g: any) =>
                g.records.map((r: any) => ({ id: r.id, ida: r.ida, ...r.fields }))
              );
              db.setRecords(records);
              db.setTotalRecords(records.length);
            } catch {}
          } else if (config.action === 'normalize_phones') {
            setShowReportsDialog(null);
            const { manageAction } = await import('@/api/wcapi');
            const res = await manageAction('normalize_phones', { default_country: 'US' });
            alert(JSON.stringify(res, null, 2));
            db.fetchRecords();
          } else if (config.action === 'email_quality_scan') {
            setShowReportsDialog(null);
            const { manageAction } = await import('@/api/wcapi');
            const res = await manageAction('email_quality_scan', {});
            alert(JSON.stringify(res, null, 2));
            db.fetchRecords();
          }
        }}
      />

      {/* Field order dialog — unified for list and detail, applies separately */}
      <FieldOrderDialog
        open={showLayoutDialog !== null}
        mode={showLayoutDialog || 'list'}
        allFields={db.allFields}
        visibleFields={showLayoutDialog === 'detail' ? db.visibleDetailFields : db.visibleListFields}
        fieldBehaviors={db.fieldBehaviors}
        rowSizes={db.detailRowSizes}
        colWidths={{ ...db.specWidths, ...db.colWidths }}
        savedLayouts={db.savedViews}
        activeLayoutName={db.activeViewName}
        theme={theme}
        onApply={(fields, rowSizes, colWidths) => {
          if (showLayoutDialog === 'detail') {
            db.updateDetailLayout(fields, rowSizes);
          } else {
            db.updateListLayout(fields);
            db.setColWidths(colWidths);
          }
        }}
        onSaveLayout={(name, fields) => db.saveView(name, fields, showLayoutDialog || 'list')}
        onLoadLayout={(layout) => db.loadView(layout)}
        onDeleteLayout={(name) => db.deleteView(name)}
        onClose={() => setShowLayoutDialog(null)}
      />
    </div>
  );
};

export default AdminWorkbench;
