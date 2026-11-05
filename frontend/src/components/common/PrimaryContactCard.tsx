/**
 * PrimaryContactCard — an org's contacts, beside the field that shows one of them.
 *
 * Bill, 2026-10-31: a de-normalized value is never edited where it is copied, only on the
 * record it comes from. An org's attention and email are its primary contact's; the field
 * opens this card to choose that contact from the org's own (its Contacts panel adds more).
 * Bill, 2026-11-05: from here a contact is also made the org's default bill-to or ship-to,
 * what the org lacks (address, phone, email, domain) is filled from it, and each contact's
 * communication records are in view. The server computes every value (from_contact command,
 * orgs/services/party_from_contact.py); the card only asks.
 *
 * LastChecked: 2026-11-05 | WhereUsed: DbForm | WhoCreated: Bill+Claude
 */
import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import apiClient from '@/api/axios';
import { getRecord, refusedFrom, saveRecord } from '@/api/wcapi';
import { COMMUNICATION_FIELDS, communicationValue } from '@/utils/communicationFields';

interface Props {
  model: string;
  org: Record<string, any>;
  anchor: DOMRect;
  /** Open a contact to change its own values. */
  onOpenContact: (id: number) => void;
  onChanged: () => Promise<void> | void;
  onClose: () => void;
}

const WIDTH = 420;
const PARTIES = ['bill_to', 'ship_to'] as const;
const PARTY_LABEL: Record<string, string> = { bill_to: 'bill-to', ship_to: 'ship-to' };

const PrimaryContactCard: React.FC<Props> = ({ model, org, anchor, onOpenContact, onChanged, onClose }) => {
  const dispatch = useDispatch();
  const cardRef = useRef<HTMLDivElement>(null);
  const contacts: { id: number; name: string }[] = org?.refs?.links?.contact || [];
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  const [records, setRecords] = useState<Record<number, any>>({});
  const [pos, setPos] = useState({ top: anchor.bottom + 4, left: anchor.left });

  useLayoutEffect(() => {
    const h = cardRef.current?.offsetHeight || 0;
    const left = Math.max(8, Math.min(anchor.left, window.innerWidth - WIDTH - 8));
    const below = anchor.bottom + 4;
    setPos({ top: below + h > window.innerHeight - 8 ? Math.max(8, anchor.top - h - 4) : below, left });
  }, [anchor, open, records]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  // A contact's communication records, read when its row opens (its own cache: refs.links).
  const show = async (id: number) => {
    setOpen((o) => (o === id ? null : id));
    if (!records[id]) {
      try {
        const response = await getRecord('contact', id);
        setRecords((r) => ({ ...r, [id]: (response as any)?.record || response }));
      } catch { /* the row shows nothing */ }
    }
  };

  const choose = async (id: number) => {
    if (id === org.contact_id) return;
    setBusy(true);
    try {
      await saveRecord(model, { id: org.id, contact_id: id });
      await onChanged();
      onClose();
    } catch (err: any) {
      dispatch(showToast({ message: `Not changed — ${refusedFrom(err)?.message || err?.message || err}`, type: 'error' }));
    }
    setBusy(false);
  };

  /** The server takes the contact's values: a party, or what the org lacks. */
  const take = async (id: number, what: { bill_to?: boolean; ship_to?: boolean; fill?: boolean }) => {
    setBusy(true);
    try {
      const res = await apiClient.post(`/wcapi/${model}/${org.id}/from_contact/`, { contact_id: id, ...what });
      const out = res.data?.data ?? res.data ?? {};
      const said = [...(out.set || []).map((r: string) => `${PARTY_LABEL[r] || r} set`),
                    ...(out.filled?.length ? [`filled ${out.filled.join(', ')}`] : what.fill ? ['nothing was missing'] : [])];
      dispatch(showToast({ message: `${model} takes contact #${id}: ${said.join('; ')}`, type: 'success' }));
      await onChanged();
    } catch (err: any) {
      dispatch(showToast({ message: `Not taken — ${refusedFrom(err)?.message || err?.message || err}`, type: 'error' }));
    }
    setBusy(false);
  };

  const partyOf = (role: string) => org?.addresses?.[role]?.contact_id;
  const lines = (rec: any) => Object.entries(COMMUNICATION_FIELDS.contact).map(([field, comm]) => {
    const count = (rec?.refs?.links?.[comm.kind] || []).length;
    return { field, label: comm.label, value: communicationValue(comm, rec), count };
  });

  return createPortal(
    <>
      <div className="fixed inset-0 z-[999]" onMouseDown={onClose} />
      <div ref={cardRef} role="dialog" aria-label="primary contact"
        className="fixed z-[1000] rounded-lg shadow-xl border border-[var(--db-border,#dee2e6)] bg-[var(--db-surface,#fff)] dark:bg-slate-800 dark:border-slate-600 p-3 text-[var(--db-text,#212529)] dark:text-slate-200"
        style={{ top: pos.top, left: pos.left, width: WIDTH }} data-zone="db.form.primary-contact | PrimaryContactCard.tsx">
        <div className="flex items-center justify-between mb-1 text-xs font-bold">
          <span>Contacts</span>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600" aria-label="close">✕</button>
        </div>
        <div className="text-[10px] text-[var(--db-text-muted,#6c757d)] mb-2">
          The primary contact gives this {model} its name, email, phone and address — change them on the contact.
          Bill-to and ship-to take a contact as the default party on documents; fill takes what this {model} lacks.
        </div>
        {contacts.length === 0 && (
          <div className="text-xs text-[var(--db-text-muted,#6c757d)]">No contacts yet — add one in the Contacts panel.</div>
        )}
        {contacts.map(c => (
          <div key={c.id} className="py-1 border-t border-[var(--db-border-light,#e9ecef)] dark:border-slate-700 first:border-t-0">
            <div className="flex items-center gap-2 text-xs">
              <label className="flex-1 inline-flex items-center gap-1.5 cursor-pointer min-w-0" title="Primary contact">
                <input type="radio" name="primary-contact" checked={c.id === org.contact_id} disabled={busy}
                  onChange={() => choose(c.id)} />
                <span className="truncate">{c.name}</span>
              </label>
              {PARTIES.map((role) => (
                <button key={role} type="button" disabled={busy}
                  className={`px-1.5 py-0.5 rounded border text-[10px] ${partyOf(role) === c.id
                    ? 'border-[var(--db-accent,#0d6efd)] text-[var(--db-accent,#0d6efd)] font-semibold'
                    : 'border-[var(--db-border,#dee2e6)] text-[var(--db-text-muted,#6c757d)] hover:text-[var(--db-text,#212529)]'}`}
                  title={partyOf(role) === c.id ? `Default ${PARTY_LABEL[role]} now` : `Make this contact the default ${PARTY_LABEL[role]}`}
                  onClick={() => take(c.id, { [role]: true })}>{PARTY_LABEL[role]}</button>
              ))}
              <button type="button" disabled={busy}
                className="px-1.5 py-0.5 rounded border border-[var(--db-border,#dee2e6)] text-[10px] text-[var(--db-text-muted,#6c757d)] hover:text-[var(--db-text,#212529)]"
                title={`Fill what this ${model} lacks (address, phone, email, domain) from this contact`}
                onClick={() => take(c.id, { fill: true })}>fill</button>
              <button type="button" className="text-[var(--db-text-muted,#6c757d)] hover:text-[var(--db-text,#212529)]"
                title="This contact's communications" onClick={() => show(c.id)}>{open === c.id ? '▾' : '▸'}</button>
              <button type="button" className="text-[var(--db-accent,#0d6efd)]" title="Open this contact to change its name, email, phone or address"
                onClick={() => { onOpenContact(c.id); onClose(); }}>↗</button>
            </div>
            {open === c.id && (
              <div className="ml-5 mt-1 text-[11px] space-y-0.5" data-wc="contact-communications">
                {!records[c.id] && <div className="text-[var(--db-text-muted,#6c757d)]">…</div>}
                {records[c.id] && lines(records[c.id]).map((l) => (
                  <div key={l.field} className="flex gap-2">
                    <span className="w-16 shrink-0 text-[var(--db-text-muted,#6c757d)]">{l.label}</span>
                    <span className="flex-1 truncate">{l.value || <span className="text-[var(--db-text-dim,#adb5bd)]">—</span>}</span>
                    {l.count > 1 && <span className="text-[var(--db-text-dim,#adb5bd)]" title={`${l.count} ${l.label} records`}>+{l.count - 1}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </>,
    document.body,
  );
};

export default PrimaryContactCard;
