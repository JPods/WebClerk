/**
 * wcuiPrefs.ts — User UI preferences stored on Contact.metadata.wcui
 *
 * Preferences belong on the user's record, not in the browser.
 * localStorage is the cache; the Contact record is the source of truth.
 *
 * Usage:
 *   const fontSize = getWcuiPref('font_size', 12);
 *   setWcuiPref('font_size', 16); // saves to localStorage + server
 */

const LS_KEY = 'wc3_wcui_prefs';

// Defaults for all preferences
const DEFAULTS: Record<string, any> = {
  font_size: 12,
  dedup_font_size: 13,
  theme: 'dark',
  detail_view_pref: 'app',
  button_style: 'glass',
  phone_display: 'local',
  phone_separator: '.',
  default_country: 'US',
  date_format: 'MM/DD/YYYY',
  currency_locale: 'en-US',
};

// In-memory cache (faster than localStorage reads)
let _cache: Record<string, any> | null = null;

function _loadCache(): Record<string, any> {
  if (_cache) return _cache;
  try {
    const stored = localStorage.getItem(LS_KEY);
    _cache = stored ? JSON.parse(stored) : {};
  } catch {
    _cache = {};
  }
  return _cache!;
}

function _saveCache(prefs: Record<string, any>) {
  _cache = prefs;
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(prefs));
  } catch {}
}

/** Get a UI preference. Returns default if not set. */
export function getWcuiPref<T = any>(key: string, fallback?: T): T {
  const prefs = _loadCache();
  const val = prefs[key];
  if (val !== undefined) return val as T;
  if (fallback !== undefined) return fallback;
  return DEFAULTS[key] as T;
}

/** Set a UI preference. Saves to localStorage immediately, server async. */
export function setWcuiPref(key: string, value: any) {
  const prefs = _loadCache();
  prefs[key] = value;
  _saveCache(prefs);

  // Save to server (Contact.metadata.wcui) — fire and forget
  _saveToServer(key, value);
}

/** Get all preferences as a dict. */
export function getAllWcuiPrefs(): Record<string, any> {
  return { ...DEFAULTS, ..._loadCache() };
}

// Debounced server save — batches rapid changes (e.g., clicking A+ multiple times)
let _saveTimer: ReturnType<typeof setTimeout> | null = null;
let _pendingSave: Record<string, any> = {};

function _saveToServer(key: string, value: any) {
  _pendingSave[key] = value;
  if (_saveTimer) clearTimeout(_saveTimer);
  _saveTimer = setTimeout(async () => {
    const updates = { ..._pendingSave };
    _pendingSave = {};
    try {
      const { manageAction } = await import('@/api/wcapi');
      // Use a lightweight manage action to patch metadata.wcui
      await manageAction('save_wcui_prefs', { prefs: updates });
    } catch (e) {
      console.warn('[wcui] Server save failed:', e);
      // localStorage still has the value — will retry on next change
    }
  }, 1000); // 1 second debounce
}

/**
 * Initialize preferences from server on login.
 * Called once after authentication succeeds.
 */
export async function loadWcuiFromServer() {
  try {
    const { getRecords } = await import('@/api/wcapi');
    const res = await getRecords('contact', { filters: { email: '_me_' }, fields: ['metadata'], limit: 1 }) as any;
    const contact = res?.results?.[0];
    if (contact?.metadata?.wcui) {
      const serverPrefs = contact.metadata.wcui;
      const localPrefs = _loadCache();
      // Server wins for each key that exists on server
      const merged = { ...localPrefs, ...serverPrefs };
      _saveCache(merged);
    }
  } catch {
    // Server not available — localStorage is fine
  }
}

/**
 * Migrate legacy localStorage keys to wcui format.
 * Call once on app startup.
 */
export function migrateLegacyPrefs() {
  const migrations: Record<string, string> = {
    'db-theme': 'theme',
    'db-fontsize': 'font_size',
    'wc3_detail_view_pref': 'detail_view_pref',
    'wc3_button_style': 'button_style',
  };

  const fontSizeMap: Record<string, number> = { S: 12, M: 14, L: 16 };
  const prefs = _loadCache();
  let migrated = false;

  for (const [oldKey, newKey] of Object.entries(migrations)) {
    const val = localStorage.getItem(oldKey);
    if (val && prefs[newKey] === undefined) {
      prefs[newKey] = newKey === 'font_size' ? (fontSizeMap[val] || 12) : val;
      migrated = true;
    }
  }

  if (migrated) _saveCache(prefs);
}
