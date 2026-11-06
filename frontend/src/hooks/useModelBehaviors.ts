/**
 * useModelBehaviors — a model's field behaviors as the screen reads them, from its wc:model
 * Setting (fieldBehaviorsOf), fetched once per model and shared. The one source of a select's
 * options (Bill, 2026-11-05: "we should not have a difference between the selectlist and
 * approved values") — a card or form never carries options of its own.
 */
import { useEffect, useState } from 'react';
import { getRecords } from '@/api/wcapi';
import { fieldBehaviorsOf } from '@/utils/fieldBehaviorsOf';

const cache = new Map<string, Promise<Record<string, any>>>();

export function loadModelBehaviors(model: string): Promise<Record<string, any>> {
  let pending = cache.get(model);
  if (!pending) {
    pending = getRecords('setting', { parent_model: model, purpose: 'wc:model', limit: 1 })
      .then((res: any) => fieldBehaviorsOf(res?.results?.[0]?.config))
      .catch(() => ({}));
    cache.set(model, pending);
  }
  return pending;
}

export function useModelBehaviors(model: string): Record<string, any> {
  const [behaviors, setBehaviors] = useState<Record<string, any>>({});
  useEffect(() => {
    let live = true;
    if (model) loadModelBehaviors(model).then((b) => { if (live) setBehaviors(b); });
    return () => { live = false; };
  }, [model]);
  return behaviors;
}
