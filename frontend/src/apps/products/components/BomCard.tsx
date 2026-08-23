/* LastChecked: 2026-08-06 | WhereUsed: ItemDetail BOM tab | WhoCreated: Claude */
/**
 * BomCard — renders a single BOM component with inline editing.
 *
 * Editable fields: quantity, scrap_factor, sequence, is_optional,
 * is_alternate, alternate_group, dt_effective_from, dt_effective_to.
 *
 * Click row to open child item. Edit/delete inline.
 */
import React, { useState, useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { saveRecord, deleteRecord } from '@/api/wcapi';
import { formatPercent } from '@/utils/stringUtils';

export interface BomCardProps {
  data: any;
  parentItemId: number;
  isEditing?: boolean;
  selected?: boolean;
  onSave?: (record: any) => void;
  onDelete?: (id: number) => void;
  onSelect?: (id: number) => void;
  onOpen?: (itemId: number) => void;
}

const BomCard: React.FC<BomCardProps> = ({
  data, parentItemId, isEditing: propEditing = false, selected = false, onSave, onDelete, onSelect, onOpen,
}) => {
  const dispatch = useDispatch();
  const [editing, setEditing] = useState(propEditing);
  const [editData, setEditData] = useState<any>({ ...data });
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => { setEditData({ ...data }); }, [data]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const { uuid: _u, metadata: _m, refs: _r, prefs: _p, ...clean } = editData;
      const res = await saveRecord('bill_of_material', clean);
      dispatch(showToast({ message: 'BOM component saved', type: 'success' }));
      setEditing(false);
      setExpanded(false);
      onSave?.(res?.record || res);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Failed to save BOM component';
      dispatch(showToast({ message: msg, type: 'error' }));
    }
    setSaving(false);
  };

  const handleDelete = async () => {
    if (!data.id) return;
    try {
      await deleteRecord('bill_of_material', data.id);
      dispatch(showToast({ message: 'BOM component removed', type: 'success' }));
      onDelete?.(data.id);
    } catch {
      dispatch(showToast({ message: 'Failed to delete', type: 'error' }));
    }
  };

  const setField = (field: string, value: unknown) => {
    setEditData((prev: any) => ({ ...prev, [field]: value }));
  };

  const childCode = data.child_ida || data.config?.child_item_code || data.child_item_code || data.ida || '';
  const childDesc = data.child_description || data.config?.child_description || '';
  const qty = data.quantity ?? 0;
  const scrap = data.scrap_factor ?? 0;
  const seq = data.sequence ?? 0;
  const isOpt = data.is_optional ?? false;
  const uom = data.unit_of_measure || data.config?.uom || 'EA';

  const inputClass = 'px-1 py-0.5 border border-blue-300 dark:border-blue-600 rounded text-[11px] bg-white dark:bg-slate-800 text-slate-900 dark:text-white';

  return (
    <div className="border-b border-slate-100 dark:border-slate-700">
      {/* Main row */}
      <div
        className={`flex items-center gap-2 px-2 py-1 text-xs ${
          editing
            ? 'bg-blue-50/30 dark:bg-blue-900/20'
            : selected
              ? 'bg-blue-100 dark:bg-blue-900/30'
              : 'hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer'
        }`}
        onClick={() => !editing && onSelect?.(data.id)}
        onDoubleClick={() => !editing && onOpen?.(data.child_item_id || data.child_item || data.config?.child_item_id)}
      >
        {/* Sequence */}
        {editing ? (
          <input type="number" value={editData.sequence ?? ''} onChange={(e) => setField('sequence', parseInt(e.target.value) || 0)}
            className={`w-8 text-center ${inputClass}`} title="Sequence" />
        ) : (
          <span className="w-8 text-center text-slate-400 text-[10px]">{seq || '—'}</span>
        )}

        {/* Item code */}
        <span className="font-mono text-slate-700 dark:text-slate-200 w-28 truncate">{childCode}</span>

        {/* Description */}
        <span className="text-slate-500 dark:text-slate-400 flex-1 truncate">{childDesc}</span>

        {/* Quantity */}
        {editing ? (
          <input type="number" step="0.01" value={editData.quantity ?? ''} onChange={(e) => setField('quantity', parseFloat(e.target.value) || 0)}
            className={`w-16 text-right ${inputClass}`} />
        ) : (
          <span className="font-mono text-right w-16">{qty}</span>
        )}

        {/* Scrap factor */}
        {editing ? (
          <input type="number" step="0.01" min="0" max="0.99" value={editData.scrap_factor ?? ''} onChange={(e) => setField('scrap_factor', parseFloat(e.target.value) || 0)}
            className={`w-16 text-right ${inputClass}`} title="Scrap factor (0-0.99)" />
        ) : (
          <span className="text-right w-16 text-slate-400">{scrap > 0 ? formatPercent(scrap * 100) : '—'}</span>
        )}

        {/* UOM */}
        <span className="text-slate-400 w-8 text-[10px]">{uom}</span>

        {/* Optional flag */}
        {editing ? (
          <label className="w-12 flex items-center justify-center" onClick={(e) => e.stopPropagation()}>
            <input type="checkbox" checked={editData.is_optional ?? false} onChange={(e) => setField('is_optional', e.target.checked)}
              className="rounded" title="Optional component" />
          </label>
        ) : (
          <span className="w-12 text-center text-[10px] text-slate-400">{isOpt ? 'opt' : ''}</span>
        )}

        {/* Actions */}
        <div className="w-20 flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
          {!editing ? (
            <>
              <button onClick={() => { setEditing(true); setExpanded(true); }} className="text-[9px] text-slate-400 hover:text-blue-600">edit</button>
              <button onClick={handleDelete} className="text-[9px] text-slate-400 hover:text-red-600">del</button>
            </>
          ) : (
            <>
              <button onClick={handleSave} disabled={saving} className="text-[9px] text-blue-600 font-medium">{saving ? '...' : 'save'}</button>
              <button onClick={() => { setEditing(false); setExpanded(false); setEditData({ ...data }); }} className="text-[9px] text-slate-400">cancel</button>
            </>
          )}
        </div>
      </div>

      {/* Expanded edit fields */}
      {editing && expanded && (
        <div className="px-2 py-2 bg-blue-50/20 dark:bg-blue-900/10 border-t border-blue-100 dark:border-blue-800">
          <div className="grid grid-cols-4 gap-2 text-[11px]">
            {/* Alternate */}
            <label className="flex items-center gap-1 text-slate-600 dark:text-slate-400">
              <input type="checkbox" checked={editData.is_alternate ?? false} onChange={(e) => setField('is_alternate', e.target.checked)} className="rounded" />
              Alternate
            </label>
            <div>
              <span className="text-slate-500 dark:text-slate-400 text-[10px]">Alt group</span>
              <input type="text" value={editData.alternate_group ?? ''} onChange={(e) => setField('alternate_group', e.target.value)}
                placeholder="group name" className={`w-full ${inputClass}`} />
            </div>
            {/* Effective dates */}
            <div>
              <span className="text-slate-500 dark:text-slate-400 text-[10px]">Effective from</span>
              <input type="date" value={editData.dt_effective_from ?? ''} onChange={(e) => setField('dt_effective_from', e.target.value || null)}
                className={`w-full ${inputClass}`} />
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400 text-[10px]">Effective to</span>
              <input type="date" value={editData.dt_effective_to ?? ''} onChange={(e) => setField('dt_effective_to', e.target.value || null)}
                className={`w-full ${inputClass}`} />
            </div>
          </div>
          {/* Revision + change reason */}
          <div className="grid grid-cols-2 gap-2 mt-2 text-[11px]">
            <div>
              <span className="text-slate-500 dark:text-slate-400 text-[10px]">Revision</span>
              <input type="text" value={editData.revision ?? ''} onChange={(e) => setField('revision', e.target.value)}
                placeholder="rev" className={`w-full ${inputClass}`} />
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400 text-[10px]">Change reason</span>
              <input type="text" value={editData.change_reason ?? ''} onChange={(e) => setField('change_reason', e.target.value)}
                placeholder="reason for change" className={`w-full ${inputClass}`} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BomCard;
