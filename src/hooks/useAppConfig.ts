/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * useAppConfig.ts — Hydrate config from wc3, expose merged state, sync back
 *
 * Lifecycle:
 *   1. On app startup, fetches the wc3 Setting record
 *      (name="app_config", purpose="React_settings")
 *   2. Merges wc3 overrides on top of the static defaults from config/*.ts
 *   3. Exposes merged getters for model defaults and select lists
 *   4. syncToBackend() pushes the current r25 state → wc3 (r25 is source of truth)
 *   5. ensureBackendMatch() verifies wc3 matches r25 and fixes any drift
 *
 * The hook is designed to be called once at the app root (via <AppConfigProvider>)
 * and consumed via `useSelector` or the convenience accessors below.
 */

import { useEffect, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import type { RootState, AppDispatch } from '@/store';
import {
  configLoadStart,
  configLoaded,
  configLoadFailed,
  configSynced,
} from '@/store/slices/configSlice';
import { getRecords, saveRecord } from '@/api/wcapi';
import { MODEL_DEFAULTS, getModelDefaults as staticModelDefaults } from '@/config/modelDefaults';
import {
  SELECT_LIST_MAP,
  DYNAMIC_LISTS,
  editableListKeys,
  type SelectOption,
} from '@/config/selectLists';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Setting record name used for the unified config store */
const CONFIG_SETTING_NAME = 'app_config';
const CONFIG_SETTING_PURPOSE = 'React_settings';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAppConfig() {
  const dispatch = useDispatch<AppDispatch>();
  const config = useSelector((s: RootState) => s.config);

  // ---- Initial load from wc3 --------------------------------------------
  useEffect(() => {
    if (config.lastSyncedAt > 0) return; // already loaded this session

    (async () => {
      dispatch(configLoadStart());
      try {
        const res = await getRecords('setting', {
          name: CONFIG_SETTING_NAME,
          purpose: CONFIG_SETTING_PURPOSE,
          is_active: true,
          limit: 1,
        });

        const record = res?.results?.[0];
        if (record?.config) {
          dispatch(
            configLoaded({
              modelDefaults: record.config.model_defaults ?? {},
              selectLists: record.config.select_lists ?? {},
              settingId: record.id ?? null,
            }),
          );
        } else {
          // No wc3 record yet — load with empty overrides
          dispatch(
            configLoaded({
              modelDefaults: {},
              selectLists: {},
              settingId: null,
            }),
          );
          console.info(
            '[useAppConfig] No app_config setting found in wc3. Using static defaults. Will create on first sync.',
          );
        }
      } catch (err) {
        console.error('[useAppConfig] Failed to fetch config from wc3:', err);
        dispatch(configLoadFailed());
      }
    })();
  }, [dispatch, config.lastSyncedAt]);

  // ---- Sync current r25 state → wc3 ------------------------------------
  const syncToBackend = useCallback(async () => {
    try {
      const payload: Record<string, unknown> = {
        name: CONFIG_SETTING_NAME,
        purpose: CONFIG_SETTING_PURPOSE,
        config: {
          model_defaults: buildFullModelDefaults(config.modelDefaults),
          select_lists: buildFullSelectLists(config.selectListOverrides),
          synced_at: Date.now(),
          source: 'r25',
        },
      };

      if (config.wc3SettingId) {
        // Update existing record
        payload.id = config.wc3SettingId;
      }

      const result = await saveRecord('setting', payload);
      const newId = result?.record?.id ?? result?.id ?? config.wc3SettingId;
      dispatch(configSynced({ settingId: newId }));
      console.info('[useAppConfig] Config synced to wc3, setting id:', newId);
      return { ok: true, settingId: newId };
    } catch (err) {
      console.error('[useAppConfig] Sync to wc3 failed:', err);
      return { ok: false, error: err };
    }
  }, [config.modelDefaults, config.selectListOverrides, config.wc3SettingId, dispatch]);

  // ---- Ensure wc3 matches r25 (drift check + fix) ----------------------
  const ensureBackendMatch = useCallback(async () => {
    const drifts: string[] = [];

    try {
      const res = await getRecords('setting', {
        name: CONFIG_SETTING_NAME,
        purpose: CONFIG_SETTING_PURPOSE,
        is_active: true,
        limit: 1,
      });

      const record = res?.results?.[0];
      if (!record?.config) {
        // No record at all — full sync needed
        drifts.push('no_config_record');
        const syncResult = await syncToBackend();
        return { drifts, fixed: syncResult.ok };
      }

      const backendDefaults = record.config.model_defaults ?? {};
      const backendLists = record.config.select_lists ?? {};
      const expected = buildFullModelDefaults(config.modelDefaults);
      const expectedLists = buildFullSelectLists(config.selectListOverrides);

      // Check model defaults
      for (const [model, fields] of Object.entries(expected)) {
        const backendFields = backendDefaults[model] ?? {};
        for (const [field, value] of Object.entries(fields as Record<string, unknown>)) {
          if (JSON.stringify(backendFields[field]) !== JSON.stringify(value)) {
            drifts.push(`model_default:${model}.${field}`);
          }
        }
      }

      // Check select lists
      for (const [key, options] of Object.entries(expectedLists)) {
        const backendOptions = backendLists[key];
        if (JSON.stringify(backendOptions) !== JSON.stringify(options)) {
          drifts.push(`select_list:${key}`);
        }
      }

      if (drifts.length > 0) {
        console.warn('[useAppConfig] Drift detected:', drifts);
        const syncResult = await syncToBackend();
        return { drifts, fixed: syncResult.ok };
      }

      return { drifts: [], fixed: true };
    } catch (err) {
      console.error('[useAppConfig] ensureBackendMatch failed:', err);
      return { drifts: ['fetch_error'], fixed: false };
    }
  }, [config.modelDefaults, config.selectListOverrides, syncToBackend]);

  return {
    config,
    syncToBackend,
    ensureBackendMatch,
  };
}

// ---------------------------------------------------------------------------
// Merged getters (usable anywhere via useSelector)
// ---------------------------------------------------------------------------

/**
 * Get the effective default value for a model field.
 * Checks config store override first, then static MODEL_DEFAULTS.
 */
export function useMergedModelDefault(modelKey: string, field: string): unknown {
  const override = useSelector(
    (s: RootState) => s.config.modelDefaults?.[modelKey]?.[field],
  );
  if (override !== undefined) return override;
  return staticModelDefaults(modelKey)[field];
}

/**
 * Get the effective defaults for a model (merged).
 */
export function useMergedModelDefaults(modelKey: string): Record<string, unknown> {
  const overrides = useSelector(
    (s: RootState) => s.config.modelDefaults?.[modelKey] ?? {},
  );
  return { ...staticModelDefaults(modelKey), ...overrides };
}

/**
 * Get the effective select list options for a key (merged).
 */
export function useMergedSelectList(key: string): SelectOption[] {
  const override = useSelector(
    (s: RootState) => s.config.selectListOverrides?.[key],
  );
  if (override && override.length > 0) return override;
  return SELECT_LIST_MAP[key]?.options ?? [];
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Build the full model defaults payload by merging static + store overrides.
 */
function buildFullModelDefaults(
  storeOverrides: Record<string, Record<string, unknown>>,
): Record<string, Record<string, unknown>> {
  const result: Record<string, Record<string, unknown>> = {};
  // Start with all static defaults
  for (const [key, entry] of Object.entries(MODEL_DEFAULTS)) {
    result[key] = { ...entry.defaults };
  }
  // Apply store overrides on top
  for (const [key, fields] of Object.entries(storeOverrides)) {
    result[key] = { ...(result[key] ?? {}), ...fields };
  }
  return result;
}

/**
 * Build the full select lists payload by merging static + store overrides.
 * Only includes editable (dynamic) lists.
 */
function buildFullSelectLists(
  storeOverrides: Record<string, SelectOption[]>,
): Record<string, SelectOption[]> {
  const result: Record<string, SelectOption[]> = {};
  for (const list of DYNAMIC_LISTS) {
    result[list.key] = storeOverrides[list.key] ?? list.options;
  }
  return result;
}

export default useAppConfig;
