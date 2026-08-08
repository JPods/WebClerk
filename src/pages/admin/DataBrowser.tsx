/* LastChecked: 2026-07-19 | WhereUsed: DataBrowser route | WhoCreated: Bill+Claude */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createBlankRecord } from '../../tools/createBlankRecord';
import { useAppSelector } from '../../store/hooks';
import { useDataBrowser, numId, type FieldSpec } from '../../hooks/useDataBrowser';
import { dbLog } from '../../utils/dbLog';
import { getDetailViewPref } from '../../layout/MacTopBar';
import BehaviorField from '../../components/common/BehaviorField';
import JsonEnvelopePanel from '../../components/common/JsonEnvelopePanel';
import FieldGroupSection from '../../components/common/FieldGroupSection';
import FieldOrderDialog from '../../components/common/FieldOrderDialog';
import RelatedDialog from '../../components/common/RelatedDialog';
import ReportsDialog from '../../components/common/ReportsDialog';
import MarkdownEditor, { resolveTokens, type FieldPath } from '../../components/common/MarkdownEditor';
import DataGrid from '../../components/common/DataGrid';
import { getRecords } from '../../api/wcapi';
import type { RowColorRule } from '../../components/common/DataGrid';
import ToolbarIcon from '../../components/common/ToolbarIcon';
import { TB } from '../../components/common/toolbarActions';
import DedupPanel from '../../components/common/DedupPanel';
import { useReportShortcuts } from '../../hooks/useReportShortcuts';
import { openUniversalPrint } from '../../components/print/UniversalPrint';
import { fetchPrintLayout } from '../../hooks/usePrintLayout';
import './DataBrowser.css';

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
  vendor: '/vendor',
  manufacturer: '/manufacturer',
  employee: '/employee',
  rep: '/rep',
  action: '/action',
};

/** Lazy-loaded detail components for App mode inline rendering in the right panel. */
/** Lazy-loaded detail components for App mode inline rendering.
 *  Every model with a detail_layout Setting should be mapped here.
 *  Models NOT mapped fall through to Admin mode (BehaviorField grid). */
const APP_DETAIL_COMPONENTS: Record<string, React.LazyExoticComponent<React.ComponentType<any>>> = {
  // Core
  contact: React.lazy(() => import('@/apps/core/models/contact/pages/ContactDetailJson')),
  report: React.lazy(() => import('@/apps/core/models/report/pages/ReportDisplay')),
  // Orgs
  customer: React.lazy(() => import('@/apps/orgs/components/OrgDetail.json')),
  vendor: React.lazy(() => import('@/apps/orgs/components/OrgDetail.json')),
  manufacturer: React.lazy(() => import('@/apps/orgs/components/OrgDetail.json')),
  employee: React.lazy(() => import('@/apps/orgs/components/OrgDetail.json')),
  rep: React.lazy(() => import('@/apps/orgs/components/OrgDetail.json')),
  // Products
  item: React.lazy(() => import('@/apps/products/pages/ItemDetailJson')),
  serial_log: React.lazy(() => import('@/apps/products/models/serial/pages/SerialDisplay')),
  // Transactions
  proposal: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  order: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  invoice: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  purchase: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  work_order: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  receipt: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  requisition: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  payment: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  // Communications — Display pages not yet built; fall through to Admin mode
  // Docs
  document: React.lazy(() => import('@/apps/docs/models/document/pages/DocumentDisplay')),
  question_answer: React.lazy(() => import('@/apps/docs/models/question_answer/pages/QuestionAnswerDisplay')),
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

// ── RelatedPanel — embedded list of FK-connected records in detail view ──

// Common FK patterns: model_id, contact_id, or refs__links__model_id
const FK_PATTERNS: Record<string, Record<string, string>> = {
  contact: {
    email: 'contact_id', phone: 'contact_id', address: 'contact_id', domain: 'contact_id',
    action: 'refs__links__contact_id', document: 'refs__links__contact_id',
    question_answer: 'refs__links__contact_id',
    order: 'customer_id', invoice: 'customer_id', payment: 'invoice__customer_id',
  },
  customer: { order: 'customer_id', invoice: 'customer_id', contact: 'customer_id' },
  vendor: { purchase: 'vendor_id', contact: 'vendor_id' },
  order: { order_line: 'order_id', document: 'refs__links__order_id', action: 'refs__links__order_id' },
  invoice: { invoice_line: 'invoice_id', payment: 'invoice_id', document: 'refs__links__invoice_id' },
  purchase: { purchase_line: 'purchase_id', document: 'refs__links__purchase_id' },
  item: { serial: 'item_id', item_xref: 'item_id', org_item: 'item_id' },
};

function getFilterKey(parentModel: string, relatedModel: string): string {
  return FK_PATTERNS[parentModel]?.[relatedModel] || `${parentModel}_id`;
}

function RelatedPanel({ modelName, parentModel, parentId, fontSize, theme }: {
  modelName: string; parentModel: string; parentId: number;
  fontSize: number; theme: any;
}) {
  const [records, setRecords] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [collapsed, setCollapsed] = React.useState(false);
  const [columns, setColumns] = React.useState<string[]>([]);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const filterKey = getFilterKey(parentModel, modelName);
        const params: Record<string, any> = { [filterKey]: parentId, limit: 50 };
        const res = await getRecords(modelName, params) as any;
        if (cancelled) return;
        const list = res?.results || [];
        setRecords(list);
        // Auto-detect columns from first record
        if (list.length > 0) {
          const keys = Object.keys(list[0]).filter(k =>
            k !== 'id' && k !== 'uuid' && k !== 'version' && k !== 'is_deleted' &&
            k !== 'is_archived' && k !== 'is_locked' && k !== 'search_vector' &&
            k !== 'security_level' && k !== 'health_rating'
          ).slice(0, 6);
          setColumns(keys);
        }
      } catch (e) {
        console.error(`[RelatedPanel] ${modelName}:`, e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [modelName, parentModel, parentId]);

  return (
    <div style={{ borderTop: `1px solid ${theme.border}`, marginTop: 4 }}>
      <div
        style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 8px', cursor: 'pointer', userSelect: 'none' }}
        onClick={() => setCollapsed(!collapsed)}
      >
        <span style={{ fontSize: fontSize - 2, color: theme.textMuted }}>{collapsed ? '▶' : '▼'}</span>
        <span style={{ fontSize: fontSize - 1, fontWeight: 600, color: theme.accent, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          {modelName.replace(/_/g, ' ')}
        </span>
        <span style={{ fontSize: fontSize - 2, color: theme.textMuted }}>({records.length})</span>
        {loading && <span style={{ fontSize: fontSize - 2, color: theme.textDim }}>loading...</span>}
      </div>
      {!collapsed && records.length > 0 && (
        <div style={{ padding: '0 4px 8px' }}>
          <DataGrid
            records={records}
            columns={columns}
            fontSize={fontSize - 1}
            theme={theme}
            hideToolbar
            noDataMessage={`No ${modelName} records`}
          />
        </div>
      )}
      {!collapsed && !loading && records.length === 0 && (
        <div style={{ padding: '4px 8px 8px', fontSize: fontSize - 2, color: theme.textMuted }}>
          No {modelName.replace(/_/g, ' ')} records
        </div>
      )}
    </div>
  );
}

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
    window.open(`/${link.target}?${link.filterKey}=${filterValue}`, '_blank');
  };

  return (
    <div className="db-spawn-bar">
      <span className="db-spawn-label">Related:</span>
      {links.map((link) => (
        <button key={link.label} className="db-btn db-btn--small db-btn--ghost"
          onClick={() => openSpawn(link)}
          title={`Open ${link.label} in new databrowser window`}>
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
          window.open(`/bill_of_material?parent_id=${itemId}`, '_blank');
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
            window.open(`/item?id=${row.item_id}`, '_blank');
          }
        }}
      />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Theme tokens — kept for passing to child components (DataGrid, BehaviorField)
// that still use inline styles. DataBrowser itself uses CSS custom properties.
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
// Btn helper — uses CSS classes from DataBrowser.css
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
// GroupedDetailFields — renders BehaviorFields in collapsible groups
// ---------------------------------------------------------------------------

type GroupedDetailFieldsProps = {
  fields: string[];
  record: Record<string, unknown>;
  fieldGroups: { key: string; label: string; fields: string[] }[];
  collapsedKeys: string[];
  onToggleGroup: (key: string) => void;
  fieldBehaviors: Record<string, any>;
  detailFieldSpecs: FieldSpec[];
  detailRowSizes: Record<string, number>;
  validationErrors: Record<string, string>;
  updateField: (field: string, value: unknown) => void;
  fontSize: number;
  theme: any;
};

function GroupedDetailFields({ fields, record, fieldGroups, collapsedKeys, onToggleGroup, fieldBehaviors, detailFieldSpecs, detailRowSizes, validationErrors, updateField, fontSize, theme }: GroupedDetailFieldsProps) {
  const presentFields = fields.filter((f) => Object.prototype.hasOwnProperty.call(record, f));
  const groupTheme = { text: theme.text, textMuted: theme.textMuted, border: theme.border, surfaceAlt: theme.surfaceAlt, inputBg: theme.inputBg };

  const renderField = (f: string) => (
    <BehaviorField key={f} name={f} value={record[f]} behavior={fieldBehaviors[f] || {}}
      onChange={(v: unknown) => updateField(f, v)} record={record}
      fontSize={fontSize} theme={theme} rowSize={detailRowSizes[f]}
      typeHint={detailFieldSpecs.find(s => s.field === f)?.typeHint}
      error={validationErrors[f]} />
  );

  // No groups defined — flat layout (backward compatible)
  if (!fieldGroups.length) {
    return <div className="db-detail-grid">{presentFields.map(renderField)}</div>;
  }

  // Partition fields into groups — preserve user's detail order within each group
  const fieldOrder = new Map(presentFields.map((f, i) => [f, i]));
  const assigned = new Set<string>();
  const groups = fieldGroups.map(g => {
    const gFields = g.fields
      .filter(f => presentFields.includes(f))
      .sort((a, b) => (fieldOrder.get(a) ?? 999) - (fieldOrder.get(b) ?? 999));
    gFields.forEach(f => assigned.add(f));
    return { ...g, presentFields: gFields };
  }).filter(g => g.presentFields.length > 0);

  const ungrouped = presentFields.filter(f => !assigned.has(f));

  return (
    <div>
      {groups.map(g => (
        <FieldGroupSection
          key={g.key}
          group={g}
          presentFields={g.presentFields}
          collapsed={collapsedKeys.includes(g.key)}
          onToggle={onToggleGroup}
          fontSize={fontSize}
          theme={groupTheme}
        >
          {g.presentFields.map(renderField)}
        </FieldGroupSection>
      ))}
      {ungrouped.length > 0 && (
        <FieldGroupSection
          group={{ key: '_other', label: 'Other', fields: ungrouped }}
          presentFields={ungrouped}
          collapsed={collapsedKeys.includes('_other')}
          onToggle={onToggleGroup}
          fontSize={fontSize}
          theme={groupTheme}
        >
          {ungrouped.map(renderField)}
        </FieldGroupSection>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const DataBrowser: React.FC = () => {
  const { isAuthenticated, user } = useAppSelector((s) => s.auth);
  const navigate = useNavigate();
  const db = useDataBrowser(isAuthenticated);

  // --- Cmd+P print shortcut ---
  useReportShortcuts({
    model: db.selectedModel,
    enabled: !!db.selectedModel,
    onPrintPrimary: async () => {
      if (db.selectedId && db.selectedRecord) {
        try {
          const layout = await fetchPrintLayout(db.selectedModel);
          await openUniversalPrint(db.selectedRecord, null, layout);
        } catch (e) {
          console.error('[DataBrowser] Print failed:', e);
          setShowReportsDialog('detail');
        }
      } else {
        setShowReportsDialog(db.selectedId ? 'detail' : 'list');
      }
    },
    onOpenSelector: () => setShowReportsDialog(db.selectedId ? 'detail' : 'list'),
  });

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
  // Per-zone color mode — stateful, initialized from contact.prefs.color_mode
  const colorMode = (user as any)?.prefs?.color_mode;
  const [listTheme, setListTheme] = useState<ThemeKey>(() => colorMode?.list || (localStorage.getItem('db-theme') as ThemeKey) || 'dark');
  const [detailTheme, setDetailTheme] = useState<ThemeKey>(() => colorMode?.detail || (localStorage.getItem('db-theme') as ThemeKey) || 'dark');

  // Listen for theme changes from TopBar Theme selector
  useEffect(() => {
    const handler = (e: Event) => {
      const { zone, mode } = (e as CustomEvent).detail;
      if (zone === 'list') setListTheme(mode);
      else if (zone === 'detail') setDetailTheme(mode);
    };
    window.addEventListener('wc3-zone-theme-changed', handler);
    return () => window.removeEventListener('wc3-zone-theme-changed', handler);
  }, []);

  // Sync when global theme toggle changes (applies to zones without explicit pref)
  useEffect(() => {
    if (!colorMode?.list) setListTheme(theme);
    if (!colorMode?.detail) setDetailTheme(theme);
  }, [theme]);
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
  const [pairedViewName, setPairedViewName] = useState<string | null>(null);
  const [showRelatedDialog, setShowRelatedDialog] = useState<'list' | 'detail' | null>(null);
  const [showReportsDialog, setShowReportsDialog] = useState<'list' | 'detail' | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [showDupes, setShowDupes] = useState(false);
  const [showDedup, setShowDedup] = useState(false);
  const [showMarkdownTemplate, setShowMarkdownTemplate] = useState<'list' | 'detail' | null>(null);
  const [mdTemplateContent, setMdTemplateContent] = useState('');
  const [mdTemplateName, setMdTemplateName] = useState('');
  const [dedupAllIds, setDedupAllIds] = useState<number[]>([]);
  const [dedupCurrentIds, setDedupCurrentIds] = useState<number[]>([]);
  const modelInputRef = useRef<HTMLInputElement>(null);
  const modelSelectRef = useRef<HTMLSelectElement>(null);

  // ── Detail component state (reported via callbacks) ──
  const [detailIsEditing, setDetailIsEditing] = useState(true); // default true for app mode
  const detailSaveRef = useRef<(() => void) | null>(null);
  const detailCancelRef = useRef<(() => void) | null>(null);
  const detailAddRef = useRef<(() => void) | null>(null);
  const detailDeleteRef = useRef<(() => void) | null>(null);

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
  const tList = themes[listTheme];
  const tDetail = themes[detailTheme];
  const baseFontSize = baseFontSizeNum;
  const [viewPref, setViewPref] = useState<'app' | 'admin'>(() => getDetailViewPref());

  // Listen for view pref changes from TopBar
  useEffect(() => {
    const handler = (e: Event) => {
      setViewPref((e as CustomEvent).detail.mode);
    };
    window.addEventListener('wc3-view-pref-changed', handler);
    return () => window.removeEventListener('wc3-view-pref-changed', handler);
  }, []);

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
  // Listen for font size changes from TopBar
  useEffect(() => {
    const handler = (e: Event) => {
      const size = (e as CustomEvent).detail.size;
      setBaseFontSizeNum(size);
      import('@/utils/wcuiPrefs').then(m => m.setWcuiPref('font_size', size));
    };
    window.addEventListener('wc3-font-size-changed', handler);
    return () => window.removeEventListener('wc3-font-size-changed', handler);
  }, []);

  // Model filter — begins with, not contains
  const filteredModels = modelFilterText.trim()
    ? db.modelNames.filter((n) => n.toLowerCase().startsWith(modelFilterText.toLowerCase()))
    : db.modelNames;

  // Track highlighted index in model picker for keyboard navigation
  const [modelHighlight, setModelHighlight] = useState(0);

  // Reset highlight when filter changes
  React.useEffect(() => { setModelHighlight(0); }, [modelFilterText]);

  // inputStyle removed — use className="db-input" or "db-search" instead

  // Keyboard shortcuts
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      // Don't intercept when typing in inputs/textareas
      const tag = (e.target as HTMLElement)?.tagName;
      const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';

      // Cmd+Shift+M = model picker (always)
      if (mod && e.shiftKey && e.key.toLowerCase() === 'm') {
        e.preventDefault();
        setShowModelPicker((p) => { const next = !p; if (next) setTimeout(() => modelInputRef.current?.focus(), 50); return next; });
        return;
      }
      // Cmd+P = reports/print (always)
      if (mod && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        e.stopPropagation();
        setShowReportsDialog(db.selectedId ? 'detail' : 'list');
        return;
      }

      // Detail shortcuts — only when not in an input
      if (isInput) return;

      // Escape = cancel / close detail pane
      if (e.key === 'Escape') {
        if (db.selectedRecord) {
          e.preventDefault();
          db.setIsDirty(false);
          db.setSelectedId(null);
          db.setSelectedRecord(null);
        }
        return;
      }
      // Cmd+S = save
      if (mod && e.key.toLowerCase() === 's') {
        e.preventDefault();
        e.stopPropagation();
        if (detailSaveRef.current) { detailSaveRef.current(); }
        else if (db.isDirty) { db.handleSaveRecord(); }
        return;
      }
      // Cmd+N = add new record
      if (mod && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        e.stopPropagation();
        if (detailAddRef.current) { detailAddRef.current(); }
        else {
          (async () => {
            try {
              const blank = createBlankRecord(db.selectedModel, db.allFields);
              if (db.fieldDefaults) {
                Object.entries(db.fieldDefaults).forEach(([k, v]) => {
                  if (v !== '' && v != null) {
                    if (k.endsWith('_offset_days')) {
                      blank[k.replace('_offset_days', '')] = Date.now() + (Number(v) * 86400000);
                    } else { blank[k] = v; }
                  }
                });
              }
              const { saveRecord: sr } = await import('@/api/wcapi');
              const result = await sr(db.selectedModel, blank) as any;
              if (result?.id) { db.fetchRecords(); db.setSelectedId(result.id); }
            } catch (err: any) { console.error('[AddRecord] error:', err); }
          })();
        }
        return;
      }
      // Cmd+Z = discard changes (only when dirty, not in input)
      if (mod && e.key.toLowerCase() === 'z' && !e.shiftKey) {
        if (db.isDirty || detailIsEditing) {
          e.preventDefault();
          db.setIsDirty(false);
          db.setSelectedId(db.selectedId);
        }
        return;
      }
    };
    window.addEventListener('keydown', handler, true);
    return () => window.removeEventListener('keydown', handler, true);
  }, [db.selectedId, db.selectedRecord, db.isDirty, detailIsEditing]);

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
    <div data-wc="databrowser" className="db-root" data-zone="db | .db-root | DataBrowser.tsx" data-theme={theme} style={{ fontSize: baseFontSize }}>

      {/* ═══ Header — model picker + search + global controls ═══ */}
      <header data-wc="db-header" className="db-header" data-zone="db.header | .db-header | DataBrowser.tsx">
        <button data-wc="db-model-picker" className="db-btn db-model-picker-btn"
          onClick={() => { setShowModelPicker((p) => { const n = !p; if (n) setTimeout(() => modelInputRef.current?.focus(), 50); return n; }); }}
          title="Cmd/Ctrl+Shift+M">{db.modelLabel} <span className="db-model-count">({db.modelNames.length})</span></button>
        <input data-wc="db-search" className="db-search" type="text" placeholder="Search records..." value={db.searchTerm} onChange={(e) => db.setSearchTerm(e.target.value)} />
        <div className="db-layout-bar">
          <select
            style={{ fontSize: 11, padding: '2px 4px', background: 'var(--db-surface-alt)', color: 'var(--db-text)', border: '1px solid var(--db-border)', borderRadius: 3, cursor: 'pointer' }}
            value={db.activeViewName || ''}
            title={db.workbenchSettingId ? `Setting #${db.workbenchSettingId}` : 'Layout'}
            onChange={(e) => {
              const name = e.target.value;
              if (name === '__list_order__') { setShowLayoutDialog('list'); return; }
              if (name === '__detail_order__') { setShowLayoutDialog('detail'); return; }
              if (name === '__save__') { db.saveView(db.activeViewName || 'default', db.listFieldSpecs, 'list'); return; }
              if (name === '__save_new__') { setShowSaveDialog(true); setSaveLayoutName(''); return; }
              if (name === '__reset__') { db.resetLayout(); return; }
              const v = db.savedViews.find(sv => sv.name === name);
              if (v) db.loadView(v);
            }}
          >
            <option value="">Layout...</option>
            {db.savedViews.map(v => (
              <option key={v.name} value={v.name}>{v.name}</option>
            ))}
            <option disabled>──────</option>
            <option value="__list_order__">List Order...</option>
            <option value="__detail_order__">Detail Order...</option>
            <option disabled>──────</option>
            <option value="__save__">Save</option>
            <option value="__save_new__">Save As New...</option>
            <option value="__reset__">Reset to Default</option>
          </select>
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

      {/* ═══ Unified Toolbar Row — list icons left, detail icons right ═══ */}
      <div className="db-toolbar-row" data-zone="db.toolbar | .db-toolbar-row | DataBrowser.tsx">
        {/* List toolbar */}
        <div data-wc="db-list-toolbar" className="db-list-toolbar" data-zone="db.ListToolbar | .db-list-toolbar | DataBrowser.tsx" style={{ gap: 4, flex: 1 }}>
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
          {db.selectedRowIds.size > 0 && <ToolbarIcon action={TB.deleteSelection} danger title="Delete Selected" onClick={async () => {
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
          }} />}
          <span className="db-separator">|</span>
          <Btn small variant="ghost" onClick={() => setShowRelatedDialog('list')}>Related</Btn>
          <span className="db-spacer" />
          <span className="db-pagination-info">{db.totalRecords}</span>
          <Btn small variant="ghost" disabled={db.page === 0} onClick={() => db.setPage((p) => p - 1)}>←</Btn>
          <span className="db-pagination-info">{db.page + 1}/{db.totalPages}</span>
          <Btn small variant="ghost" disabled={db.page >= db.totalPages - 1} onClick={() => db.setPage((p) => p + 1)}>→</Btn>
        </div>

        {/* Detail toolbar — shown when record selected or list empty */}
        {(db.selectedRecord || (db.selectedModel && db.totalRecords === 0 && !db.recordsLoading)) && (
          <>
            <div className="db-toolbar-divider" />
            <div data-wc="db-detail-toolbar" className="db-list-toolbar" data-zone="db.DetailToolbar | .db-detail-toolbar | DataBrowser.tsx" style={{ gap: 4, width: detailWidth, flexShrink: 0 }}>
              <ToolbarIcon action={TB.addRecord} title="Add New Record" onClick={() => {
                if (detailAddRef.current) { detailAddRef.current(); }
                else {
                  (async () => {
                    try {
                      const blank = createBlankRecord(db.selectedModel, db.allFields);
                      if (db.fieldDefaults) {
                        Object.entries(db.fieldDefaults).forEach(([k, v]) => {
                          if (v !== '' && v != null) {
                            if (k.endsWith('_offset_days')) {
                              const targetField = k.replace('_offset_days', '');
                              blank[targetField] = Date.now() + (Number(v) * 86400000);
                            } else { blank[k] = v; }
                          }
                        });
                      }
                      const { saveRecord: sr } = await import('@/api/wcapi');
                      const result = await sr(db.selectedModel, blank) as any;
                      if (result?.id) { db.fetchRecords(); db.setSelectedId(result.id); }
                    } catch (err: any) { console.error('[AddRecord] error:', err); alert('Add failed: ' + (err?.message || JSON.stringify(err))); }
                  })();
                }
              }} />
              <ToolbarIcon action={TB.save} title="Save" disabled={!detailIsEditing && !db.isDirty} onClick={() => {
                if (detailSaveRef.current) { detailSaveRef.current(); }
                else { db.handleSaveRecord(); }
              }} />
              <ToolbarIcon action={TB.discard} title="Discard Changes" disabled={!detailIsEditing && !db.isDirty} onClick={() => {
                db.setIsDirty(false); db.setSelectedId(db.selectedId);
              }} />
              <ToolbarIcon action={TB.cancel} title="Cancel / Close Record" onClick={() => {
                db.setIsDirty(false);
                db.setSelectedId(null);
                db.setSelectedRecord(null);
              }} />
              <ToolbarIcon action={TB.print} title="Report / Print" disabled={!db.selectedId} onClick={() => setShowReportsDialog('detail')} />
              <ToolbarIcon action={TB.modelMenu} title={`${db.modelLabel} menu`} onClick={() => {}} />
              <Btn small variant="ghost" onClick={() => {
                dbLog('openDialog:detail', { model: db.selectedModel });
                setShowLayoutDialog('detail');
              }}>Detail Order</Btn>
              {db.selectedId && <span className="db-detail-id">#{db.selectedId}</span>}
              {db.isDirty && <span className="db-unsaved-badge">UNSAVED</span>}
              <ToolbarIcon action={TB.deleteRecord} danger title="Delete Record" disabled={!db.selectedId} onClick={() => {
                if (detailDeleteRef.current) { detailDeleteRef.current(); }
                else if (db.selectedId) { db.handleDeleteRecord(); }
              }} />
            </div>
          </>
        )}
      </div>

      {/* ═══ Two-pane body ═══ */}
      <div className="db-main" ref={mainRef}>

        {/* List pane */}
        <div data-wc="db-list-pane" className="db-list-pane" data-zone="db.list | .db-list-pane | DataBrowser.tsx" data-theme={listTheme}>
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
                // Both modes: select record — right panel renders db.detail (Admin) or ui.json (App)
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
              onWidthClick={db.handleWidthClick}
              onCellEdit={async (rid, field, value) => {
                try {
                  const { saveRecord } = await import('@/api/wcapi');
                  await saveRecord(db.selectedModel, { id: rid, [field]: value });
                  db.fetchRecords();
                } catch (e) { console.error('Inline edit failed:', e); }
              }}
              numId={numId}
              theme={tList}
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
          const AppDetailComponent = viewPref === 'app' ? APP_DETAIL_COMPONENTS[db.selectedModel] : null;
          return (
        <div data-wc="db-detail-pane" data-zone="db.detail | .db-detail-pane | DataBrowser.tsx" data-theme={detailTheme} className={`db-detail-pane ${viewPref === 'app' && AppDetailComponent ? 'db-detail-pane--app' : ''}`} style={{ width: detailWidth }}>
          {/* Glass detail toolbar removed — DetailToolbar in each ui.json component is the single source */}
          <div className="db-detail-body">
            {/* App mode: render the model's Detail.tsx component inline */}
            {viewPref === 'app' && AppDetailComponent && db.selectedId ? (
              <React.Suspense fallback={<div style={{ padding: 20, textAlign: 'center', color: '#888' }}>Loading...</div>}>
                <AppDetailComponent
                  modeProp="edit"
                  recordId={db.selectedId}
                  id={db.selectedId}
                  modelName={db.selectedModel}
                  dataProp={db.selectedRecord}
                  hideBreadcrumb
                  inline
                  onSaved={() => db.fetchRecords()}
                  onCancelInline={() => { db.setSelectedId(null); }}
                  onRegisterActions={(actions: { save?: () => void; cancel?: () => void; addNew?: () => void; delete?: () => void }) => {
                    detailSaveRef.current = actions.save || null;
                    detailCancelRef.current = actions.cancel || null;
                    detailAddRef.current = actions.addNew || null;
                    detailDeleteRef.current = actions.delete || null;
                  }}
                  onEditStateChange={(editing: boolean) => setDetailIsEditing(editing)}
                />
              </React.Suspense>
            ) : db.selectedRecord ? (
              /* Admin mode: DataBrowser field grid — grouped or flat */
              <GroupedDetailFields
                fields={db.visibleDetailFields}
                record={db.selectedRecord}
                fieldGroups={db.activeViewName === 'flat' ? [] : db.fieldGroups}
                collapsedKeys={db.currentCollapsed}
                onToggleGroup={db.toggleFieldGroup}
                fieldBehaviors={db.fieldBehaviors}
                detailFieldSpecs={db.detailFieldSpecs}
                detailRowSizes={db.detailRowSizes}
                validationErrors={db.validationErrors}
                updateField={db.updateField}
                fontSize={baseFontSize}
                theme={tDetail}
              />
            ) : null}

            {/* Related panels — FK models listed in config.db.related[] */}
            {db.selectedId && db.relatedModels.length > 0 && db.relatedModels.map((relModel) => (
              <RelatedPanel
                key={relModel}
                modelName={relModel}
                parentModel={db.selectedModel}
                parentId={db.selectedId!}
                fontSize={baseFontSize}
                theme={tDetail}
              />
            ))}

            {/* JSON envelope panel — tree editors for metadata, prefs, config, refs */}
            {viewPref !== 'app' && db.selectedRecord && (
              <JsonEnvelopePanel
                record={db.selectedRecord as Record<string, any>}
                onChange={(field, value) => db.updateField(field, value)}
                modelName={db.selectedModel}
                recordId={db.selectedId ?? undefined}
                jsonExpert={!!(user as any)?.prefs?.staff?.json_expert}
                fontSize={baseFontSize}
                theme={{ text: tDetail.text, textMuted: tDetail.textMuted, border: tDetail.border, surfaceAlt: tDetail.surfaceAlt, inputBg: tDetail.inputBg }}
              />
            )}

            {/* BOM panel — show when viewing an Item (Admin mode only) */}
            {viewPref !== 'app' && db.selectedRecord && db.selectedModel === 'item' && db.selectedId && (
              <BOMPanel itemId={db.selectedId} theme={tDetail} fontSize={baseFontSize} />
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
          } else if (config.action === 'markdown_template' || (report.output_type || '').toLowerCase() === 'merge') {
            setShowReportsDialog(null);
            setMdTemplateContent(config.template || config.template_content || `# ${report.name}\n\n`);
            setMdTemplateName(report.name || '');
            setShowMarkdownTemplate(showReportsDialog);
          }
        }}
      />

      {/* Markdown template editor — opened from Reports (merge/template type) */}
      {showMarkdownTemplate && (
        <div
          data-wc="md-template-backdrop"
          onClick={(e) => { if (e.target === e.currentTarget) setShowMarkdownTemplate(null); }}
          style={{
            position: 'fixed', inset: 0, zIndex: 9000,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <div style={{
            background: t.surface, border: `1px solid ${t.border}`,
            borderRadius: 8, width: 900, maxWidth: '90vw', maxHeight: '85vh',
            display: 'flex', flexDirection: 'column',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          }}>
            <div style={{
              padding: '10px 16px', borderBottom: `1px solid ${t.border}`,
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span style={{ fontWeight: 700, color: t.accent }}>
                {mdTemplateName || 'Markdown Template'}
                <span style={{ fontWeight: 400, color: t.textMuted, marginLeft: 8, fontSize: baseFontSize - 1 }}>
                  {showMarkdownTemplate === 'list'
                    ? `${db.records?.length || 0} records`
                    : db.selectedId ? `Record #${db.selectedId}` : ''}
                </span>
              </span>
              <button onClick={() => setShowMarkdownTemplate(null)} style={{
                background: 'none', border: 'none', color: t.textMuted,
                fontSize: 18, cursor: 'pointer',
              }}>&times;</button>
            </div>
            <div style={{ flex: 1, overflow: 'auto' }}>
              <MarkdownEditor
                value={mdTemplateContent}
                onChange={setMdTemplateContent}
                record={showMarkdownTemplate === 'detail' && db.selectedId
                  ? db.records?.find((r: any) => numId(r) === db.selectedId)
                  : undefined}
                listData={showMarkdownTemplate === 'list' ? db.records : undefined}
                modelName={db.selectedModel}
                fieldPaths={db.allFields.map((f: FieldSpec) => ({
                  path: f.key,
                  label: f.label || f.key,
                  type: f.type,
                } as FieldPath))}
                templateName={mdTemplateName}
                height={500}
              />
            </div>
          </div>
        </div>
      )}

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
        sampleRecord={db.records?.[0]}
        onApply={(fields, rowSizes, colWidths) => {
          if (showLayoutDialog === 'detail') {
            db.updateDetailLayout(fields, rowSizes);
          } else {
            db.updateListLayout(fields, colWidths);
            db.setColWidths(prev => ({ ...prev, ...colWidths }));
          }
        }}
        onSaveLayout={(name, fields, widths) => {
          if (widths) db.setColWidths(prev => ({ ...prev, ...widths }));
          db.saveView(name, fields, showLayoutDialog || 'list', widths);
        }}
        onLoadLayout={(layout) => db.loadView(layout)}
        onDeleteLayout={(name) => db.deleteView(name)}
        onClose={() => setShowLayoutDialog(null)}
        pairedViewName={pairedViewName}
        onPairedViewChange={setPairedViewName}
        relatedModels={db.relatedModels}
        onRelatedModelsChange={db.setRelatedModels}
      />
    </div>
  );
};

export default DataBrowser;
