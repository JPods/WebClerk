/* LastChecked: 2026-08-03 | WhereUsed: CommunicationsPanel, ContactDetail | WhoCreated: Claude */
/**
 * CommCard — renders a single communication record (email, phone, address, domain)
 * from a detail_layout Setting. JSON-driven, same FieldRow as UiDetail.
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
    if (!confirm(`Delete this ${model} record?`)) return;
    if (!confirm('CONFIRM: Permanently delete. This cannot be undone.')) return;
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
    <div
      className="db-panel-row px-3 py-2 text-xs"
      style={{
        borderBottom: '1px solid var(--db-border-light)',
        background: editing ? 'var(--db-row-active)' : undefined,
        color: 'var(--db-text)',
      }}
    >
      <div className="flex items-center gap-1 mb-1">
        <span className="font-medium capitalize text-[11px]" style={{ color: 'var(--db-text)' }}>{model}</span>
        {data.is_primary && <span className="text-[9px]" style={{ color: 'var(--db-accent-gold)' }}>★</span>}
        {data.id && <span className="text-[9px] font-mono" style={{ color: 'var(--db-text-dim)' }}>#{data.id}</span>}
        <span className="flex-1" />
        {!editing && (
          <>
            <button onClick={() => setEditing(true)} className="text-[9px] px-1" style={{ color: 'var(--db-text-muted)' }}>edit</button>
            <button onClick={handleDelete} className="text-[9px] px-1" style={{ color: 'var(--db-text-muted)' }}>del</button>
          </>
        )}
        {editing && (
          <>
            <button onClick={handleSave} disabled={saving} className="text-[9px] px-1 font-medium" style={{ color: 'var(--db-accent)' }}>
              {saving ? '...' : 'save'}
            </button>
            <button onClick={() => { setEditing(false); setEditData({ ...data }); onCancel?.(); }} className="text-[9px] px-1" style={{ color: 'var(--db-text-muted)' }}>cancel</button>
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
