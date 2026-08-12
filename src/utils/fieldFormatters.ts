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

// ── Home country — user preference for phone/zip display ─────────────
// Set once at app startup from bootstrap or user prefs.
// Default: "US". Components call formatPhone() without needing React context.
let _homeCountry = "US";
export function setHomeCountry(iso: string) { _homeCountry = (iso || "US").toUpperCase(); }
export function getHomeCountry(): string { return _homeCountry; }

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

/**
 * Format a phone number for display.
 *
 * US domestic: (555) 867-5309  — parentheses on area code, dash between exchange/subscriber
 * Foreign:     +44 20-7946-0958  — country code shown, dashes between groups
 *
 * @param normalized  Digits-only string with country code prefix
 * @param homeCountry User's home country (ISO 3166-1 alpha-2). Numbers matching
 *                    this country's code display without the country prefix.
 *                    Set via user prefs: contact.prefs.phone.home_country
 */
export function formatPhone(normalized: string, homeCountry?: string): string {
  if (!homeCountry) homeCountry = _homeCountry;
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

  const countryCodeMap: Record<string, string> = {
    US: "1", CA: "1", UK: "44", GB: "44", ZA: "27", FR: "33", DE: "49", AU: "61", IN: "91", MX: "52",
  };
  const homeCode = countryCodeMap[homeCountry.toUpperCase()] || "1";
  const isForeign = code !== homeCode;

  if (code === "1" && !isForeign && parts.length >= 3) {
    // US/CA domestic: (555) 867-5309
    return `(${parts[0]}) ${parts[1]}-${parts[2]}`;
  }

  // All other: join with dashes, prepend +CC if foreign
  const formatted = parts.filter(Boolean).join("-");
  return isForeign ? `+${code} ${formatted}` : formatted;
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

// ── Address ─────────────────────────────────────────────────────────
// Format by DESTINATION country, not user's country.
// Based on Universal Postal Union (UPU) and Google libaddressinput templates.
//
// Template tokens: %N=name, %O=org, %1=address1, %2=address2,
//   %C=city, %S=state/province, %Z=zip/postal, %n=newline
// state_label/zip_label: what to call these fields in the UI

interface AddressTemplate {
  template: string;
  state_label: string;
  zip_label: string;
  zip_before_city?: boolean;
  state_required?: boolean;
}

const ADDRESS_TEMPLATES: Record<string, AddressTemplate> = {
  US: { template: '%1%n%2%n%C, %S %Z', state_label: 'State', zip_label: 'ZIP', state_required: true },
  CA: { template: '%1%n%2%n%C %S %Z', state_label: 'Province', zip_label: 'Postal Code', state_required: true },
  GB: { template: '%1%n%2%n%C%n%Z', state_label: 'County', zip_label: 'Postcode' },
  UK: { template: '%1%n%2%n%C%n%Z', state_label: 'County', zip_label: 'Postcode' },
  AU: { template: '%1%n%2%n%C %S %Z', state_label: 'State', zip_label: 'Postcode', state_required: true },
  DE: { template: '%1%n%2%n%Z %C', state_label: 'Bundesland', zip_label: 'PLZ', zip_before_city: true },
  FR: { template: '%1%n%2%n%Z %C', state_label: 'Région', zip_label: 'Code Postal', zip_before_city: true },
  IT: { template: '%1%n%2%n%Z %C %S', state_label: 'Provincia', zip_label: 'CAP', zip_before_city: true },
  ES: { template: '%1%n%2%n%Z %C', state_label: 'Provincia', zip_label: 'Código Postal', zip_before_city: true },
  NL: { template: '%1%n%2%n%Z %C', state_label: 'Provincie', zip_label: 'Postcode', zip_before_city: true },
  JP: { template: '〒%Z%n%S%C%n%1%n%2', state_label: 'Prefecture', zip_label: '〒', zip_before_city: true },
  CN: { template: '%Z%n%S%C%n%1%n%2', state_label: 'Province', zip_label: 'Postal Code', zip_before_city: true },
  IN: { template: '%1%n%2%n%C %Z%n%S', state_label: 'State', zip_label: 'PIN', state_required: true },
  BR: { template: '%1%n%2%n%C-%S%n%Z', state_label: 'Estado', zip_label: 'CEP', state_required: true },
  MX: { template: '%1%n%2%n%Z %C, %S', state_label: 'Estado', zip_label: 'C.P.', zip_before_city: true },
  ZA: { template: '%1%n%2%n%C%n%S%n%Z', state_label: 'Province', zip_label: 'Postal Code' },
  KR: { template: '%S %C%n%1%n%2%n%Z', state_label: 'Province', zip_label: 'Postal Code', zip_before_city: true },
  NZ: { template: '%1%n%2%n%C %Z', state_label: 'Region', zip_label: 'Postcode' },
  CH: { template: '%1%n%2%n%Z %C', state_label: 'Kanton', zip_label: 'PLZ', zip_before_city: true },
  SE: { template: '%1%n%2%n%Z %C', state_label: 'Län', zip_label: 'Postnummer', zip_before_city: true },
};

// Fallback for countries not in the list
const DEFAULT_TEMPLATE: AddressTemplate = {
  template: '%1%n%2%n%C, %S %Z', state_label: 'State/Province', zip_label: 'Postal Code',
};

export interface AddressComponents {
  address1?: string;
  address2?: string;
  city?: string;
  state?: string;
  zip?: string;
  country?: string; // ISO 3166-1 alpha-2
  name?: string;
  org?: string;
}

/**
 * Format an address using the destination country's postal conventions.
 *
 * The country field on the address determines the format — not the user's locale.
 * A US database displaying a German address uses German format (PLZ before city).
 */
export function formatAddress(addr: AddressComponents): string {
  if (!addr) return '';
  const cc = (addr.country || _homeCountry || 'US').toUpperCase();
  const tmpl = ADDRESS_TEMPLATES[cc] || DEFAULT_TEMPLATE;

  let result = tmpl.template
    .replace(/%N/g, addr.name || '')
    .replace(/%O/g, addr.org || '')
    .replace(/%1/g, addr.address1 || '')
    .replace(/%2/g, addr.address2 || '')
    .replace(/%C/g, addr.city || '')
    .replace(/%S/g, addr.state || '')
    .replace(/%Z/g, formatZip(addr.zip || '', cc));

  // Clean up: remove empty lines, collapse multiple commas/spaces
  return result
    .split('%n')
    .map(line => line.replace(/^[\s,]+|[\s,]+$/g, '').replace(/\s+/g, ' '))
    .filter(Boolean)
    .join('\n');
}

/** Get the address template for a country — useful for UI labels */
export function getAddressTemplate(country = 'US'): AddressTemplate {
  return ADDRESS_TEMPLATES[country.toUpperCase()] || DEFAULT_TEMPLATE;
}

/** Assemble address_full for storage (single line, comma-separated) */
export function assembleAddressFull(addr: AddressComponents): string {
  return formatAddress(addr).replace(/\n/g, ', ');
}

// ── Date/Time ──────────────────────────────────────────────────────
// Storage: epoch milliseconds (UTC). Display: user's local timezone.
// Some legacy records store epoch seconds — auto-detected.

const EPOCH_MS_THRESHOLD = 1_000_000_000_000;

/** Auto-detect seconds vs ms, return ms. */
export function normalizeEpochMs(value: number): number {
  return (value > 0 && value < EPOCH_MS_THRESHOLD) ? value * 1000 : value;
}

/**
 * Format a datetime value for display in the user's local timezone.
 *
 * @param value   epoch ms, epoch seconds (auto-detected), ISO string, null, or 0
 * @param mode    'date' = date only (M/D/YYYY), 'datetime' = date + time, 'iso' = YYYY-MM-DD
 * @param field   optional field name for heuristics (dt_ prefix, date_ prefix)
 */
export function formatDt(value: unknown, mode?: 'date' | 'datetime' | 'iso', field?: string): string {
  if (value == null || value === 0 || value === '') return '—';

  let d: Date;
  if (typeof value === 'number') {
    const ms = normalizeEpochMs(value);
    if (isNaN(ms) || ms < 1e10) return String(value);
    d = new Date(ms);
  } else if (typeof value === 'string') {
    d = new Date(value);
  } else {
    return String(value);
  }
  if (isNaN(d.getTime())) return String(value);

  // Auto-detect mode from field name if not specified
  if (!mode && field) {
    if (/^date_|_date$|effective|deadline|dt_created|dt_modified/.test(field)) mode = 'date';
  }
  if (!mode) mode = 'date';

  switch (mode) {
    case 'iso':
      // Local YYYY-MM-DD (for <input type="date">)
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    case 'datetime':
      return d.toLocaleString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    case 'date':
    default:
      return d.toLocaleDateString();
  }
}

/**
 * Format epoch for <input type="date"> value (YYYY-MM-DD in local time).
 */
export function formatDtInput(value: unknown): string {
  return formatDt(value, 'iso');
}

/**
 * Parse a local date input (YYYY-MM-DD) to epoch ms (UTC).
 */
export function parseDtInput(isoLocal: string): number {
  if (!isoLocal) return 0;
  return new Date(isoLocal + 'T00:00:00').getTime();
}

/**
 * Parse a local datetime-local input to epoch ms (UTC).
 */
export function parseDatetimeInput(dtLocal: string): number {
  if (!dtLocal) return 0;
  return new Date(dtLocal).getTime();
}
