/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * configSlice.ts — Redux slice for app configuration (r25 source of truth)
 *
 * Holds the merged state of:
 *   - Static defaults (from config/*.ts files — ship with the build)
 *   - Dynamic overrides (fetched from wc3 on startup)
 *
 * Merge rule: wc3 overrides win for dynamic lists / model defaults when present.
 * Static-only lists are never overridden.
 *
 * The sync mechanism (useAppConfig) pushes r25 state → wc3 when admins save.
 * This makes r25 the source of truth; wc3 is persistence + backup.
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { SelectOption } from '@/config/selectLists';

// ---------------------------------------------------------------------------
// State shape
// ---------------------------------------------------------------------------

export interface ConfigState {
  /** When config was last loaded from wc3 (epoch ms, 0 = never) */
  lastSyncedAt: number;
  /** Whether the initial fetch from wc3 is in progress */
  loading: boolean;
  /** Whether local changes exist that haven't been pushed to wc3 */
  dirty: boolean;

  /** Per-model default values (merged: static + wc3 overrides) */
  modelDefaults: Record<string, Record<string, unknown>>;

  /** Select list overrides (key → options). Only dynamic (editable) lists appear here. */
  selectListOverrides: Record<string, SelectOption[]>;

  /** wc3 Setting record ID used for config storage (null until first fetch) */
  wc3SettingId: number | null;
}

const initialState: ConfigState = {
  lastSyncedAt: 0,
  loading: false,
  dirty: false,
  modelDefaults: {},
  selectListOverrides: {},
  wc3SettingId: null,
};

// ---------------------------------------------------------------------------
// Slice
// ---------------------------------------------------------------------------

const configSlice = createSlice({
  name: 'config',
  initialState,
  reducers: {
    /** Mark the fetch as starting */
    configLoadStart(state) {
      state.loading = true;
    },

    /**
     * Hydrate from wc3 setting record.
     * Payload is the parsed `data` JSON from the Setting record.
     */
    configLoaded(
      state,
      action: PayloadAction<{
        modelDefaults?: Record<string, Record<string, unknown>>;
        selectLists?: Record<string, SelectOption[]>;
        settingId: number | null;
      }>,
    ) {
      const { modelDefaults, selectLists, settingId } = action.payload;
      if (modelDefaults) {
        state.modelDefaults = modelDefaults;
      }
      if (selectLists) {
        state.selectListOverrides = selectLists;
      }
      state.wc3SettingId = settingId;
      state.lastSyncedAt = Date.now();
      state.loading = false;
      state.dirty = false;
    },

    /** Loading failed — clear loading flag but keep existing state */
    configLoadFailed(state) {
      state.loading = false;
    },

    /**
     * Update a single model's defaults (admin edit).
     * Marks state as dirty so the next sync push will fire.
     */
    setModelDefaults(
      state,
      action: PayloadAction<{ model: string; defaults: Record<string, unknown> }>,
    ) {
      state.modelDefaults[action.payload.model] = action.payload.defaults;
      state.dirty = true;
    },

    /**
     * Update a single select list's options (admin edit).
     */
    setSelectListOptions(
      state,
      action: PayloadAction<{ key: string; options: SelectOption[] }>,
    ) {
      state.selectListOverrides[action.payload.key] = action.payload.options;
      state.dirty = true;
    },

    /** Mark state as synced (after successful push to wc3) */
    configSynced(state, action: PayloadAction<{ settingId: number }>) {
      state.wc3SettingId = action.payload.settingId;
      state.lastSyncedAt = Date.now();
      state.dirty = false;
    },

    /** Full reset to initial state */
    configReset() {
      return initialState;
    },
  },
});

export const {
  configLoadStart,
  configLoaded,
  configLoadFailed,
  setModelDefaults,
  setSelectListOptions,
  configSynced,
  configReset,
} = configSlice.actions;

export default configSlice.reducer;
