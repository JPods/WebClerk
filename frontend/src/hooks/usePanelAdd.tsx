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
import { useCallback, useState } from 'react';
import { useDispatch } from 'react-redux';
import { newRecord, saveRecord } from '@/api/wcapi';
import { getModelDefinition } from '@/api/modelDefinition';
import { getModelDetailPath, getModelWindowPreset, getModelWindowTitle } from '@/apps/common/components/panels/getModelDetailPath';
import { useWindowManager } from '@/context/WindowManagerContext';
import { showToast } from '@/store/slices/toastSlice';
import AddCard, { type ParentLink } from '@/components/common/AddCard';
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
    <AddCard model={model} spec={card.spec} anchor={card.anchor} onClose={() => setCard(null)}
      make={(typed) => makeUnderParent(model, opts, typed)} />
  ) : null;

  return { onAdd: opts ? onAdd : undefined, addCard };
}
