/* LastChecked: 2026-07-03 | WhereUsed: DataBrowser route | WhoCreated: Bill+Claude */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createBlankRecord } from '../../tools/createBlankRecord';
import { useAppSelector } from '../../store/hooks';
import { useDataBrowser, numId, type FieldSpec } from '../../hooks/useDataBrowser';
import { dbLog } from '../../utils/dbLog';
import BehaviorField from '../../components/common/BehaviorField';
import FieldOrderDialog from '../../components/common/FieldOrderDialog';
import RelatedDialog from '../../components/common/RelatedDialog';
import ReportsDialog from '../../components/common/ReportsDialog';
import DataGrid from '../../components/common/DataGrid';
import type { RowColorRule } from '../../components/common/DataGrid';
import './AdminWorkbench.css';

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
// Component
// ---------------------------------------------------------------------------

const AdminWorkbench: React.FC = () => {
  const { isAuthenticated, user } = useAppSelector((s) => s.auth);
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
          {/* List toolbar */}
          <div data-wc="db-list-toolbar" className="db-list-toolbar">
            <Btn small variant="ghost" onClick={() => {
              dbLog('openDialog:list', { model: db.selectedModel, allFields: db.allFields.length, visibleList: db.visibleListFields, visibleDetail: db.visibleDetailFields.length, behaviors: Object.keys(db.fieldBehaviors).length });
              setShowLayoutDialog('list');
            }}>List Order</Btn>
            <span className="db-separator">|</span>
            <Btn small variant="ghost" onClick={() => setShowReportsDialog('list')}>Reports</Btn>
            <Btn small variant="ghost" onClick={() => setShowRelatedDialog('list')}>Related</Btn>
            <span className="db-separator">|</span>
            <Btn small variant={showFilters ? 'primary' : 'ghost'} onClick={() => setShowFilters(!showFilters)}>Filter</Btn>
            <Btn small variant={showDupes ? 'save' : 'ghost'} onClick={() => setShowDupes(!showDupes)}>Dupes</Btn>
            <span className="db-separator">|</span>
            <Btn small variant="ghost" onClick={db.selectAllRows}>Sel All</Btn>
            <Btn small variant="ghost" onClick={() => db.setSelectedRowIds(new Set())}>Clear</Btn>
            <Btn small variant={db.subsetMode === 'show' ? 'save' : 'ghost'} onClick={() => db.setSubsetMode(db.subsetMode === 'show' ? 'all' : 'show')}>Show</Btn>
            <Btn small variant={db.subsetMode === 'omit' ? 'danger' : 'ghost'} onClick={() => db.setSubsetMode(db.subsetMode === 'omit' ? 'all' : 'omit')}>Omit</Btn>
            {db.subsetMode !== 'all' && <Btn small variant="ghost" onClick={() => db.setSubsetMode('all')}>All</Btn>}
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
              onSelectRecord={() => {}}
              onRowDoubleClicked={(row) => { const id = typeof row?.id === 'number' ? row.id : Number(row?.id); if (id) { db.setSelectedId(id); db.setIsDirty(false); } }}
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

        {/* Detail pane — collapsed when no record selected */}
        {db.selectedRecord && (
        <div data-wc="db-detail-pane" className="db-detail-pane">
          {/* Detail toolbar */}
          <div data-wc="db-detail-toolbar" className="db-list-toolbar">
            <span className="db-detail-model-label">{db.modelLabel}</span>
            {db.selectedId && <span className="db-detail-id">#{db.selectedId}</span>}
            {db.isDirty && <span className="db-unsaved-badge">UNSAVED</span>}
            <span className="db-spacer" />
            <Btn small variant="ghost" onClick={() => setShowReportsDialog('detail')}>Reports</Btn>
            <Btn small variant="ghost" onClick={() => setShowRelatedDialog('detail')}>Related</Btn>
            <span className="db-separator">|</span>
            <Btn small onClick={() => { if (db.selectedModel && db.allFields.length) { const b = createBlankRecord(db.selectedModel, db.allFields); db.setSelectedRecord(b); db.setSelectedId(null); } }}>+ New</Btn>
            <Btn small variant="ghost" onClick={() => {
              dbLog('openDialog:detail', { model: db.selectedModel, allFields: db.allFields.length, visibleDetail: db.visibleDetailFields, behaviors: Object.keys(db.fieldBehaviors).length });
              setShowLayoutDialog('detail');
            }}>Form Order</Btn>
            <Btn variant="primary" small onClick={db.handleSaveRecord} disabled={!db.selectedRecord}>Save</Btn>
            <Btn variant="danger" small disabled={!db.selectedRecord || !db.selectedId} onClick={db.handleDeleteRecord}>Delete</Btn>
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
