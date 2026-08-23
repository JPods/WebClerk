/* LastChecked: 2026-08-03 | WhereUsed: OrgPanel, ContactDetail | WhoCreated: Claude */
/**
 * OrgCard — renders a single org record (customer, vendor, manufacturer, employee, rep)
 * from a detail_layout Setting. JSON-driven, same FieldRow as all ui.json pages.
 *
 * Usage:
 *   <OrgCard model="customer" data={customerRecord} isEditing={true} onChange={handleChange} />
 */
import React, { useState, useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { saveRecord, deleteRecord } from '@/api/wcapi';
import { useDetailLayout } from '@/hooks/useDetailLayout';
import FieldRow from '@/apps/transactions/components/detail/FieldRow';

export type OrgModel = 'customer' | 'vendor' | 'manufacturer' | 'employee' | 'rep';

export interface OrgCardProps {
  model: OrgModel;
  data: any;
  isEditing?: boolean;
  compact?: boolean;  // compact = single column, full = multi-column from layout
  onSave?: (record: any) => void;
  onDelete?: (id: number) => void;
  onClick?: (id: number) => void;
}

const OrgCard: React.FC<OrgCardProps> = ({
  model, data, isEditing: propEditing = false, compact = true, onSave, onDelete, onClick,
}) => {
  const dispatch = useDispatch();
  const { layout } = useDetailLayout(model);
  const [editing, setEditing] = useState(propEditing);
  const [editData, setEditData] = useState<any>({ ...data });
  const [saving, setSaving] = useState(false);

  useEffect(() => { setEditData({ ...data }); }, [data]);

  const handleChange = (field: string, value: unknown) => {
    setEditData((prev: any) => {
      if (!prev) return prev;
      if (!field.includes('.')) return { ...prev, [field]: value };
      const parts = field.split('.');
      const clone = JSON.parse(JSON.stringify(prev));
      let obj = clone;
      for (let i = 0; i < parts.length - 1; i++) {
        if (obj[parts[i]] == null || typeof obj[parts[i]] !== 'object') obj[parts[i]] = {};
        obj = obj[parts[i]];
      }
      obj[parts[parts.length - 1]] = value;
      return clone;
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const { uuid: _u, metadata: _m, refs: _r, prefs: _p, ...clean } = editData;
      const res = await saveRecord(model, clean);
      dispatch(showToast({ message: `${model} saved`, type: 'success' }));
      setEditing(false);
      onSave?.(res?.record || res);
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

  // Get fields — compact shows first column only, full shows all columns
  const headerSection = layout?.sections?.find((s: any) => s.type === 'header') as any;
  let fields: any[] = [];
  if (compact) {
    // Show key fields from first column
    const firstCol = headerSection?.columns?.[0];
    fields = firstCol?.fields || headerSection?.fields || [];
  }

  const currentData = editing ? editData : data;
  const displayName = data.company || data.attention || data.display_name || `#${data.id}`;

  return (
    <div
      className={`border rounded-lg p-2 text-xs ${editing ? 'border-blue-300 bg-blue-50/30 dark:bg-blue-900/10' : 'border-slate-200 dark:border-slate-700 hover:border-blue-300 cursor-pointer'}`}
      onClick={() => !editing && onClick?.(data.id)}
    >
      <div className="flex items-center gap-1 mb-1">
        <span className="font-medium text-slate-700 dark:text-slate-200 capitalize text-[11px]">{model}</span>
        <span className="text-[10px] text-slate-500 truncate">{displayName}</span>
        {data.id && <span className="text-[9px] text-slate-400 font-mono">#{data.id}</span>}
        <span className="flex-1" />
        {!editing && (
          <>
            <button onClick={(e) => { e.stopPropagation(); setEditing(true); }} className="text-[9px] text-slate-400 hover:text-blue-600 px-1">edit</button>
            <button onClick={(e) => { e.stopPropagation(); handleDelete(); }} className="text-[9px] text-slate-400 hover:text-red-600 px-1">del</button>
          </>
        )}
        {editing && (
          <>
            <button onClick={handleSave} disabled={saving} className="text-[9px] text-blue-600 hover:text-blue-800 px-1 font-medium">
              {saving ? '...' : 'save'}
            </button>
            <button onClick={() => { setEditing(false); setEditData({ ...data }); }} className="text-[9px] text-slate-400 hover:text-slate-600 px-1">cancel</button>
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

export default OrgCard;
