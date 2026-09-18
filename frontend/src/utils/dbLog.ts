/**
 * dbLog — toggleable console logger for DataBrowser debugging.
 *
 * Toggle: localStorage.setItem('db-debug', '1') to enable
 *         localStorage.removeItem('db-debug') to disable
 *         Or call dbLog.enable() / dbLog.disable() from browser console
 *
 * Usage:
 *   import { dbLog } from '@/utils/dbLog';
 *   dbLog('fetchRecords', { model, page, fields });
 *   dbLog.warn('stale data', { expected, actual });
 */

const KEY = 'db-debug';

function isEnabled(): boolean {
  try { return localStorage.getItem(KEY) === '1'; } catch { return false; }
}

function log(label: string, ...args: unknown[]) {
  if (!isEnabled()) return;
  console.log(`%c[DB] ${label}`, 'color: #9cdcfe; font-weight: bold', ...args);
}

function warn(label: string, ...args: unknown[]) {
  if (!isEnabled()) return;
  console.warn(`%c[DB] ${label}`, 'color: #e8c870; font-weight: bold', ...args);
}

function error(label: string, ...args: unknown[]) {
  // Errors always log regardless of toggle
  console.error(`%c[DB] ${label}`, 'color: #e05252; font-weight: bold', ...args);
}

function table(label: string, data: unknown) {
  if (!isEnabled()) return;
  console.log(`%c[DB] ${label}`, 'color: #9cdcfe; font-weight: bold');
  console.table(data);
}

function enable() { localStorage.setItem(KEY, '1'); console.log('[DB] Debug logging ENABLED'); }
function disable() { localStorage.removeItem(KEY); console.log('[DB] Debug logging DISABLED'); }

export const dbLog = Object.assign(log, { warn, error, table, enable, disable });
