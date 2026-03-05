/**
 * useTransactionDefaults
 *
 * Fetches the singleton Setting record (name="transaction_defaults",
 * purpose="React_settings") once on startup and caches it for the session.
 *
 * Returns a stable `defaults` object with fields used when creating new
 * transactions:
 *   - terms          (string)  e.g. "On Order"
 *   - due_date_period (number) days to add to dt for due_date
 *   - price_level    (string)  e.g. "retail"
 *   - priority       (string)  e.g. "standard"
 */
import { useState, useEffect, useCallback } from 'react';
import { getRecords } from '@/api/wcapi';

export interface TransactionDefaults {
  terms: string;
  due_date_period: number;
  price_level: string;
  priority: string;
}

const FALLBACK: TransactionDefaults = {
  terms: 'On Order',
  due_date_period: 1,
  price_level: 'retail',
  priority: 'standard',
};

// Module-level cache so every consumer shares the same data without re-fetching.
let cached: TransactionDefaults | null = null;
let cachePromise: Promise<TransactionDefaults> | null = null;

async function loadDefaults(): Promise<TransactionDefaults> {
  try {
    const res = await getRecords('setting', {
      name: 'transaction_defaults',
      purpose: 'React_settings',
      is_active: true,
      limit: 1,
    });

    const record = res?.results?.[0];
    if (record?.data) {
      const d = record.data;
      cached = {
        terms: d.terms ?? FALLBACK.terms,
        due_date_period: Number(d.due_date_period ?? FALLBACK.due_date_period),
        price_level: d.price_level ?? FALLBACK.price_level,
        priority: d.priority ?? FALLBACK.priority,
      };
    } else {
      console.warn('[useTransactionDefaults] No transaction_defaults setting found, using fallback');
      cached = { ...FALLBACK };
    }
  } catch (err) {
    console.error('[useTransactionDefaults] Failed to fetch:', err);
    cached = { ...FALLBACK };
  }

  cachePromise = null; // allow future retry if needed
  return cached;
}

export function useTransactionDefaults() {
  const [defaults, setDefaults] = useState<TransactionDefaults>(cached ?? FALLBACK);
  const [loading, setLoading] = useState(!cached);

  const refresh = useCallback(async () => {
    cached = null;
    cachePromise = null;
    setLoading(true);
    const result = await loadDefaults();
    setDefaults(result);
    setLoading(false);
  }, []);

  useEffect(() => {
    if (cached) {
      setDefaults(cached);
      setLoading(false);
      return;
    }

    // Deduplicate concurrent calls
    if (!cachePromise) {
      cachePromise = loadDefaults();
    }

    cachePromise.then((result) => {
      setDefaults(result);
      setLoading(false);
    });
  }, []);

  return { defaults, loading, refresh };
}

/** Compute due_date by adding `due_date_period` days to `dt`. */
export function computeDueDate(dt: string, periodDays: number): string {
  const d = new Date(dt);
  d.setDate(d.getDate() + periodDays);
  return d.toISOString().split('T')[0];
}

export default useTransactionDefaults;
