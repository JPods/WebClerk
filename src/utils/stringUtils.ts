/**
 * String utilities — ported from wc2 String_* methods.
 * Only the ones that aren't trivial JS built-ins.
 */

/** Capitalize first character: "hello world" → "Hello world" */
export const capitalizeFirst = (s: string): string =>
  s ? s[0].toUpperCase() + s.slice(1) : '';

/** Capitalize each word: "hello world" → "Hello World" */
export const capitalizeWords = (s: string): string =>
  s ? s.replace(/\b\w/g, (c) => c.toUpperCase()) : '';

/** Convert slug/snake to title: "order_line" → "Order Line", "some-slug" → "Some Slug" */
export const slugToTitle = (s: string): string =>
  s ? s.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : '';

/** Check if string contains keyword (case-insensitive) */
export const containsKeyword = (s: string, keyword: string): boolean =>
  s.toLowerCase().includes(keyword.toLowerCase());

/** Validate phone number — loose check for digits, dashes, parens, plus, spaces */
export const isValidPhone = (s: string): boolean =>
  /^[+]?[\d\s()-]{7,20}$/.test(s.trim());

/** Format phone for display: "6124849255" → "(612) 484-9255" */
export const formatPhone = (s: string): string => {
  const digits = s.replace(/\D/g, '');
  if (digits.length === 10) return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  if (digits.length === 11 && digits[0] === '1') return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  return s; // return as-is if not standard US format
};

/** Format currency: 1234.5 → "$1,234.50" */
export const formatCurrency = (n: number | string | null | undefined, symbol = '$'): string => {
  const num = typeof n === 'string' ? parseFloat(n) : n;
  if (num == null || isNaN(num)) return '';
  return `${symbol}${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

/** Format date from epoch ms: 1783000000000 → "Jul 2, 2026" */
export const formatDate = (epochMs: number | null | undefined): string => {
  if (!epochMs) return '';
  return new Date(epochMs).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
};

/** Format datetime from epoch ms: 1783000000000 → "Jul 2, 2026 3:45 PM" */
export const formatDateTime = (epochMs: number | null | undefined): string => {
  if (!epochMs) return '';
  return new Date(epochMs).toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
};

/** Truncate with ellipsis: "long text here" → "long tex…" */
export const truncate = (s: string, maxLen: number): string =>
  s && s.length > maxLen ? s.slice(0, maxLen - 1) + '…' : s;

/** Extract display value from a JSON object — first string value found */
export const extractDisplay = (obj: unknown): string => {
  if (obj == null) return '';
  if (typeof obj === 'string') return obj;
  if (typeof obj === 'number' || typeof obj === 'boolean') return String(obj);
  if (typeof obj === 'object') {
    const o = obj as Record<string, unknown>;
    // Priority keys for display
    for (const key of ['display_name', 'name', 'ida', 'title', 'label', 'email', 'description']) {
      if (typeof o[key] === 'string' && o[key]) return o[key] as string;
    }
    // First non-null string value
    for (const v of Object.values(o)) {
      if (typeof v === 'string' && v) return v;
    }
  }
  return String(obj);
};
