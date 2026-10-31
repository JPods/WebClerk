/**
 * PrimaryContactCard — which of an org's contacts it shows, chosen beside the field.
 *
 * Bill, 2026-10-31: a de-normalized value is never edited where it is copied, only on the
 * record it comes from. An org's attention and email are its primary contact's; the field
 * opens this card to choose that contact from the org's own (its Contacts panel adds more).
 * The server takes the chosen contact's name, email, phone, address and domain.
 *
 * LastChecked: 2026-10-31 | WhereUsed: ModelDetailPage | WhoCreated: Bill+Claude
 */
import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { saveRecord } from '@/api/wcapi';

interface Props {
  model: string;
  org: Record<string, any>;
  anchor: DOMRect;
  /** Open a contact to change its own values. */
  onOpenContact: (id: number) => void;
  onChanged: () => Promise<void> | void;
  onClose: () => void;
}

const WIDTH = 320;

const PrimaryContactCard: React.FC<Props> = ({ model, org, anchor, onOpenContact, onChanged, onClose }) => {
  const dispatch = useDispatch();
  const cardRef = useRef<HTMLDivElement>(null);
  const contacts: { id: number; name: string }[] = org?.refs?.links?.contact || [];
  const [busy, setBusy] = useState(false);
  const [pos, setPos] = useState({ top: anchor.bottom + 4, left: anchor.left });

  useLayoutEffect(() => {
    const h = cardRef.current?.offsetHeight || 0;
    const left = Math.max(8, Math.min(anchor.left, window.innerWidth - WIDTH - 8));
    const below = anchor.bottom + 4;
    setPos({ top: below + h > window.innerHeight - 8 ? Math.max(8, anchor.top - h - 4) : below, left });
  }, [anchor]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const choose = async (id: number) => {
    if (id === org.contact_id) return;
    setBusy(true);
    try {
      await saveRecord(model, { id: org.id, contact_id: id });
      await onChanged();
      onClose();
    } catch (err: any) {
      dispatch(showToast({ message: `Not changed — ${err?.message || err}`, type: 'error' }));
    }
    setBusy(false);
  };

  return createPortal(
    <>
      <div className="fixed inset-0 z-[999]" onMouseDown={onClose} />
      <div ref={cardRef} role="dialog" aria-label="primary contact"
        className="fixed z-[1000] rounded-lg shadow-xl border border-[var(--db-border,#dee2e6)] bg-[var(--db-surface,#fff)] dark:bg-slate-800 dark:border-slate-600 p-3 text-[var(--db-text,#212529)] dark:text-slate-200"
        style={{ top: pos.top, left: pos.left, width: WIDTH }} data-zone="db.detail.primary-contact | PrimaryContactCard.tsx">
        <div className="flex items-center justify-between mb-1 text-xs font-bold">
          <span>Primary contact</span>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600" aria-label="close">✕</button>
        </div>
        <div className="text-[10px] text-[var(--db-text-muted,#6c757d)] mb-2">
          Name, email, phone and address come from this contact. Change them on the contact.
        </div>
        {contacts.length === 0 && (
          <div className="text-xs text-[var(--db-text-muted,#6c757d)]">No contacts yet — add one in the Contacts panel.</div>
        )}
        {contacts.map(c => (
          <div key={c.id} className="flex items-center gap-2 py-0.5 text-xs">
            <label className="flex-1 inline-flex items-center gap-1.5 cursor-pointer">
              <input type="radio" name="primary-contact" checked={c.id === org.contact_id} disabled={busy}
                onChange={() => choose(c.id)} />
              {c.name}
            </label>
            <button type="button" className="text-[var(--db-accent,#0d6efd)]" title="Open this contact to change its name, email, phone or address"
              onClick={() => { onOpenContact(c.id); onClose(); }}>↗</button>
          </div>
        ))}
      </div>
    </>,
    document.body,
  );
};

export default PrimaryContactCard;
