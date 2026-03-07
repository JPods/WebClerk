/**
 * dateUtils.ts — Single canonical datetime formatting utility
 *
 * Replaces the 6+ ad-hoc copies scattered across the codebase.
 * All epoch timestamps in wc3 are stored as milliseconds (BigIntegerField).
 * Some legacy records store epoch *seconds* — we auto-detect and handle both.
 *
 * Key behavior: null/undefined/0 values are displayed as "now" via
 * applyDtFallback from fieldDefaults.ts rather than showing "Jan 1 1970".
 */

import { applyDtFallback } from '@/config/fieldDefaults';

// ---------------------------------------------------------------------------
// Core formatter
// ---------------------------------------------------------------------------

/** Threshold: if value < this, it's epoch seconds not ms (year ~2001 in ms). */
const EPOCH_MS_THRESHOLD = 1_000_000_000_000;

/**
 * Auto-detect whether value is epoch seconds or milliseconds.
 * Returns milliseconds either way.
 */
export function normalizeEpochMs(value: number): number {
  if (value > 0 && value < EPOCH_MS_THRESHOLD) {
    return value * 1000; // was seconds
  }
  return value;
}

/**
 * Format an epoch timestamp for display.
 *
 * - Applies the dt fallback (null/0 → now)
 * - Auto-detects seconds vs milliseconds
 * - Returns a locale-formatted string
 *
 * @param value   Epoch ms (or seconds, auto-detected), null, or 0
 * @param options Intl.DateTimeFormat options (defaults to date + time)
 * @returns       Formatted date string
 */
export function formatEpochMs(
  value: number | null | undefined,
  options?: Intl.DateTimeFormatOptions,
): string {
  const ms = normalizeEpochMs(applyDtFallback(value));
  const fmt: Intl.DateTimeFormatOptions = options ?? {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  };
  return new Date(ms).toLocaleDateString('en-US', fmt);
}

/**
 * Format an epoch timestamp as date only (no time).
 */
export function formatEpochDate(value: number | null | undefined): string {
  return formatEpochMs(value, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format an epoch timestamp as YYYY-MM-DD (for date inputs).
 */
export function formatEpochISO(value: number | null | undefined): string {
  const ms = normalizeEpochMs(applyDtFallback(value));
  return new Date(ms).toISOString().split('T')[0];
}

/**
 * Format an epoch timestamp as ISO datetime-local (for datetime-local inputs).
 * Useful for <input type="datetime-local" value={...} />.
 */
export function formatEpochDatetimeLocal(value: number | null | undefined): string {
  const ms = normalizeEpochMs(applyDtFallback(value));
  return new Date(ms).toISOString().slice(0, 16);
}

/**
 * Convert a Date object to epoch milliseconds.
 */
export function dateToEpochMs(d: Date): number {
  return d.getTime();
}

/**
 * Convert a YYYY-MM-DD or ISO string to epoch milliseconds.
 */
export function isoToEpochMs(isoStr: string): number {
  return new Date(isoStr).getTime();
}

// ---------------------------------------------------------------------------
// Legacy-compatible formatters (drop-in replacements)
// ---------------------------------------------------------------------------

/**
 * Drop-in replacement for the multiple `formatDate(d: Date)` copies
 * that return YYYY-MM-DD from a Date object.
 */
export function formatDate(d: Date): string {
  let month = '' + (d.getMonth() + 1);
  let day = '' + d.getDate();
  const year = d.getFullYear();
  if (month.length < 2) month = '0' + month;
  if (day.length < 2) day = '0' + day;
  return [year, month, day].join('-');
}

/**
 * Drop-in replacement for `getDateAsStr(d: Date)` → MM/DD/YYYY.
 */
export function getDateAsStr(d: Date): string {
  let month = '' + (d.getMonth() + 1);
  let day = '' + d.getDate();
  const year = d.getFullYear();
  if (month.length < 2) month = '0' + month;
  if (day.length < 2) day = '0' + day;
  return [month, day, year].join('/');
}
