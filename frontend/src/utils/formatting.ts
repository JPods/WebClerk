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
  /** A field's own say, from the model's behaviors (model.field or model.leaf): `time` shows
   *  and takes the clock beside the day, `date_format` writes this field's day its own way. */
  fields?: Record<string, FieldFormatting>;
}

export interface FieldFormatting { time?: boolean; date_format?: string }

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

/** What a model's behaviors say about how single fields are written (`time`, `date_format`). */
function fieldsOf(modelConfig: any): Record<string, FieldFormatting> {
  const out: Record<string, FieldFormatting> = {};
  const behaviors = modelConfig?.behaviors;
  if (!behaviors || typeof behaviors !== 'object') return out;
  for (const [field, b] of Object.entries<any>(behaviors)) {
    if (!b || typeof b !== 'object') continue;
    const own: FieldFormatting = {};
    if (typeof b.time === 'boolean') own.time = b.time;
    if (typeof b.date_format === 'string' && b.date_format) own.date_format = b.date_format;
    if (Object.keys(own).length) out[field] = own;
  }
  return out;
}

/** A model's formatting: what its definition sets, over the company's, over the shipped
 *  (Bill, 2026-11-24: "a company default with an override by model.field or model.leaf"). */
export function formattingOf(modelConfig: any, company?: Partial<Formatting>): Formatting {
  const fields = fieldsOf(modelConfig);
  return { ...SHIPPED_FORMATTING, ...(company || {}), ...blockOf(modelConfig), ...(Object.keys(fields).length ? { fields } : {}) };
}

/** The formatting one field is written with: the screen's, with the field's own date_format. */
export function fieldFormatting(fmt: Formatting, field?: string): Formatting & { time: boolean } {
  const own = (field && fmt.fields?.[field]) || {};
  return { ...fmt, ...(own.date_format ? { date_format: own.date_format } : {}), time: own.time === true };
}

let companyCache: Promise<Partial<Formatting>> | null = null;

/** The company's formatting (the company profile's config.defaults.formatting), read once per page load. */
export function companyFormatting(): Promise<Partial<Formatting>> {
  if (!companyCache) {
    companyCache = getRecords('setting', { purpose: 'wc:company_profile', limit: 1 })
      .then((res: any) => blockOf(res?.results?.[0]?.config))
      .catch(() => ({}));
  }
  return companyCache;
}

/** The model's formatting overlaid by the party org's (its config.defaults.formatting), key by key. */
export function resolveFormatting(model: Formatting | any | null | undefined, partyConfig?: any): Formatting {
  const base: Formatting = model && KEYS.every((k) => k in (model as object)) ? (model as Formatting) : formattingOf(model);
  return { ...base, ...blockOf(partyConfig) };   // base.fields rides along: a field's say is the model's
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
  // With a time, the day is written the same way as without one: one date format on a screen.
  const opts: Intl.DateTimeFormatOptions = withTime
    ? { ...(style as Intl.DateTimeFormatOptions), hour: '2-digit', minute: '2-digit' }
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
    modelCache.set(modelName, Promise.all([getRecords('setting', { purpose: 'wc:model', parent_model: modelName, limit: 1 }), companyFormatting()])
      .then(([res, company]: [any, Partial<Formatting>]) => formattingOf(res?.results?.[0]?.config, company))
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
