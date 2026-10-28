/**
 * Playwright — the panel read sweep (e2e/panel-reads.e2e.ts). Runs against the dev servers
 * already up (vite :5173, Django :8000); it starts nothing.
 *   npx playwright test
 */
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: '*.e2e.ts',
  timeout: 30 * 60_000,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: process.env.WC_SWEEP_URL || 'http://localhost:5173',
    viewport: { width: 1600, height: 1000 },
  },
});
