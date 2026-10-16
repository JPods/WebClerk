/**
 * CommunicationCard — a floating card over the contact for its phones, addresses or domains.
 *
 * Bill, 2026-10-16: opening the Phone record in its own window lost the contact. The card
 * floats beside the field instead. It still edits the Phone / Address / Domain record
 * itself (one way to edit, so the record and the contact's cache cannot drift); the
 * contact's list comes from its cache, refs.links.<kind>, which the server rebuilds after
 * each save. A new record is made only on Save, so an abandoned "+ add" leaves nothing.
 *
 * LastChecked: 2026-10-16 | WhereUsed: ModelDetailPage | WhoCreated: Bill+Claude
 */
import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { createRecord, deleteRecord, saveRecord } from '@/api/wcapi';
import type { CommunicationField } from '@/utils/communicationFields';

interface Props {
  comm: CommunicationField;
  /** The owning contact (its cache and pointer). */
  owner: Record<string, any>;
  ownerModel: string;
  anchor: DOMRect;
  /** Re-read the owner after a change here. */
  onChanged: () => Promise<void> | void;
  onClose: () => void;
}

const WIDTH = 360;

function errorText(err: any): string {
  const resp = err?.response?.data;
  const d = resp?.detail || resp?.message || resp?.error?.details || err?.message || String(err);
  return typeof d === 'string' ? d : JSON.stringify(d);
}

const CommunicationCard: React.FC<Props> = ({ comm, owner, ownerModel, anchor, onChanged, onClose }) => {
  const dispatch = useDispatch();
  const cardRef = useRef<HTMLDivElement>(null);
  const rows: Record<string, any>[] = owner?.refs?.links?.[comm.kind] || [];
  const primaryId = owner?.[comm.pointer];
  // editing: a record id, 'new', or null (list only). Open straight to the form when empty.
  const [editing, setEditing] = useState<number | 'new' | null>(rows.length ? null : 'new');
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [pos, setPos] = useState({ top: anchor.bottom + 4, left: anchor.left });

  // Keep the card on screen: below the field, or above it when there's no room.
  useLayoutEffect(() => {
    const h = cardRef.current?.offsetHeight || 0;
    const left = Math.max(8, Math.min(anchor.left, window.innerWidth - WIDTH - 8));
    const below = anchor.bottom + 4;
    const top = below + h > window.innerHeight - 8 ? Math.max(8, anchor.top - h - 4) : below;
    setPos({ top, left });
  }, [anchor, editing, rows.length]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const startEdit = (target: number | 'new') => {
    const row = target === 'new' ? {} : rows.find(r => r.id === target) || {};
    setValues(Object.fromEntries(comm.inputs.map(i => [i.field, row[i.cache || i.field] ?? ''])));
    setConfirmDelete(false);
    setEditing(target);
  };

  useEffect(() => { if (editing === 'new') startEdit('new'); }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const run = async (what: string, fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await onChanged();
      setEditing(null);
      setConfirmDelete(false);
    } catch (err) {
      dispatch(showToast({ message: `${what} failed: ${errorText(err)}`, type: 'error' }));
    }
    setBusy(false);
  };

  const save = () => {
    const filled = Object.fromEntries(Object.entries(values).map(([k, v]) => [k, String(v).trim()]));
    if (!Object.values(filled).some(Boolean)) { dispatch(showToast({ message: `Enter a ${comm.label}`, type: 'error' })); return; }
    return run('Save', () => editing === 'new'
      ? createRecord(comm.model, { ...filled, contact_id: owner.id })
      : saveRecord(comm.model, { ...filled, id: editing }));
  };

  const remove = () => run('Delete', () => deleteRecord(comm.model, editing as number));
  const makePrimary = (id: number) => run('Primary', () => saveRecord(ownerModel, { id: owner.id, [comm.pointer]: id }));

  const btn = 'px-2 py-0.5 rounded text-xs border border-[var(--db-border,#cbd5e1)] disabled:opacity-50';

  // Portal to <body>: a window frame's transform would otherwise offset position:fixed.
  return createPortal(
    <>
      {/* Click outside closes; nothing unsaved is kept. */}
      <div className="fixed inset-0 z-[999]" onMouseDown={onClose} />
      <div ref={cardRef} role="dialog" aria-label={`${comm.label}s`}
        className="fixed z-[1000] rounded-lg shadow-xl border border-[var(--db-border,#dee2e6)] bg-[var(--db-surface,#fff)] dark:bg-slate-800 dark:border-slate-600 p-3 text-[var(--db-text,#212529)] dark:text-slate-200"
        style={{ top: pos.top, left: pos.left, width: WIDTH }} data-zone="db.detail.communication-card | CommunicationCard.tsx">
        <div className="flex items-center justify-between mb-2 text-xs font-bold">
          <span>{comm.label}s</span>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600" aria-label="close">✕</button>
        </div>

        {rows.length > 0 && (
          <ul className="mb-2 divide-y divide-[var(--db-border,#e2e8f0)]">
            {rows.map(r => (
              <li key={r.id} className="flex items-center gap-2 py-1 text-xs">
                <span title={r.id === primaryId ? 'primary — shown on the contact' : 'make primary'}
                  className={r.id === primaryId ? 'text-amber-500' : 'text-slate-300 cursor-pointer hover:text-amber-400'}
                  onClick={() => r.id !== primaryId && !busy && makePrimary(r.id)}>★</span>
                <button type="button" className="flex-1 min-w-0 truncate text-left hover:underline"
                  onClick={() => startEdit(r.id)} disabled={busy}>{comm.line(r) || '(blank)'}</button>
              </li>
            ))}
          </ul>
        )}

        {editing !== null ? (
          <div className="border-t border-[var(--db-border,#e2e8f0)] pt-2">
            <div className="grid grid-cols-2 gap-2">
              {comm.inputs.map((inp, i) => (
                <label key={inp.field} className={`text-[10px] text-[var(--db-text-muted,#6c757d)] ${inp.wide ? 'col-span-2' : ''}`}>
                  {inp.label}
                  <input autoFocus={i === 0 || undefined} value={values[inp.field] ?? ''} disabled={busy}
                    onChange={e => setValues(v => ({ ...v, [inp.field]: e.target.value }))}
                    onKeyDown={e => { if (e.key === 'Enter') save(); }}
                    className="block w-full mt-0.5 px-1.5 py-1 text-xs rounded border border-[var(--db-border,#cbd5e1)] bg-transparent text-[var(--db-text,#212529)] dark:text-slate-200" />
                </label>
              ))}
            </div>
            <div className="flex items-center gap-2 mt-2">
              <button type="button" className={`${btn} bg-blue-600 text-white border-blue-600`} onClick={save} disabled={busy}>
                {editing === 'new' ? `Add ${comm.label}` : 'Save'}
              </button>
              <button type="button" className={btn} disabled={busy}
                onClick={() => (rows.length ? setEditing(null) : onClose())}>Cancel</button>
              {editing !== 'new' && (
                <button type="button" className={`${btn} ml-auto ${confirmDelete ? 'bg-red-600 text-white border-red-600' : 'text-red-600'}`}
                  disabled={busy} onClick={() => (confirmDelete ? remove() : setConfirmDelete(true))}>
                  {confirmDelete ? 'Confirm delete' : 'Delete'}
                </button>
              )}
            </div>
          </div>
        ) : (
          <button type="button" className={btn} onClick={() => startEdit('new')} disabled={busy}>+ add {comm.label}</button>
        )}
      </div>
    </>,
    document.body,
  );
};

export default CommunicationCard;
