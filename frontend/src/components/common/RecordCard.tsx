/**
 * RecordCard — a record's card beside a panel list (Bill, 2026-10-30, 2026-10-31).
 *
 * The card is the model's config.layout.card spec (card.edit, else card.add), drawn by
 * CardRenderer.
 *   New ("+ add"): nothing is made until Save (Bill, 2026-10-16: an abandoned + add leaves
 *   nothing); Save makes the record under its parent (usePanelAdd's makeUnderParent).
 *   Existing (a row opened): the card reads the record and saves what changed. While it is
 *   open, a plain click or arrow in the list moves it to that row; unsaved edits are dropped,
 *   and the card offers Undo (the WC List Standard).
 * Every save is announced on the window channel, so the panel — here or in another window —
 * reads again.
 */
import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { getRecord, saveRecord } from '@/api/wcapi';
import CardRenderer from '@/components/cards/CardRenderer';
import type { CardSpec } from '@/components/cards/cardRegistry';

export interface ParentLink {
  /** The new record's field that links it to the parent (customer_id, contact_id). */
  field: string;
  id: number;
}

/** Edits a moved card dropped, kept for its Undo. */
export interface DroppedEdits {
  id: number;
  label: string;
  values: Record<string, unknown>;
}

interface Props {
  model: string;
  spec: CardSpec;
  anchor: DOMRect;
  /** New: make the record with what was typed. */
  make?: (typed: Record<string, unknown>) => Promise<unknown>;
  /** Existing: the record shown. */
  recordId?: number;
  /** Existing: edits to put back (Undo), and the edits the last move dropped. */
  restore?: Record<string, unknown> | null;
  dropped?: DroppedEdits | null;
  onUndo?: () => void;
  /** Existing: the card's unsaved edits, read by the panel before it moves the card. */
  onRegisterEdits?: (get: () => Record<string, unknown> | null) => void;
  onClose: () => void;
}

const WIDTH = 380;

const RecordCard: React.FC<Props> = ({ model, spec, anchor, make, recordId, restore, dropped, onUndo, onRegisterEdits, onClose }) => {
  const dispatch = useDispatch();
  const cardRef = useRef<HTMLDivElement>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown>>({});
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [busy, setBusy] = useState(false);
  const [pos, setPos] = useState({ top: anchor.bottom + 4, left: anchor.left });
  const isNew = recordId == null;

  // On screen: below the anchor, or above it when there is no room.
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

  // Existing: read the record; Undo's edits go back on once it has loaded.
  useEffect(() => {
    if (isNew) return;
    let live = true;
    getRecord(model, recordId!).then((r: any) => {
      if (!live) return;
      const rec = r?.record || r || {};
      const shown = Object.fromEntries(spec.fields.map((f) => [f.field, rec[f.field] ?? '']));
      setLoaded(shown);
      setValues(restore ? { ...shown, ...restore } : shown);
    });
    return () => { live = false; };
  }, [model, recordId, isNew, spec, restore]);

  const changed = () => Object.fromEntries(Object.entries(values).filter(([k, v]) => v !== loaded[k]));
  const current = useRef(changed);
  current.current = changed;
  useEffect(() => {
    onRegisterEdits?.(() => { const c = current.current(); return Object.keys(c).length ? c : null; });
  }, [onRegisterEdits]);

  const save = async () => {
    setBusy(true);
    try {
      if (isNew) {
        await make?.(values);
        dispatch(showToast({ message: `${spec.title || model} added`, type: 'success' }));
      } else {
        const edits = changed();
        if (Object.keys(edits).length) await saveRecord(model, { ...edits, id: recordId });
      }
      onClose();
    } catch (err: any) {
      dispatch(showToast({ message: `${isNew ? `Could not add ${model}` : 'Not saved'} — ${err?.message || err}`, type: 'error' }));
      setBusy(false);
    }
  };

  // Portal to <body>: a window frame's transform would otherwise offset position:fixed. A new
  // record's card closes on a click outside; an existing one stays while the list moves it.
  return createPortal(
    <>
      {isNew && <div className="fixed inset-0 z-[999]" onMouseDown={onClose} />}
      <div ref={cardRef} role="dialog" aria-label={isNew ? `Add ${model}` : `${model} #${recordId}`}
        className="fixed z-[1000] shadow-xl rounded-lg"
        style={{ top: pos.top, left: pos.left, width: WIDTH }} data-zone={`panel.card.${model} | RecordCard.tsx`}>
        {dropped && (
          <div role="status" className="flex items-center gap-2 px-3 py-1 text-xs rounded-t-lg"
            style={{ background: 'var(--db-row-checked, #fff3cd)', color: 'var(--db-text, #212529)' }}>
            Changes to {dropped.label} discarded
            <button type="button" onClick={onUndo} className="font-semibold underline"
              style={{ color: 'var(--db-accent, #0d6efd)' }}>Undo</button>
          </div>
        )}
        <CardRenderer spec={spec} data={values} isEditing
          onChange={(field, value) => setValues((v) => ({ ...v, [field]: value }))} />
        <div className="flex items-center gap-2 px-3 pb-3 -mt-1" style={{ background: 'var(--db-surface)' }}>
          <button type="button" disabled={busy} onClick={save}
            className="px-2 py-0.5 rounded text-xs bg-blue-600 text-white disabled:opacity-50">{isNew ? 'Add' : 'Save'}</button>
          <button type="button" disabled={busy} onClick={onClose}
            className="px-2 py-0.5 rounded text-xs border" style={{ borderColor: 'var(--db-border)' }}>{isNew ? 'Cancel' : 'Close'}</button>
        </div>
      </div>
    </>,
    document.body,
  );
};

export default RecordCard;
