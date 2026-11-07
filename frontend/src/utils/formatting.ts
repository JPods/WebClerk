/**
 * formatting — how money, numbers and dates look, read from the stored formatting (readme 106;
 * Bill, 2026-11-07: "Yes we should use stored formatting").
 *
 * One resolver: a model's definition carries config.defaults.formatting ({currency, locale,
 * date_format, number_precision}); a document with a customer or vendor overlays the org's own
 * config.defaults.formatting (a customer's CAD / en-CA). Display only: the server's figures are
 * the document's own, formatting never changes a number. SHIPPED_FORMATTING is the one literal,
 * what the seed ships (backend core/services/defaults.SHIPPED_FORMATTING), used until a
 * definition is read.
 */
import { getRecord, getRecords } from '@/api/wcapi';

export interface Formatting {
  currency: string;
  locale: string;
  /** short (11/7/2026), medium (Nov 7, 2026), long (November 7, 2026) */
  date_format: string;
  number_precision: number;
}

export const SHIPPED_FORMATTING: Formatting = { currency: 'USD', locale: 'en-US', date_format: 'short', number_precision: 2 };

const KEYS: (keyof Formatting)[] = ['currency', 'locale', 'date_format', 'number_precision'];

/** The block a definition (or an org) holds under config.defaults.formatting; only the four keys, only set ones. */
function blockOf(config: any): Partial<Formatting> {
  const block = config?.defaults?.formatting;
  const out: Partial<Formatting> = {};
  if (!block || typeof block !== 'object') return out;
  for (const k of KEYS) {
    const v = block[k];
    if (v === undefined || v === null || v === '') continue;
    (out as any)[k] = k === 'number_precision' ? Number(v) : String(v);
  }
  if (out.number_precision !== undefined && !Number.isFinite(out.number_precision)) delete out.number_precision;
  return out;
}

/** A model definition's formatting, the shipped one where it says nothing. */
export function formattingOf(modelConfig: any): Formatting {
  return { ...SHIPPED_FORMATTING, ...blockOf(modelConfig) };
}

/** The model's formatting overlaid by the party org's (its config.defaults.formatting), key by key. */
export function resolveFormatting(model: Formatting | any | null | undefined, partyConfig?: any): Formatting {
  const base: Formatting = model && KEYS.every((k) => k in (model as object)) ? (model as Formatting) : formattingOf(model);
  return { ...base, ...blockOf(partyConfig) };
}

/** Money in the formatting's currency and locale: "$1,234.50", "CA$1,234.50", "1 234,50 $". */
export function money(n: number | string | null | undefined, fmt: Formatting = SHIPPED_FORMATTING, precision?: number): string {
  const num = typeof n === 'string' ? parseFloat(n) : n;
  if (num == null || isNaN(num)) return '';
  const dp = precision ?? fmt.number_precision;
  try {
    return new Intl.NumberFormat(fmt.locale, { style: 'currency', currency: fmt.currency, minimumFractionDigits: dp, maximumFractionDigits: dp }).format(num);
  } catch {
    return `${fmt.currency} ${num.toFixed(dp)}`;        // an unknown currency code or locale: still a number
  }
}

/** A plain number in the formatting's locale, at the precision given (the formatting's by default). */
export function number(n: number | string | null | undefined, fmt: Formatting = SHIPPED_FORMATTING, precision?: number): string {
  const num = typeof n === 'string' ? parseFloat(n) : n;
  if (num == null || isNaN(num)) return '';
  const dp = precision ?? fmt.number_precision;
  try {
    return num.toLocaleString(fmt.locale, { minimumFractionDigits: dp, maximumFractionDigits: dp });
  } catch {
    return num.toFixed(dp);
  }
}

/** A local date in the formatting's locale and style. */
export function dateText(d: Date, fmt: Formatting = SHIPPED_FORMATTING, withTime = false): string {
  const style = fmt.date_format === 'long' ? { year: 'numeric', month: 'long', day: 'numeric' }
    : fmt.date_format === 'medium' ? { year: 'numeric', month: 'short', day: 'numeric' }
    : { year: 'numeric', month: 'numeric', day: 'numeric' };
  const opts: Intl.DateTimeFormatOptions = withTime
    ? { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
    : (style as Intl.DateTimeFormatOptions);
  try {
    return withTime ? d.toLocaleString(fmt.locale, opts) : d.toLocaleDateString(fmt.locale, opts);
  } catch {
    return withTime ? d.toLocaleString(undefined, opts) : d.toLocaleDateString();
  }
}

// ── the resolver for a document outside the form (a print from a dialog) ──────
const modelCache = new Map<string, Promise<Formatting>>();

/** A model's formatting from its definition, read once per page load. */
export function modelFormatting(modelName: string): Promise<Formatting> {
  if (!modelCache.has(modelName)) {
    modelCache.set(modelName, getRecords('setting', { purpose: 'wc:model', parent_model: modelName, limit: 1 })
      .then((res: any) => formattingOf(res?.results?.[0]?.config))
      .catch(() => ({ ...SHIPPED_FORMATTING })));
  }
  return modelCache.get(modelName)!;
}

/** A document's formatting: its model's, overlaid by its customer's or vendor's. The form hands
 *  the party's config along as record.customer_config; a dialog that has only the record fetches it. */
export async function documentFormatting(modelName: string, record: any): Promise<Formatting> {
  const model = await modelFormatting(modelName);
  let party = record?.customer_config;
  if (!party) {
    const isBuy = modelName === 'purchase' || modelName === 'receipt';
    const id = isBuy ? (record?.vendor_id || record?.vendor) : (record?.customer_id || record?.customer);
    if (id) {
      try {
        const res: any = await getRecord(isBuy ? 'vendor' : 'customer', Number(id));
        party = (res?.record || res)?.config;
      } catch { party = undefined; }
    }
  }
  return resolveFormatting(model, party);
}
