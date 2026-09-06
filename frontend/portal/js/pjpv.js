/**
 * pjpv.js — PJPV-compliant JSON path reader and formatter.
 *
 * Every view reads envelope fields through this module.
 * Never hardcode field access or formatting in views.
 */

// Field metadata cache (loaded from /wcapi/_pjpv_fields/)
let _catalog = null;

/**
 * Load the PJPV field catalog from the server.
 * @param {string} baseUrl
 * @param {string} token - JWT access token
 */
export async function loadCatalog(baseUrl, token) {
  if (_catalog) return _catalog;
  try {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const res = await fetch(`${baseUrl}/wcapi/_pjpv_fields/`, { headers });
    if (res.ok) {
      const data = await res.json();
      _catalog = data?.envelopes || {};
    } else {
      _catalog = {};
    }
  } catch {
    _catalog = {};
  }
  return _catalog;
}

/**
 * Read a value from a record using a dot-path.
 * e.g. read(item, 'price.retail') reads item.price.retail
 *
 * @param {object} record
 * @param {string} path - dot-separated path
 * @param {*} fallback - default if missing
 * @returns {*}
 */
export function read(record, path, fallback = null) {
  if (!record || !path) return fallback;
  const parts = path.split('.');
  let current = record;
  for (const part of parts) {
    if (current == null || typeof current !== 'object') return fallback;
    current = current[part];
  }
  return current !== undefined ? current : fallback;
}

/**
 * Get field metadata from the catalog.
 * @param {string} envelope - e.g. 'price', 'totals'
 * @param {string} field - e.g. 'retail', 'total'
 * @returns {object|null}
 */
export function fieldMeta(envelope, field) {
  if (!_catalog) return null;
  return _catalog[envelope]?.[field] || null;
}

/**
 * Format a value according to its PJPV metadata.
 * Falls back to type-based guessing if catalog is not loaded.
 *
 * @param {*} value
 * @param {string} path - e.g. 'price.retail', 'totals.total'
 * @returns {string}
 */
export function format(value, path) {
  if (value == null) return '\u2014'; // em-dash

  // Try catalog metadata
  const parts = path.split('.');
  const meta = parts.length >= 2 ? fieldMeta(parts[0], parts.slice(1).join('.')) : null;

  if (meta) {
    if (meta.widget === 'currency') return formatCurrency(value, meta.precision);
    if (meta.widget === 'percent') return formatPercent(value, meta.precision);
    if (meta.widget === 'number') return formatNumber(value, meta.precision);
    if (meta.widget === 'date') return formatDate(value);
  }

  // Guess from field name
  const leaf = parts[parts.length - 1];
  if (['price', 'retail', 'wholesale', 'distributor', 'msrp', 'base',
       'total', 'subtotal', 'tax', 'shipping', 'balance', 'received',
       'cost', 'discount', 'margin', 'standard', 'last', 'avg', 'landed'].includes(leaf)) {
    return formatCurrency(value);
  }
  if (leaf.endsWith('_pc') || leaf.endsWith('_pct') || leaf === 'margin_pc') {
    return formatPercent(value);
  }
  if (typeof value === 'number') return formatNumber(value);
  return String(value);
}

export function formatCurrency(value, precision = 2) {
  const num = Number(value);
  if (isNaN(num)) return '\u2014';
  return '$' + num.toFixed(precision).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

export function formatPercent(value, precision = 1) {
  const num = Number(value);
  if (isNaN(num)) return '\u2014';
  return num.toFixed(precision) + '%';
}

export function formatNumber(value, precision) {
  const num = Number(value);
  if (isNaN(num)) return '\u2014';
  if (precision != null) return num.toFixed(precision);
  return num.toLocaleString();
}

export function formatDate(value) {
  if (!value) return '\u2014';
  // Handle epoch milliseconds (WebClerk standard)
  const ms = typeof value === 'number' ? value : Number(value);
  if (!isNaN(ms) && ms > 1e12) {
    return new Date(ms).toLocaleDateString();
  }
  // ISO string
  const d = new Date(value);
  return isNaN(d.getTime()) ? String(value) : d.toLocaleDateString();
}

/**
 * Format a status value as an HTML badge.
 * @param {string} status
 * @returns {string} HTML string
 */
export function statusBadge(status) {
  if (!status) return '';
  const cls = `badge badge-${status.toLowerCase().replace(/\s+/g, '_')}`;
  return `<span class="${cls}">${status}</span>`;
}
