/* LastChecked: 2026-08-03 | WhereUsed: UiDetail | WhoCreated: Claude */
/**
 * DesignMode — visual form designer overlay.
 *
 * When active, the form becomes a layout editor:
 * - Click a column → see available fields not yet placed
 * - Click a field → it's added to that column
 * - Drag to reorder (future)
 * - Shift+click a placed field → remove it
 * - Save → updates the detail_layout Setting
 *
 * The form IS the designer. Same components, design overlay.
 */
import React, { useState, useCallback, useMemo } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { saveRecord } from '@/api/wcapi';
import type { DetailLayout } from '@/hooks/useDetailLayout';

// All possible fields a transaction form could show
// PJPV: display/edit binds to JSON aspects, not scalar columns
const ALL_FIELDS: Array<{ field: string; label: string; group: string; type?: string }> = [
  // Bill To (from addresses/emails/phones JSON aspects)
  { field: 'company', label: 'company', group: 'party' },
  { field: 'addresses.bill_to.attention', label: 'attention', group: 'party' },
  { field: 'phones.bill_to.number', label: 'phone', group: 'party' },
  { field: 'emails.bill_to.email', label: 'email', group: 'party' },
  { field: 'addresses.bill_to.full_address', label: 'address', group: 'party' },
  { field: 'addresses.bill_to.instructions', label: 'instructions', group: 'party' },
  // Ship To (from addresses/emails/phones JSON aspects)
  { field: 'addresses.ship_to.attention', label: 'attention', group: 'ship' },
  { field: 'phones.ship_to.number', label: 'phone', group: 'ship' },
  { field: 'emails.ship_to.email', label: 'email', group: 'ship' },
  { field: 'addresses.ship_to.full_address', label: 'address', group: 'ship' },
  { field: 'addresses.ship_to.instructions', label: 'instructions', group: 'ship' },
  { field: 'ship_via', label: 'ship via', group: 'ship', type: 'select' },
  { field: 'conditions_description', label: 'conditions', group: 'ship', type: 'select' },
  // Transaction
  { field: 'price_level', label: 'price lvl', group: 'transaction', type: 'select' },
  { field: 'terms', label: 'terms', group: 'transaction', type: 'select' },
  { field: 'status', label: 'status', group: 'transaction', type: 'select' },
  { field: 'dt_created', label: 'date', group: 'transaction', type: 'readonly' },
  { field: 'dt_needed', label: 'need by', group: 'transaction' },
  { field: 'source_name', label: 'source', group: 'transaction' },
  { field: 'priority', label: 'priority', group: 'transaction' },
  { field: 'parent_model', label: 'parent', group: 'transaction', type: 'readonly' },
  { field: 'ida', label: 'id', group: 'transaction', type: 'readonly' },
  { field: 'totals.total', label: 'total', group: 'transaction', type: 'readonly' },
  { field: 'totals.balance', label: 'balance', group: 'transaction', type: 'readonly' },
  { field: 'is_commission', label: 'commission', group: 'transaction' },
  { field: 'line_increment', label: 'line inc', group: 'transaction' },
];

export interface DesignModeProps {
  layout: DetailLayout;
  modelName: string;
  onLayoutChange: (layout: DetailLayout) => void;
}

const DesignMode: React.FC<DesignModeProps> = ({ layout, modelName, onLayoutChange }) => {
  const dispatch = useDispatch();
  const [activeColumn, setActiveColumn] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  // Find all fields currently placed on the form
  const placedFields = useMemo(() => {
    const placed = new Set<string>();
    for (const section of layout.sections || []) {
      if ((section as any).columns) {
        for (const col of (section as any).columns) {
          for (const f of col.fields || []) {
            placed.add(f.field);
          }
        }
      }
    }
    return placed;
  }, [layout]);

  // Fields available to add
  const availableFields = useMemo(() => {
    return ALL_FIELDS.filter(f => !placedFields.has(f.field));
  }, [placedFields]);

  // Add field to a column
  const addField = useCallback((colIdx: number, field: typeof ALL_FIELDS[0]) => {
    const newLayout = JSON.parse(JSON.stringify(layout));
    const headerSection = newLayout.sections.find((s: any) => s.type === 'header');
    if (headerSection?.columns?.[colIdx]) {
      headerSection.columns[colIdx].fields.push({
        field: field.field,
        label: field.label,
        type: field.type || 'editable',
      });
    }
    onLayoutChange(newLayout);
    setActiveColumn(null);
    dispatch(showToast({ message: `Added ${field.label} to column ${colIdx + 1}`, type: 'success' }));
  }, [layout, onLayoutChange, dispatch]);

  // Remove field from a column
  const removeField = useCallback((colIdx: number, fieldIdx: number) => {
    const newLayout = JSON.parse(JSON.stringify(layout));
    const headerSection = newLayout.sections.find((s: any) => s.type === 'header');
    if (headerSection?.columns?.[colIdx]) {
      const removed = headerSection.columns[colIdx].fields.splice(fieldIdx, 1);
      onLayoutChange(newLayout);
      dispatch(showToast({ message: `Removed ${removed[0]?.label || 'field'}`, type: 'info' }));
    }
  }, [layout, onLayoutChange, dispatch]);

  // Save layout to Setting
  const saveLayout = useCallback(async () => {
    setSaving(true);
    try {
      // Find the Setting by model_name + purpose
      const { getRecords } = await import('@/api/wcapi');
      const res = await getRecords('setting', { parent_model: modelName, purpose: 'wc:detail_layout', limit: 1 });
      const setting = res?.results?.[0] || res?.records?.[0];
      if (setting) {
        await saveRecord('setting', { id: setting.id, config: layout });
        dispatch(showToast({ message: 'Layout saved', type: 'success' }));
      } else {
        dispatch(showToast({ message: 'Layout Setting not found', type: 'error' }));
      }
    } catch {
      dispatch(showToast({ message: 'Failed to save layout', type: 'error' }));
    }
    setSaving(false);
  }, [layout, modelName, dispatch]);

  // Get columns from layout
  const headerSection = layout.sections?.find((s: any) => s.type === 'header') as any;
  const columns = headerSection?.columns || [];

  return (
    <div className="bg-amber-50 dark:bg-amber-900/20 border-2 border-dashed border-amber-400 rounded-lg p-3 mb-3">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-xs font-bold text-amber-700 dark:text-amber-300">DESIGN MODE</span>
        <span className="text-[10px] text-amber-600">Click a column to add fields. Shift+click a field to remove it.</span>
        <span className="flex-1" />
        <button onClick={saveLayout} disabled={saving}
          className="px-3 py-1 text-xs font-medium bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50">
          {saving ? 'Saving...' : 'Save Layout'}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {columns.map((col: any, colIdx: number) => (
          <div key={colIdx}
            className={`border rounded-lg p-2 cursor-pointer transition-colors ${activeColumn === colIdx ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-amber-300 hover:border-blue-400'}`}
            onClick={() => setActiveColumn(activeColumn === colIdx ? null : colIdx)}
          >
            <div className="text-[10px] font-bold text-slate-600 mb-1">{col.title}</div>
            {(col.fields || []).map((f: any, fIdx: number) => (
              <div key={f.field}
                className="text-[10px] px-1.5 py-0.5 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-600 mb-0.5 flex items-center gap-1 group"
                onClick={(e) => { if (e.shiftKey) { e.stopPropagation(); removeField(colIdx, fIdx); } }}
                title="Shift+click to remove"
              >
                <span className="text-slate-500 w-12 text-right shrink-0"
                  style={{ color: f.type === 'select' ? '#1e40af' : f.type === 'readonly' ? '#94a3b8' : '#64748b',
                           fontStyle: f.type === 'readonly' ? 'italic' : undefined,
                           fontWeight: f.type === 'search' ? 700 : undefined }}>
                  {f.label}
                </span>
                <span className="text-[9px] text-slate-400 font-mono">{f.field}</span>
                <span className="hidden group-hover:inline text-red-400 ml-auto text-[9px]">shift+click ✕</span>
              </div>
            ))}
            {activeColumn === colIdx && (
              <div className="mt-2 pt-2 border-t border-blue-200">
                <div className="text-[9px] font-medium text-blue-600 mb-1">Available Fields:</div>
                <div className="max-h-40 overflow-y-auto space-y-0.5">
                  {availableFields.map(f => (
                    <button key={f.field}
                      onClick={(e) => { e.stopPropagation(); addField(colIdx, f); }}
                      className="w-full text-left text-[10px] px-1.5 py-0.5 rounded hover:bg-blue-100 dark:hover:bg-blue-800 flex items-center gap-2"
                    >
                      <span className="text-blue-700 font-medium">{f.label}</span>
                      <span className="text-slate-400 font-mono text-[9px]">{f.field}</span>
                      <span className="text-slate-300 text-[9px] ml-auto">{f.group}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default DesignMode;
