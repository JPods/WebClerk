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
 *   name         = <storageKey>
 *   data         = { setups, active }
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
  uploadToServer: () => Promise<void>;
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
}

const STORAGE_PREFIX = "ColumnSetups:v1:";

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
      setSetups((prev) => {
        const filtered = prev.filter((s) => s.name !== name);
        const next = [...filtered, { name, config }];
        setActiveSetupName(name);
        persist(next, name);
        return next;
      });
    },
    [persist],
  );

  const updateSetup = useCallback(
    (name: string, config: ColumnSetupEntry) => {
      setSetups((prev) => {
        const next = prev.map((s) => (s.name === name ? { ...s, config } : s));
        persist(next, activeSetupName);
        return next;
      });
    },
    [persist, activeSetupName],
  );

  const renameSetup = useCallback(
    (oldName: string, newName: string) => {
      setSetups((prev) => {
        const next = prev.map((s) => (s.name === oldName ? { ...s, name: newName } : s));
        const newActive = activeSetupName === oldName ? newName : activeSetupName;
        setActiveSetupName(newActive);
        persist(next, newActive);
        return next;
      });
    },
    [persist, activeSetupName],
  );

  const deleteSetup = useCallback(
    (name: string) => {
      setSetups((prev) => {
        const next = prev.filter((s) => s.name !== name);
        const newActive = activeSetupName === name ? null : activeSetupName;
        setActiveSetupName(newActive);
        persist(next, newActive);
        return next;
      });
    },
    [persist, activeSetupName],
  );

  const clearActive = useCallback(() => {
    setActiveSetupName(null);
    persist(setups, null);
  }, [setups, persist]);

  // ── Server sync ─────────────────────────────────────────────────────────

  const uploadToServer = useCallback(async () => {
    if (!storageKey) return;
    setSyncing(true);
    try {
      // Check if a setting already exists for this config
      const existing = await getRecords("setting", {
        purpose: "list_column_config",
        name: storageKey,
      });
      const records = existing?.records ?? existing ?? [];
      const settingId = Array.isArray(records) && records.length > 0 ? records[0].id : undefined;

      const payload: Record<string, unknown> = {
        name: storageKey,
        purpose: "list_column_config",
        parent_model: modelKey ?? "",
        data: { v: 1, setups, active: activeSetupName },
      };
      if (settingId) {
        payload.id = settingId;
      }
      await saveRecord("setting", payload);
    } catch (err) {
      console.error("[useColumnSetups] uploadToServer failed:", err);
    } finally {
      setSyncing(false);
    }
  }, [storageKey, modelKey, setups, activeSetupName]);

  const downloadFromServer = useCallback(async () => {
    if (!storageKey) return;
    setSyncing(true);
    try {
      const result = await getRecords("setting", {
        purpose: "list_column_config",
        name: storageKey,
      });
      const records = result?.records ?? result ?? [];
      if (Array.isArray(records) && records.length > 0) {
        const data = records[0].data as PersistedPayload | undefined;
        if (data?.setups) {
          setSetups(data.setups);
          setActiveSetupName(data.active ?? null);
          persist(data.setups, data.active ?? null);
        }
      }
    } catch (err) {
      console.error("[useColumnSetups] downloadFromServer failed:", err);
    } finally {
      setSyncing(false);
    }
  }, [storageKey, persist]);

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
