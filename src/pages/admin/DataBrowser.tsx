/* LastChecked: 2026-08-14 | WhereUsed: DataBrowser route | WhoCreated: Bill+Claude */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getUI, setUI } from '@/utils/contactUI';
import { createBlankRecord } from '../../tools/createBlankRecord';
import { useAppSelector } from '../../store/hooks';
import { useDataBrowser, numId, type FieldSpec } from '../../hooks/useDataBrowser';
import { getDetailViewPref } from '../../layout/MacTopBar';
import JsonEnvelopePanel from '../../components/common/JsonEnvelopePanel';
import FieldOrderDialog from '../../components/common/FieldOrderDialog';
import RelatedDialog from '../../components/common/RelatedDialog';
import ReportsDialog from '../../components/common/ReportsDialog';
import MarkdownEditor, { resolveTokens, type FieldPath } from '../../components/common/MarkdownEditor';
import DataGrid from '../../components/common/DataGrid';
import { getRecords } from '../../api/wcapi';
import ToolbarIcon from '../../components/common/ToolbarIcon';
import { WorkflowSelect } from '../../components/common/WorkflowSelect';
import { TB } from '../../components/common/toolbarActions';
import DedupPanel from '../../components/common/DedupPanel';
import { useReportShortcuts } from '../../hooks/useReportShortcuts';
import { openUniversalPrint } from '../../components/print/UniversalPrint';
import { fetchPrintLayout } from '../../hooks/usePrintLayout';
import QueryBuilderPanel from '../../components/common/QueryBuilderPanel';
import { RelatedPanel } from './RelatedPanel';
import { HarvestBar } from './HarvestBar';
import { SpawnLinks } from './SpawnLinks';
// TouchBar available at ./TouchBar if needed (currently not rendered — see comment in detail body)
import { BOMPanel } from './BOMPanel';
import { MatchCandidatesPanel } from './MatchCandidatesPanel';
import { GroupedDetailFields } from './GroupedDetailFields';
import { themes, type ThemeKey } from './dbThemes';
import { APP_DETAIL_ROUTES, APP_DETAIL_COMPONENTS } from './dbRoutes';
import './DataBrowser.css';

// ---------------------------------------------------------------------------
// Extracted components — each in its own file in this directory:
// RelatedPanel, HarvestBar, SpawnLinks, TouchBar, BOMPanel,
// MatchCandidatesPanel, GroupedDetailFields, dbThemes
// ---------------------------------------------------------------------------

// Btn helper — uses CSS classes from DataBrowser.css
const Btn: React.FC<{
  variant?: 'default' | 'primary' | 'save' | 'danger' | 'ghost';
  small?: boolean; disabled?: boolean; title?: string;
  onClick?: (e: React.MouseEvent) => void; children: React.ReactNode;
  t?: any;
}> = ({ variant = 'default', small, disabled, title, onClick, children }) => (
  <button
    className={`db-btn ${small ? 'db-btn--small' : ''} ${variant !== 'default' ? `db-btn--${variant}` : ''}`}
    disabled={disabled} title={title} onClick={onClick}>{children}</button>
);

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const DataBrowser: React.FC<{ defaultModel?: string }> = ({ defaultModel }) => {
  const { isAuthenticated, user } = useAppSelector((s) => s.auth);
  const navigate = useNavigate();

  // ── Date range + Who filter (header bar) ──────────────────────────────────
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [staffFilter, setStaffFilter] = useState<number | ''>('');
  const [staffList, setStaffList] = useState<{ id: number; name: string }[]>([]);

  // Load staff list once
  useEffect(() => {
    (async () => {
      try {
        const res = await getRecords('contact', { is_staff: true, is_active: true, limit: 200 }) as any;
        const contacts = res?.results || res || [];
        setStaffList(
          contacts.map((c: any) => ({
            id: c.id,
            name: `${c.name_first || ''} ${c.name_last || ''}`.trim() || c.ida || `#${c.id}`,
          })).sort((a: any, b: any) => a.name.localeCompare(b.name))
        );
      } catch { /* staff list unavailable */ }
    })();
  }, []);

  // Query builder filters (from Filter panel)
  const [queryFilters, setQueryFilters] = useState<Record<string, unknown> | null>(null);

  // Build extra filters from date range + who + query builder
  const extraFilters = useMemo(() => {
    const f: Record<string, unknown> = {};
    if (dateFrom) {
      f.dt_created__gte = new Date(dateFrom + 'T00:00:00').getTime();
    }
    if (dateTo) {
      f.dt_created__lte = new Date(dateTo + 'T23:59:59').getTime();
    }
    if (staffFilter) {
      f.contact_id = staffFilter;
    }
    // Merge query builder filters
    if (queryFilters) {
      Object.assign(f, queryFilters);
    }
    return Object.keys(f).length > 0 ? f : undefined;
  }, [dateFrom, dateTo, staffFilter, queryFilters]);

  const db = useDataBrowser(isAuthenticated, defaultModel, extraFilters);

  // Emit date range event for DDCardDashboard to re-tally cards
  useEffect(() => {
    window.dispatchEvent(new CustomEvent('wc3-date-range-changed', {
      detail: { dateFrom, dateTo, staffId: staffFilter || null },
    }));
  }, [dateFrom, dateTo, staffFilter]);

  // Date presets
  const setDatePreset = useCallback((preset: string) => {
    const today = new Date();
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    const todayStr = iso(today);
    switch (preset) {
      case 'today':
        setDateFrom(todayStr); setDateTo(todayStr); break;
      case 'yesterday': {
        const d = new Date(today); d.setDate(d.getDate() - 1);
        const y = iso(d); setDateFrom(y); setDateTo(y); break;
      }
      case 'this_week': {
        const d = new Date(today); d.setDate(d.getDate() - d.getDay());
        setDateFrom(iso(d)); setDateTo(todayStr); break;
      }
      case 'this_month':
        setDateFrom(`${todayStr.slice(0, 7)}-01`); setDateTo(todayStr); break;
      case 'this_quarter': {
        const q = Math.floor(today.getMonth() / 3) * 3;
        setDateFrom(`${today.getFullYear()}-${String(q + 1).padStart(2, '0')}-01`);
        setDateTo(todayStr); break;
      }
      case 'ytd':
        setDateFrom(`${today.getFullYear()}-01-01`); setDateTo(todayStr); break;
      case 'tomorrow': {
        const d = new Date(today); d.setDate(d.getDate() + 1);
        const t = iso(d); setDateFrom(t); setDateTo(t); break;
      }
      case 'next_7': {
        const d = new Date(today); d.setDate(d.getDate() + 7);
        setDateFrom(todayStr); setDateTo(iso(d)); break;
      }
      case 'next_30': {
        const d = new Date(today); d.setDate(d.getDate() + 30);
        setDateFrom(todayStr); setDateTo(iso(d)); break;
      }
      case 'next_90': {
        const d = new Date(today); d.setDate(d.getDate() + 90);
        setDateFrom(todayStr); setDateTo(iso(d)); break;
      }
      case 'clear':
        setDateFrom(''); setDateTo(''); setStaffFilter(''); break;
    }
  }, []);

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
  const [theme, setTheme] = useState<ThemeKey>(() => getUI<ThemeKey>('theme.active', 'dark'));
  // Theme is now unified via config.ui.theme.active
  const [listTheme, setListTheme] = useState<ThemeKey>(() => getUI<ThemeKey>('theme.active', 'dark'));
  const [detailTheme, setDetailTheme] = useState<ThemeKey>(() => getUI<ThemeKey>('theme.active', 'dark'));

  // Listen for theme changes from TopBar
  useEffect(() => {
    const handler = (e: Event) => {
      const { zone, mode } = (e as CustomEvent).detail;
      if (zone === 'all' || zone === 'list') setListTheme(mode);
      if (zone === 'all' || zone === 'detail') setDetailTheme(mode);
    };
    window.addEventListener('wc3-zone-theme-changed', handler);
    return () => window.removeEventListener('wc3-zone-theme-changed', handler);
  }, []);

  // Sync zone themes when global theme changes
  useEffect(() => {
    setListTheme(theme);
    setDetailTheme(theme);
  }, [theme]);
  const [baseFontSizeNum, setBaseFontSizeNum] = useState<number>(() => {
    const active = getUI<string>('theme.active', 'dark');
    return getUI<number>(`theme.${active}.font.size`, 14);
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

  // Load UI config from server on mount
  useEffect(() => {
    if (!isAuthenticated) return;
    import('@/utils/contactUI').then(({ loadUIFromServer, migrateFromWcuiPrefs, getUI }) => {
      migrateFromWcuiPrefs();
      loadUIFromServer().then(() => {
        const t = getUI<string>('theme.active', 'dark');
        if (t === 'dark' || t === 'light') setTheme(t as ThemeKey);
        const active = t || 'dark';
        const fs = getUI<number>(`theme.${active}.font.size`, 14);
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
    setTheme(n); setListTheme(n); setDetailTheme(n);
    setUI('theme.active', n);
    window.dispatchEvent(new CustomEvent('wc3-theme-changed', { detail: { theme: n } }));
  };
  // Listen for font size changes from TopBar
  useEffect(() => {
    const handler = (e: Event) => {
      const size = (e as CustomEvent).detail.size;
      setBaseFontSizeNum(size);
      const active = getUI('theme.active', 'dark');
      setUI(`theme.${active}.font.size`, size);
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
    <div data-wc="databrowser" className="db-root" data-zone="db | .db-root | DataBrowser.tsx" data-theme={theme} style={{ fontSize: baseFontSize, ['--db-font-size' as any]: `${baseFontSize}px` }}>

      {/* ═══ Header — model picker + search + date range + who ═══ */}
      <header data-wc="db-header" className="db-header" data-zone="db.header | .db-header | DataBrowser.tsx">
        <button data-wc="db-model-picker" className="db-btn db-model-picker-btn"
          onClick={() => { setShowModelPicker((p) => { const n = !p; if (n) setTimeout(() => modelInputRef.current?.focus(), 50); return n; }); }}
          title="Cmd/Ctrl+Shift+M">{db.modelLabel} <span className="db-model-count">({db.modelNames.length})</span></button>
        <input data-wc="db-search" className="db-search" type="text" placeholder="Search records..." value={db.searchTerm} onChange={(e) => db.setSearchTerm(e.target.value)} />

        {/* Date range */}
        <input type="date" className="db-date-input" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} title="From date" />
        <input type="date" className="db-date-input" value={dateTo} onChange={(e) => setDateTo(e.target.value)} title="To date" />

        {/* Date presets */}
        <select className="db-date-preset" value="" onChange={(e) => { if (e.target.value) setDatePreset(e.target.value); e.target.value = ''; }} title="Date presets">
          <option value="">Range...</option>
          <option value="today">Today</option>
          <option value="yesterday">Yesterday</option>
          <option value="tomorrow">Tomorrow</option>
          <option disabled>──────</option>
          <option value="this_week">This Week</option>
          <option value="this_month">This Month</option>
          <option value="this_quarter">This Quarter</option>
          <option value="ytd">YTD</option>
          <option disabled>──────</option>
          <option value="next_7">Next 7 Days</option>
          <option value="next_30">Next 30 Days</option>
          <option value="next_90">Next 90 Days</option>
          <option disabled>──────</option>
          <option value="clear">Clear</option>
        </select>

        {/* Who (staff filter) */}
        <select className="db-who-filter" value={staffFilter} onChange={(e) => setStaffFilter(e.target.value ? Number(e.target.value) : '')} title="Filter by staff">
          <option value="">All</option>
          {staffList.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>

        {/* Clear filters */}
        {(dateFrom || dateTo || staffFilter) && (
          <button className="db-btn db-clear-filters" onClick={() => setDatePreset('clear')} title="Clear date range and who filter">×</button>
        )}
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
              className="db-apply-select"
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
          <select
            className="db-layout-select"
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
              <WorkflowSelect modelName={db.selectedModel} record={db.selectedRecord} onComplete={db.fetchRecords} />
              <select
                className="db-apply-select"
                value={db.activeViewName || ''}
                title="Detail Layout"
                onChange={(e) => {
                  const name = e.target.value;
                  if (name === '__detail_order__') { setShowLayoutDialog('detail'); return; }
                  if (name === '__list_order__') { setShowLayoutDialog('list'); return; }
                  if (name === '__save__') { db.saveView(db.activeViewName || 'default', db.detailFieldSpecs, 'detail'); return; }
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
                <option value="__detail_order__">Detail Order...</option>
                <option value="__list_order__">List Order...</option>
                <option disabled>──────</option>
                <option value="__save__">Save</option>
                <option value="__save_new__">Save As New...</option>
                <option value="__reset__">Reset to Default</option>
              </select>
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

      {/* ═══ Query Builder Panel ═══ */}
      {showFilters && (
        <QueryBuilderPanel
          fields={db.allFields}
          fieldBehaviors={db.fieldBehaviors}
          model={db.selectedModel}
          onExecute={(filters) => setQueryFilters(Object.keys(filters).length > 0 ? filters : null)}
          onClear={() => setQueryFilters(null)}
        />
      )}

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
        <div data-wc="db-detail-pane" data-zone="db.detail | .db-detail-pane | DataBrowser.tsx" data-theme={detailTheme} className={`db-detail-pane ${viewPref === 'app' && AppDetailComponent ? 'db-detail-pane--app' : ''}`} style={{ width: detailWidth, fontSize: baseFontSize }}>
          {/* Glass detail toolbar removed — DetailToolbar in each ui.json component is the single source */}
          <div className="db-detail-body">
            {/* App mode: render the model's Detail.tsx component inline */}
            {viewPref === 'app' && AppDetailComponent && db.selectedId ? (
              <React.Suspense fallback={<div className="db-loading-fallback">Loading...</div>}>
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

            {/* Spawn links — below primary contact info */}
            {db.selectedRecord && db.selectedId && (
              <SpawnLinks model={db.selectedModel} record={db.selectedRecord} recordId={db.selectedId} />
            )}

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

            {/* Touch bar + spawn links moved to top of detail body */}
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
          className="db-md-overlay"
          onClick={(e) => { if (e.target === e.currentTarget) setShowMarkdownTemplate(null); }}
        >
          <div className="db-md-dialog">
            <div className="db-md-header">
              <span className="db-md-title">
                {mdTemplateName || 'Markdown Template'}
                <span className="db-md-subtitle" style={{ fontSize: baseFontSize - 1 }}>
                  {showMarkdownTemplate === 'list'
                    ? `${db.records?.length || 0} records`
                    : db.selectedId ? `Record #${db.selectedId}` : ''}
                </span>
              </span>
              <button onClick={() => setShowMarkdownTemplate(null)} className="db-md-close">&times;</button>
            </div>
            <div className="db-md-body">
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
