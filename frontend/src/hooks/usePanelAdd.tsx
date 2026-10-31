/**
 * usePanelAdd — "+ add" for a panel list (Bill, 2026-10-30). The model's card
 * (config.layout.card.add) opens beside the button and makes the record on Save; a model
 * without one gets its record made now and opens in its own window — it needs an id to
 * open. Either way the save reaches the panel through the window channel.
 *
 * How the new record belongs to the panel's parent:
 *   parent    — its own link field (a contact's customer_id): `new` saves it linked.
 *   values    — fields copied from the parent (an action made from an order gets its
 *               customer): saved with the record.
 *   afterMade — the parent lists it in refs.links: the panel adds the new id there.
 */
import { useCallback, useRef, useState } from 'react';
import { useDispatch } from 'react-redux';
import { newRecord, saveRecord } from '@/api/wcapi';
import { getModelDefinition } from '@/api/modelDefinition';
import { getModelDetailPath, getModelWindowPreset, getModelWindowTitle } from '@/apps/common/components/panels/getModelDetailPath';
import { useWindowManager } from '@/context/WindowManagerContext';
import { showToast } from '@/store/slices/toastSlice';
import RecordCard, { type DroppedEdits, type ParentLink } from '@/components/common/RecordCard';
import type { CardSpec } from '@/components/cards/cardRegistry';

export interface PanelAddOptions {
  parent?: ParentLink;
  values?: Record<string, unknown>;
  afterMade?: (id: number) => Promise<void> | void;
}

/** Make the record under its parent, save what the user or the parent supplies. */
export async function makeUnderParent(model: string, opts: PanelAddOptions, typed: Record<string, unknown> = {}) {
  const made = await newRecord(model, opts.parent ? { _parent: opts.parent } : {});
  const values = { ...(opts.values || {}), ...typed };
  if (Object.keys(values).length) await saveRecord(model, { ...values, id: made.id });
  await opts.afterMade?.(made.id);
  return made;
}

export function usePanelAdd(model: string, opts: PanelAddOptions | null) {
  const dispatch = useDispatch();
  const windowManager = useWindowManager();
  const [card, setCard] = useState<{ spec: CardSpec; anchor: DOMRect } | null>(null);

  const onAdd = useCallback(async (anchorEl: HTMLElement) => {
    if (!opts) return;
    const anchor = anchorEl.getBoundingClientRect();
    try {
      const spec = (await getModelDefinition(model))?.config?.layout?.card?.add as CardSpec | undefined;
      if (spec?.fields?.length) { setCard({ spec, anchor }); return; }
      const made = await makeUnderParent(model, opts);
      windowManager.ensureWindow(getModelDetailPath(model, made.id),
        getModelWindowTitle(model, made.id, made.record?.ida), getModelWindowPreset(model));
    } catch (err: any) {
      const resp = err?.response?.data;
      dispatch(showToast({ message: `Could not add ${model}: ${resp?.message || err?.message || err}`, type: 'error' }));
    }
  }, [model, opts, windowManager, dispatch]);

  const addCard = card && opts ? (
    <RecordCard model={model} spec={card.spec} anchor={card.anchor} onClose={() => setCard(null)}
      make={(typed) => makeUnderParent(model, opts, typed)} />
  ) : null;

  return { onAdd: opts ? onAdd : undefined, addCard };
}

/** The card a model's records open in: card.edit, else card.add. */
async function cardSpec(model: string): Promise<CardSpec | undefined> {
  const card = (await getModelDefinition(model))?.config?.layout?.card;
  const spec = (card?.edit || card?.add) as CardSpec | undefined;
  return spec?.fields?.length ? spec : undefined;
}

/**
 * usePanelOpen — opening a row of a panel list (the WC List Standard, Bill 2026-10-31).
 * Double-click or Enter opens the record's card beside the row, or its own window when the
 * model has no card; Option-double-click opens a browser window of its own. While the card is
 * open, a plain click or arrow moves it to that row; unsaved edits are dropped with Undo.
 */
export function usePanelOpen(model: string) {
  const dispatch = useDispatch();
  const windowManager = useWindowManager();
  const [card, setCard] = useState<{ spec: CardSpec; anchor: DOMRect; id: number; label: string;
    restore?: Record<string, unknown> | null; dropped?: DroppedEdits | null } | null>(null);
  const edits = useRef<(() => Record<string, unknown> | null) | null>(null);
  const registerEdits = useCallback((get: () => Record<string, unknown> | null) => { edits.current = get; }, []);

  const open = useCallback(async (id: number, label: string, anchorEl: HTMLElement) => {
    const anchor = anchorEl.getBoundingClientRect();
    try {
      const spec = await cardSpec(model);
      if (spec) { setCard({ spec, anchor, id, label }); return; }
      windowManager.ensureWindow(getModelDetailPath(model, id), getModelWindowTitle(model, id, undefined, label),
        getModelWindowPreset(model));
    } catch (err: any) {
      dispatch(showToast({ message: `Could not open ${model}: ${err?.message || err}`, type: 'error' }));
    }
  }, [model, windowManager, dispatch]);

  /** A plain click or arrow: an open card moves to that row. */
  const move = useCallback((id: number, label: string, anchorEl: HTMLElement) => {
    setCard((c) => {
      if (!c || c.id === id) return c;
      const values = edits.current?.() ?? null;
      return { ...c, id, label, anchor: anchorEl.getBoundingClientRect(), restore: null,
        dropped: values ? { id: c.id, label: c.label, values } : null };
    });
  }, []);

  const undo = useCallback(() => {
    setCard((c) => c?.dropped ? { ...c, id: c.dropped.id, label: c.dropped.label,
      restore: c.dropped.values, dropped: null } : c);
  }, []);

  const openWindow = useCallback((id: number) => {
    window.open(getModelDetailPath(model, id), `${model}-${id}`, 'popup,width=1200,height=850');
  }, [model]);

  const recordCard = card ? (
    <RecordCard key={`${card.id}:${card.restore ? 'undo' : ''}`} model={model} spec={card.spec} anchor={card.anchor}
      recordId={card.id} restore={card.restore} dropped={card.dropped} onUndo={undo}
      onRegisterEdits={registerEdits} onClose={() => setCard(null)} />
  ) : null;

  return { open, move, openWindow, openId: card?.id ?? null, recordCard };
}
