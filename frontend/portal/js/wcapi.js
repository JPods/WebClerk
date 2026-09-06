/**
 * wcapi.js — JWT auth + wcapi client for the portal.
 *
 * Thin wrapper over fetch(). Stores JWT in memory (not localStorage for
 * httpOnly refresh cookie flow, but access token needs to be in memory
 * for Authorization header).
 */

let _baseUrl = '';
let _accessToken = null;
let _user = null;

/**
 * Initialize the API client.
 * @param {string} baseUrl - e.g. '' for same-origin, 'https://webclerk.com'
 */
export function init(baseUrl) {
  _baseUrl = baseUrl.replace(/\/+$/, '');
}

/** Current access token */
export function getToken() { return _accessToken; }

/** Current user object */
export function getUser() { return _user; }

/** Is the user authenticated? */
export function isAuthenticated() { return !!_accessToken && !!_user; }

/**
 * Login and store the JWT + user profile.
 * @param {string} email
 * @param {string} password
 * @returns {object} user profile
 */
export async function login(email, password) {
  const res = await _post('wcapi/login/', { email, password }, true);
  const data = res?.data || res;
  _accessToken = data.access;
  _user = data.user;
  return _user;
}

/** Logout — clear tokens */
export async function logout() {
  try { await _post('wcapi/logout/', {}); } catch { /* best effort */ }
  _accessToken = null;
  _user = null;
}

/**
 * GET records from wcapi.
 * @param {string} modelName - e.g. 'item', 'invoice', 'contact'
 * @param {object} params - query parameters (filters, limit, offset, etc.)
 * @returns {object} { results: [], total: N }
 */
export async function getRecords(modelName, params = {}) {
  const qs = new URLSearchParams();
  qs.set('model_name', modelName);
  for (const [k, v] of Object.entries(params)) {
    if (v != null) qs.set(k, String(v));
  }
  return _get(`wcapi/get/?${qs}`);
}

/**
 * GET a single record.
 * @param {string} modelName
 * @param {number|string} id
 * @returns {object} record
 */
export async function getRecord(modelName, id) {
  return _get(`wcapi/get/?model_name=${modelName}&id=${id}`);
}

/**
 * Save a record (create or update).
 * @param {string} modelName
 * @param {object} data - fields to save. Include id for update.
 * @returns {object} saved record
 */
export async function saveRecord(modelName, data) {
  return _post('wcapi/save/', { model_name: modelName, ...data });
}

/**
 * Save a transaction (header + lines).
 * @param {object} payload - { model_name, header: {...}, lines: [...] }
 * @returns {object} saved transaction
 */
export async function saveTransaction(payload) {
  return _post('wcapi/transaction/save/', payload);
}

/**
 * Get the current user's profile (contact record).
 * @returns {object}
 */
export async function getMe() {
  return _get('wcapi/me/');
}

// --- Internal helpers ---

async function _get(path) {
  const res = await fetch(`${_baseUrl}/${path}`, {
    headers: _headers(),
    credentials: 'include', // send refresh cookie
  });
  if (!res.ok) throw await _error(res);
  const body = await res.json();
  return body?.data ?? body;
}

async function _post(path, data, noAuth = false) {
  const res = await fetch(`${_baseUrl}/${path}`, {
    method: 'POST',
    headers: noAuth ? { 'Content-Type': 'application/json' } : _headers(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!res.ok) throw await _error(res);
  const body = await res.json();
  return body?.data ?? body;
}

function _headers() {
  const h = { 'Content-Type': 'application/json' };
  if (_accessToken) h['Authorization'] = `Bearer ${_accessToken}`;
  return h;
}

async function _error(res) {
  let msg = `HTTP ${res.status}`;
  try {
    const body = await res.json();
    msg = body?.message || body?.detail || body?.error || msg;
  } catch { /* text body */ }
  return new Error(msg);
}
