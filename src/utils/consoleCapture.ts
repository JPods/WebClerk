/**
 * ConsoleCapture — intercepts console output and stores in a ring buffer.
 *
 * Alice can read captured logs via the Alice Dashboard or "Send to Alice" button.
 * Captures console.log, console.warn, console.error.
 * Stores last 200 entries with timestamps.
 *
 * Usage:
 *   import { consoleCapture } from '@/utils/consoleCapture';
 *   consoleCapture.start();  // begin capturing (call once at app init)
 *   consoleCapture.stop();   // stop capturing
 *   consoleCapture.getEntries();  // get captured entries
 *   consoleCapture.sendToAlice(); // POST to wcapi as alice_log
 *   consoleCapture.clear();  // clear buffer
 */

const MAX_ENTRIES = 200;

export interface ConsoleEntry {
  dt: number;       // epoch ms
  level: 'log' | 'warn' | 'error';
  args: string[];   // stringified arguments
}

let entries: ConsoleEntry[] = [];
let capturing = false;
let origLog: typeof console.log;
let origWarn: typeof console.warn;
let origError: typeof console.error;

function stringify(args: any[]): string[] {
  return args.map((a) => {
    if (typeof a === 'string') return a;
    try { return JSON.stringify(a); }
    catch { return String(a); }
  });
}

function capture(level: 'log' | 'warn' | 'error', args: any[]) {
  entries.push({
    dt: Date.now(),
    level,
    args: stringify(args),
  });
  if (entries.length > MAX_ENTRIES) entries = entries.slice(-MAX_ENTRIES);
}

function start() {
  if (capturing) return;
  origLog = console.log;
  origWarn = console.warn;
  origError = console.error;

  console.log = (...args: any[]) => { capture('log', args); origLog.apply(console, args); };
  console.warn = (...args: any[]) => { capture('warn', args); origWarn.apply(console, args); };
  console.error = (...args: any[]) => { capture('error', args); origError.apply(console, args); };
  capturing = true;
}

function stop() {
  if (!capturing) return;
  console.log = origLog;
  console.warn = origWarn;
  console.error = origError;
  capturing = false;
}

function getEntries(): ConsoleEntry[] {
  return [...entries];
}

function getErrors(): ConsoleEntry[] {
  return entries.filter((e) => e.level === 'error' || e.level === 'warn');
}

function clear() {
  entries = [];
}

function getSummary(): { total: number; errors: number; warns: number; last5: ConsoleEntry[] } {
  return {
    total: entries.length,
    errors: entries.filter((e) => e.level === 'error').length,
    warns: entries.filter((e) => e.level === 'warn').length,
    last5: entries.slice(-5),
  };
}

async function sendToAlice(context?: string) {
  const errors = getErrors();
  if (!errors.length && !context) return;

  const body = [
    context ? `Context: ${context}` : '',
    `Console: ${entries.length} total, ${errors.length} errors/warnings`,
    '',
    ...errors.slice(-20).map((e) =>
      `[${new Date(e.dt).toLocaleTimeString()}] ${e.level.toUpperCase()}: ${e.args.join(' ').slice(0, 200)}`
    ),
  ].join('\n').slice(0, 250); // wcapi name field limit

  try {
    const { default: apiClient } = await import('@/api/axios');
    await apiClient.post('/wcapi/save/', {
      model_name: 'setting',
      name: body,
      purpose: 'alice_log',
      data: {
        entries: errors.slice(-20),
        context,
        dt_captured: Date.now(),
        user_agent: navigator.userAgent,
      },
    });
  } catch (e) {
    origError?.call(console, 'Failed to send console to Alice:', e);
  }
}

export const consoleCapture = { start, stop, getEntries, getErrors, clear, getSummary, sendToAlice };
