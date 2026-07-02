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
  onSaveLayout: (name: string) => void;
  onLoadLayout: (layout: SavedLayout) => void;
  onDeleteLayout: (name: string) => void;
  onClose: () => void;
  theme?: 'dark' | 'light';
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
  colWidths: initialColWidths,
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
  const dragOverIdx = useRef<number | null>(null);

  const PROTECTED_LAYOUTS = ['alpha', 'best_guess', 'alice_guess', 'alphabetical'];

  const trySave = useCallback((name: string) => {
    if (PROTECTED_LAYOUTS.includes(name.toLowerCase().trim())) {
      alert(`"${name}" is a system layout and cannot be overwritten. Save with a different name.`);
      return;
    }
    onSaveLayout(name.trim());
    setSaveDialogOpen(false);
  }, [onSaveLayout]);

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

  // Initialize from props when dialog opens
  useEffect(() => {
    if (!open) return;
    const vis = new Set(visibleFields);
    setOrder([...visibleFields, ...allFields.filter((f) => !vis.has(f))]);
    setVisible(new Set(visibleFields));
    setSizes({ ...(initialRowSizes || {}) });
    setWidths({ ...(initialColWidths || {}) });
    setSelectedLayout(activeLayoutName || '__current__');

    // Fetch Alice's recommended widths (synced from WCHQ via Setting)
    if (!recWidths) {
      getRecords('setting', { name: 'column_widths', purpose: 'alice_coaching' })
        .then((res: any) => {
          const rec = (res?.results || [])[0];
          if (rec?.data) setRecWidths(rec.data);
        })
        .catch(() => {});
    }
    setSaveDialogOpen(false);
    setSaveName('');
  }, [open, allFields, visibleFields, initialRowSizes, activeLayoutName]);

  // Load a saved layout into the editor
  const handleLoadLayout = useCallback((layoutName: string) => {
    if (layoutName === '__current__') {
      // Reset to current live state
      const vis = new Set(visibleFields);
      setOrder([...visibleFields, ...allFields.filter((f) => !vis.has(f))]);
      setVisible(new Set(visibleFields));
      return;
    }
    const layout = savedLayouts.find((l) => l.name === layoutName);
    if (!layout) return;
    const fields = mode === 'list' ? layout.list : layout.detail;
    const vis = new Set(fields);
    setOrder([...fields, ...allFields.filter((f) => !vis.has(f))]);
    setVisible(vis);
    setSelectedLayout(layoutName);
  }, [savedLayouts, allFields, visibleFields, mode]);

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
  }, []);

  // Drag and drop
  const handleDragStart = useCallback((idx: number) => setDragIdx(idx), []);

  const handleDragOver = useCallback((e: React.DragEvent, idx: number) => {
    e.preventDefault();
    dragOverIdx.current = idx;
  }, []);

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
              {sortedLayouts.map((l) => (
                <option key={l.name} value={l.name}>{l.name}{PROTECTED_LAYOUTS.includes(l.name) ? ' (system)' : ''}</option>
              ))}
            </select>
            <button onClick={() => { setSaveDialogOpen(!saveDialogOpen); setSaveName(selectedLayout === '__current__' ? '' : selectedLayout); }}
              style={{ padding: '4px 10px', fontSize: 11, fontWeight: 600, border: `1px solid ${isDark ? '#2f8f45' : '#157347'}`, borderRadius: 4, background: isDark ? '#1a6b2e' : '#198754', color: '#fff', cursor: 'pointer' }}>
              Save
            </button>
            {selectedLayout !== '__current__' && !PROTECTED_LAYOUTS.includes(selectedLayout) && (
              <button onClick={() => { onDeleteLayout(selectedLayout); setSelectedLayout('__current__'); }}
                style={{ padding: '4px 8px', fontSize: 11, border: `1px solid ${border}`, borderRadius: 4, background: 'transparent', color: isDark ? '#e05252' : '#dc3545', cursor: 'pointer' }}
                title="Delete this layout">
                Del
              </button>
            )}
          </div>

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

          {/* Bulk actions */}
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <button onClick={handleSelectAll} style={{ padding: '3px 10px', fontSize: 11, fontWeight: 600, border: `1px solid ${border}`, borderRadius: 4, background: 'transparent', color: textMuted, cursor: 'pointer' }}>All</button>
            <button onClick={handleSelectNone} style={{ padding: '3px 10px', fontSize: 11, fontWeight: 600, border: `1px solid ${border}`, borderRadius: 4, background: 'transparent', color: textMuted, cursor: 'pointer' }}>Min</button>
          </div>
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
              <div
                key={field}
                draggable
                onDragStart={() => handleDragStart(idx)}
                onDragOver={(e) => handleDragOver(e, idx)}
                onDrop={() => handleDrop(idx)}
                onDragEnd={() => setDragIdx(null)}
                style={{
                  display: 'flex', alignItems: 'center', padding: '5px 18px',
                  borderBottom: `1px solid ${isDark ? '#2e2e2e' : '#f0f0f0'}`,
                  background: isDragging ? dragBg : 'transparent',
                  opacity: isVisible ? 1 : 0.4,
                  cursor: 'grab', fontSize: 12,
                  transition: 'background 0.1s',
                }}
                onMouseEnter={(e) => { if (!isDragging) (e.currentTarget).style.background = rowHover; }}
                onMouseLeave={(e) => { if (!isDragging) (e.currentTarget).style.background = 'transparent'; }}
              >
                {/* Checkbox */}
                <span style={{ width: 30 }}>
                  <input type="checkbox" checked={isVisible} onChange={() => toggleVisible(field)} />
                </span>

                {/* Arrows */}
                <span style={{ width: 30, display: 'flex', flexDirection: 'column', gap: 0 }}>
                  <button disabled={idx === 0} onClick={() => moveField(idx, 'up')}
                    style={{ background: 'none', border: 'none', color: textMuted, fontSize: 8, cursor: idx === 0 ? 'default' : 'pointer', opacity: idx === 0 ? 0.2 : 1, padding: 0, lineHeight: 1 }}>▲</button>
                  <button disabled={idx === order.length - 1} onClick={() => moveField(idx, 'down')}
                    style={{ background: 'none', border: 'none', color: textMuted, fontSize: 8, cursor: idx === order.length - 1 ? 'default' : 'pointer', opacity: idx === order.length - 1 ? 0.2 : 1, padding: 0, lineHeight: 1 }}>▼</button>
                </span>

                {/* Field name */}
                <span style={{ flex: 1, fontWeight: 500, color: isVisible ? text : textMuted }}>{field}</span>

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
                    <input type="number" min={40} max={600}
                      value={widths[field] || ''}
                      placeholder={String(getRecWidth(field))}
                      onChange={(e) => setWidths((prev) => ({ ...prev, [field]: parseInt(e.target.value) || 0 }))}
                      onClick={(e) => e.stopPropagation()}
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
                        style={{ width: 40, textAlign: 'center', fontSize: 11, padding: '2px 4px', border: `1px solid ${border}`, borderRadius: 3, background: bgAlt, color: text }}
                      />
                    ) : (
                      <span style={{ fontSize: 10, color: textMuted }}>—</span>
                    )}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* ═══ Footer ═══ */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 18px', borderTop: `1px solid ${border}` }}>
          <span style={{ fontSize: 11, color: textMuted }}>
            Drag to reorder · check to show/hide
          </span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={onClose}
              style={{ padding: '6px 16px', fontSize: 12, fontWeight: 600, border: `1px solid ${border}`, borderRadius: 4, background: 'transparent', color: textMuted, cursor: 'pointer' }}>Cancel</button>
            <button onClick={handleApply}
              style={{ padding: '6px 16px', fontSize: 12, fontWeight: 600, border: 'none', borderRadius: 4, background: accent, color: '#fff', cursor: 'pointer' }}>Apply</button>
          </div>
        </div>
      </div>
    </div>
  );
}
