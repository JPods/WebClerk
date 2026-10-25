/**
 * jsonLimits — the JSON size limits a save must fit, checked before it leaves the browser.
 *
 * The numbers are served by the backend (/wcapi/_system_info/ → json_limits, from
 * common/models.py) and never copied here: one source. Backend is the law; this is the
 * courtesy that tells the user before the save, not after (Bill, 2026-10-24).
 *
 *   per_save — bytes one save may send for one field: send the change, not the record
 *   caps     — bytes a record may store per JSON field; a model may widen a field
 *              (Setting config: null = as big as its users need)
 */
import apiClient from '@/api/axios';
import { resolveModelName } from '@/api/modelNameResolver';

export interface JsonLimits {
  per_save: number;
  depth: number;
  caps: Record<string, number>;
  models: Record<string, { caps: Record<string, number | null>; depth: Record<string, number> }>;
}

export interface JsonLimitProblem {
  field: string;
  size: number;
  limit: number;
  kind: 'save' | 'record';
  /** What the user can do about it. */
  fix: string;
}

let limits: JsonLimits | null = null;
let loading: Promise<JsonLimits | null> | null = null;

/** Fetch the limits once; until they arrive nothing is checked here (the backend still is). */
export function loadJsonLimits(): Promise<JsonLimits | null> {
  if (limits) return Promise.resolve(limits);
  if (!loading) {
    loading = apiClient.get('/wcapi/_system_info/')
      .then(res => {
        const body: any = res.data;
        limits = (body?.data ?? body)?.json_limits ?? null;
        return limits;
      })
      .catch(() => { loading = null; return null; });
  }
  return loading;
}

export function jsonLimitsLoaded(): JsonLimits | null {
  return limits;
}

const bytes = (v: unknown) => new TextEncoder().encode(JSON.stringify(v)).length;
const kb = (n: number) => `${(n / 1000).toFixed(1)} KB`;

/** null = no limit for this model's field. */
function capFor(model: string, field: string): number | null {
  if (!limits) return null;
  const widened = limits.models[model]?.caps ?? {};
  if (field in widened) return widened[field];
  return limits.caps[field] ?? null;
}

function saveCapFor(model: string, field: string): number | null {
  if (!limits) return null;
  const top = field.split('.')[0];
  const widened = limits.models[model]?.caps ?? {};
  if (top in widened && widened[top] === null) return null;
  return limits.per_save;
}

/**
 * Problems with a save before it is sent.
 * @param payload  what will be sent (the changed fields)
 * @param record   the record as it will be after the save, when the caller holds it
 */
export function checkJsonLimits(model: string, payload: Record<string, any>,
                                record?: Record<string, any>): JsonLimitProblem[] {
  if (!limits) return [];
  model = resolveModelName(model);
  const problems: JsonLimitProblem[] = [];
  for (const [field, value] of Object.entries(payload)) {
    if (value === null || value === undefined || field.startsWith('_')) continue;
    const cap = saveCapFor(model, field);
    if (cap === null) continue;
    const size = bytes(value);
    if (size > cap) {
      problems.push({
        field, size, limit: cap, kind: 'save',
        fix: `One save may send ${kb(cap)} for a field; this sends ${kb(size)}. ` +
             `Save in smaller steps, changing one part at a time.`,
      });
    }
  }
  if (record) {
    for (const field of Object.keys(limits.caps)) {
      const value = record[field];
      if (value === null || value === undefined) continue;
      const cap = capFor(model, field);
      if (cap === null) continue;
      const size = bytes(value);
      if (size > cap) {
        problems.push({
          field, size, limit: cap, kind: 'record',
          fix: `${field} would be ${kb(size)}; this record may hold ${kb(cap)}. ` +
               `Remove entries no longer used, or move large content into a Document and link it.`,
        });
      }
    }
  }
  return problems;
}

/** One message for a toast, a title, or an error. */
export function describeJsonLimitProblems(problems: JsonLimitProblem[]): string {
  return problems.map(p => `Not saved — ${p.field}: ${p.fix}`).join(' ');
}
