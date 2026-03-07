/**
 * useTransactionDefaults
 *
 * Thin wrapper around the unified config system (configSlice + useAppConfig).
 * Returns the same { defaults, loading, refresh } shape for backward
 * compatibility, but now delegates to the centralized config store.
 *
 * The source of truth for transaction defaults is:
 *   src/config/modelDefaults.ts  (static, ships with build)
 *   + configSlice overrides      (fetched from wc3 on startup, pushed back on save)
 *
 * Legacy consumers can continue using this hook unchanged.
 * New code should prefer `useMergedModelDefaults(modelKey)` directly.
 */
import { useMemo } from 'react';
import { useSelector } from 'react-redux';
import type { RootState } from '@/store';
import { getModelDefaults } from '@/config/modelDefaults';

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

/**
 * Build TransactionDefaults from the merged config for a given model.
 * Defaults to 'order' model when no model is specified.
 */
function buildDefaults(
  storeOverrides: Record<string, unknown> | undefined,
  modelKey = 'order',
): TransactionDefaults {
  const statics = getModelDefaults(modelKey);
  const merged = { ...statics, ...(storeOverrides ?? {}) };
  return {
    terms: (merged.terms as string) ?? FALLBACK.terms,
    due_date_period: Number(merged.due_date_period ?? FALLBACK.due_date_period),
    price_level: (merged.price_level as string) ?? FALLBACK.price_level,
    priority: (merged.priority as string) ?? FALLBACK.priority,
  };
}

export function useTransactionDefaults(modelKey = 'order') {
  const loading = useSelector((s: RootState) => s.config.loading);
  const overrides = useSelector(
    (s: RootState) => s.config.modelDefaults?.[modelKey],
  );

  const defaults = useMemo(
    () => buildDefaults(overrides, modelKey),
    [overrides, modelKey],
  );

  // refresh is now handled by useAppConfig().syncToBackend() at the app level.
  // Kept here as a no-op for backward compatibility.
  const refresh = async () => {
    console.info('[useTransactionDefaults] refresh() is deprecated. Use useAppConfig().syncToBackend() instead.');
  };

  return { defaults, loading, refresh };
}

/** Compute due_date by adding `due_date_period` days to `dt`. */
export function computeDueDate(dt: string, periodDays: number): string {
  const d = new Date(dt);
  d.setDate(d.getDate() + periodDays);
  return d.toISOString().split('T')[0];
}

export default useTransactionDefaults;
