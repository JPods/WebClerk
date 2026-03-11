/**
 * useColumnSetups — manages named column-layout configurations.
 *
 * Each "setup" captures:
 *   - column order (array of persist-keys)
 *   - visibility  (Record<key, boolean>)
 *   - widths      (Record<key, string | undefined>)  – e.g. "120px"
 *   - sort        ({ field: string; direction: "asc" | "desc" } | null)
 *
 * Setups live in localStorage under
 *   `ColumnSetups:v1:${storageKey}`
 *
 * They can also be synced to wc3 via wcapi Setting records:
 *   purpose      = "list_column_config"
 *   parent_model = <modelKey>
 *   name         = "list_column_config:<modelKey>"
 *   data         = {
 *     v: 1,
 *     lists: {
 *       [storageKey]: { setups, active, current }
 *     }
 *   }
 */

import { useCallback, useEffect, useState } from "react";
import { getRecords, saveRecord } from "@/api/wcapi";

// ── Public types ──────────────────────────────────────────────────────────────

export interface ColumnSort {
  field: string;
  direction: "asc" | "desc";
}

export interface ColumnSetupEntry {
  /** Persist-key → boolean (true = visible) */
  visibility: Record<string, boolean>;
  /** Ordered array of persist-keys */
  order: string[];
  /** Persist-key → CSS width string, e.g. "120px" */
  widths: Record<string, string>;
  /** Active sort, or null */
  sort: ColumnSort | null;
  /** Optional per-column JSONB metadata used by setup editor side panel */
  jsonb?: Record<string, Record<string, unknown>>;
}

export interface ColumnSetup {
  name: string;
  config: ColumnSetupEntry;
}

export interface ColumnSetupsApi {
  setups: ColumnSetup[];
  activeSetupName: string | null;
  /** Apply a saved setup by name */
  applySetup: (name: string) => ColumnSetupEntry | null;
  /** Save current state under a name (creates or overwrites) */
  saveSetup: (name: string, config: ColumnSetupEntry) => void;
  /** Update an existing setup's config (for dialog edits) */
  updateSetup: (name: string, config: ColumnSetupEntry) => void;
  /** Rename a setup */
  renameSetup: (oldName: string, newName: string) => void;
  /** Delete a named setup */
  deleteSetup: (name: string) => void;
  /** Clear the "active" marker (revert to ad-hoc / current) */
  clearActive: () => void;
  /** Upload all setups to wc3 Setting record */
  uploadToServer: (currentConfig?: ColumnSetupEntry) => Promise<void>;
  /** Download setups from wc3 Setting record, merging / replacing local */
  downloadFromServer: () => Promise<void>;
  /** Whether a server sync is in progress */
  syncing: boolean;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

interface PersistedPayload {
  v: 1;
  setups: ColumnSetup[];
  active: string | null;
  current?: ColumnSetupEntry | null;
}

interface ServerCollectionPayload {
  v: 1;
  storageKey?: string;
  current?: ColumnSetupEntry | null;
  setups?: ColumnSetup[];
  active?: string | null;
  lists: Record<string, PersistedPayload>;
}

const STORAGE_PREFIX = "ColumnSetups:v1:";

function pickRecords(result: any): any[] {
  const records =
    result?.results ??
    result?.records ??
    result?.data?.results ??
    result?.data?.records ??
    result;
  return Array.isArray(records) ? records : [];
}

function normalizePersistedPayload(raw: any): PersistedPayload {
  return {
    v: 1,
    setups: Array.isArray(raw?.setups) ? raw.setups : [],
    active: typeof raw?.active === "string" ? raw.active : null,
    current: raw?.current ?? null,
  };
}

function readListFromServerData(
  serverData: any,
  storageKey: string,
): PersistedPayload | null {
  // New shape: data.lists[storageKey]
  const maybeLists = serverData?.lists;
  if (maybeLists && typeof maybeLists === "object") {
    const scoped = maybeLists[storageKey];
    if (scoped && typeof scoped === "object") {
      return normalizePersistedPayload(scoped);
    }
  }

  // Backward compatibility: single-list payload stored directly in data
  if (serverData && typeof serverData === "object" && Array.isArray(serverData.setups)) {
    return normalizePersistedPayload(serverData);
  }

  return null;
}

function readLocal(storageKey: string): PersistedPayload {
  try {
    const raw = localStorage.getItem(`${STORAGE_PREFIX}${storageKey}`);
    if (!raw) return { v: 1, setups: [], active: null };
    const parsed = JSON.parse(raw) as PersistedPayload;
    return { v: 1, setups: parsed.setups ?? [], active: parsed.active ?? null };
  } catch {
    return { v: 1, setups: [], active: null };
  }
}

function writeLocal(storageKey: string, payload: PersistedPayload) {
  try {
    localStorage.setItem(`${STORAGE_PREFIX}${storageKey}`, JSON.stringify(payload));
  } catch {
    // ignore quota errors
  }
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useColumnSetups(
  storageKey: string | undefined,
  modelKey?: string,
): ColumnSetupsApi {
  const [setups, setSetups] = useState<ColumnSetup[]>([]);
  const [activeSetupName, setActiveSetupName] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  // Hydrate from localStorage on mount / storageKey change
  useEffect(() => {
    if (!storageKey) return;
    const { setups: s, active } = readLocal(storageKey);
    setSetups(s);
    setActiveSetupName(active);
  }, [storageKey]);

  // Persist helper
  const persist = useCallback(
    (nextSetups: ColumnSetup[], nextActive: string | null) => {
      if (!storageKey) return;
      writeLocal(storageKey, { v: 1, setups: nextSetups, active: nextActive });
    },
    [storageKey],
  );

  const uploadSnapshotToServer = useCallback(
    async (
      nextSetups: ColumnSetup[],
      nextActiveSetupName: string | null,
      currentConfig?: ColumnSetupEntry,
    ) => {
      if (!storageKey || !modelKey) return;
      setSyncing(true);
      try {
        // One settings row per parent_model + purpose; list variants go in data.lists
        const existing = await getRecords("setting", {
          name: `list_column_config:${modelKey}`,
          purpose: "list_column_config",
          parent_model: modelKey,
          is_active: true,
          limit: 50,
        });
        const records = pickRecords(existing);
        const latestRecord =
          Array.isArray(records) && records.length > 0
            ? [...records].sort((a, b) => {
                const aTs = Number(a?.dt_modified ?? a?.dt_created ?? 0);
                const bTs = Number(b?.dt_modified ?? b?.dt_created ?? 0);
                if (aTs !== bTs) return bTs - aTs;
                return Number(b?.id ?? 0) - Number(a?.id ?? 0);
              })[0]
            : undefined;
        const settingId = latestRecord?.id;
        const existingData = latestRecord?.data;

        const activeConfig =
          nextActiveSetupName != null
            ? nextSetups.find((s) => s.name === nextActiveSetupName)?.config ?? null
            : null;

        const existingLists =
          existingData?.lists && typeof existingData.lists === "object"
            ? ({ ...existingData.lists } as Record<string, PersistedPayload>)
            : {};

        // Migrate old single-list format into collection format when encountered.
        if (Object.keys(existingLists).length === 0 && existingData?.setups) {
          existingLists[storageKey] = normalizePersistedPayload(existingData);
        }

        existingLists[storageKey] = {
          v: 1,
          setups: nextSetups,
          active: nextActiveSetupName,
          current: currentConfig ?? activeConfig,
        };

        const collection: ServerCollectionPayload = {
          v: 1,
          storageKey,
          current: currentConfig ?? activeConfig,
          setups: nextSetups,
          active: nextActiveSetupName,
          lists: existingLists,
        };

        const payload: Record<string, unknown> = {
          name: `list_column_config:${modelKey}`,
          purpose: "list_column_config",
          parent_model: modelKey,
          data: collection,
        };
        if (settingId) {
          payload.id = settingId;
        }
        await saveRecord("setting", payload);
      } catch (err) {
        console.error("[useColumnSetups] uploadSnapshotToServer failed:", err);
      } finally {
        setSyncing(false);
      }
    },
    [storageKey, modelKey],
  );

  const applySetup = useCallback(
    (name: string): ColumnSetupEntry | null => {
      const found = setups.find((s) => s.name === name);
      if (!found) return null;
      setActiveSetupName(name);
      persist(setups, name);
      return found.config;
    },
    [setups, persist],
  );

  const saveSetup = useCallback(
    (name: string, config: ColumnSetupEntry) => {
      const filtered = setups.filter((s) => s.name !== name);
      const next = [...filtered, { name, config }];
      setSetups(next);
      setActiveSetupName(name);
      persist(next, name);
      void uploadSnapshotToServer(next, name, config);
    },
    [persist, setups, uploadSnapshotToServer],
  );

  const updateSetup = useCallback(
    (name: string, config: ColumnSetupEntry) => {
      const next = setups.map((s) => (s.name === name ? { ...s, config } : s));
      setSetups(next);
      persist(next, activeSetupName);
      void uploadSnapshotToServer(next, activeSetupName, config);
    },
    [persist, activeSetupName, setups, uploadSnapshotToServer],
  );

  const renameSetup = useCallback(
    (oldName: string, newName: string) => {
      const next = setups.map((s) => (s.name === oldName ? { ...s, name: newName } : s));
      const newActive = activeSetupName === oldName ? newName : activeSetupName;
      setSetups(next);
      setActiveSetupName(newActive);
      persist(next, newActive);
      void uploadSnapshotToServer(next, newActive);
    },
    [persist, activeSetupName, setups, uploadSnapshotToServer],
  );

  const deleteSetup = useCallback(
    (name: string) => {
      const next = setups.filter((s) => s.name !== name);
      const newActive = activeSetupName === name ? null : activeSetupName;
      setSetups(next);
      setActiveSetupName(newActive);
      persist(next, newActive);
      void uploadSnapshotToServer(next, newActive);
    },
    [persist, activeSetupName, setups, uploadSnapshotToServer],
  );

  const clearActive = useCallback(() => {
    setActiveSetupName(null);
    persist(setups, null);
    void uploadSnapshotToServer(setups, null);
  }, [setups, persist, uploadSnapshotToServer]);

  // ── Server sync ─────────────────────────────────────────────────────────

  const uploadToServer = useCallback(async (currentConfig?: ColumnSetupEntry) => {
    await uploadSnapshotToServer(setups, activeSetupName, currentConfig);
  }, [setups, activeSetupName, uploadSnapshotToServer]);

  const downloadFromServer = useCallback(async () => {
    if (!storageKey || !modelKey) return;
    setSyncing(true);
    try {
      const result = await getRecords("setting", {
        purpose: "list_column_config",
        parent_model: modelKey,
      });
      const records = pickRecords(result);
      if (Array.isArray(records) && records.length > 0) {
        const serverData = records[0].data;
        const listPayload = readListFromServerData(serverData, storageKey);
        if (listPayload?.setups) {
          setSetups(listPayload.setups);
          setActiveSetupName(listPayload.active ?? null);
          persist(listPayload.setups, listPayload.active ?? null);
        }
      }
    } catch (err) {
      console.error("[useColumnSetups] downloadFromServer failed:", err);
    } finally {
      setSyncing(false);
    }
  }, [storageKey, modelKey, persist]);

  return {
    setups,
    activeSetupName,
    applySetup,
    saveSetup,
    updateSetup,
    renameSetup,
    deleteSetup,
    clearActive,
    uploadToServer,
    downloadFromServer,
    syncing,
  };
}
