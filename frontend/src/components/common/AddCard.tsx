/**
 * AddCard — "+ add" on a panel opens the new record's card beside the button (Bill,
 * 2026-10-30). The card is the model's config.layout.card.add spec, drawn by CardRenderer.
 * Nothing is made until Save (Bill, 2026-10-16: an abandoned + add leaves nothing); Save
 * makes the record under its parent (usePanelAdd's makeUnderParent) with what was typed. The
 * save is announced on the window channel, so the panel — in this window or another —
 * reads again.
 */
import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import CardRenderer from '@/components/cards/CardRenderer';
import type { CardSpec } from '@/components/cards/cardRegistry';

export interface ParentLink {
  /** The new record's field that links it to the parent (customer_id, contact_id). */
  field: string;
  id: number;
}

interface Props {
  model: string;
  spec: CardSpec;
  anchor: DOMRect;
  /** Make the record with what was typed. */
  make: (typed: Record<string, unknown>) => Promise<unknown>;
  onClose: () => void;
}

const WIDTH = 380;

const AddCard: React.FC<Props> = ({ model, spec, anchor, make, onClose }) => {
  const dispatch = useDispatch();
  const cardRef = useRef<HTMLDivElement>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [busy, setBusy] = useState(false);
  const [pos, setPos] = useState({ top: anchor.bottom + 4, left: anchor.left });

  // On screen: below the button, or above it when there is no room.
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

  const save = async () => {
    setBusy(true);
    try {
      await make(values);
      dispatch(showToast({ message: `${spec.title || model} added`, type: 'success' }));
      onClose();
    } catch (err: any) {
      const resp = err?.response?.data;
      dispatch(showToast({ message: `Could not add ${model}: ${resp?.message || err?.message || err}`, type: 'error' }));
      setBusy(false);
    }
  };

  // Portal to <body>: a window frame's transform would otherwise offset position:fixed.
  return createPortal(
    <>
      <div className="fixed inset-0 z-[999]" onMouseDown={onClose} />
      <div ref={cardRef} role="dialog" aria-label={`Add ${model}`} className="fixed z-[1000] shadow-xl rounded-lg"
        style={{ top: pos.top, left: pos.left, width: WIDTH }} data-zone={`panel.add-card.${model} | AddCard.tsx`}>
        <CardRenderer spec={spec} data={values} isEditing
          onChange={(field, value) => setValues((v) => ({ ...v, [field]: value }))} />
        <div className="flex items-center gap-2 px-3 pb-3 -mt-1" style={{ background: 'var(--db-surface)' }}>
          <button type="button" disabled={busy} onClick={save}
            className="px-2 py-0.5 rounded text-xs bg-blue-600 text-white disabled:opacity-50">Add</button>
          <button type="button" disabled={busy} onClick={onClose}
            className="px-2 py-0.5 rounded text-xs border" style={{ borderColor: 'var(--db-border)' }}>Cancel</button>
        </div>
      </div>
    </>,
    document.body,
  );
};

export default AddCard;
