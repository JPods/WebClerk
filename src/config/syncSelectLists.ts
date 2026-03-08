/**
 * syncSelectLists.ts — Sync editable select lists between r25 and wc3
 *
 * wc3 stores each select list as a Setting record with:
 *   - purpose: "admin_selectlist"
 *   - name:    the list key (e.g. "terms", "priority")
 *   - data:    { options: SelectOption[], label: string }
 *
 * Functions:
 *   fetchSelectListsFromWc3()   — pull all admin_selectlist settings
 *   fetchSelectListFromWc3(key) — pull a single list by key
 *   pushSelectListToWc3(key)    — push a single r25 list → wc3 setting
 *   pushAllSelectListsToWc3()   — push all editable r25 lists → wc3
 *   mergeWc3SelectLists()       — fetch from wc3 and merge into runtime
 *
 * Usage:
 *   import { pushAllSelectListsToWc3, mergeWc3SelectLists } from '@/config/syncSelectLists';
 *
 *   // On app init — merge wc3 overrides into runtime
 *   await mergeWc3SelectLists();
 *
 *   // Admin saves a list — push back to wc3
 *   await pushSelectListToWc3('terms');
 */

import { getRecords, saveRecord } from '@/api/wcapi';
import {
  DYNAMIC_LISTS,
  SELECT_LIST_MAP,
  type SelectOption,
} from './selectLists';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SETTING_PURPOSE = 'admin_selectlist';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Shape of a wc3 Setting record for select lists */
interface SelectListSetting {
  id: number;
  name: string;
  purpose: string;
  data: {
    options: SelectOption[];
    label: string;
  };
  is_active: boolean;
}

/** Result of a sync operation */
export interface SyncResult {
  key: string;
  action: 'created' | 'updated' | 'unchanged' | 'error';
  settingId?: number;
  optionCount?: number;
  error?: string;
}

// ---------------------------------------------------------------------------
// Fetch from wc3
// ---------------------------------------------------------------------------

/**
 * Fetch all admin_selectlist Setting records from wc3.
 * Returns a map of list key → SelectOption[].
 */
export async function fetchSelectListsFromWc3(): Promise<
  Record<string, { options: SelectOption[]; label: string; settingId: number }>
> {
  const res = await getRecords('setting', { purpose: SETTING_PURPOSE });
  const items: SelectListSetting[] = res.results || [];

  const map: Record<string, { options: SelectOption[]; label: string; settingId: number }> = {};
  for (const item of items) {
    if (item.name && item.data?.options) {
      map[item.name] = {
        options: item.data.options,
        label: item.data.label || item.name,
        settingId: item.id,
      };
    }
  }
  return map;
}

/**
 * Fetch a single select list from wc3 by key.
 * Returns the options array, or null if not found.
 */
export async function fetchSelectListFromWc3(
  key: string,
): Promise<{ options: SelectOption[]; label: string; settingId: number } | null> {
  const res = await getRecords('setting', { purpose: SETTING_PURPOSE, name: key });
  const items: SelectListSetting[] = res.results || [];
  const match = items.find((s) => s.name === key);
  if (!match?.data?.options) return null;
  return {
    options: match.data.options,
    label: match.data.label || key,
    settingId: match.id,
  };
}

// ---------------------------------------------------------------------------
// Push to wc3
// ---------------------------------------------------------------------------

/**
 * Push a single r25 select list to wc3 as a Setting record.
 * Creates or updates the Setting with purpose="admin_selectlist".
 */
export async function pushSelectListToWc3(key: string): Promise<SyncResult> {
  const listDef = SELECT_LIST_MAP[key];
  if (!listDef) {
    return { key, action: 'error', error: `Unknown list key: ${key}` };
  }
  if (!listDef.editable) {
    return { key, action: 'error', error: `List '${key}' is not editable` };
  }

  try {
    // Check if setting already exists
    const existing = await fetchSelectListFromWc3(key);

    const payload: Record<string, any> = {
      name: key,
      purpose: SETTING_PURPOSE,
      data: {
        options: listDef.options,
        label: listDef.label,
      },
    };

    if (existing) {
      // Check if data is unchanged
      const oldOpts = JSON.stringify(existing.options);
      const newOpts = JSON.stringify(listDef.options);
      if (oldOpts === newOpts && existing.label === listDef.label) {
        return {
          key,
          action: 'unchanged',
          settingId: existing.settingId,
          optionCount: listDef.options.length,
        };
      }
      // Update existing
      payload.id = existing.settingId;
    }

    const result = await saveRecord('setting', payload);
    return {
      key,
      action: existing ? 'updated' : 'created',
      settingId: result?.id ?? existing?.settingId,
      optionCount: listDef.options.length,
    };
  } catch (err: any) {
    return {
      key,
      action: 'error',
      error: err?.message || String(err),
    };
  }
}

/**
 * Push all editable r25 select lists to wc3.
 * Returns an array of SyncResult for each list.
 */
export async function pushAllSelectListsToWc3(): Promise<SyncResult[]> {
  const results: SyncResult[] = [];
  for (const listDef of DYNAMIC_LISTS) {
    const result = await pushSelectListToWc3(listDef.key);
    results.push(result);
  }
  return results;
}

// ---------------------------------------------------------------------------
// Merge from wc3 into runtime
// ---------------------------------------------------------------------------

/**
 * Fetch all admin_selectlist settings from wc3 and merge into the
 * runtime SELECT_LIST_MAP. wc3 options override r25 defaults for
 * any list that exists in wc3.
 *
 * Call this on app init so admin-edited lists are reflected in the UI.
 * Returns the keys that were overridden.
 */
export async function mergeWc3SelectLists(): Promise<string[]> {
  const wc3Lists = await fetchSelectListsFromWc3();
  const overridden: string[] = [];

  for (const [key, wc3Data] of Object.entries(wc3Lists)) {
    const listDef = SELECT_LIST_MAP[key];
    if (listDef && listDef.editable && wc3Data.options.length > 0) {
      listDef.options = wc3Data.options;
      if (wc3Data.label) {
        listDef.label = wc3Data.label;
      }
      overridden.push(key);
    }
  }

  return overridden;
}

// ---------------------------------------------------------------------------
// Utility: diff for admin UI
// ---------------------------------------------------------------------------

/**
 * Compare r25 list with wc3 list for a given key.
 * Useful for admin UI showing which lists are out of sync.
 */
export async function diffSelectList(key: string): Promise<{
  key: string;
  r25Options: SelectOption[];
  wc3Options: SelectOption[] | null;
  inSync: boolean;
}> {
  const listDef = SELECT_LIST_MAP[key];
  const wc3 = await fetchSelectListFromWc3(key);

  const r25Options = listDef?.options ?? [];
  const wc3Options = wc3?.options ?? null;

  const inSync = wc3Options !== null
    && JSON.stringify(r25Options) === JSON.stringify(wc3Options);

  return { key, r25Options, wc3Options, inSync };
}
