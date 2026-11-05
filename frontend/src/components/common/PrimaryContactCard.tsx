/**
 * PrimaryContactCard — an org's contacts, beside the field that shows one of them.
 *
 * Bill, 2026-10-31: a de-normalized value is never edited where it is copied, only on the
 * record it comes from. An org's attention and email are its primary contact's; the field
 * opens this card to choose that contact from the org's own (its Contacts panel adds more).
 * Bill, 2026-11-05: from here a contact is also made the org's default bill-to or ship-to,
 * what the org lacks (address, phone, email, domain) is filled from it, and each contact's
 * name and communication records are edited in place — the name on the contact, each
 * communication in its own record's card (CommunicationCard), so nothing is edited where
 * it is copied. The server computes every value the org takes (from_contact command,
 * orgs/services/party_from_contact.py); the org follows a contact's change (Contact.save).
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
import CommunicationCard from './CommunicationCard';

interface Props {
  model: string;
  org: Record<string, any>;
  anchor: DOMRect;
  /** Open a contact to change its own values. */
  onOpenContact: (id: number) => void;
  onChanged: () => Promise<void> | void;
  onClose: () => void;
}

const WIDTH = 440;
const PARTIES = ['bill_to', 'ship_to'] as const;
const PARTY_LABEL: Record<string, string> = { bill_to: 'bill-to', ship_to: 'ship-to' };
const INPUT = 'px-1.5 py-0.5 text-[11px] rounded border border-[var(--db-input-border,#ced4da)] bg-[var(--db-input-bg,#fff)] text-[var(--db-text,#212529)] dark:bg-slate-900 dark:border-slate-600';

const PrimaryContactCard: React.FC<Props> = ({ model, org, anchor, onOpenContact, onChanged, onClose }) => {
  const dispatch = useDispatch();
  const cardRef = useRef<HTMLDivElement>(null);
  const contacts: { id: number; name: string }[] = org?.refs?.links?.contact || [];
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  const [records, setRecords] = useState<Record<number, any>>({});
  const [names, setNames] = useState<Record<number, { name_first: string; name_last: string }>>({});
  const [comm, setComm] = useState<{ id: number; field: string; anchor: DOMRect } | null>(null);
  const [pos, setPos] = useState({ top: anchor.bottom + 4, left: anchor.left });

  useLayoutEffect(() => {
    const h = cardRef.current?.offsetHeight || 0;
    const left = Math.max(8, Math.min(anchor.left, window.innerWidth - WIDTH - 8));
    const below = anchor.bottom + 4;
    setPos({ top: below + h > window.innerHeight - 8 ? Math.max(8, anchor.top - h - 4) : below, left });
  }, [anchor, open, records]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && !comm) onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, comm]);

  const fail = (what: string, err: any) =>
    dispatch(showToast({ message: `${what} — ${refusedFrom(err)?.message || err?.message || err}`, type: 'error' }));

  // A contact's record, read when its row opens: its names, and its communication cache (refs.links).
  const load = async (id: number) => {
    try {
      const response = await getRecord('contact', id);
      const rec = (response as any)?.record || response;
      setRecords((r) => ({ ...r, [id]: rec }));
      setNames((n) => ({ ...n, [id]: { name_first: rec?.name_first || '', name_last: rec?.name_last || '' } }));
      return rec;
    } catch (err) { fail('Could not read the contact', err); return null; }
  };
  const show = async (id: number) => {
    setOpen((o) => (o === id ? null : id));
    if (!records[id]) await load(id);
  };

  const choose = async (id: number) => {
    if (id === org.contact_id) return;
    setBusy(true);
    try {
      await saveRecord(model, { id: org.id, contact_id: id });
      await onChanged();
      onClose();
    } catch (err: any) { fail('Not changed', err); }
    setBusy(false);
  };

  /** The server takes the contact's values: a party, or what the org lacks. */
  const take = async (id: number, what: { bill_to?: boolean; ship_to?: boolean; fill?: boolean }) => {
    setBusy(true);
    try {
      // The version the card loaded: a stale one is refused (412), like any save.
      const res = await apiClient.post(`/wcapi/${model}/${org.id}/from_contact/`, { contact_id: id, version: org.version, ...what });
      const out = res.data?.data ?? res.data ?? {};
      const said = [...(out.set || []).map((r: string) => `${PARTY_LABEL[r] || r} set`),
                    ...(out.filled?.length ? [`filled ${out.filled.join(', ')}`] : what.fill ? ['nothing was missing'] : [])];
      dispatch(showToast({ message: `${model} takes contact #${id}: ${said.join('; ')}`, type: 'success' }));
      await onChanged();
    } catch (err: any) { fail('Not taken', err); }
    setBusy(false);
  };

  /** The contact's own name, saved on the contact; the org follows (attention derives on the server). */
  const saveName = async (id: number) => {
    const rec = records[id]; const n = names[id];
    if (!rec || !n) return;
    if (n.name_first === (rec.name_first || '') && n.name_last === (rec.name_last || '')) return;
    setBusy(true);
    try {
      await saveRecord('contact', { id, version: rec.version, name_first: n.name_first, name_last: n.name_last });
      await load(id);
      await onChanged();
      dispatch(showToast({ message: `contact #${id} renamed`, type: 'success' }));
    } catch (err: any) { fail('Not renamed', err); }
    setBusy(false);
  };

  const partyOf = (role: string) => org?.addresses?.[role]?.contact_id;
  const lines = (rec: any) => Object.entries(COMMUNICATION_FIELDS.contact).map(([field, c]) => ({
    field, label: c.label, value: communicationValue(c, rec), count: (rec?.refs?.links?.[c.kind] || []).length,
  }));
  const nameDirty = (id: number) => {
    const rec = records[id]; const n = names[id];
    return !!rec && !!n && (n.name_first !== (rec.name_first || '') || n.name_last !== (rec.name_last || ''));
  };

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
          The primary contact gives this {model} its name, email, phone and address. Bill-to and ship-to take a
          contact as the default party on documents; fill takes what this {model} lacks. Open a row to change
          the contact's name or its email, phone, address and domain — each in its own record.
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
                <span className="truncate">{records[c.id]?.attention || c.name}</span>
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
                title="This contact's name and communications" onClick={() => show(c.id)}>{open === c.id ? '▾' : '▸'}</button>
              <button type="button" className="text-[var(--db-accent,#0d6efd)]" title="Open this contact"
                onClick={() => { onOpenContact(c.id); onClose(); }}>↗</button>
            </div>
            {open === c.id && (
              <div className="ml-5 mt-1 text-[11px] space-y-1" data-wc="contact-communications">
                {!records[c.id] && <div className="text-[var(--db-text-muted,#6c757d)]">…</div>}
                {records[c.id] && (
                  <div className="flex items-center gap-2">
                    <span className="w-16 shrink-0 text-[var(--db-text-muted,#6c757d)]">name</span>
                    <input className={`${INPUT} w-28`} placeholder="first" value={names[c.id]?.name_first ?? ''} disabled={busy}
                      onChange={(e) => setNames((n) => ({ ...n, [c.id]: { ...n[c.id], name_first: e.target.value } }))}
                      onKeyDown={(e) => { if (e.key === 'Enter') saveName(c.id); }} />
                    <input className={`${INPUT} w-32`} placeholder="last" value={names[c.id]?.name_last ?? ''} disabled={busy}
                      onChange={(e) => setNames((n) => ({ ...n, [c.id]: { ...n[c.id], name_last: e.target.value } }))}
                      onKeyDown={(e) => { if (e.key === 'Enter') saveName(c.id); }} />
                    {nameDirty(c.id) && (
                      <button type="button" disabled={busy} className="text-[var(--db-accent,#0d6efd)] font-medium"
                        title="Save the name on the contact (Enter)" onClick={() => saveName(c.id)}>save</button>
                    )}
                  </div>
                )}
                {records[c.id] && lines(records[c.id]).map((l) => (
                  <div key={l.field} className="flex items-center gap-2">
                    <span className="w-16 shrink-0 text-[var(--db-text-muted,#6c757d)]">{l.label}</span>
                    <button type="button" disabled={busy}
                      className="flex-1 min-w-0 text-left truncate px-1.5 py-0.5 rounded border border-dashed border-[var(--db-border,#dee2e6)] hover:border-[var(--db-accent,#0d6efd)]"
                      title={l.value ? `Edit this ${l.label} in its record` : `Add ${l.label === 'address' ? 'an' : 'a'} ${l.label}`}
                      onClick={(e) => setComm({ id: c.id, field: l.field, anchor: e.currentTarget.getBoundingClientRect() })}>
                      {l.value || <span className="text-[var(--db-text-dim,#adb5bd)]">+ add {l.label}</span>}
                    </button>
                    {l.count > 1 && <span className="text-[var(--db-text-dim,#adb5bd)]" title={`${l.count} ${l.label} records`}>+{l.count - 1}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      {comm && records[comm.id] && COMMUNICATION_FIELDS.contact[comm.field] && (
        <CommunicationCard comm={COMMUNICATION_FIELDS.contact[comm.field]} owner={records[comm.id]} anchor={comm.anchor}
          onChanged={async () => { await load(comm.id); await onChanged(); }} onClose={() => setComm(null)} />
      )}
    </>,
    document.body,
  );
};

export default PrimaryContactCard;
