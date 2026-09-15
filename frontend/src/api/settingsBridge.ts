import { getRecords, saveRecord } from "@/api/wcapi";

export interface SettingScope {
  purpose: string;
  parent_model?: string;
  name?: string;
  role?: string;
}

export interface SettingRecord<T = unknown> {
  id?: number;
  name?: string | null;
  purpose?: string | null;
  parent_model?: string | null;
  role?: string | null;
  config?: T | null;
  dt_created?: number;
  dt_modified?: number;
  is_active?: boolean;
}

/** Extract rows from wcapi getRecords() response.
 *  getRecords() already unwraps the ApiEnvelope (res.data.data),
 *  so the result is a GetListPayload with a .results array. */
function pickRows(result: any): SettingRecord[] {
  if (Array.isArray(result?.results)) return result.results as SettingRecord[];
  return [];
}

function sortLatest(a: SettingRecord, b: SettingRecord): number {
  const aTs = Number(a?.dt_modified ?? a?.dt_created ?? 0);
  const bTs = Number(b?.dt_modified ?? b?.dt_created ?? 0);
  if (aTs !== bTs) return bTs - aTs;
  return Number(b?.id ?? 0) - Number(a?.id ?? 0);
}

export async function fetchLatestSettingRecord<T = unknown>(
  scope: SettingScope,
): Promise<SettingRecord<T> | null> {
  const params: Record<string, unknown> = {
    purpose: scope.purpose,
    limit: 50,
  };
  if (scope.parent_model) params.parent_model = scope.parent_model;
  if (scope.name) params.name = scope.name;
  if (scope.role) params.role = scope.role;

  const result = await getRecords("setting", params);
  const rows = pickRows(result);
  if (!rows.length) return null;
  return [...rows].sort(sortLatest)[0] as SettingRecord<T>;
}

export async function fetchSettingRecords<T = unknown>(
  scope: SettingScope,
): Promise<SettingRecord<T>[]> {
  const params: Record<string, unknown> = {
    purpose: scope.purpose,
    limit: 200,
  };
  if (scope.parent_model) params.parent_model = scope.parent_model;
  if (scope.name) params.name = scope.name;
  if (scope.role) params.role = scope.role;

  const result = await getRecords("setting", params);
  return pickRows(result).sort(sortLatest) as SettingRecord<T>[];
}

export async function upsertSettingRecord<T = unknown>(args: {
  scope: SettingScope;
  config: T;
}): Promise<SettingRecord<T>> {
  const { scope, config } = args;
  const existing = await fetchLatestSettingRecord<T>(scope);

  const payload: Record<string, unknown> = {
    purpose: scope.purpose,
    config,
  };

  if (scope.parent_model) payload.parent_model = scope.parent_model;
  if (scope.name) payload.name = scope.name;
  if (scope.role) payload.role = scope.role;
  if (existing?.id) payload.id = existing.id;

  const saved = await saveRecord("setting", payload);
  return (saved as SettingRecord<T>) ?? ({ ...payload } as SettingRecord<T>);
}
