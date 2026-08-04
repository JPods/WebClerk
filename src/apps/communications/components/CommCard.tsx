/* LastChecked: 2026-08-03 | WhereUsed: CommunicationsPanel, ContactDetail | WhoCreated: Claude */
/**
 * CommCard — renders a single communication record (email, phone, address, domain)
 * from a detail_layout Setting. JSON-driven, same FieldRow as TransactionDetail.
 *
 * Usage:
 *   <CommCard model="email" data={emailRecord} isEditing={true} onChange={handleChange} />
 */
import React, { useState, useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { saveRecord, deleteRecord } from '@/api/wcapi';
import { useDetailLayout } from '@/hooks/useDetailLayout';
import FieldRow from '@/apps/transactions/components/detail/FieldRow';

export interface CommCardProps {
  model: 'email' | 'phone' | 'address' | 'domain';
  data: any;
  isEditing?: boolean;
  isNew?: boolean;
  onSave?: (record: any) => void;
  onDelete?: (id: number) => void;
  onCancel?: () => void;
}

const CommCard: React.FC<CommCardProps> = ({
  model, data, isEditing: propEditing = false, isNew = false, onSave, onDelete, onCancel,
}) => {
  const dispatch = useDispatch();
  const { layout } = useDetailLayout(model);
  const [editing, setEditing] = useState(propEditing || isNew);
  const [editData, setEditData] = useState<any>({ ...data });
  const [saving, setSaving] = useState(false);

  useEffect(() => { setEditData({ ...data }); }, [data]);

  const handleChange = (field: string, value: unknown) => {
    setEditData((prev: any) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const { uuid: _u, metadata: _m, refs: _r, prefs: _p, ...clean } = editData;
      const res = await saveRecord(model, clean);
      const saved = res?.record || res;
      dispatch(showToast({ message: `${model} saved`, type: 'success' }));
      setEditing(false);
      onSave?.(saved);
    } catch {
      dispatch(showToast({ message: `Failed to save ${model}`, type: 'error' }));
    }
    setSaving(false);
  };

  const handleDelete = async () => {
    if (!data.id) return;
    try {
      await deleteRecord(model, data.id);
      dispatch(showToast({ message: `${model} deleted`, type: 'success' }));
      onDelete?.(data.id);
    } catch {
      dispatch(showToast({ message: `Failed to delete ${model}`, type: 'error' }));
    }
  };

  // Get fields from layout
  const fields = layout?.sections?.[0]?.fields
    || (layout?.sections?.[0] as any)?.columns?.[0]?.fields
    || [];

  const currentData = editing ? editData : data;

  return (
    <div className={`border rounded-lg p-2 text-xs ${editing ? 'border-blue-300 bg-blue-50/30 dark:bg-blue-900/10' : 'border-slate-200 dark:border-slate-700'}`}>
      <div className="flex items-center gap-1 mb-1">
        <span className="font-medium text-slate-700 dark:text-slate-200 capitalize text-[11px]">{model}</span>
        {data.is_primary && <span className="text-[9px] text-amber-500">★</span>}
        {data.id && <span className="text-[9px] text-slate-400 font-mono">#{data.id}</span>}
        <span className="flex-1" />
        {!editing && (
          <>
            <button onClick={() => setEditing(true)} className="text-[9px] text-slate-400 hover:text-blue-600 px-1">edit</button>
            <button onClick={handleDelete} className="text-[9px] text-slate-400 hover:text-red-600 px-1">del</button>
          </>
        )}
        {editing && (
          <>
            <button onClick={handleSave} disabled={saving} className="text-[9px] text-blue-600 hover:text-blue-800 px-1 font-medium">
              {saving ? '...' : 'save'}
            </button>
            <button onClick={() => { setEditing(false); setEditData({ ...data }); onCancel?.(); }} className="text-[9px] text-slate-400 hover:text-slate-600 px-1">cancel</button>
          </>
        )}
      </div>
      {fields.map((f: any) => (
        <FieldRow
          key={f.field}
          field={f.field}
          label={f.label}
          data={currentData}
          isEditing={editing}
          options={f.options}
          fieldType={f.type}
          help={f.help}
          onChange={handleChange}
        />
      ))}
    </div>
  );
};

export default CommCard;
