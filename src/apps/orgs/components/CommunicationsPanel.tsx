/**
 * CommunicationsPanel — inline-editable email, phone, address, domain records.
 *
 * Fetches communications via Contact FK (source of truth).
 * Saves directly to communication records, not to org aspects.
 * Shows primary badges, verification status, opt-out flags.
 *
 * Usage:
 *   <CommunicationsPanel contactId={42} orgType="customer" />
 */
import { useCallback, useEffect, useState } from 'react';
import { getRecord, saveRecord, deleteRecord } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';
import { useDispatch } from 'react-redux';

interface CommRecord {
  id?: number;
  [key: string]: unknown;
}

interface Props {
  contactId: number | null;
  orgType?: string;
  readOnly?: boolean;
}

const COMM_TYPES = [
  { key: 'emails', model: 'email', label: 'Email', icon: '✉', addLabel: '+ Email',
    fields: ['email', 'name', 'type', 'is_primary', 'is_verified', 'opt_out'] },
  { key: 'phones', model: 'phone', label: 'Phone', icon: '☎', addLabel: '+ Phone',
    fields: ['number', 'country_code', 'name', 'format', 'opt_out'] },
  { key: 'addresses', model: 'address', label: 'Address', icon: '📍', addLabel: '+ Address',
    fields: ['address1', 'address2', 'city', 'state', 'zip', 'country', 'address_type'] },
  { key: 'domains', model: 'domain', label: 'Domain', icon: '🌐', addLabel: '+ Domain',
    fields: ['path', 'type', 'status'] },
];

export default function CommunicationsPanel({ contactId, readOnly }: Props) {
  const dispatch = useDispatch();
  const [comms, setComms] = useState<Record<string, CommRecord[]>>({});
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<CommRecord>({});
  const [expandedType, setExpandedType] = useState<string | null>('emails');

  const fetchComms = useCallback(async () => {
    if (!contactId) return;
    try {
      setLoading(true);
      const res = await getRecord('contact', contactId) as any;
      const record = res?.record || res;
      setComms({
        emails: record?.communications?.emails || [],
        phones: record?.communications?.phones || [],
        addresses: record?.communications?.addresses || [],
        domains: record?.communications?.domains || [],
      });
    } catch { /* silent — comms not available */ }
    finally { setLoading(false); }
  }, [contactId]);

  useEffect(() => { fetchComms(); }, [fetchComms]);

  const handleSave = useCallback(async (model: string, data: CommRecord) => {
    try {
      const payload = { ...data, contact_id: contactId };
      await saveRecord(model, payload);
      dispatch(showToast({ message: 'Saved', type: 'success' }));
      setEditingId(null);
      setEditDraft({});
      fetchComms();
    } catch (e: any) {
      dispatch(showToast({ message: e?.message || 'Save failed', type: 'error' }));
    }
  }, [contactId, dispatch, fetchComms]);

  const handleDelete = useCallback(async (model: string, id: number) => {
    if (!confirm('Delete this record?')) return;
    try {
      await deleteRecord(model, id);
      dispatch(showToast({ message: 'Deleted', type: 'success' }));
      fetchComms();
    } catch {
      dispatch(showToast({ message: 'Delete failed', type: 'error' }));
    }
  }, [dispatch, fetchComms]);

  const startAdd = useCallback((model: string) => {
    setEditingId(-1);
    setEditDraft({ _model: model });
  }, []);

  if (!contactId) return <div className="text-xs text-gray-400 p-3">No contact linked.</div>;

  return (
    <div className="divide-y divide-gray-100 dark:divide-gray-700">
      {COMM_TYPES.map((ct) => {
        const items = comms[ct.key] || [];
        const isExpanded = expandedType === ct.key;

        return (
          <div key={ct.key}>
            {/* Section header */}
            <button
              onClick={() => setExpandedType(isExpanded ? null : ct.key)}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            >
              <span>{ct.icon}</span>
              <span className="uppercase tracking-wider">{ct.label}</span>
              <span className="text-gray-400 font-normal">({items.length})</span>
              <span className="ml-auto text-[10px]">{isExpanded ? '▼' : '▶'}</span>
            </button>

            {isExpanded && (
              <div className="px-3 pb-2">
                {loading && <div className="text-[10px] text-gray-400">Loading...</div>}

                {/* Items */}
                {items.map((item: any) => {
                  const isEditing = editingId === item.id;

                  if (isEditing) {
                    return (
                      <div key={item.id} className="mb-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
                        <div className="grid grid-cols-2 gap-2">
                          {ct.fields.filter(f => typeof item[f] !== 'boolean').map((f) => (
                            <input key={f} placeholder={f}
                              value={String(editDraft[f] ?? item[f] ?? '')}
                              onChange={(e) => setEditDraft((d) => ({ ...d, [f]: e.target.value }))}
                              className="px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                            />
                          ))}
                        </div>
                        <div className="flex gap-2 mt-2">
                          <button onClick={() => handleSave(ct.model, { ...item, ...editDraft })}
                            className="px-2 py-1 text-[10px] font-semibold bg-blue-600 text-white rounded hover:bg-blue-700">Save</button>
                          <button onClick={() => { setEditingId(null); setEditDraft({}); }}
                            className="px-2 py-1 text-[10px] text-gray-500 rounded hover:bg-gray-100 dark:hover:bg-gray-700">Cancel</button>
                        </div>
                      </div>
                    );
                  }

                  // Display row
                  const primary = ct.fields[0]; // main display field
                  const secondary = ct.fields.slice(1, 3);
                  return (
                    <div key={item.id}
                      className="flex items-center gap-2 py-1.5 px-1 text-xs group hover:bg-gray-50 dark:hover:bg-gray-800 rounded"
                    >
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-gray-800 dark:text-gray-200">{item[primary] || '--'}</span>
                        {secondary.map((f) => item[f] && typeof item[f] !== 'boolean' ? (
                          <span key={f} className="ml-2 text-gray-400">{item[f]}</span>
                        ) : null)}
                      </div>
                      {/* Badges */}
                      {item.is_primary && <span className="px-1.5 py-0.5 text-[9px] font-bold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded">PRIMARY</span>}
                      {item.is_verified && <span className="px-1.5 py-0.5 text-[9px] font-bold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded">✓</span>}
                      {item.opt_out && <span className="px-1.5 py-0.5 text-[9px] font-bold bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400 rounded">OPT-OUT</span>}
                      {/* Actions */}
                      {!readOnly && (
                        <div className="opacity-0 group-hover:opacity-100 flex gap-1 transition">
                          <button onClick={() => { setEditingId(item.id); setEditDraft({}); }}
                            className="px-1.5 py-0.5 text-[10px] text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded">Edit</button>
                          <button onClick={() => handleDelete(ct.model, item.id)}
                            className="px-1.5 py-0.5 text-[10px] text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded">Del</button>
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Add new */}
                {!readOnly && editingId === -1 && (editDraft as any)?._model === ct.model ? (
                  <div className="mt-1 p-2 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800">
                    <div className="grid grid-cols-2 gap-2">
                      {ct.fields.filter(f => !f.startsWith('is_') && f !== 'opt_out').map((f) => (
                        <input key={f} placeholder={f}
                          value={String(editDraft[f] ?? '')}
                          onChange={(e) => setEditDraft((d) => ({ ...d, [f]: e.target.value }))}
                          className="px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                        />
                      ))}
                    </div>
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => { const { _model, ...rest } = editDraft; handleSave(ct.model, rest); }}
                        className="px-2 py-1 text-[10px] font-semibold bg-green-600 text-white rounded hover:bg-green-700">Add</button>
                      <button onClick={() => { setEditingId(null); setEditDraft({}); }}
                        className="px-2 py-1 text-[10px] text-gray-500 rounded hover:bg-gray-100 dark:hover:bg-gray-700">Cancel</button>
                    </div>
                  </div>
                ) : !readOnly && (
                  <button onClick={() => startAdd(ct.model)}
                    className="mt-1 px-2 py-1 text-[10px] text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition">
                    {ct.addLabel}
                  </button>
                )}

                {items.length === 0 && editingId !== -1 && (
                  <div className="text-[10px] text-gray-400 py-1">None</div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
