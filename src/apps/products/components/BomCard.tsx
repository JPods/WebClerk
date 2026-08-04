/* LastChecked: 2026-08-03 | WhereUsed: ItemDetail BOM tab | WhoCreated: Claude */
/**
 * BomCard — renders a single BOM component record.
 * Shows parent→child relationship with quantity.
 * Used inside the Item detail BOM tab as a list.
 *
 * db.json handles standalone BOM admin.
 * This card handles the embedded view inside an item.
 */
import React, { useState, useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { saveRecord, deleteRecord } from '@/api/wcapi';

export interface BomCardProps {
  data: any;
  parentItemId: number;
  isEditing?: boolean;
  onSave?: (record: any) => void;
  onDelete?: (id: number) => void;
  onClick?: (itemId: number) => void;
}

const BomCard: React.FC<BomCardProps> = ({
  data, parentItemId, isEditing: propEditing = false, onSave, onDelete, onClick,
}) => {
  const dispatch = useDispatch();
  const [editing, setEditing] = useState(propEditing);
  const [editData, setEditData] = useState<any>({ ...data });
  const [saving, setSaving] = useState(false);

  useEffect(() => { setEditData({ ...data }); }, [data]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const { uuid: _u, metadata: _m, refs: _r, prefs: _p, ...clean } = editData;
      const res = await saveRecord('bill_of_material', clean);
      dispatch(showToast({ message: 'BOM component saved', type: 'success' }));
      setEditing(false);
      onSave?.(res?.record || res);
    } catch {
      dispatch(showToast({ message: 'Failed to save BOM component', type: 'error' }));
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

  const childCode = data.config?.child_item_code || data.child_item_code || data.ida || '';
  const childDesc = data.config?.child_description || data.child_description || '';
  const qty = data.quantity || data.config?.quantity || 0;

  return (
    <div className={`flex items-center gap-2 px-2 py-1 text-xs border-b border-slate-100 dark:border-slate-700 ${editing ? 'bg-blue-50/30' : 'hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer'}`}
      onClick={() => !editing && onClick?.(data.child_item_id || data.config?.child_item_id)}
    >
      <span className="font-mono text-slate-700 dark:text-slate-200 w-28 truncate">{childCode}</span>
      <span className="text-slate-500 flex-1 truncate">{childDesc}</span>
      {editing ? (
        <input type="number" value={editData.quantity || editData.config?.quantity || ''}
          onChange={(e) => setEditData((p: any) => ({ ...p, quantity: parseFloat(e.target.value) || 0 }))}
          className="w-16 text-right px-1 py-0.5 border border-blue-300 rounded text-[11px]" />
      ) : (
        <span className="font-mono text-right w-16">{qty}</span>
      )}
      <span className="text-slate-400 w-8">{data.unit_of_measure || data.config?.uom || 'EA'}</span>
      {!editing && (
        <>
          <button onClick={(e) => { e.stopPropagation(); setEditing(true); }} className="text-[9px] text-slate-400 hover:text-blue-600">edit</button>
          <button onClick={(e) => { e.stopPropagation(); handleDelete(); }} className="text-[9px] text-slate-400 hover:text-red-600">del</button>
        </>
      )}
      {editing && (
        <>
          <button onClick={handleSave} disabled={saving} className="text-[9px] text-blue-600 font-medium">{saving ? '...' : 'save'}</button>
          <button onClick={() => { setEditing(false); setEditData({ ...data }); }} className="text-[9px] text-slate-400">cancel</button>
        </>
      )}
    </div>
  );
};

export default BomCard;
