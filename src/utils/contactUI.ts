/**
 * contactUI.ts — User UI configuration stored on Contact.config.ui
 *
 * One namespace for everything the user controls about their interface.
 * localStorage is the cache; the Contact record is the source of truth.
 *
 * Replaces wcuiPrefs.ts — all UI config now lives in config.ui.
 *
 * Usage:
 *   const theme = getUI('theme.active', 'dark');
 *   setUI('theme.active', 'light');
 *   setUIBatch({ 'theme.active': 'light', 'detail.default_view': 'admin' });
 */

const LS_KEY = 'wc3_config_ui';

// Default config.ui structure — matches backend DEFAULT_UI_CONFIG
const DEFAULTS: Record<string, any> = {
  theme: {
    active: 'dark',
    dark: {
      colors: { text: '#ececec', surface: '#252526', accent: '#9cdcfe' },
      font: { size: 14 },
    },
    light: {
      colors: { text: '#212529', surface: '#ffffff', accent: '#1e40af' },
      font: { size: 14 },
    },
  },
  navbar: {
    models: ['proposal', 'order', 'invoice', 'purchase', 'action'],
    dashboards: [
      'dashboard', 'products', 'transactions', 'orgs',
      'administration', 'alice', 'kanban', 'gantt',
      'databrowser', 'json',
    ],
  },
  console: {
    visible: true,
    position: 'bottom',
    height: 200,
  },
  detail: {
    auto_edit: true,
    default_view: 'app',
  },
  list: {
    page_size: 50,
    default_sort: 'dt_modified',
  },
  badge: {
    bg_color: '',
    text_color: '',
    initials: '',
  },
  format: {
    button_style: 'glass',
    phone_display: 'local',
    date_format: 'MM/DD/YYYY',
    currency_locale: 'en-US',
  },
};

// In-memory cache
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

function _saveCache(ui: Record<string, any>) {
  _cache = ui;
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(ui));
  } catch {}
}

/** Deep-get a value by dot path: getUI('theme.active') → 'dark' */
function _deepGet(obj: Record<string, any>, path: string): any {
  const keys = path.split('.');
  let current: any = obj;
  for (const key of keys) {
    if (current == null || typeof current !== 'object') return undefined;
    current = current[key];
  }
  return current;
}

/** Deep-set a value by dot path: _deepSet(obj, 'theme.active', 'light') */
function _deepSet(obj: Record<string, any>, path: string, value: any) {
  const keys = path.split('.');
  let current = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (!(keys[i] in current) || typeof current[keys[i]] !== 'object') {
      current[keys[i]] = {};
    }
    current = current[keys[i]];
  }
  current[keys[keys.length - 1]] = value;
}

/** Deep-merge source into target. Source wins on leaf conflicts. */
function _deepMerge(target: Record<string, any>, source: Record<string, any>): Record<string, any> {
  for (const key of Object.keys(source)) {
    if (key in target && typeof target[key] === 'object' && typeof source[key] === 'object'
        && !Array.isArray(target[key]) && !Array.isArray(source[key])) {
      _deepMerge(target[key], source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

/**
 * Get a UI config value by dot path.
 * Falls back to DEFAULTS if not set in user config.
 *
 *   getUI('theme.active') → 'dark'
 *   getUI('list.page_size') → 50
 *   getUI('theme.dark.colors.accent') → '#9cdcfe'
 */
export function getUI<T = any>(path: string, fallback?: T): T {
  const cached = _loadCache();
  const val = _deepGet(cached, path);
  if (val !== undefined) return val as T;
  const def = _deepGet(DEFAULTS, path);
  if (def !== undefined) return def as T;
  return fallback as T;
}

/**
 * Set a UI config value by dot path. Saves to localStorage immediately, server async.
 *
 *   setUI('theme.active', 'light');
 *   setUI('detail.default_view', 'admin');
 */
export function setUI(path: string, value: any) {
  const ui = _loadCache();
  _deepSet(ui, path, value);
  _saveCache(ui);
  _saveToServer({ [path]: value });
}

/**
 * Set multiple values at once. Single debounced server save.
 *
 *   setUIBatch({ 'theme.active': 'light', 'list.page_size': 25 });
 */
export function setUIBatch(updates: Record<string, any>) {
  const ui = _loadCache();
  for (const [path, value] of Object.entries(updates)) {
    _deepSet(ui, path, value);
  }
  _saveCache(ui);
  _saveToServer(updates);
}

/**
 * Get a top-level section with defaults filled in.
 *
 *   getUISection('theme') → { active: 'dark', dark: {...}, light: {...} }
 */
export function getUISection<T = Record<string, any>>(section: string): T {
  const cached = _loadCache();
  const defaultSection = DEFAULTS[section] || {};
  const userSection = cached[section] || {};
  const result = JSON.parse(JSON.stringify(defaultSection));
  _deepMerge(result, userSection);
  return result as T;
}

/** Get the full config.ui with defaults filled in. */
export function getFullUI(): Record<string, any> {
  const cached = _loadCache();
  const result = JSON.parse(JSON.stringify(DEFAULTS));
  _deepMerge(result, cached);
  return result;
}

/** Get the active theme colors and font. */
export function getActiveTheme(): { colors: { text: string; surface: string; accent: string }; font: { size: number } } {
  const active = getUI<string>('theme.active', 'dark');
  return getUISection(`theme.${active}`) || getUISection('theme.dark');
}

// ── Server sync (debounced) ──

let _saveTimer: ReturnType<typeof setTimeout> | null = null;
let _pendingSave: Record<string, any> = {};

function _saveToServer(updates: Record<string, any>) {
  Object.assign(_pendingSave, updates);
  if (_saveTimer) clearTimeout(_saveTimer);
  _saveTimer = setTimeout(async () => {
    // Convert dot-path updates into nested object for server
    const nested: Record<string, any> = {};
    for (const [path, value] of Object.entries(_pendingSave)) {
      _deepSet(nested, path, value);
    }
    _pendingSave = {};
    try {
      const { manageAction } = await import('@/api/wcapi');
      await manageAction('save_ui_config', { config_ui: nested });
    } catch (e) {
      console.warn('[config.ui] Server save failed:', e);
    }
  }, 1000);
}

/**
 * Load config.ui from server on login. Server wins over localStorage.
 * Called once after authentication succeeds.
 */
export async function loadUIFromServer() {
  try {
    const { manageAction } = await import('@/api/wcapi');
    const result = await manageAction('get_ui_config', {}) as any;
    if (result && typeof result === 'object') {
      const localUI = _loadCache();
      // Server wins — merge server over local
      const merged = JSON.parse(JSON.stringify(localUI));
      _deepMerge(merged, result);
      _saveCache(merged);
    }
  } catch {
    // Server not available — localStorage is fine
  }
}

/**
 * Migrate from old wcuiPrefs localStorage format to config.ui.
 * Call once on app startup. Safe to call multiple times.
 */
export function migrateFromWcuiPrefs() {
  const OLD_KEY = 'wc3_wcui_prefs';
  const raw = localStorage.getItem(OLD_KEY);
  if (!raw) return;

  try {
    const old = JSON.parse(raw);
    const ui = _loadCache();
    let migrated = false;

    // Theme
    if (old.theme && !_deepGet(ui, 'theme.active')) {
      _deepSet(ui, 'theme.active', old.theme);
      migrated = true;
    }

    // Font size
    if (old.font_size && !_deepGet(ui, `theme.${old.theme || 'dark'}.font.size`)) {
      _deepSet(ui, `theme.${old.theme || 'dark'}.font.size`, old.font_size);
      migrated = true;
    }

    // Detail view
    if ((old.detail_view_pref || old.view_mode) && !_deepGet(ui, 'detail.default_view')) {
      _deepSet(ui, 'detail.default_view', old.detail_view_pref || old.view_mode);
      migrated = true;
    }

    // Format fields
    const formatKeys = ['button_style', 'phone_display', 'phone_separator', 'date_format', 'currency_locale', 'default_country'];
    for (const key of formatKeys) {
      if (old[key] && !_deepGet(ui, `format.${key}`)) {
        _deepSet(ui, `format.${key}`, old[key]);
        migrated = true;
      }
    }

    if (migrated) {
      _saveCache(ui);
    }

    // Also migrate standalone localStorage keys
    const legacyTheme = localStorage.getItem('theme') || localStorage.getItem('db-theme');
    if (legacyTheme && !_deepGet(ui, 'theme.active')) {
      _deepSet(ui, 'theme.active', legacyTheme);
      _saveCache(ui);
    }

    const legacyView = localStorage.getItem('wc3_detail_view_pref');
    if (legacyView && !_deepGet(ui, 'detail.default_view')) {
      _deepSet(ui, 'detail.default_view', legacyView);
      _saveCache(ui);
    }
  } catch {
    // Bad JSON — ignore
  }
}
