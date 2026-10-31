/**
 * usePanelRecords — the one way a panel reads its records (Bill, 2026-10-27: panels inherit
 * their common behavior). 25 panels each wrote their own fetch with their own loading, error
 * and empty handling; this does it once and hands back the status the panel frame shows
 * (usePanelFrame({ status })).
 *
 * Reads go through the one read channel (getRecords); a panel whose rows come from a service
 * view instead (inventory layers) passes `read`. `reloadKey` is anything that changes
 * when the server's data may have changed — the parent's version or dt_modified: a held
 * answer is void after any server change (TFTS 2026-10-26, calculated values).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { getRecords } from '@/api/wcapi';
import { windowChannel } from '@/utils/windowChannel';
import type { PanelStatus } from '@/apps/common/components/CollapsiblePanel';

interface Options {
  /** Skip the read (no parent id yet). */
  enabled?: boolean;
  /** Changes when the server's data may have changed: the parent's version / dt_modified. */
  reloadKey?: unknown;
  emptyText?: string;
  /** Rows from a service view rather than the model channel; `model` then only names the read. */
  read?: (params: Record<string, unknown>) => Promise<unknown[]>;
}

export function usePanelRecords<T = Record<string, any>>(
  model: string, params: Record<string, unknown>, { enabled = true, reloadKey, emptyText, read }: Options = {},
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
      const p = JSON.parse(paramKey);
      if (read) {
        setRecords((await read(p)) as T[]);
      } else {
        const res: any = await getRecords(model, p);
        setRecords((res?.results || []) as T[]);
      }
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || `Could not read ${model}`);
    } finally {
      setLoading(false);
      setLoadedOnce(true);
    }
  }, [model, paramKey, enabled]); // eslint-disable-line react-hooks/exhaustive-deps -- read is a module function

  useEffect(() => { refresh(); }, [refresh, reloadKey]);

  // A record of this panel's model saved or deleted in any window: read again (Bill,
  // 2026-10-30 — + add opens a card or form elsewhere; its save updates the panel).
  useEffect(() => {
    const again = ({ model: saved }: { model?: string }) => { if (saved === model) refresh(); };
    const offSaved = windowChannel.on('record-saved', again);
    const offDeleted = windowChannel.on('record-deleted', again);
    return () => { offSaved(); offDeleted(); };
  }, [model, refresh]);

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
