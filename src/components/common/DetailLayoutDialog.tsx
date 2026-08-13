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
import './DetailLayoutDialog.css';

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

const BEHAVIOR_LABELS: Record<string, string> = {
  email:     'Email →',
  phone:     'Phone →',
  address:   'Map →',
  geo:       'Geo →',
  url:       'Link →',
  select:    'Select ▾',
  lookup:    'Lookup ◎',
  currency:  '$ Currency',
  boolean:   '☑ Bool',
  json:      '{ } JSON',
  textarea:  '¶ Text',
  timestamp: '⏱ Time',
  readonly:  '🔒 Read',
  date:      '📅 Date',
  number:    '# Num',
  text:      'Abc',
};

// Fields that support multi-row sizing
const SIZABLE_TYPES = ['json', 'textarea', 'text'];

export default function DetailLayoutDialog({
  open, allFields, visibleFields, fieldBehaviors, rowSizes, onApply, onClose,
}: Props) {
  const [order, setOrder] = useState<string[]>([]);
  const [visible, setVisible] = useState<Set<string>>(new Set());
  const [sizes, setSizes] = useState<Record<string, number>>({});
  const [dragIdx, setDragIdx] = useState<number | null>(null);

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
    <div className="dld-overlay" onClick={onClose}>
      <div className="dld-panel" onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div className="dld-header">
          <div>
            <div className="dld-header-title">Detail Form Layout</div>
            <div className="dld-header-subtitle">{visibleCount} of {allFields.length} fields · drag or arrows to reorder</div>
          </div>
          <div className="dld-header-actions">
            <button onClick={handleSelectAll} className="dld-header-btn">All</button>
            <button onClick={handleSelectNone} className="dld-header-btn">Min</button>
          </div>
        </div>

        {/* Column headers */}
        <div className="dld-col-headers">
          <span className="dld-col-spacer"></span>
          <span className="dld-col-spacer"></span>
          <span className="dld-col-field">Field</span>
          <span className="dld-col-behavior">Behavior</span>
          <span className="dld-col-rows">Rows</span>
        </div>

        {/* Field list */}
        <div className="dld-field-list">
          {order.map((field, idx) => {
            const isVisible = visible.has(field);
            const beh = fieldBehaviors[field] || {};
            const behType: string = beh.type || '';
            const behLabel = BEHAVIOR_LABELS[behType] || null;
            const isSizable = SIZABLE_TYPES.includes(behType) || behType === 'json';
            const currentSize = sizes[field] || (behType === 'json' ? 4 : behType === 'textarea' ? 3 : 1);

            const rowClasses = [
              'dld-field-row',
              dragIdx === idx ? 'dld-field-row--dragging' : '',
              !isVisible ? 'dld-field-row--hidden' : '',
            ].filter(Boolean).join(' ');

            return (
              <div
                key={field}
                draggable
                onDragStart={() => setDragIdx(idx)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => handleDrop(idx)}
                onDragEnd={() => setDragIdx(null)}
                className={rowClasses}
              >
                {/* Checkbox */}
                <span className="dld-cell-check">
                  <input type="checkbox" checked={isVisible} onChange={() => toggleVisible(field)} />
                </span>

                {/* Arrows */}
                <span className="dld-cell-arrows">
                  <button disabled={idx === 0} onClick={() => moveField(idx, 'up')}
                    className="dld-arrow-btn">▲</button>
                  <button disabled={idx === order.length - 1} onClick={() => moveField(idx, 'down')}
                    className="dld-arrow-btn">▼</button>
                </span>

                {/* Field name */}
                <span className={isVisible ? 'dld-cell-name' : 'dld-cell-name dld-cell-name--hidden'}>{field}</span>

                {/* Behavior */}
                <span className="dld-cell-behavior">
                  {behLabel && (
                    <span className={`dld-behavior-badge dld-behavior-badge--${behType}`}>
                      {behLabel}
                    </span>
                  )}
                </span>

                {/* Row size */}
                <span className="dld-cell-rows">
                  {isSizable ? (
                    <input type="number" min={1} max={12} value={currentSize}
                      onChange={(e) => setRowSize(field, parseInt(e.target.value) || 1)}
                      className="dld-row-size-input"
                    />
                  ) : (
                    <span className="dld-cell-rows-dash">—</span>
                  )}
                </span>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="dld-footer">
          <span className="dld-footer-hint">
            Drag fields to reorder · check to show/hide · set rows for text fields
          </span>
          <div className="dld-footer-actions">
            <button onClick={onClose} className="dld-btn-cancel">Cancel</button>
            <button onClick={handleApply} className="dld-btn-apply">Apply</button>
          </div>
        </div>
      </div>
    </div>
  );
}
