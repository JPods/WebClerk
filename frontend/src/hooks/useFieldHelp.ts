/**
 * useFieldHelp — lazy-fetch field help from coaching Settings.
 *
 * Fetches coaching data for a model on first access, caches in sessionStorage.
 * Provides getFieldHelp(fieldName) for Shift-for-Help tooltips.
 *
 * Shift-for-Help standard: readmes/wisdom/shift-for-help.md
 */
import { useState, useEffect, useCallback } from 'react';
import { getRecords } from '@/api/wcapi';

const CACHE_PREFIX = 'fieldHelp:';

interface FieldHelpData {
  field_help: Record<string, string>;
}

/** Get cached coaching data from sessionStorage */
function getCached(model: string): FieldHelpData | null {
  try {
    const raw = sessionStorage.getItem(CACHE_PREFIX + model);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/** Store coaching data in sessionStorage */
function setCache(model: string, data: FieldHelpData) {
  try {
    sessionStorage.setItem(CACHE_PREFIX + model, JSON.stringify(data));
  } catch {
    // sessionStorage full or unavailable — proceed without cache
  }
}

export function useFieldHelp(model: string | undefined) {
  const [helpData, setHelpData] = useState<FieldHelpData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!model) return;

    // Check cache first
    const cached = getCached(model);
    if (cached) {
      setHelpData(cached);
      return;
    }

    // Fetch from backend
    setLoading(true);
    getRecords('setting', { parent_model: model, purpose: 'wc:coaching', limit: 1 })
      .then((res: any) => {
        const records = res?.records || res?.results || [];
        const config = records[0]?.config || {};
        const data: FieldHelpData = {
          field_help: config.field_help || {},
        };
        setCache(model, data);
        setHelpData(data);
      })
      .catch(() => {
        // No coaching data for this model — cache empty to avoid re-fetching
        const empty: FieldHelpData = { field_help: {} };
        setCache(model, empty);
        setHelpData(empty);
      })
      .finally(() => setLoading(false));
  }, [model]);

  const getFieldHelp = useCallback(
    (fieldName: string): string | null => {
      return helpData?.field_help?.[fieldName] || null;
    },
    [helpData],
  );

  return { getFieldHelp, loading, helpData };
}

export default useFieldHelp;
