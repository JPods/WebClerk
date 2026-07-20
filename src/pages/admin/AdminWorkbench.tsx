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
import './AdminWorkbench.css';

const APP_DETAIL_ROUTES: Record<string, string> = {
  order: '/transactions/order', invoice: '/transactions/invoice',
  proposal: '/transactions/proposal', purchase: '/transactions/purchase',
  workorder: '/transactions/workorder', receipt: '/transactions/receipt',
  payment: '/transactions/payment', customer: '/org/customer',
  vendor: '/org/vendor', item: '/products/item',
  contact: '/core/contact', action: '/core/action',
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
// GlassBtn — WC glass button (3-state sprite: normal/hover/pressed)
// ---------------------------------------------------------------------------
const GBS = 56;
const GlassBtn: React.FC<{
  icon: string; title: string; onClick?: (e?: React.MouseEvent) => void; disabled?: boolean; active?: boolean;
}> = ({ icon, title, onClick, disabled, active }) => {
  const [st, setSt] = React.useState<0|1|2>(0);
  return (
    <button style={{ width: GBS, height: GBS, padding: 0, border: 'none', background: 'transparent',
      cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.35 : active ? 1 : 0.8,
      outline: active ? '2px solid var(--db-accent, #9cdcfe)' : 'none', borderRadius: 4, overflow: 'hidden', flexShrink: 0 }}
      title={title} disabled={disabled} onClick={(e) => onClick?.(e)}
      onMouseEnter={() => !disabled && setSt(1)} onMouseLeave={() => setSt(0)}
      onMouseDown={() => !disabled && setSt(2)} onMouseUp={() => !disabled && setSt(1)}>
      <div style={{ width: GBS, height: GBS * 3,
        backgroundImage: `url(/src/components/ui/button/button_glass/${encodeURIComponent(icon)}.png)`,
        backgroundSize: `${GBS}px auto`, backgroundRepeat: 'no-repeat',
        transform: `translateY(${-st * GBS}px)` }} />
    </button>
  );
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const AdminWorkbench: React.FC = () => {
  const { isAuthenticated, user } = useAppSelector((s) => s.auth);
  const navigate = useNavigate();
  const db = useDataBrowser(isAuthenticated);

  // --- Local UI state ---
  const [theme, setTheme] = useState<ThemeKey>(() => (localStorage.getItem('db-theme') as ThemeKey) || 'dark');
  const [fontSize, setFontSize] = useState<'S' | 'M' | 'L'>(() => (localStorage.getItem('db-fontsize') as 'S' | 'M' | 'L') || 'S');
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [modelFilterText, setModelFilterText] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveLayoutName, setSaveLayoutName] = useState('');
  const [showLayoutDialog, setShowLayoutDialog] = useState<'list' | 'detail' | null>(null);
  const [showRelatedDialog, setShowRelatedDialog] = useState<'list' | 'detail' | null>(null);
  const [showReportsDialog, setShowReportsDialog] = useState<'list' | 'detail' | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [showDupes, setShowDupes] = useState(false);
  const modelInputRef = useRef<HTMLInputElement>(null);
  const modelSelectRef = useRef<HTMLSelectElement>(null);
  const prefsSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const navLogBuffer = useRef<{ model: string; dt: number }[]>([]);
  const navLogTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const t = themes[theme];
  const fontSizes = { S: 12, M: 14, L: 16 };
  const baseFontSize = fontSizes[fontSize];

  // Save DataBrowser preferences to contact.metadata.databrowser (debounced)
  const savePrefsToContact = useCallback((newTheme: ThemeKey, newFontSize: 'S' | 'M' | 'L') => {
    if (!user?.id) return;
    if (prefsSaveTimer.current) clearTimeout(prefsSaveTimer.current);
    prefsSaveTimer.current = setTimeout(async () => {
      try {
        const { getRecord, saveRecord } = await import('@/api/wcapi');
        const contact = await getRecord('contact', Number(user.id)) as any;
        const metadata = contact?.metadata || {};
        metadata.databrowser = { theme: newTheme, fontSize: newFontSize, activeLayout: db.activeViewName || '' };
        await saveRecord('contact', { id: Number(user.id), metadata });
      } catch { /* silent — localStorage is the fallback */ }
    }, 2000); // 2s debounce — don't save on every click
  }, [user?.id, db.activeViewName]);

  // Load preferences from contact on mount
  useEffect(() => {
    if (!user?.id || !isAuthenticated) return;
    (async () => {
      try {
        const { getRecord } = await import('@/api/wcapi');
        const contact = await getRecord('contact', Number(user.id)) as any;
        const prefs = contact?.metadata?.databrowser;
        if (prefs) {
          if (prefs.theme && (prefs.theme === 'dark' || prefs.theme === 'light')) {
            setTheme(prefs.theme); localStorage.setItem('db-theme', prefs.theme);
          }
          if (prefs.fontSize && ['S', 'M', 'L'].includes(prefs.fontSize)) {
            setFontSize(prefs.fontSize as 'S' | 'M' | 'L'); localStorage.setItem('db-fontsize', prefs.fontSize);
          }
        }
      } catch { /* use localStorage defaults */ }
    })();
  }, [user?.id, isAuthenticated]);

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
    savePrefsToContact(n, fontSize);
  };
  const cycleFontSize = () => {
    const n = fontSize === 'S' ? 'M' : fontSize === 'M' ? 'L' : 'S';
    setFontSize(n); localStorage.setItem('db-fontsize', n);
    savePrefsToContact(theme, n);
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

  // Keyboard shortcut for model picker
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'm') {
        e.preventDefault();
        setShowModelPicker((p) => { const next = !p; if (next) setTimeout(() => modelInputRef.current?.focus(), 50); return next; });
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

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
    <div data-wc="databrowser" className="db-root" data-theme={theme} data-fontsize={fontSize}>

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
          <button data-wc="db-font-size" className="db-font-toggle" onClick={cycleFontSize}>{fontSize}</button>
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
      <div className="db-main">

        {/* List pane */}
        <div data-wc="db-list-pane" className="db-list-pane">
          {/* List toolbar — glass buttons: Print, Sort, Filter, ShowAll, ShowSubset, Omit; then text */}
          <div data-wc="db-list-toolbar" className="db-list-toolbar" style={{ gap: 4 }}>
            <GlassBtn icon="Query" title="Filter" active={showFilters} onClick={() => setShowFilters(!showFilters)} />
            <GlassBtn icon="ShowAll" title="Show All (Shift+click clears selection)" onClick={(e) => {
              if (e?.shiftKey) { db.setSelectedRowIds(new Set()); }
              db.setSubsetMode('all'); db.setSearchTerm('');
            }} />
            <GlassBtn icon="ShowSubset" title="Show Selected" active={db.subsetMode === 'show'} onClick={() => db.setSubsetMode(db.subsetMode === 'show' ? 'all' : 'show')} />
            <GlassBtn icon="OmitSelection" title="Omit Selected" active={db.subsetMode === 'omit'} onClick={() => db.setSubsetMode(db.subsetMode === 'omit' ? 'all' : 'omit')} />
            <GlassBtn icon="OrderBy" title="Sort" onClick={() => {}} />
            <GlassBtn icon="Print" title="Reports" onClick={() => setShowReportsDialog(db.selectedId ? 'detail' : 'list')} />
            <GlassBtn icon="Delete Selection" title="Delete Selected" disabled={db.selectedRowIds.size === 0} onClick={async () => {
              const n = db.selectedRowIds.size;
              if (n > 0
                && confirm(`Delete ${n} selected ${db.modelLabel} records?`)
                && confirm(`CONFIRM: Permanently delete ${n} records. This cannot be undone.`)) {
                const { deleteRecord: dr } = await import('@/api/wcapi');
                for (const rid of db.selectedRowIds) { await dr(db.selectedModel, rid); }
                db.setSelectedRowIds(new Set());
              }
            }} />
            <span className="db-separator">|</span>
            <Btn small variant="ghost" onClick={() => {
              dbLog('openDialog:list', { model: db.selectedModel, allFields: db.allFields.length, visibleList: db.visibleListFields, visibleDetail: db.visibleDetailFields.length, behaviors: Object.keys(db.fieldBehaviors).length });
              setShowLayoutDialog('list');
            }}>List Order</Btn>
            <Btn small variant="ghost" onClick={() => setShowRelatedDialog('list')}>Related</Btn>
            <Btn small variant={showDupes ? 'save' : 'ghost'} onClick={() => setShowDupes(!showDupes)}>Dupes</Btn>
            <span className="db-spacer" />
            <span className="db-pagination-info">{db.totalRecords}</span>
            <Btn small variant="ghost" disabled={db.page === 0} onClick={() => db.setPage((p) => p - 1)}>←</Btn>
            <span className="db-pagination-info">{db.page + 1}/{db.totalPages}</span>
            <Btn small variant="ghost" disabled={db.page >= db.totalPages - 1} onClick={() => db.setPage((p) => p + 1)}>→</Btn>
          </div>
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
              onSelectRecord={(id) => {
                const pref = getDetailViewPref();
                const route = APP_DETAIL_ROUTES[db.selectedModel];
                if (pref === 'app' && route) { navigate(`${route}/${id}`); }
                else { db.setSelectedId(id); db.setIsDirty(false); }
              }}
              onRowDoubleClicked={(row) => {
                const id = typeof row?.id === 'number' ? row.id : Number(row?.id);
                if (!id) return;
                const pref = getDetailViewPref();
                const route = APP_DETAIL_ROUTES[db.selectedModel];
                if (pref === 'admin' && route) { navigate(`${route}/${id}`); }
                else { db.setSelectedId(id); db.setIsDirty(false); }
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

        {/* Detail pane — show when record selected OR when list is empty (so Add button is accessible) */}
        {(db.selectedRecord || (db.selectedModel && db.totalRecords === 0 && !db.recordsLoading)) && (
        <div data-wc="db-detail-pane" className="db-detail-pane">
          {/* Detail toolbar — record-focused glass buttons */}
          <div data-wc="db-detail-toolbar" className="db-list-toolbar" style={{ gap: 6 }}>
            <GlassBtn icon="AddRecord" title="Add New Record" onClick={async () => {
              const blank = createBlankRecord(db.allFields, db.fieldBehaviors);
              const { saveRecord: sr } = await import('@/api/wcapi');
              const result = await sr(db.selectedModel, blank) as any;
              if (result?.id) { db.setSelectedId(result.id); }
            }} />
            <GlassBtn icon="OK" title="Save" disabled={!db.isDirty} onClick={() => db.handleSaveRecord()} />
            <GlassBtn icon="Cancel" title="Discard Changes" disabled={!db.isDirty} onClick={() => { db.setIsDirty(false); db.setSelectedId(db.selectedId); }} />
            <GlassBtn icon="Delete Record" title="Delete Record" disabled={!db.selectedId} onClick={() => { if (db.selectedId) db.handleDeleteRecord(); }} />
            <span className="db-separator">|</span>
            <span className="db-detail-model-label">{db.modelLabel}</span>
            {db.selectedId && <span className="db-detail-id">#{db.selectedId}</span>}
            {db.isDirty && <span className="db-unsaved-badge">UNSAVED</span>}
            <span className="db-spacer" />
            <Btn small variant="ghost" onClick={() => {
              dbLog('openDialog:detail', { model: db.selectedModel, allFields: db.allFields.length, visibleDetail: db.visibleDetailFields, behaviors: Object.keys(db.fieldBehaviors).length });
              setShowLayoutDialog('detail');
            }}>Form Order</Btn>
          </div>
          <div className="db-detail-body">
            {db.selectedRecord ? (
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

            {/* BOM panel — show when viewing an Item */}
            {db.selectedRecord && db.selectedModel === 'item' && db.selectedId && (
              <BOMPanel itemId={db.selectedId} theme={t} fontSize={baseFontSize} />
            )}

            {/* Spawn links — show related windows for complex records */}
            {db.selectedRecord && db.selectedId && (
              <SpawnLinks model={db.selectedModel} record={db.selectedRecord} recordId={db.selectedId} />
            )}
          </div>
        </div>
        )}
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
