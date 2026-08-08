/**
 * FieldOrderDialog — unified field selection, ordering, and layout management.
 *
 * Used for BOTH list columns and detail fields. Features:
 *   - Layout selector dropdown at top (load existing → modify → save)
 *   - Drag-and-drop reordering (HTML5 drag + arrow buttons)
 *   - Checkbox visibility toggles
 *   - Behavior indicator column (color-coded badges)
 *   - Row size column for text/json fields (detail mode only)
 *   - Save as new layout or overwrite existing
 *
 * Usage:
 *   <FieldOrderDialog
 *     open={true}
 *     mode="list"            // "list" or "detail"
 *     allFields={allFields}
 *     visibleFields={visibleListFields}
 *     fieldBehaviors={fieldBehaviors}
 *     rowSizes={detailRowSizes}   // only used in detail mode
 *     savedLayouts={savedViews}
 *     activeLayoutName={activeViewName}
 *     onApply={(fields, rowSizes) => { ... }}
 *     onSaveLayout={(name, listFields, detailFields, rowSizes) => { ... }}
 *     onLoadLayout={(layout) => { ... }}
 *     onDeleteLayout={(name) => { ... }}
 *     onClose={() => { ... }}
 *     theme="dark"
 *   />
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getRecords } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SavedLayout {
  name: string;
  list: string[];
  detail: string[];
  listWidths?: Record<string, number>;
}

interface Props {
  open: boolean;
  mode: 'list' | 'detail';
  allFields: string[];
  visibleFields: string[];
  fieldBehaviors: Record<string, any>;
  rowSizes?: Record<string, number>;
  colWidths?: Record<string, number>;  // current column widths (list mode)
  savedLayouts: SavedLayout[];
  activeLayoutName: string | null;
  onApply: (fields: string[], rowSizes: Record<string, number>, colWidths: Record<string, number>) => void;
  onSaveLayout: (name: string, fields?: string[], widths?: Record<string, number>) => void;
  onLoadLayout: (layout: SavedLayout) => void;
  onDeleteLayout: (name: string) => void;
  onClose: () => void;
  theme?: 'dark' | 'light';
  sampleRecord?: Record<string, any>;
  /** Name of the paired view (detail when editing list, list when editing detail) */
  pairedViewName?: string | null;
  /** Called when user changes the paired view selection */
  onPairedViewChange?: (viewName: string | null) => void;
}

// ---------------------------------------------------------------------------
// Behavior labels
// ---------------------------------------------------------------------------

const BEH_LABELS: Record<string, { label: string; color: string }> = {
  email:     { label: 'Email →', color: '#0d6efd' },
  phone:     { label: 'Phone →', color: '#0d6efd' },
  address:   { label: 'Map →', color: '#0d6efd' },
  geo:       { label: 'Geo →', color: '#0d6efd' },
  url:       { label: 'Link →', color: '#0d6efd' },
  select:    { label: 'Select ▾', color: '#198754' },
  lookup:    { label: 'Lookup ◎', color: '#6f42c1' },
  currency:  { label: '$ Curr', color: '#fd7e14' },
  boolean:   { label: '☑ Bool', color: '#6c757d' },
  json:      { label: '{ } JSON', color: '#6c757d' },
  textarea:  { label: '¶ Text', color: '#6c757d' },
  timestamp: { label: '⏱ Time', color: '#6c757d' },
  readonly:  { label: '🔒 Read', color: '#adb5bd' },
  date:      { label: '📅 Date', color: '#6c757d' },
  number:    { label: '# Num', color: '#6c757d' },
  text:      { label: 'Abc', color: '#6c757d' },
};

const SIZABLE_TYPES = ['json', 'textarea', 'text'];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function FieldOrderDialog({
  open, mode, allFields, visibleFields, fieldBehaviors, rowSizes: initialRowSizes,
  savedLayouts, activeLayoutName, onApply, onSaveLayout, onLoadLayout, onDeleteLayout, onClose, theme = 'dark',
  colWidths: initialColWidths, sampleRecord, pairedViewName, onPairedViewChange,
}: Props) {
  // Local edit state
  const [order, setOrder] = useState<string[]>([]);
  const [visible, setVisible] = useState<Set<string>>(new Set());
  const [sizes, setSizes] = useState<Record<string, number>>({});
  const [widths, setWidths] = useState<Record<string, number>>({});
  const [recWidths, setRecWidths] = useState<{ by_name: Record<string, number>; by_type: Record<string, number>; default: number } | null>(null);
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [selectedLayout, setSelectedLayout] = useState<string>('__current__');
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const [expandedJsonFields, setExpandedJsonFields] = useState<Set<string>>(new Set());
  const dragOverIdx = useRef<number | null>(null);
  const initialOrderRef = useRef<string>('');

  const PROTECTED_LAYOUTS = ['alpha', 'best_guess', 'alice_guess', 'alphabetical', 'flat'];

  const trySave = useCallback((name: string) => {
    if (!name.trim()) { alert('Please enter a layout name.'); return; }
    if (PROTECTED_LAYOUTS.includes(name.toLowerCase().trim())) {
      alert(`"${name}" is a system layout and cannot be overwritten. Save with a different name.`);
      return;
    }
    // Always save current state — user clicked Save, that's sovereign
    const fields = order.filter((f) => visible.has(f));
    onApply(fields, sizes, widths);
    onSaveLayout(name.trim(), fields, widths);
    setSaveDialogOpen(false);
    setHasChanges(false);
  }, [onSaveLayout, onApply, order, visible, sizes, widths]);

  // Sort layouts: user layouts first, then protected at bottom
  const sortedLayouts = useMemo(() => {
    const user = savedLayouts.filter((l) => !PROTECTED_LAYOUTS.includes(l.name));
    const system = savedLayouts.filter((l) => PROTECTED_LAYOUTS.includes(l.name));
    return [...user, ...system];
  }, [savedLayouts]);

  const isDark = theme === 'dark';
  const bg = isDark ? '#252526' : '#ffffff';
  const bgAlt = isDark ? '#1e1e1e' : '#f8f9fa';
  const border = isDark ? '#3c3c3c' : '#dee2e6';
  const text = isDark ? '#d4d4d4' : '#212529';
  const textMuted = isDark ? '#888' : '#6c757d';
  const accent = isDark ? '#9cdcfe' : '#0d6efd';
  const rowHover = isDark ? '#2a2d2e' : '#f1f3f5';
  const dragBg = isDark ? '#094771' : '#cfe2ff';

  // Initialize from props when dialog opens (only on open transition)
  const prevOpenRef = useRef(false);
  useEffect(() => {
    if (!open) { prevOpenRef.current = false; return; }
    if (prevOpenRef.current) return; // already open — don't re-init
    prevOpenRef.current = true;

    const vis = new Set(visibleFields);
    const unselected = allFields.filter((f) => !vis.has(f)).sort((a, b) => a.localeCompare(b));
    const initialOrder = [...visibleFields, ...unselected];
    setOrder(initialOrder);
    setVisible(new Set(visibleFields));
    setSizes({ ...(initialRowSizes || {}) });
    setWidths({ ...(initialColWidths || {}) });
    setSelectedLayout(activeLayoutName || '__current__');
    setHasChanges(false);
    setExpandedJsonFields(new Set());
    initialOrderRef.current = JSON.stringify([...visibleFields]);

    // Fetch Alice's recommended widths (synced from WCHQ via Setting)
    if (!recWidths) {
      getRecords('setting', { name: 'column_widths', purpose: 'alice_coaching' })
        .then((res: any) => {
          const rec = (res?.results || [])[0];
          if (rec?.config) setRecWidths(rec.config);
        })
        .catch(() => {});
    }
    setSaveDialogOpen(false);
    setSaveName('');
  }, [open, allFields, visibleFields, initialRowSizes, activeLayoutName]);

  // Load a saved layout into the editor
  const handleLoadLayout = useCallback((layoutName: string) => {
    if (layoutName === '__current__') {
      const vis = new Set(visibleFields);
      const unselected = allFields.filter((f) => !vis.has(f)).sort((a, b) => a.localeCompare(b));
      setOrder([...visibleFields, ...unselected]);
      setVisible(new Set(visibleFields));
      setSelectedLayout('__current__');
      setHasChanges(false);
      return;
    }
    const layout = savedLayouts.find((l) => l.name === layoutName);
    if (!layout) return;
    const rawFields = mode === 'list' ? layout.list : layout.detail;
    // Normalize: fields may be strings or FieldSpec objects
    const fields = rawFields.map((f: any) => typeof f === 'string' ? f : f.field);
    const vis = new Set(fields);
    const unselected = allFields.filter((f) => !vis.has(f)).sort((a, b) => a.localeCompare(b));
    setOrder([...fields, ...unselected]);
    setVisible(vis);
    setSelectedLayout(layoutName);
    setHasChanges(true);
    // Also apply immediately so the list/detail updates as soon as layout is selected
    onApply(fields, sizes, widths);
  }, [savedLayouts, allFields, visibleFields, mode, onApply, sizes, widths]);

  // Toggle field visibility
  const toggleVisible = useCallback((field: string) => {
    setVisible((prev) => {
      const next = new Set(prev);
      const wasVisible = next.has(field);
      wasVisible ? next.delete(field) : next.add(field);

      // Reorder: selected fields above unselected
      setOrder((prevOrder) => {
        const without = prevOrder.filter((f) => f !== field);
        if (wasVisible) {
          // Deselected → move below last selected
          const selected = without.filter((f) => next.has(f));
          const unselected = without.filter((f) => !next.has(f));
          return [...selected, field, ...unselected];
        } else {
          // Selected → move above first unselected
          const selected = without.filter((f) => next.has(f));
          const unselected = without.filter((f) => !next.has(f));
          return [...selected, field, ...unselected];
        }
      });

      return next;
    });
    setHasChanges(true);
  }, []);

  // Arrow reorder
  const moveField = useCallback((idx: number, direction: 'up' | 'down') => {
    setOrder((prev) => {
      const next = [...prev];
      const target = direction === 'up' ? idx - 1 : idx + 1;
      if (target < 0 || target >= next.length) return prev;
      [next[idx], next[target]] = [next[target], next[idx]];
      return next;
    });
    setHasChanges(true);
  }, []);

  // Pointer-based drag (works in modals — HTML5 drag does not)
  const handlePointerDown = useCallback((idx: number, e: React.PointerEvent) => {
    e.preventDefault();
    setDragIdx(idx);
  }, []);

  const handlePointerEnter = useCallback((idx: number) => {
    if (dragIdx === null || dragIdx === idx) return;
    // Swap on hover — instant visual feedback
    setOrder((prev) => {
      const next = [...prev];
      const [moved] = next.splice(dragIdx, 1);
      next.splice(idx, 0, moved);
      return next;
    });
    setDragIdx(idx); // update drag index to new position
    setHasChanges(true);
  }, [dragIdx]);

  const handlePointerUp = useCallback(() => {
    setDragIdx(null);
  }, []);

  // Global pointer up listener to catch release outside the list
  useEffect(() => {
    if (dragIdx === null) return;
    const handleUp = () => setDragIdx(null);
    window.addEventListener('pointerup', handleUp);
    return () => window.removeEventListener('pointerup', handleUp);
  }, [dragIdx]);

  // Legacy drop handler (kept for compatibility)
  const handleDrop = useCallback((dropIdx: number) => {
    if (dragIdx === null || dragIdx === dropIdx) { setDragIdx(null); return; }
    setOrder((prev) => {
      const next = [...prev];
      const [moved] = next.splice(dragIdx, 1);
      next.splice(dropIdx, 0, moved);
      return next;
    });
    setDragIdx(null);
  }, [dragIdx]);

  // Row size
  const setRowSize = useCallback((field: string, size: number) => {
    setSizes((prev) => ({ ...prev, [field]: Math.max(1, Math.min(12, size)) }));
  }, []);

  // Apply
  const handleApply = useCallback(() => {
    const fields = order.filter((f) => visible.has(f));
    onApply(fields, sizes, widths);
    onClose();
  }, [order, visible, sizes, widths, onApply, onClose]);

  // Select all / min
  const handleSelectAll = useCallback(() => setVisible(new Set(allFields)), [allFields]);
  const handleSelectNone = useCallback(() => {
    setVisible(new Set(order.slice(0, 1)));
  }, [order]);

  const visibleCount = useMemo(() => order.filter((f) => visible.has(f)).length, [order, visible]);

  // Get recommended width — 4-tier: by_name → by_type → by_pattern → by_django_type → default
  const getRecWidth = useCallback((field: string): number => {
    if (!recWidths) return 120;
    // 1. Exact name match
    if (recWidths.by_name?.[field]) return recWidths.by_name[field];
    // 2. Behavior type match
    const beh = fieldBehaviors[field];
    if (beh?.type && recWidths.by_type?.[beh.type]) return recWidths.by_type[beh.type];
    // 3. Pattern match (prefix/suffix)
    if (recWidths.by_pattern) {
      for (const [pattern, width] of Object.entries(recWidths.by_pattern)) {
        if (pattern.endsWith('_') && field.startsWith(pattern)) return width as number;
        if (pattern.startsWith('_') && field.endsWith(pattern)) return width as number;
      }
    }
    return recWidths.default || 120;
  }, [recWidths, fieldBehaviors]);

  if (!open) return null;

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.5)' }}
      onClick={onClose}>
      <div style={{ background: bg, border: `1px solid ${border}`, borderRadius: 10, boxShadow: '0 16px 48px rgba(0,0,0,0.4)', width: 580, maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}
        onClick={(e) => e.stopPropagation()}>

        {/* ═══ Header with layout selector ═══ */}
        <div style={{ padding: '14px 18px', borderBottom: `1px solid ${border}` }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: accent }}>
              {mode === 'list' ? 'List Columns' : 'Detail Fields'}
            </div>
            <div style={{ fontSize: 11, color: textMuted }}>{visibleCount}/{allFields.length} fields</div>
          </div>

          {/* Layout selector row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 10, fontWeight: 600, color: textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Layout:</span>
            <select
              data-wc="db-layout-selector"
              value={selectedLayout}
              onChange={(e) => { setSelectedLayout(e.target.value); handleLoadLayout(e.target.value); }}
              style={{ flex: 1, padding: '4px 8px', fontSize: 12, background: bgAlt, border: `1px solid ${border}`, borderRadius: 4, color: text, cursor: 'pointer' }}
            >
              <option value="__current__">Current (unsaved)</option>
              {sortedLayouts.map((l, i) => {
                const isSystem = PROTECTED_LAYOUTS.includes(l.name);
                const prevIsUser = i > 0 && !PROTECTED_LAYOUTS.includes(sortedLayouts[i - 1].name);
                return (
                  <React.Fragment key={l.name}>
                    {isSystem && prevIsUser && <option disabled>──────────</option>}
                    <option value={l.name}>{l.name}{isSystem ? ' (system)' : ''}</option>
                  </React.Fragment>
                );
              })}
            </select>
            <button onClick={onClose}
              style={{ padding: '4px 10px', fontSize: 11, fontWeight: 600, border: `1px solid ${border}`, borderRadius: 4, background: 'transparent', color: textMuted, cursor: 'pointer' }}>
              Cancel
            </button>
            <button onClick={handleApply}
              style={{ padding: '4px 10px', fontSize: 11, fontWeight: 600, border: 'none', borderRadius: 4, background: accent, color: '#fff', cursor: 'pointer' }}>
              Apply
            </button>
            <button onClick={() => { setSaveDialogOpen(!saveDialogOpen); setSaveName(selectedLayout === '__current__' ? '' : selectedLayout); }}
              style={{ padding: '4px 10px', fontSize: 11, fontWeight: 600, border: `1px solid ${isDark ? '#2f8f45' : '#157347'}`, borderRadius: 4, background: isDark ? '#1a6b2e' : '#198754', color: '#fff', cursor: 'pointer' }}>
              Save
            </button>
            {selectedLayout !== '__current__' && !PROTECTED_LAYOUTS.includes(selectedLayout) && (
              <button onClick={() => { onDeleteLayout(selectedLayout); setSelectedLayout('__current__'); }}
                style={{ padding: '4px 10px', fontSize: 11, fontWeight: 600, border: `1px solid ${isDark ? '#c04040' : '#dc3545'}`, borderRadius: 4, background: isDark ? '#6b1a1a' : '#f8d7da', color: isDark ? '#ff6b6b' : '#dc3545', cursor: 'pointer' }}
                title={`Delete layout "${selectedLayout}"`}>
                Delete
              </button>
            )}
          </div>

          {/* Paired view selector — pick which detail opens from this list (or vice versa) */}
          {onPairedViewChange && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8 }}>
              <span style={{ fontSize: 10, fontWeight: 600, color: textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                {mode === 'list' ? 'Detail:' : 'List:'}
              </span>
              <select
                value={pairedViewName || ''}
                onChange={(e) => onPairedViewChange(e.target.value || null)}
                style={{ flex: 1, padding: '4px 8px', fontSize: 12, background: bgAlt, border: `1px solid ${border}`, borderRadius: 4, color: text, cursor: 'pointer' }}
              >
                <option value="">Default</option>
                {savedLayouts.map((l) => (
                  <option key={l.name} value={l.name}>{l.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Save name input (inline, shows when Save clicked) */}
          {saveDialogOpen && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8 }}>
              <input
                type="text" placeholder="Layout name..." value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && saveName.trim()) { trySave(saveName); } if (e.key === 'Escape') setSaveDialogOpen(false); }}
                style={{ flex: 1, padding: '4px 8px', fontSize: 12, background: bgAlt, border: `1px solid ${border}`, borderRadius: 4, color: text }}
                autoFocus
              />
              <button onClick={() => { if (saveName.trim()) trySave(saveName); }}
                style={{ padding: '4px 10px', fontSize: 11, fontWeight: 600, border: 'none', borderRadius: 4, background: accent, color: '#fff', cursor: 'pointer' }}>
                Save
              </button>
              <button onClick={() => setSaveDialogOpen(false)}
                style={{ padding: '4px 8px', fontSize: 11, border: `1px solid ${border}`, borderRadius: 4, background: 'transparent', color: textMuted, cursor: 'pointer' }}>
                Cancel
              </button>
            </div>
          )}

        </div>

        {/* ═══ Column headers ═══ */}
        <div style={{ display: 'flex', alignItems: 'center', padding: '6px 18px', borderBottom: `1px solid ${border}`, background: bgAlt, fontSize: 10, fontWeight: 700, color: textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          <span style={{ width: 30 }}></span>
          <span style={{ width: 30 }}></span>
          <span style={{ flex: 1 }}>Field</span>
          <span style={{ width: 100, textAlign: 'center' }}>Behavior</span>
          {mode === 'list' && <span style={{ width: 70, textAlign: 'center' }}>Width</span>}
          {mode === 'detail' && <span style={{ width: 70, textAlign: 'center' }}>Rows</span>}
        </div>

        {/* ═══ Field list ═══ */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {order.map((field, idx) => {
            const isVisible = visible.has(field);
            const beh = fieldBehaviors[field] || {};
            const behInfo = BEH_LABELS[beh.type] || null;
            const isSizable = mode === 'detail' && SIZABLE_TYPES.includes(beh.type || '');
            const currentSize = sizes[field] || (beh.type === 'json' ? 4 : beh.type === 'textarea' ? 3 : 1);
            const isDragging = dragIdx === idx;

            return (
              <React.Fragment key={field}>
              <div
                onPointerDown={(e) => handlePointerDown(idx, e)}
                onPointerUp={handlePointerUp}
                onPointerEnter={() => handlePointerEnter(idx)}
                style={{
                  display: 'flex', alignItems: 'center', padding: '4px 14px',
                  borderBottom: `1px solid ${isDark ? '#2e2e2e' : '#f0f0f0'}`,
                  background: isDragging ? dragBg : 'transparent',
                  opacity: isVisible ? 1 : (isDark ? 0.55 : 0.4),
                  fontSize: 12,
                  cursor: 'grab',
                  userSelect: 'none',
                  touchAction: 'none',
                  transition: 'background 0.05s',
                }}
                onMouseEnter={(e) => { if (dragIdx === null) (e.currentTarget).style.background = rowHover; }}
                onMouseLeave={(e) => { if (dragIdx === null) (e.currentTarget).style.background = 'transparent'; }}
              >

                {/* Checkbox */}
                <span style={{ width: 26 }}>
                  <input type="checkbox" checked={isVisible} onChange={() => toggleVisible(field)} onPointerDown={(e) => e.stopPropagation()} />
                </span>

                {/* Field name — expandable for JSON types */}
                <span
                  style={{ flex: 1, fontWeight: 500, color: isVisible ? text : textMuted, cursor: beh.type === 'json' && sampleRecord?.[field] ? 'pointer' : 'default' }}
                  onPointerDown={(e) => {
                    if (beh.type === 'json' && sampleRecord?.[field] && typeof sampleRecord[field] === 'object') {
                      e.stopPropagation();
                      setExpandedJsonFields(prev => {
                        const next = new Set(prev);
                        next.has(field) ? next.delete(field) : next.add(field);
                        return next;
                      });
                    }
                  }}
                >
                  {beh.type === 'json' && sampleRecord?.[field] && typeof sampleRecord[field] === 'object' && (
                    <span style={{ fontSize: 10, marginRight: 4, color: textMuted }}>{expandedJsonFields.has(field) ? '▼' : '▶'}</span>
                  )}
                  {field}
                </span>

                {/* Behavior badge */}
                <span style={{ width: 100, textAlign: 'center' }}>
                  {behInfo && (
                    <span style={{ fontSize: 10, fontWeight: 600, color: behInfo.color, padding: '1px 6px', borderRadius: 3, border: `1px solid ${behInfo.color}40`, background: `${behInfo.color}10` }}>
                      {behInfo.label}
                    </span>
                  )}
                </span>

                {/* Column width (list mode) — shows recommended as placeholder */}
                {mode === 'list' && (
                  <span style={{ width: 80, textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
                    <input type="number" min={3} max={600}
                      value={widths[field] || ''}
                      placeholder={String(getRecWidth(field))}
                      onChange={(e) => { const v = parseInt(e.target.value) || 0; setWidths((prev) => ({ ...prev, [field]: v > 0 ? Math.max(3, v) : 0 })); }}
                      onClick={(e) => e.stopPropagation()}
                      onPointerDown={(e) => e.stopPropagation()}
                      style={{ width: 48, textAlign: 'center', fontSize: 11, padding: '2px 3px', border: `1px solid ${border}`, borderRadius: 3, background: bgAlt, color: widths[field] ? text : textMuted }}
                      title={`Recommended: ${getRecWidth(field)}px`}
                    />
                    {!widths[field] && (
                      <button onClick={(e) => { e.stopPropagation(); setWidths((prev) => ({ ...prev, [field]: getRecWidth(field) })); }}
                        style={{ background: 'none', border: 'none', color: accent, fontSize: 10, cursor: 'pointer', padding: 0 }}
                        title="Use recommended width">↵</button>
                    )}
                  </span>
                )}

                {/* Row size (detail mode only) */}
                {mode === 'detail' && (
                  <span style={{ width: 70, textAlign: 'center' }}>
                    {isSizable ? (
                      <input type="number" min={1} max={12} value={currentSize}
                        onChange={(e) => setRowSize(field, parseInt(e.target.value) || 1)}
                        onClick={(e) => e.stopPropagation()}
                        onPointerDown={(e) => e.stopPropagation()}
                        style={{ width: 40, textAlign: 'center', fontSize: 11, padding: '2px 4px', border: `1px solid ${border}`, borderRadius: 3, background: bgAlt, color: text }}
                      />
                    ) : (
                      <span style={{ fontSize: 10, color: textMuted }}>—</span>
                    )}
                  </span>
                )}
              </div>

              {/* JSON object tree — shown when field is expanded */}
              {beh.type === 'json' && expandedJsonFields.has(field) && sampleRecord?.[field] && typeof sampleRecord[field] === 'object' && (() => {
                const renderTree = (obj: any, prefix: string, depth: number): React.ReactNode[] => {
                  if (!obj || typeof obj !== 'object') return [];
                  return Object.entries(obj).map(([key, val]) => {
                    const path = `${prefix}.${key}`;
                    const isObj = val && typeof val === 'object' && !Array.isArray(val);
                    const isArr = Array.isArray(val);
                    const display = isObj ? '{ }' : isArr ? `[${val.length}]` : String(val ?? '—');
                    const truncated = display.length > 40 ? display.slice(0, 40) + '…' : display;
                    const isSelected = visible.has(path);
                    return (
                      <React.Fragment key={path}>
                        <div
                          style={{
                            display: 'flex', alignItems: 'center', padding: '2px 14px', paddingLeft: 26 + depth * 16,
                            borderBottom: `1px solid ${isDark ? '#1e1e1e' : '#f8f8f8'}`,
                            fontSize: 11, color: textMuted,
                            background: isSelected ? (isDark ? '#1a3a2a' : '#e8f5e9') : 'transparent',
                          }}
                          onPointerDown={(e) => e.stopPropagation()}
                        >
                          <span style={{ width: 26 }}>
                            <input type="checkbox" checked={isSelected}
                              onChange={() => {
                                setVisible(prev => { const next = new Set(prev); next.has(path) ? next.delete(path) : next.add(path); return next; });
                                if (!order.includes(path)) setOrder(prev => [...prev, path]);
                                setHasChanges(true);
                              }}
                            />
                          </span>
                          <span style={{ flex: 1, fontFamily: 'monospace', color: isSelected ? text : textMuted }}>
                            {key}
                          </span>
                          <span style={{ fontSize: 10, color: isObj ? accent : textMuted, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {truncated}
                          </span>
                        </div>
                        {isObj && renderTree(val, path, depth + 1)}
                      </React.Fragment>
                    );
                  });
                };
                return renderTree(sampleRecord[field], field, 0);
              })()}
              </React.Fragment>
            );
          })}
        </div>

        {/* ═══ Footer ═══ */}
        <div style={{ padding: '6px 18px', borderTop: `1px solid ${border}`, fontSize: 10, color: textMuted }}>
          drag row to reorder · ☑ check to show/hide
        </div>
      </div>
    </div>
  );
}
