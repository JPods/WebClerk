/**
 * usePanelRecords — the one way a panel reads its records (Bill, 2026-10-27: panels inherit
 * their common behavior). 25 panels each wrote their own fetch with their own loading, error
 * and empty handling; this does it once and hands back the status the panel frame shows
 * (usePanelFrame({ status })).
 *
 * Reads go through the one read channel (getRecords). `reloadKey` is anything that changes
 * when the server's data may have changed — the parent's version or dt_modified: a held
 * answer is void after any server change (TFTS 2026-10-26, calculated values).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { getRecords } from '@/api/wcapi';
import type { PanelStatus } from '@/apps/common/components/CollapsiblePanel';

interface Options {
  /** Skip the read (no parent id yet). */
  enabled?: boolean;
  /** Changes when the server's data may have changed: the parent's version / dt_modified. */
  reloadKey?: unknown;
  emptyText?: string;
}

export function usePanelRecords<T = Record<string, any>>(
  model: string, params: Record<string, unknown>, { enabled = true, reloadKey, emptyText }: Options = {},
) {
  const [records, setRecords] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadedOnce, setLoadedOnce] = useState(false);
  const paramKey = JSON.stringify(params);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const res: any = await getRecords(model, JSON.parse(paramKey));
      setRecords((res?.results || res?.records || []) as T[]);
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || `Could not read ${model}`);
    } finally {
      setLoading(false);
      setLoadedOnce(true);
    }
  }, [model, paramKey, enabled]);

  useEffect(() => { refresh(); }, [refresh, reloadKey]);

  const status: PanelStatus = useMemo(() => ({
    // Only the first read blocks the body; a refresh keeps the rows on screen.
    loading: loading && !loadedOnce,
    error,
    empty: loadedOnce && !loading && !error && records.length === 0,
    emptyText,
    onRetry: refresh,
  }), [loading, loadedOnce, error, records.length, emptyText, refresh]);

  return { records, loading, error, refresh, status };
}
