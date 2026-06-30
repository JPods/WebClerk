/* LastChecked: 2026-06-29 | WhereUsed: DataBrowser route | WhoCreated: Bill+Claude */
import React, { useRef, useState } from 'react';
import { createBlankRecord } from '../../tools/createBlankRecord';
import { useAppSelector } from '../../store/hooks';
import { useDataBrowser, numId } from '../../hooks/useDataBrowser';
import { dbLog } from '../../utils/dbLog';
import BehaviorField from '../../components/common/BehaviorField';
import FieldOrderDialog from '../../components/common/FieldOrderDialog';
import DataGrid from '../../components/common/DataGrid';
import type { RowColorRule } from '../../components/common/DataGrid';

// ---------------------------------------------------------------------------
// Theme tokens — JPods Console inspired
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
// Btn helper
// ---------------------------------------------------------------------------

const Btn: React.FC<{
  t: typeof themes.dark; variant?: 'default' | 'primary' | 'save' | 'danger' | 'ghost';
  small?: boolean; disabled?: boolean; title?: string;
  onClick?: (e: React.MouseEvent) => void; children: React.ReactNode;
}> = ({ t, variant = 'default', small, disabled, title, onClick, children }) => (
  <button style={{
    border: `1px solid ${variant === 'primary' ? t.btnPrimary : variant === 'save' ? t.btnSaveBorder : variant === 'danger' ? t.btnDangerBorder : t.borderLight}`,
    borderRadius: 4, padding: small ? '2px 8px' : '4px 12px', fontSize: small ? 11 : 12, fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
    background: variant === 'primary' ? t.btnPrimary : variant === 'save' ? t.btnSave : variant === 'danger' ? t.btnDanger : variant === 'ghost' ? 'transparent' : t.btnBg,
    color: variant === 'primary' || variant === 'save' || variant === 'danger' ? '#fff' : t.text,
    opacity: disabled ? 0.4 : 1, transition: 'background 0.15s',
  }} disabled={disabled} title={title} onClick={onClick}>{children}</button>
);

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const AdminWorkbench: React.FC = () => {
  const { isAuthenticated } = useAppSelector((s) => s.auth);
  const db = useDataBrowser(isAuthenticated);

  // --- Local UI state ---
  const [theme, setTheme] = useState<ThemeKey>(() => (localStorage.getItem('db-theme') as ThemeKey) || 'dark');
  const [fontSize, setFontSize] = useState<'S' | 'M' | 'L'>(() => (localStorage.getItem('db-fontsize') as 'S' | 'M' | 'L') || 'S');
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [modelFilterText, setModelFilterText] = useState('');
  const [showFieldConfig, setShowFieldConfig] = useState<'list' | 'detail' | null>(null);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveLayoutName, setSaveLayoutName] = useState('');
  const [showLayoutDialog, setShowLayoutDialog] = useState<'list' | 'detail' | null>(null);
  const modelInputRef = useRef<HTMLInputElement>(null);
  const modelSelectRef = useRef<HTMLSelectElement>(null);

  const t = themes[theme];
  const fontSizes = { S: 12, M: 14, L: 16 };
  const baseFontSize = fontSizes[fontSize];

  const toggleTheme = () => { const n = theme === 'dark' ? 'light' : 'dark'; setTheme(n); localStorage.setItem('db-theme', n); };
  const cycleFontSize = () => { const n = fontSize === 'S' ? 'M' : fontSize === 'M' ? 'L' : 'S'; setFontSize(n); localStorage.setItem('db-fontsize', n); };

  // Model filter — begins with, not contains
  const filteredModels = modelFilterText.trim()
    ? db.modelNames.filter((n) => n.toLowerCase().startsWith(modelFilterText.toLowerCase()))
    : db.modelNames;

  // Track highlighted index in model picker for keyboard navigation
  const [modelHighlight, setModelHighlight] = useState(0);

  // Reset highlight when filter changes
  React.useEffect(() => { setModelHighlight(0); }, [modelFilterText]);

  const inputStyle: React.CSSProperties = {
    background: t.inputBg, border: `1px solid ${t.inputBorder}`, borderRadius: 4,
    color: t.text, fontSize: baseFontSize - 1, padding: '4px 8px', outline: 'none',
  };

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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: t.bg, color: t.text, fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", fontSize: baseFontSize }}>

      {/* ═══ Header ═══ */}
      <header style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 12px', background: t.surface, borderBottom: `1px solid ${t.border}`, height: 38, flexShrink: 0 }}>
        <button onClick={() => { setShowModelPicker((p) => { const n = !p; if (n) setTimeout(() => modelInputRef.current?.focus(), 50); return n; }); }}
          style={{ background: t.surfaceAlt, border: `1px solid ${t.borderLight}`, borderRadius: 4, padding: '4px 12px', color: t.accent, fontSize: baseFontSize, fontWeight: 700, cursor: 'pointer', minWidth: 160, textAlign: 'left' }}
          title="Cmd/Ctrl+Shift+M">{db.modelLabel} <span style={{ fontSize: baseFontSize - 3, color: t.textMuted, marginLeft: 8 }}>({db.modelNames.length})</span></button>
        <input type="text" placeholder="Search records..." value={db.searchTerm} onChange={(e) => db.setSearchTerm(e.target.value)} style={{ ...inputStyle, flex: 1, maxWidth: 280 }} />
        <Btn t={t} small onClick={() => { if (db.selectedModel && db.allFields.length) { const b = createBlankRecord(db.selectedModel, db.allFields); db.setSelectedRecord(b); db.setSelectedId(null); } }}>+ New</Btn>
        <Btn t={t} small variant="ghost" onClick={db.exportCSV}>CSV</Btn>
        <Btn t={t} small variant="ghost" onClick={() => setShowFieldConfig('list')}>List Cols</Btn>
        <Btn t={t} small variant="ghost" onClick={() => setShowFieldConfig('detail')}>Detail Fields</Btn>
        <Btn t={t} small variant="ghost" onClick={() => {
          dbLog('openDialog:list', { model: db.selectedModel, allFields: db.allFields.length, visibleList: db.visibleListFields, visibleDetail: db.visibleDetailFields.length, behaviors: Object.keys(db.fieldBehaviors).length });
          setShowLayoutDialog('list');
        }}>List Order</Btn>
        <Btn t={t} small variant="ghost" onClick={() => {
          dbLog('openDialog:detail', { model: db.selectedModel, allFields: db.allFields.length, visibleDetail: db.visibleDetailFields, behaviors: Object.keys(db.fieldBehaviors).length });
          setShowLayoutDialog('detail');
        }}>Form Order</Btn>
        <div style={{ display: 'flex', alignItems: 'center', gap: 3, borderLeft: `1px solid ${t.border}`, paddingLeft: 8 }}>
          <span style={{ fontSize: baseFontSize - 3, color: t.textMuted, fontWeight: 600, textTransform: 'uppercase' }}>Layouts</span>
          {db.savedViews.map((v) => (
            <button key={v.name} onClick={(e) => { if (e.shiftKey) { db.deleteView(v.name); return; } db.loadView(v); }}
              style={{ border: `1px solid ${db.activeViewName === v.name ? t.accent : t.borderLight}`, borderRadius: 3, padding: '2px 8px', fontSize: baseFontSize - 2, fontWeight: 600, cursor: 'pointer', background: db.activeViewName === v.name ? (theme === 'dark' ? '#094771' : '#cfe2ff') : t.btnBg, color: db.activeViewName === v.name ? t.accent : t.text }}
              title="Click to load. Shift-click to delete.">{v.name}</button>
          ))}
          <Btn t={t} small variant="save" onClick={() => { setShowSaveDialog(true); setSaveLayoutName(db.activeViewName || ''); }}>Save</Btn>
          {db.activeViewName && <Btn t={t} small onClick={() => db.saveView(db.activeViewName!)}>Update</Btn>}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
          <button onClick={cycleFontSize} style={{ background: 'none', border: `1px solid ${t.borderLight}`, borderRadius: 4, padding: '3px 8px', fontSize: 11, color: t.textMuted, cursor: 'pointer', fontWeight: 700 }}>{fontSize}</button>
          <button onClick={toggleTheme} style={{ background: 'none', border: `1px solid ${t.borderLight}`, borderRadius: 4, padding: '3px 8px', fontSize: 11, color: t.textMuted, cursor: 'pointer' }}>{theme === 'dark' ? 'Light' : 'Dark'}</button>
        </div>
      </header>

      {/* Model picker */}
      {showModelPicker && (
        <div style={{ padding: '8px 12px', background: t.surfaceAlt, borderBottom: `1px solid ${t.border}`, display: 'flex', gap: 8, alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width: 280 }}>
            <input ref={modelInputRef} type="text" placeholder="Type to filter (begins with)..." value={modelFilterText}
              onChange={(e) => setModelFilterText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') { setShowModelPicker(false); setModelFilterText(''); }
                if (e.key === 'ArrowDown') { e.preventDefault(); setModelHighlight((h) => Math.min(h + 1, filteredModels.length - 1)); }
                if (e.key === 'ArrowUp') { e.preventDefault(); setModelHighlight((h) => Math.max(h - 1, 0)); }
                if (e.key === 'Enter' && filteredModels.length) { db.handleSelectModel(filteredModels[modelHighlight]); setShowModelPicker(false); setModelFilterText(''); }
              }}
              style={{ ...inputStyle, width: '100%' }} autoFocus />
            <div ref={modelSelectRef as any} style={{ ...inputStyle, width: '100%', maxHeight: 240, overflowY: 'auto', padding: 0 }}>
              {filteredModels.map((n, i) => (
                <div key={n}
                  onClick={() => { db.handleSelectModel(n); setShowModelPicker(false); setModelFilterText(''); }}
                  onMouseEnter={() => setModelHighlight(i)}
                  ref={i === modelHighlight ? (el) => el?.scrollIntoView({ block: 'nearest' }) : undefined}
                  style={{
                    padding: '5px 10px', cursor: 'pointer', fontSize: baseFontSize - 1,
                    background: i === modelHighlight ? (theme === 'dark' ? '#094771' : '#cfe2ff') : n === db.selectedModel ? (theme === 'dark' ? '#2d2d2d' : '#f1f3f5') : 'transparent',
                    color: i === modelHighlight ? (theme === 'dark' ? '#fff' : '#000') : t.text,
                    fontWeight: n === db.selectedModel ? 700 : 400,
                  }}>
                  {n}
                </div>
              ))}
            </div>
            <div style={{ fontSize: baseFontSize - 3, color: t.textMuted }}>{filteredModels.length}/{db.modelNames.length} · Cmd/Ctrl+Shift+M</div>
          </div>
        </div>
      )}

      {/* Save layout */}
      {showSaveDialog && (
        <div style={{ padding: '10px 12px', background: theme === 'dark' ? '#2a3000' : '#fff8e1', borderBottom: `1px solid ${t.border}`, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: baseFontSize, fontWeight: 600 }}>Save Layout:</span>
          <input type="text" value={saveLayoutName} onChange={(e) => setSaveLayoutName(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && saveLayoutName.trim()) { db.saveView(saveLayoutName); setShowSaveDialog(false); } if (e.key === 'Escape') setShowSaveDialog(false); }}
            style={{ ...inputStyle, flex: 1, maxWidth: 250 }} autoFocus placeholder="Layout name..." />
          <Btn t={t} variant="save" small onClick={() => { db.saveView(saveLayoutName); setShowSaveDialog(false); }} disabled={!saveLayoutName.trim()}>Save</Btn>
          <Btn t={t} small onClick={() => setShowSaveDialog(false)}>Cancel</Btn>
        </div>
      )}

      {/* Field config panel */}
      {showFieldConfig && (
        <div style={{ padding: '8px 12px', background: t.surfaceAlt, borderBottom: `1px solid ${t.border}`, maxHeight: 140, overflowY: 'auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <span style={{ fontSize: baseFontSize - 1, fontWeight: 700, color: t.accent, textTransform: 'uppercase' }}>{showFieldConfig === 'list' ? 'List Columns' : 'Detail Fields'}</span>
            <Btn t={t} small variant="ghost" onClick={() => db.bulkSetFields(showFieldConfig, 'all')}>All</Btn>
            <Btn t={t} small variant="ghost" onClick={() => db.bulkSetFields(showFieldConfig, 'clear')}>None</Btn>
            <span style={{ fontSize: baseFontSize - 2, color: t.textMuted }}>{(showFieldConfig === 'list' ? db.visibleListFields : db.visibleDetailFields).length}/{db.allFields.length}</span>
            <span style={{ flex: 1 }} />
            <Btn t={t} small variant="ghost" onClick={() => setShowFieldConfig(showFieldConfig === 'list' ? 'detail' : 'list')}>{showFieldConfig === 'list' ? 'Detail Fields' : 'List Cols'}</Btn>
            <Btn t={t} small onClick={() => setShowFieldConfig(null)}>Done</Btn>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            {db.allFields.map((f) => {
              const active = showFieldConfig === 'list' ? db.visibleListFields.includes(f) : db.visibleDetailFields.includes(f);
              return <button key={f} onClick={() => db.toggleField(showFieldConfig, f)}
                style={{ padding: '3px 8px', fontSize: baseFontSize - 2, fontWeight: 500, borderRadius: 3, border: `1px solid ${active ? t.accent : t.borderLight}`, background: active ? (theme === 'dark' ? '#094771' : '#cfe2ff') : t.btnBg, color: active ? t.accent : t.text, cursor: 'pointer' }}>{f}</button>;
            })}
          </div>
        </div>
      )}

      {/* Pagination + subset bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 12px', background: t.surface, borderBottom: `1px solid ${t.border}`, fontSize: baseFontSize - 2, color: t.textMuted }}>
        <span>{db.totalRecords} records</span><span style={{ color: t.textDim }}>|</span>
        <span>Page {db.page + 1}/{db.totalPages}</span>
        <Btn t={t} small variant="ghost" disabled={db.page === 0} onClick={() => db.setPage((p) => p - 1)}>←</Btn>
        <Btn t={t} small variant="ghost" disabled={db.page >= db.totalPages - 1} onClick={() => db.setPage((p) => p + 1)}>→</Btn>
        <span style={{ flex: 1 }} />
        <Btn t={t} small variant="ghost" onClick={db.selectAllRows}>Sel All</Btn>
        <Btn t={t} small variant="ghost" onClick={() => db.setSelectedRowIds(new Set())}>Clear</Btn>
        <span style={{ color: t.textDim }}>|</span>
        <Btn t={t} small variant={db.subsetMode === 'show' ? 'save' : 'ghost'} onClick={() => db.setSubsetMode(db.subsetMode === 'show' ? 'all' : 'show')}>Show</Btn>
        <Btn t={t} small variant={db.subsetMode === 'omit' ? 'danger' : 'ghost'} onClick={() => db.setSubsetMode(db.subsetMode === 'omit' ? 'all' : 'omit')}>Omit</Btn>
        {db.subsetMode !== 'all' && <Btn t={t} small variant="ghost" onClick={() => db.setSubsetMode('all')}>All</Btn>}
      </div>

      {/* ═══ Two-pane body ═══ */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* List pane — DataGrid with all 10 features */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: `1px solid ${t.border}`, minWidth: 0 }}>
          {db.recordsLoading && <div style={{ padding: 16, color: t.textMuted }}>Loading...</div>}
          {db.recordsError && <div style={{ padding: 16, color: t.accentRed }}>{db.recordsError}</div>}
          {!db.recordsLoading && (
            <DataGrid
              records={db.displayRecords}
              columns={db.visibleListFields}
              colWidths={db.colWidths}
              fieldBehaviors={db.fieldBehaviors}
              selectedId={db.selectedId}
              selectedRowIds={db.selectedRowIds}
              sort={db.sort}
              onSelectRecord={(id) => { db.setSelectedId(id); db.setIsDirty(false); }}
              onToggleRow={db.toggleRow}
              onSelectAll={db.selectAllRows}
              onClearSelection={() => db.setSelectedRowIds(new Set())}
              onSort={(field) => db.handleSort(field)}
              onColumnDrop={db.handleColumnDrop}
              onResizeStart={db.handleResizeStart}
              onCellEdit={async (rid, field, value) => {
                // Inline edit → save via wcapi
                try {
                  const { saveRecord } = await import('@/api/wcapi');
                  await saveRecord(db.selectedModel, { id: rid, [field]: value });
                  db.fetchRecords();
                } catch (e) { console.error('Inline edit failed:', e); }
              }}
              numId={numId}
              theme={t}
              fontSize={baseFontSize}
            />
          )}
        </div>

        {/* Detail pane */}
        <div style={{ width: '42%', minWidth: 320, maxWidth: 600, display: 'flex', flexDirection: 'column', background: t.surface }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', borderBottom: `1px solid ${t.border}`, background: t.surfaceAlt }}>
            <div>
              <div style={{ fontSize: baseFontSize + 1, fontWeight: 700, color: t.accent }}>{db.modelLabel}</div>
              {db.selectedId && <div style={{ fontSize: baseFontSize - 1, color: t.textMuted }}>#{db.selectedId}</div>}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {db.isDirty && <span style={{ fontSize: 10, fontWeight: 700, color: t.accentGold, padding: '2px 6px', background: theme === 'dark' ? '#3a3a1a' : '#fff3cd', borderRadius: 3 }}>UNSAVED</span>}
              <Btn t={t} variant="primary" small onClick={db.handleSaveRecord} disabled={!db.selectedRecord}>Save</Btn>
              <Btn t={t} variant="danger" small disabled={!db.selectedRecord || !db.selectedId} onClick={db.handleDeleteRecord}>Delete</Btn>
            </div>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
            {db.selectedRecord ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {db.visibleDetailFields
                  .filter((f) => Object.prototype.hasOwnProperty.call(db.selectedRecord!, f))
                  .map((f) => (
                    <BehaviorField key={f} name={f} value={db.selectedRecord![f]} behavior={db.fieldBehaviors[f] || {}}
                      onChange={(v) => db.updateField(f, v)} record={db.selectedRecord as Record<string, unknown>}
                      fontSize={baseFontSize} theme={t} rowSize={db.detailRowSizes[f]} />
                  ))}
              </div>
            ) : (
              <div style={{ padding: 24, color: t.textDim }}>
                {db.selectedModel ? <><div>No record selected.</div><div style={{ fontSize: baseFontSize - 2, color: t.textMuted, marginTop: 4 }}>{db.visibleDetailFields.length} detail fields · {db.allFields.length} available</div></> : 'Choose a model.'}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Field order dialog — unified for list and detail, applies separately */}
      <FieldOrderDialog
        open={showLayoutDialog !== null}
        mode={showLayoutDialog || 'list'}
        allFields={db.allFields}
        visibleFields={showLayoutDialog === 'detail' ? db.visibleDetailFields : db.visibleListFields}
        fieldBehaviors={db.fieldBehaviors}
        rowSizes={db.detailRowSizes}
        colWidths={db.colWidths}
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
        onSaveLayout={(name) => db.saveView(name)}
        onLoadLayout={(layout) => db.loadView(layout)}
        onDeleteLayout={(name) => db.deleteView(name)}
        onClose={() => setShowLayoutDialog(null)}
      />
    </div>
  );
};

export default AdminWorkbench;
