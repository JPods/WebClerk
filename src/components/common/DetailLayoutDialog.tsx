/**
 * DetailLayoutDialog — drag/reorder detail fields, see behaviors, set row sizes.
 *
 * Opens as a modal. Shows all available fields with:
 *   Column 1: Checkbox (visible) + field name (drag or arrow to reorder)
 *   Column 2: Behavior indicator (action/select/lookup/etc.)
 *   Column 3: Row size for text/json fields (1-12 rows)
 *
 * On Apply, updates the detail field list + row sizes in the parent.
 *
 * Usage:
 *   <DetailLayoutDialog
 *     open={showLayoutDialog}
 *     allFields={allFields}
 *     visibleFields={visibleDetailFields}
 *     fieldBehaviors={fieldBehaviors}
 *     rowSizes={detailRowSizes}
 *     onApply={(fields, rowSizes) => { ... }}
 *     onClose={() => setShowLayoutDialog(false)}
 *   />
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';

interface Props {
  open: boolean;
  allFields: string[];
  visibleFields: string[];
  fieldBehaviors: Record<string, any>;
  rowSizes: Record<string, number>;
  onApply: (fields: string[], rowSizes: Record<string, number>) => void;
  onClose: () => void;
  theme?: 'dark' | 'light';
}

const BEHAVIOR_LABELS: Record<string, { label: string; color: string }> = {
  email:     { label: 'Email →', color: '#0d6efd' },
  phone:     { label: 'Phone →', color: '#0d6efd' },
  address:   { label: 'Map →', color: '#0d6efd' },
  geo:       { label: 'Geo →', color: '#0d6efd' },
  url:       { label: 'Link →', color: '#0d6efd' },
  select:    { label: 'Select ▾', color: '#198754' },
  lookup:    { label: 'Lookup ◎', color: '#6f42c1' },
  currency:  { label: '$ Currency', color: '#fd7e14' },
  boolean:   { label: '☑ Bool', color: '#6c757d' },
  json:      { label: '{ } JSON', color: '#6c757d' },
  textarea:  { label: '¶ Text', color: '#6c757d' },
  timestamp: { label: '⏱ Time', color: '#6c757d' },
  readonly:  { label: '🔒 Read', color: '#adb5bd' },
  date:      { label: '📅 Date', color: '#6c757d' },
  number:    { label: '# Num', color: '#6c757d' },
  text:      { label: 'Abc', color: '#6c757d' },
};

// Fields that support multi-row sizing
const SIZABLE_TYPES = ['json', 'textarea', 'text'];

export default function DetailLayoutDialog({
  open, allFields, visibleFields, fieldBehaviors, rowSizes, onApply, onClose, theme = 'dark',
}: Props) {
  const [order, setOrder] = useState<string[]>([]);
  const [visible, setVisible] = useState<Set<string>>(new Set());
  const [sizes, setSizes] = useState<Record<string, number>>({});
  const [dragIdx, setDragIdx] = useState<number | null>(null);

  const isDark = theme === 'dark';
  const bg = isDark ? '#252526' : '#ffffff';
  const bgAlt = isDark ? '#1e1e1e' : '#f8f9fa';
  const border = isDark ? '#3c3c3c' : '#dee2e6';
  const text = isDark ? '#d4d4d4' : '#212529';
  const textMuted = isDark ? '#888' : '#6c757d';
  const accent = isDark ? '#9cdcfe' : '#0d6efd';
  const rowHover = isDark ? '#2a2d2e' : '#f1f3f5';

  // Initialize from props when dialog opens
  useEffect(() => {
    if (!open) return;
    // Build order: visible fields first (in their order), then remaining
    const vis = new Set(visibleFields);
    const ordered = [
      ...visibleFields,
      ...allFields.filter((f) => !vis.has(f)),
    ];
    setOrder(ordered);
    setVisible(new Set(visibleFields));
    setSizes({ ...rowSizes });
  }, [open, allFields, visibleFields, rowSizes]);

  const toggleVisible = useCallback((field: string) => {
    setVisible((prev) => {
      const next = new Set(prev);
      if (next.has(field)) next.delete(field); else next.add(field);
      return next;
    });
  }, []);

  const moveField = useCallback((idx: number, direction: 'up' | 'down') => {
    setOrder((prev) => {
      const next = [...prev];
      const target = direction === 'up' ? idx - 1 : idx + 1;
      if (target < 0 || target >= next.length) return prev;
      [next[idx], next[target]] = [next[target], next[idx]];
      return next;
    });
  }, []);

  const handleDrop = useCallback((dropIdx: number) => {
    if (dragIdx === null || dragIdx === dropIdx) return;
    setOrder((prev) => {
      const next = [...prev];
      const [moved] = next.splice(dragIdx, 1);
      next.splice(dropIdx, 0, moved);
      return next;
    });
    setDragIdx(null);
  }, [dragIdx]);

  const setRowSize = useCallback((field: string, size: number) => {
    setSizes((prev) => ({ ...prev, [field]: Math.max(1, Math.min(12, size)) }));
  }, []);

  const handleApply = useCallback(() => {
    const fields = order.filter((f) => visible.has(f));
    onApply(fields, sizes);
    onClose();
  }, [order, visible, sizes, onApply, onClose]);

  const handleSelectAll = useCallback(() => setVisible(new Set(allFields)), [allFields]);
  const handleSelectNone = useCallback(() => {
    const first = order[0];
    setVisible(new Set(first ? [first] : []));
  }, [order]);

  const visibleCount = useMemo(() => order.filter((f) => visible.has(f)).length, [order, visible]);

  if (!open) return null;

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.5)' }}
      onClick={onClose}>
      <div style={{ background: bg, border: `1px solid ${border}`, borderRadius: 10, boxShadow: '0 16px 48px rgba(0,0,0,0.4)', width: 560, maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}
        onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', borderBottom: `1px solid ${border}` }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: accent }}>Detail Form Layout</div>
            <div style={{ fontSize: 11, color: textMuted, marginTop: 2 }}>{visibleCount} of {allFields.length} fields · drag or arrows to reorder</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={handleSelectAll} style={{ padding: '4px 10px', fontSize: 11, fontWeight: 600, border: `1px solid ${border}`, borderRadius: 4, background: 'transparent', color: textMuted, cursor: 'pointer' }}>All</button>
            <button onClick={handleSelectNone} style={{ padding: '4px 10px', fontSize: 11, fontWeight: 600, border: `1px solid ${border}`, borderRadius: 4, background: 'transparent', color: textMuted, cursor: 'pointer' }}>Min</button>
          </div>
        </div>

        {/* Column headers */}
        <div style={{ display: 'flex', alignItems: 'center', padding: '6px 18px', borderBottom: `1px solid ${border}`, background: bgAlt, fontSize: 10, fontWeight: 700, color: textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          <span style={{ width: 30 }}></span>
          <span style={{ width: 30 }}></span>
          <span style={{ flex: 1 }}>Field</span>
          <span style={{ width: 100, textAlign: 'center' }}>Behavior</span>
          <span style={{ width: 70, textAlign: 'center' }}>Rows</span>
        </div>

        {/* Field list */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {order.map((field, idx) => {
            const isVisible = visible.has(field);
            const beh = fieldBehaviors[field] || {};
            const behInfo = BEHAVIOR_LABELS[beh.type] || null;
            const isSizable = SIZABLE_TYPES.includes(beh.type || '') || beh.type === 'json';
            const currentSize = sizes[field] || (beh.type === 'json' ? 4 : beh.type === 'textarea' ? 3 : 1);

            return (
              <div
                key={field}
                draggable
                onDragStart={() => setDragIdx(idx)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => handleDrop(idx)}
                onDragEnd={() => setDragIdx(null)}
                style={{
                  display: 'flex', alignItems: 'center', padding: '5px 18px',
                  borderBottom: `1px solid ${isDark ? '#2e2e2e' : '#f0f0f0'}`,
                  background: dragIdx === idx ? (isDark ? '#094771' : '#cfe2ff') : 'transparent',
                  opacity: isVisible ? 1 : 0.4,
                  cursor: 'grab',
                  fontSize: 12,
                }}
                onMouseEnter={(e) => { if (dragIdx === null) (e.currentTarget).style.background = rowHover; }}
                onMouseLeave={(e) => { if (dragIdx !== idx) (e.currentTarget).style.background = 'transparent'; }}
              >
                {/* Checkbox */}
                <span style={{ width: 30 }}>
                  <input type="checkbox" checked={isVisible} onChange={() => toggleVisible(field)} />
                </span>

                {/* Arrows */}
                <span style={{ width: 30, display: 'flex', flexDirection: 'column', gap: 0 }}>
                  <button disabled={idx === 0} onClick={() => moveField(idx, 'up')}
                    style={{ background: 'none', border: 'none', color: textMuted, fontSize: 8, cursor: idx === 0 ? 'default' : 'pointer', opacity: idx === 0 ? 0.2 : 1, padding: 0 }}>▲</button>
                  <button disabled={idx === order.length - 1} onClick={() => moveField(idx, 'down')}
                    style={{ background: 'none', border: 'none', color: textMuted, fontSize: 8, cursor: idx === order.length - 1 ? 'default' : 'pointer', opacity: idx === order.length - 1 ? 0.2 : 1, padding: 0 }}>▼</button>
                </span>

                {/* Field name */}
                <span style={{ flex: 1, fontWeight: 500, color: isVisible ? text : textMuted }}>{field}</span>

                {/* Behavior */}
                <span style={{ width: 100, textAlign: 'center' }}>
                  {behInfo && (
                    <span style={{ fontSize: 10, fontWeight: 600, color: behInfo.color, padding: '1px 6px', borderRadius: 3, border: `1px solid ${behInfo.color}40`, background: `${behInfo.color}10` }}>
                      {behInfo.label}
                    </span>
                  )}
                </span>

                {/* Row size */}
                <span style={{ width: 70, textAlign: 'center' }}>
                  {isSizable ? (
                    <input type="number" min={1} max={12} value={currentSize}
                      onChange={(e) => setRowSize(field, parseInt(e.target.value) || 1)}
                      style={{ width: 40, textAlign: 'center', fontSize: 11, padding: '2px 4px', border: `1px solid ${border}`, borderRadius: 3, background: bgAlt, color: text }}
                    />
                  ) : (
                    <span style={{ fontSize: 10, color: textMuted }}>—</span>
                  )}
                </span>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 18px', borderTop: `1px solid ${border}` }}>
          <span style={{ fontSize: 11, color: textMuted }}>
            Drag fields to reorder · check to show/hide · set rows for text fields
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
