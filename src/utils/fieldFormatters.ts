/**
 * fieldFormatters.ts — Client-side normalize + format for phone, zip, email.
 *
 * Storage: canonical form (digits only for phone/zip, lowercase for email).
 * Display: formatted per locale/nation.
 * Input: accept anything, normalize on blur, show formatted result.
 *
 * These mirror the server-side normalizers in core/services/phone_normalizer.py.
 * The server is authoritative; the client provides instant feedback.
 */

// ── Phone ────────────────────────────────────────────────────────────

const PHONE_COUNTRY_FORMATS: Record<string, { length: number; groups: number[]; name: string }> = {
  "1":   { length: 10, groups: [3, 3, 4], name: "US/CA" },
  "44":  { length: 10, groups: [2, 4, 4], name: "UK" },
  "27":  { length: 9,  groups: [2, 3, 4], name: "ZA" },
  "33":  { length: 9,  groups: [1, 2, 2, 2, 2], name: "FR" },
  "49":  { length: 10, groups: [3, 3, 4], name: "DE" },
  "61":  { length: 9,  groups: [1, 4, 4], name: "AU" },
  "91":  { length: 10, groups: [5, 5], name: "IN" },
  "52":  { length: 10, groups: [2, 4, 4], name: "MX" },
};

function stripToDigits(s: string): string {
  return (s || '').replace(/\D/g, '');
}

function detectCountryCode(digits: string): [string, string] {
  for (const len of [3, 2, 1]) {
    const prefix = digits.slice(0, len);
    const fmt = PHONE_COUNTRY_FORMATS[prefix];
    if (fmt) {
      const remaining = digits.slice(len);
      if (Math.abs(remaining.length - fmt.length) <= 2) {
        return [prefix, remaining];
      }
    }
  }
  return ["", digits];
}

export function normalizePhone(raw: string, defaultCountry = "US"): string {
  if (!raw?.trim()) return "";
  const hasPlus = raw.trim().startsWith('+');
  const digits = stripToDigits(raw);
  if (digits.length < 7) return "";

  const countryCodeMap: Record<string, string> = { US: "1", CA: "1", UK: "44", GB: "44", ZA: "27", FR: "33", DE: "49", AU: "61", IN: "91", MX: "52" };
  const defaultCode = countryCodeMap[defaultCountry.toUpperCase()] || "1";
  const expectedLength = PHONE_COUNTRY_FORMATS[defaultCode]?.length || 10;

  if (hasPlus) {
    const [code, number] = detectCountryCode(digits);
    return code ? code + number : digits;
  }

  // No + prefix — 10 digits = local number, prepend default country code
  if (digits.length === expectedLength) return defaultCode + digits;
  if (defaultCode === "1" && digits.length === 11 && digits[0] === "1") return digits;

  const [code, number] = detectCountryCode(digits);
  return code ? code + number : defaultCode + digits;
}

export function formatPhone(normalized: string, displayMode: "local" | "international" = "local", defaultCountry = "US", separator = "."): string {
  if (!normalized) return "";
  const digits = stripToDigits(normalized);
  if (digits.length < 7) return normalized;

  const [code, number] = detectCountryCode(digits);
  if (!code) return normalized;

  const fmt = PHONE_COUNTRY_FORMATS[code];
  if (!fmt) return `+${code} ${number}`;

  const parts: string[] = [];
  let pos = 0;
  for (const g of fmt.groups) {
    parts.push(number.slice(pos, pos + g));
    pos += g;
  }
  if (pos < number.length) parts.push(number.slice(pos));
  const formatted = parts.filter(Boolean).join(separator);

  const countryCodeMap: Record<string, string> = { US: "1", CA: "1", UK: "44", GB: "44", ZA: "27" };
  const defaultCode = countryCodeMap[defaultCountry.toUpperCase()] || "1";
  const isForeign = code !== defaultCode;

  return (displayMode === "international" || isForeign) ? `+${code} ${formatted}` : formatted;
}

// ── Email ────────────────────────────────────────────────────────────

export function normalizeEmail(raw: string): string {
  return (raw || '').trim().toLowerCase();
}

export function formatEmail(email: string): string {
  return email || '';
}

// ── Zip/Postal Code ──────────────────────────────────────────────────

const ZIP_FORMATS: Record<string, { pattern: RegExp; format: (d: string) => string }> = {
  US: {
    pattern: /^(\d{5})(\d{4})?$/,
    format: (d) => {
      const m = d.match(/^(\d{5})(\d{4})$/);
      return m ? `${m[1]}-${m[2]}` : d.slice(0, 5);
    },
  },
  CA: {
    pattern: /^([A-Z]\d[A-Z])(\d[A-Z]\d)$/i,
    format: (d) => {
      const clean = d.replace(/\s/g, '').toUpperCase();
      return clean.length === 6 ? `${clean.slice(0, 3)} ${clean.slice(3)}` : clean;
    },
  },
  UK: {
    pattern: /^([A-Z]{1,2}\d[A-Z\d]?)(\d[A-Z]{2})$/i,
    format: (d) => {
      const clean = d.replace(/\s/g, '').toUpperCase();
      return clean.length >= 5 ? `${clean.slice(0, -3)} ${clean.slice(-3)}` : clean;
    },
  },
};

export function normalizeZip(raw: string, country = "US"): string {
  if (!raw?.trim()) return "";
  const clean = raw.replace(/[\s\-]/g, '');
  if (country === "US") return stripToDigits(clean).slice(0, 9); // 5 or 9 digits
  return clean.toUpperCase();
}

export function formatZip(normalized: string, country = "US"): string {
  if (!normalized) return "";
  const fmt = ZIP_FORMATS[country];
  if (fmt) return fmt.format(normalized);
  return normalized;
}
