/**
 * supportContext.ts — Collect diagnostic context for support Q&A.
 *
 * When a user asks a question or Alice escalates, this gathers:
 *   - Current screen (URL path)
 *   - Model/field context (from URL params or data-wc attrs)
 *   - Recent navigation (last 5 pages from sessionStorage)
 *   - Recent manage actions (last 5 from consoleCapture)
 *   - Recent errors (last 3 from consoleCapture)
 *   - Browser memory usage
 *   - Viewport size
 *   - User agent
 *   - Session uptime
 *   - Alice hints currently shown
 *
 * No screenshots. No user data. Just operational context that helps
 * the team understand WHERE the user was and WHAT was happening.
 */

const APP_BOOT_TIME = Date.now();

interface SupportContext {
  screen: string;
  model: string;
  field: string;
  recent_nav: string[];
  recent_actions: string[];
  recent_errors: string[];
  recent_console: string[];
  memory_mb: number | null;
  viewport: { width: number; height: number };
  user_agent: string;
  user_role: string;
  alice_hints: string[];
  uptime_min: number;
}

/**
 * Track page navigation in sessionStorage (ring buffer, max 20).
 * Call this on every route change.
 */
export function trackNavigation(path: string): void {
  try {
    const key = 'support_nav_history';
    const raw = sessionStorage.getItem(key);
    const history: string[] = raw ? JSON.parse(raw) : [];
    history.push(`${new Date().toISOString().slice(11, 19)} ${path}`);
    if (history.length > 20) history.splice(0, history.length - 20);
    sessionStorage.setItem(key, JSON.stringify(history));
  } catch { /* sessionStorage unavailable */ }
}

/**
 * Track manage action calls (ring buffer, max 20).
 * Call this after every POST /wcapi/manage/.
 */
export function trackAction(actionName: string): void {
  try {
    const key = 'support_action_history';
    const raw = sessionStorage.getItem(key);
    const history: string[] = raw ? JSON.parse(raw) : [];
    history.push(`${new Date().toISOString().slice(11, 19)} ${actionName}`);
    if (history.length > 20) history.splice(0, history.length - 20);
    sessionStorage.setItem(key, JSON.stringify(history));
  } catch { /* sessionStorage unavailable */ }
}

/**
 * Collect full diagnostic context for a support question.
 */
export function collectSupportContext(): SupportContext {
  // Screen and model from URL
  const path = window.location.pathname;
  let model = '';
  let field = '';

  // Parse /db/<model> or /admin-wb?model=<model>
  const dbMatch = path.match(/\/db\/([a-z_]+)/);
  if (dbMatch) model = dbMatch[1];
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('model')) model = urlParams.get('model') || '';
  if (urlParams.get('field')) field = urlParams.get('field') || '';

  // Recent navigation
  let recentNav: string[] = [];
  try {
    const raw = sessionStorage.getItem('support_nav_history');
    if (raw) recentNav = JSON.parse(raw);
  } catch { /* ignore */ }

  // Recent actions
  let recentActions: string[] = [];
  try {
    const raw = sessionStorage.getItem('support_action_history');
    if (raw) recentActions = JSON.parse(raw);
  } catch { /* ignore */ }

  // Recent errors + recent console output from consoleCapture
  let recentErrors: string[] = [];
  let recentConsole: string[] = [];
  try {
    // consoleCapture exposes getErrors() and getReport() — see consoleCapture.ts
    const capture = (window as any).__consoleCapture;
    if (capture?.getErrors) {
      const errors = capture.getErrors();
      recentErrors = errors.slice(-3).map((e: any) =>
        typeof e === 'string' ? e : (e.message || JSON.stringify(e)).slice(0, 200)
      );
    }
    if (capture?.getSummary) {
      const summary = capture.getSummary();
      // Last 10 console entries (log+warn+error) — enough to see what was happening
      recentConsole = (summary.recent || []).slice(-10).map((e: any) =>
        `[${e.level || 'log'}] ${(e.message || String(e)).slice(0, 150)}`
      );
    }
  } catch { /* ignore */ }

  // Memory (Chrome only)
  let memoryMb: number | null = null;
  try {
    const perf = (performance as any).memory;
    if (perf?.usedJSHeapSize) {
      memoryMb = Math.round(perf.usedJSHeapSize / 1024 / 1024);
    }
  } catch { /* ignore */ }

  // Alice hints currently visible
  let aliceHints: string[] = [];
  try {
    const hintElements = document.querySelectorAll('[data-wc="alice-hint-bar"] [data-hint-message]');
    hintElements.forEach(el => {
      const msg = el.getAttribute('data-hint-message') || el.textContent?.slice(0, 100);
      if (msg) aliceHints.push(msg);
    });
  } catch { /* ignore */ }

  // User role from contact prefs (if loaded)
  let userRole = '';
  try {
    const raw = sessionStorage.getItem('user_profile');
    if (raw) {
      const profile = JSON.parse(raw);
      userRole = profile.role || profile.user_type || '';
    }
  } catch { /* ignore */ }

  return {
    screen: path,
    model,
    field,
    recent_nav: recentNav.slice(-5),
    recent_actions: recentActions.slice(-5),
    recent_errors: recentErrors,
    recent_console: recentConsole,
    memory_mb: memoryMb,
    viewport: { width: window.innerWidth, height: window.innerHeight },
    user_agent: navigator.userAgent,
    user_role: userRole,
    alice_hints: aliceHints.slice(0, 5),
    uptime_min: Math.round((Date.now() - APP_BOOT_TIME) / 60000),
  };
}
