import { useCallback, useEffect, useState } from "react";
import {
  fetchLatestSettingRecord,
  type SettingRecord,
  type SettingScope,
  upsertSettingRecord,
} from "@/api/settingsBridge";

export function useSettingRecord<T = unknown>(scope: SettingScope) {
  const [record, setRecord] = useState<SettingRecord<T> | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const latest = await fetchLatestSettingRecord<T>(scope);
      setRecord(latest);
      return latest;
    } catch (err) {
      setError((err as Error).message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [scope]);

  const save = useCallback(
    async (data: T) => {
      setSaving(true);
      setError(null);
      try {
        const next = await upsertSettingRecord<T>({ scope, config: data });
        setRecord(next);
        return next;
      } catch (err) {
        setError((err as Error).message);
        throw err;
      } finally {
        setSaving(false);
      }
    },
    [scope],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return {
    record,
    data: (record?.config as T | null | undefined) ?? null,
    loading,
    saving,
    error,
    refresh,
    save,
  };
}
