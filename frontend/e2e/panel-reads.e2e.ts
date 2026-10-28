/**
 * Panel read sweep — every record page, every tab, every panel, read against the real backend
 * (Bill, 2026-10-28: assure uniform behavior and correct data between frontend and backend).
 *
 * Why a browser: each panel builds its own read parameters; only the running panel knows them.
 * The backend refuses what it does not understand (unknown filters, a list read with ?id=), and
 * the panel frame shows a failed read as an error. So a panel that is opened and reads cleanly
 * agrees with the backend; one that does not shows up here. Found by the first panel loop
 * (2026-10-27): a list read with ?id= ignored the filter and returned the wrong item, inventory
 * layers answered 500, ActionsPanel sent a filter the backend did not have.
 *
 * Read-only: every non-GET request is blocked and reported — opening a page must not write.
 * Signs in as claude@jpods.com (a refresh cookie minted by the backend), never as Bill.
 *
 * Fails on: a /wcapi/ read answered >= 400 (401 excepted, the client refreshes), a panel
 * showing its error line, an uncaught page error, a write attempted on opening a page.
 * Writes e2e/results/panel-reads.json.
 */
import { test, expect, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { TRANSACTION_MODELS, DETAIL_MODELS } from '../src/routes/recordRoutes';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BACKEND = path.resolve(HERE, '../../backend');
const SWEEP_USER = process.env.WC_SWEEP_USER || 'claude@jpods.com';

/** Records with linked data worth reading (the AF-2011 flight-sim chain, a BOM item, a customer
 *  with contacts). Every model's newest record is swept as well. */
const PINNED: Record<string, number[]> = {
  order: [171], invoice: [160], purchase: [53], receipt: [19], item: [687, 625], customer: [5604],
};

/** Tabs that act rather than read: "+ link" saves a link on click. */
const SKIP_TABS = new Set(['_link', 'link']);

function mintRefreshToken(): string {
  const py = [
    'from django.contrib.auth import get_user_model',
    'from apps.core.token_views import RoleTokenObtainPairSerializer',
    `u = get_user_model().objects.get(email=${JSON.stringify(SWEEP_USER)})`,
    'print(RoleTokenObtainPairSerializer.get_token(u))',
  ].join('\n');
  const out = execFileSync(path.join(BACKEND, 'venv/bin/python'), ['manage.py', 'shell', '-c', py],
    { cwd: BACKEND, encoding: 'utf8' });
  return out.trim().split('\n').pop()!.trim();
}

interface Finding { page: string; kind: 'read' | 'panel' | 'page_error' | 'write' | 'repeat'; detail: string }

/** Reads of one address while one page is swept; past this the page is reading in a loop. */
const REPEAT_LIMIT = 10;

/** The backend throttles a user at 1000 requests a minute (settings DEFAULT_THROTTLE_RATES); the
 *  sweep reads up to ~130 a record and checks only between records, so it paces well under that. */
const PACE_PER_MINUTE = 500;
const requestTimes: number[] = [];

const SIGN_INS_PER_MINUTE = 8;
const signInTimes: number[] = [];

async function paceSignIn() {
  for (;;) {
    const cutoff = Date.now() - 60_000;
    while (signInTimes.length && signInTimes[0] < cutoff) signInTimes.shift();
    if (signInTimes.length < SIGN_INS_PER_MINUTE) { signInTimes.push(Date.now()); return; }
    await new Promise((r) => setTimeout(r, signInTimes[0] - cutoff + 100));
  }
}

async function pace() {
  for (;;) {
    const cutoff = Date.now() - 60_000;
    while (requestTimes.length && requestTimes[0] < cutoff) requestTimes.shift();
    if (requestTimes.length < PACE_PER_MINUTE) return;
    await new Promise((r) => setTimeout(r, requestTimes[0] - cutoff + 100));
  }
}

/** Network quiet and no panel still loading; then a beat for the last status to render. */
async function settle(page: Page) {
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {});
  await page.waitForFunction(() => ![...document.querySelectorAll('[data-wc-panel]')]
    .some((p) => /Loading(…|\.\.\.)/.test(p.textContent || '')), null, { timeout: 10_000 }).catch(() => {});
  await page.waitForTimeout(300);
}

/** The newest record of a model, through the one read channel. */
/** The newest record of a model, through the one read channel; a refused read is the reason. */
async function newestId(page: Page, model: string): Promise<number | string | null> {
  return page.evaluate(async (m) => {
    const { getRecords } = await import('/src/api/wcapi.ts');
    try {
      const res: any = await Promise.race([getRecords(m, { ordering: '-id', limit: 1 }),
        new Promise((_, no) => setTimeout(() => no(new Error('no answer in 20 s')), 20_000))]);
      return res?.results?.[0]?.id ?? null;
    } catch (e: any) { return `${e?.response?.status || ''} ${e?.response?.data?.message || e?.message}`; }
  }, model);
}

async function sweepRecord(page: Page, model: string, id: number, findings: Finding[]): Promise<number> {
  const where = `/${model}/${id}`;
  const reads = new Map<string, number>();
  const onResponse = (res: any) => {
    const url = new URL(res.url());
    if (!url.pathname.startsWith('/wcapi/') || res.request().method() !== 'GET') return;
    const key = `${url.pathname}${url.search}`;
    reads.set(key, (reads.get(key) || 0) + 1);
    if (res.status() >= 400 && res.status() !== 401) {
      res.text().then((body: string) => {
        let msg = body.slice(0, 300);
        try { const j = JSON.parse(body); msg = j.message || j.error?.message || msg; } catch { /* not JSON */ }
        findings.push({ page: where, kind: 'read', detail: `${res.status()} ${url.pathname}${url.search} — ${msg}` });
      }).catch(() => findings.push({ page: where, kind: 'read', detail: `${res.status()} ${url.pathname}${url.search}` }));
    }
  };
  const onError = (err: Error) => findings.push({ page: where, kind: 'page_error', detail: err.message.slice(0, 300) });
  page.on('response', onResponse);
  page.on('pageerror', onError);
  try {
    // Each record is a fresh load, as a viewer opening it from a link; a load signs in again,
    // and sign-in is limited to 10 a minute (settings 'auth'), so loads are paced.
    await paceSignIn();
    await page.goto(where);
    await settle(page);

    // Every tab, in every tab bar; the DOM changes after each click, so re-query by position.
    for (let i = 0; i < 200; i++) {
      const tabs = page.locator('[data-wc-tab]:visible');
      if (i >= await tabs.count()) break;
      const tab = tabs.nth(i);
      if (SKIP_TABS.has((await tab.getAttribute('data-wc-tab')) || '')) continue;
      await tab.click({ timeout: 5_000 }).catch(() => {});
      await settle(page);
      await expandPanels(page);
    }
    await expandPanels(page);

    // Line cards: select the first line, then open each sub-panel.
    const firstLine = page.locator('[data-wc="line-cards"]:visible tr[data-rid] td').first();
    if (await firstLine.count()) {
      await firstLine.click({ timeout: 5_000 }).catch(() => {});
      for (const sub of ['inventory', 'spec', 'xref', 'margin']) {
        const btn = page.locator(`[data-wc-subpanel="${sub}"]:visible`).first();
        if (await btn.count()) { await btn.click({ timeout: 5_000 }).catch(() => {}); await settle(page); await collectPanelErrors(page, where, `line ${sub}`, findings); }
      }
    }
    await collectPanelErrors(page, where, '', findings);
  } finally {
    for (const [key, n] of reads) if (n > REPEAT_LIMIT) findings.push({ page: where, kind: 'repeat', detail: `${n}× GET ${key}` });
    page.off('response', onResponse);
    page.off('pageerror', onError);
  }
  return [...reads.values()].reduce((a, b) => a + b, 0);
}

async function expandPanels(page: Page) {
  for (let n = 0; n < 50; n++) {
    const collapsed = page.locator('[data-wc-collapsed]:visible [data-wc-panel-toggle]').first();
    if (!(await collapsed.count())) return;
    await collapsed.click({ timeout: 5_000 }).catch(() => {});
    await settle(page);
  }
}

async function collectPanelErrors(page: Page, where: string, context: string, findings: Finding[]) {
  const errors = await page.locator('[data-wc-panel]:has(> div > [data-wc-panel-error]), [data-wc-panel-error]').evaluateAll(
    // Only the window on screen: earlier records' windows stay mounted, hidden.
    (els) => els.filter((e) => e.hasAttribute('data-wc-panel-error') && (e as HTMLElement).offsetParent !== null).map((e) => {
      const panel = e.closest('[data-wc-panel]')?.getAttribute('data-wc-panel') || '?';
      return `${panel}: ${(e.textContent || '').replace('Try again', '').trim()}`;
    }));
  for (const detail of new Set(errors)) {
    const d = context ? `${context} — ${detail}` : detail;
    if (!findings.some((f) => f.page === where && f.detail === d)) findings.push({ page: where, kind: 'panel', detail: d });
  }
}

test('every panel reads cleanly against the backend', async ({ page, context, baseURL }) => {
  const findings: Finding[] = [];
  const swept: string[] = [];

  // Read-only: block and report every write. POSTs that only read pass: the record channel's
  // preview commands (channel_view.PREVIEW_COMMANDS — compute, never save) and _manage actions
  // named get_* / check_*.
  await page.route('**/wcapi/**', (route) => {
    const req = route.request();
    const pathname = new URL(req.url()).pathname;
    let action = '';
    try { action = JSON.parse(req.postData() || '{}').action || ''; } catch { /* not JSON */ }
    if (req.method() === 'GET'
      || /^\/wcapi\/(token_refresh|logout)\/$/.test(pathname)
      || /^\/wcapi\/[a-z_]+\/\d+\/(totals|journal_preview)\/$/.test(pathname)
      || (pathname === '/wcapi/_manage/' && /^(get|check)_/.test(action))) return route.continue();
    findings.push({ page: new URL(page.url()).pathname, kind: 'write', detail: `${req.method()} ${new URL(req.url()).pathname}${action ? ` ${action}` : ''} (blocked) ${(req.postData() || '').slice(0, 200)}` });
    return route.abort();
  });

  page.on('request', (r) => { if (r.url().includes('/wcapi/')) requestTimes.push(Date.now()); });
  await context.addCookies([{
    name: 'refresh_token', value: mintRefreshToken(), url: `${baseURL}/wcapi/`,
  }]);
  // Sign in once; every record after is in-app navigation. Fail fast if sign-in was refused
  // (the 'auth' limit is 10 a minute — back-to-back runs use it up) rather than hang on reads
  // queued behind a refresh that never comes.
  const signedIn = page.waitForResponse((r) => r.url().includes('/wcapi/token_refresh/'), { timeout: 30_000 });
  await paceSignIn();
  await page.goto('/');
  const refresh = await signedIn;
  expect(refresh.status(), `sign-in as ${SWEEP_USER}: ${(await refresh.text()).slice(0, 200)}`).toBe(200);
  await settle(page);

  const only = process.env.WC_SWEEP_MODELS?.split(',');
  const models = [...TRANSACTION_MODELS, ...DETAIL_MODELS].filter((m) => !only || only.includes(m));
  for (const model of models) {
    const ids = new Set(PINNED[model] || []);
    const newest = await newestId(page, model);
    if (typeof newest === 'string') findings.push({ page: `/${model}`, kind: 'read', detail: `newest record: ${newest}` });
    else if (newest != null) ids.add(newest);
    for (const id of ids) {
      await pace();
      const reads = await sweepRecord(page, model, id, findings);
      swept.push(`${model}/${id} (${reads} reads)`);
    }
  }

  const outDir = path.join(HERE, 'results');
  mkdirSync(outDir, { recursive: true });
  writeFileSync(path.join(outDir, 'panel-reads.json'), JSON.stringify({ swept, findings }, null, 2));
  const summary = findings.map((f) => `${f.kind.padEnd(10)} ${f.page.padEnd(18)} ${f.detail}`).join('\n');
  expect(findings, `${findings.length} findings across ${swept.length} records:\n${summary}`).toEqual([]);
});
