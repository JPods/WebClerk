/**
 * modelDefinition — a model's wc:model Setting, read once per page and kept until a setting
 * is saved (Fable review 2026-10-30: panels each read it on their own).
 */
import { getRecords } from '@/api/wcapi';
import { windowChannel } from '@/utils/windowChannel';

export interface ModelDefinition {
  id?: number;
  parent_model?: string;
  config?: Record<string, any> | null;
  prefs?: Record<string, any> | null;
}

const held = new Map<string, Promise<ModelDefinition | null>>();

windowChannel.on('record-saved', ({ model }) => { if (model === 'setting') held.clear(); });

export function getModelDefinition(model: string): Promise<ModelDefinition | null> {
  let answer = held.get(model);
  if (!answer) {
    answer = getRecords('setting', { parent_model: model, purpose: 'wc:model', limit: 1 })
      .then((res: any) => (res?.results?.[0] as ModelDefinition) ?? null)
      .catch((err) => { held.delete(model); throw err; });
    held.set(model, answer);
  }
  return answer;
}
