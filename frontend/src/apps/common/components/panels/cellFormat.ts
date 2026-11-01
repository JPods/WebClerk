/**
 * cellFormat — how a value looks in a list cell, the same in every list (panels, db.list, line
 * grids, trees). One formatter: the type comes from the field's behavior, else a saved FieldSpec
 * format, else the field's name.
 *
 * A list shows what the server sent (Bill: the screen shows what the server calculates) — this
 * only formats it.
 */
import type React from 'react';
import { formatDt, formatEmail, formatPhone, formatZip, formatAddress } from '@/utils/fieldFormatters';
import type { AddressComponents } from '@/utils/fieldFormatters';

export interface CellType {
  /** The field's behavior type (currency, number, date, select, …) */
  type?: string;
  /** A saved FieldSpec format (currency, percent, date, number, phone) */
  format?: string | null;
  precision?: number;
}

/** A field's display type when nothing says it: its name. */
export function guessType(field: string): string | undefined {
  const leaf = field.split('.').pop() || field;
  if (leaf.startsWith('dt_')) return 'date';
  if (/(^|_)(price|cost|amount|total|balance|debit|credit)$/.test(leaf)) return 'currency';
  if (/(^|_)(phone|fax)$/.test(leaf)) return 'phone';
  if (leaf === 'email') return 'email';
  return undefined;
}

/** A value at a dot path; `[n]` indexes an array, and on an object means its n-th value. */
export function valueAt(record: unknown, field: string): unknown {
  if (!field.includes('.') && !field.includes('[')) return (record as Record<string, unknown> | null)?.[field];
  return field.replace(/\[(\d+)\]/g, '.$1').split('.').reduce<unknown>((o, k) => {
    if (o == null || typeof o !== 'object') return undefined;
    const obj = o as Record<string, unknown>;
    if (obj[k] === undefined && !Array.isArray(o)) {
      const idx = parseInt(k, 10);
      const vals = Object.values(obj);
      if (!isNaN(idx) && idx < vals.length) return vals[idx];
    }
    return obj[k];
  }, record);
}

/** A record reference, a list of them, or a language map, said in words; null when it is none. */
export function readable(val: unknown): string | null {
  if (Array.isArray(val)) {
    if (!val.length) return '';
    return val.every((v) => v && typeof v === 'object' && 'name' in (v as object))
      ? val.map((v) => String((v as { name: unknown }).name ?? '')).filter(Boolean).join(', ')
      : null;
  }
  if (val && typeof val === 'object') {
    const obj = val as Record<string, unknown>;
    if (!Object.keys(obj).length) return '';
    if (obj.name || obj.display_name) return String(obj.name || obj.display_name);
    const lang = (navigator.language || 'en').slice(0, 2);
    if (typeof obj[lang] === 'string') return obj[lang] as string;
    if (typeof obj.en === 'string') return obj.en;
    const first = Object.values(obj).find((x) => typeof x === 'string');
    return first != null ? String(first) : null;
  }
  return null;
}

/** The text a cell shows. Empty is blank: a missing value should not look like a value. */
export function formatCell(value: unknown, field: string, t: CellType = {}): string {
  if (value == null || value === '') return '';
  const type = t.type || t.format || guessType(field);
  if (typeof value === 'boolean') return value ? '✅' : '';
  if (typeof value === 'object') {
    if (type === 'address') return formatAddress(value as AddressComponents);
    const said = readable(value);
    if (said != null) return said;
    return JSON.stringify(value).slice(0, 80);
  }
  const n = typeof value === 'number' ? value : NaN;
  switch (type) {
    case 'currency': {
      const v = typeof value === 'number' ? value : Number(value);
      if (isNaN(v)) return String(value);
      const dp = t.precision ?? 2;
      return v.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
    }
    case 'percent': {
      const v = typeof value === 'number' ? value : Number(value);
      return isNaN(v) ? String(value) : (v >= 1 ? v : v * 100).toFixed(1) + '%';
    }
    case 'number': {
      if (isNaN(n)) return String(value);
      const dp = t.precision ?? 0;
      return n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
    }
    case 'date': case 'datetime': case 'timestamp':
      return formatDt(value, 'date', field);
    case 'phone':
      return String(value).replace(/\D/g, '').length >= 7 ? formatPhone(String(value)) : String(value);
    case 'email':
      return formatEmail(String(value));
    case 'zip':
      return formatZip(String(value));
  }
  if (typeof value === 'number' && /(^|\.)dt_/.test(field) && value > 1e12) return formatDt(value, 'date', field);
  return String(value);
}

/** The full value a cell's tooltip shows (a date with its time). */
export function cellTitle(value: unknown, field: string, t: CellType = {}): string {
  if (value == null) return '';
  const type = t.type || guessType(field);
  if ((type === 'date' || type === 'datetime' || type === 'timestamp') && value) return formatDt(value, 'datetime', field);
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

const RIGHT = new Set(['currency', 'number', 'percent']);
const CENTER = new Set(['date', 'datetime', 'timestamp', 'boolean']);
const RIGHT_NAMES = /^(total|balance|amount|debit|credit|price|cost|qty|quantity|version|priority|sequence|difficulty|health_rating|security_level|line_number|count_accessed|percent_complete|burndown|linkage)$/;

/** Where a column's values sit: numbers right, dates and flags centered, words left. */
export function cellAlign(field: string, t: CellType & { align?: 'left' | 'right' | 'center' } = {}, sample?: unknown): 'left' | 'right' | 'center' {
  if (t.align) return t.align;
  const type = t.type || t.format || guessType(field);
  if (type && RIGHT.has(type)) return 'right';
  if (type && CENTER.has(type)) return 'center';
  if (type) return 'left';
  const leaf = (field.split('.').pop() || field).toLowerCase();
  if (leaf.startsWith('dt_') || leaf.includes('date')) return 'center';
  if (RIGHT_NAMES.test(leaf)) return 'right';
  if (/^is_/.test(leaf)) return 'center';
  if (typeof sample === 'number') return 'right';
  if (typeof sample === 'boolean') return 'center';
  return 'left';
}

const HEADER_COLORS: Record<string, string> = {
  readonly: 'var(--db-text-dim, #94a3b8)', timestamp: 'var(--db-text-dim, #94a3b8)',
  email: 'var(--db-accent-green, #166534)', phone: 'var(--db-accent-green, #166534)',
  address: 'var(--db-accent-green, #166534)', url: 'var(--db-accent-green, #166534)',
  geo: 'var(--db-accent-green, #166534)',
  select: 'var(--db-accent, #1e40af)', lookup: 'var(--db-accent, #1e40af)',
};
const HEADER_ITALIC = new Set(['readonly', 'timestamp', 'hidden']);

/** A column label's look by behavior: italic gray system-set, green an action, blue a choice. */
export function headerStyle(type?: string): React.CSSProperties | undefined {
  if (!type) return undefined;
  const color = HEADER_COLORS[type];
  const italic = HEADER_ITALIC.has(type);
  if (!color && !italic) return undefined;
  return { color, fontStyle: italic ? 'italic' : undefined };
}

/** A column's label from its field: the last part of a dot path, underscores as spaces. */
export function fieldLabel(field: string): string {
  const leaf = field.includes('.') ? field.split('.').slice(-2).join('.') : field;
  return leaf.replace(/\[\d+\]$/, '');
}

export type FooterKind = 'sum' | 'average' | 'count';

// A price, a rate or a per-unit cost summed over rows means nothing; an amount, a quantity or a
// balance summed does. Names are the field's last part.
const NO_TOTAL = /^(id|ida|sequence|line_number|version|priority|difficulty|security_level|health_rating)$|_id$|(^|_)(price|rate|pct|percent|percentage)($|_)|^(unit|cost|cost_avg|cost_last|cost_unit|cost_standard|cost_snapshot|cost_rollup|unit_cost|unit_price|disc_price|margin_pct|tax_pct|discount_pct|scrap_factor|yield_pct)$/;

/** What a list's Σ row shows under a column — of the rows on screen (Bill, 2026-11-01: users
 *  show and omit records, the sums follow). A behavior's own `footer` decides ('sum', 'average',
 *  'count', 'none'); otherwise numbers and amounts sum, except prices, rates and per-unit costs. */
export function footerKind(field: string, behavior?: { type?: string; footer?: string } | null): FooterKind | null {
  const own = behavior?.footer;
  if (own === 'sum' || own === 'average' || own === 'count') return own;
  if (own === 'none') return null;
  const type = behavior?.type;
  if (type !== 'currency' && type !== 'number') return null;
  const leaf = (field.split('.').pop() || field).toLowerCase();
  return NO_TOTAL.test(leaf) ? null : 'sum';
}
