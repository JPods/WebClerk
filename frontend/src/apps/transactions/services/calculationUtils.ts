/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Calculation Utilities — shared math, rounding, and formatting
 *
 * All numeric helpers used by line-level and header-level calculation services
 * live here.  The formulae are intentionally identical to the WC3 Django backend
 * so that the frontend can compute optimistic totals that match what the server
 * will persist.
 *
 * WC3 backend reference:
 *   apps/transactions/models/base_line_model.py  — _calculate_extended_price()
 *   apps/transactions/services/order_totals.py   — compute_order_sell_cost_totals()
 *
 * @see webClerk3/readmes/topics/transactions/transactions-totals.md
 */

// ============================================================================
// Precision-aware rounding
// ============================================================================

/**
 * Round a number to `places` decimal places.
 *
 * Mirrors the Python `Decimal.quantize()` rounding used by WC3's `_to_decimal`.
 * Uses "round half away from zero" to match the Python ROUND_HALF_UP default.
 */
export function round(value: number, places = 2): number {
  if (!Number.isFinite(value)) return 0;
  const factor = 10 ** places;
  // Math.round uses "round half to even" on exact halves in some engines,
  // so we nudge with Number.EPSILON to match Python's Decimal behaviour.
  return Math.round((value + Number.EPSILON) * factor) / factor;
}

/**
 * Coerce an unknown value to a finite number, falling back to `fallback`.
 *
 * Mirrors WC3's `_d()` helper in the totals services.
 */
export function toNumber(value: unknown, fallback = 0): number {
  if (value === null || value === undefined || value === '') return fallback;
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

// ============================================================================
// Currency / display formatting
// ============================================================================

// Canonical formatters — re-exported from stringUtils
export { formatCurrency, formatPercent } from '@/utils/stringUtils';

/**
 * Format a plain number with locale grouping (e.g. "1,234").
 */
export function formatNumber(
  value: number | null | undefined,
  decimals = 2,
): string {
  if (value === null || value === undefined) return '--';
  return value.toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  });
}
