/**
 * getModelDetailPath — Maps a model name + record ID to its detail route.
 *
 * Used by panel row buttons to open records in floating windows
 * via WindowManager.ensureWindow(path, title, options).
 *
 * Route patterns sourced from src/routes/Routes.ts (PageRoutes).
 * Window size presets sourced from WINDOW_PRESETS below.
 */

import type { EnsureWindowOptions } from "@/context/WindowManagerContext";

// ---------------------------------------------------------------------------
// Window size presets
// ---------------------------------------------------------------------------

/**
 * Centralized window sizing for display_related.
 *
 * Use these when calling ensureWindow() so every "open related" interaction
 * gets a consistent, appropriate window size.
 *
 * DETAIL  — single record edit/view (item, contact, order, etc.)
 * LIST    — collection / table view (wider to accommodate columns)
 * COMPACT — small reference popup (inventory check, quick lookup)
 * FULL    — maximized (dashboard-style views)
 */
export const WINDOW_PRESETS = {
  /** Single record detail — 980 × 640, floating */
  DETAIL:  { maximized: false, width: 980, height: 640 } as EnsureWindowOptions,
  /** Collection / list view — 1200 × 720, floating */
  LIST:    { maximized: false, width: 1200, height: 720 } as EnsureWindowOptions,
  /** Compact reference panel — 720 × 500, floating */
  COMPACT: { maximized: false, width: 720, height: 500 } as EnsureWindowOptions,
  /** Full-screen / dashboard — maximized */
  FULL:    { maximized: true } as EnsureWindowOptions,
} as const;

/**
 * Per-model default window preset.
 * Falls back to DETAIL if not specified.
 */
const MODEL_WINDOW_PRESET: Partial<Record<string, EnsureWindowOptions>> = {
  // Transactions get detail preset (they have lines, so plenty of height)
  order:    WINDOW_PRESETS.DETAIL,
  invoice:  WINDOW_PRESETS.DETAIL,
  proposal: WINDOW_PRESETS.DETAIL,
  purchase: WINDOW_PRESETS.DETAIL,
  receipt:  WINDOW_PRESETS.DETAIL,
  workorder: WINDOW_PRESETS.DETAIL,

  // Products
  item:   WINDOW_PRESETS.DETAIL,
  serial: WINDOW_PRESETS.COMPACT,

  // Orgs
  customer: WINDOW_PRESETS.DETAIL,
  vendor:   WINDOW_PRESETS.DETAIL,

  // Core — compact for simple entities
  contact:  WINDOW_PRESETS.DETAIL,
  action:   WINDOW_PRESETS.COMPACT,
  email:    WINDOW_PRESETS.COMPACT,
  phone:    WINDOW_PRESETS.COMPACT,
  address:  WINDOW_PRESETS.COMPACT,
  domain:   WINDOW_PRESETS.COMPACT,
};

/**
 * Returns the default EnsureWindowOptions for a model.
 * Use this when you don't need to override sizing at the callsite.
 *
 * @example getModelWindowPreset("item")   → { maximized: false, width: 980, height: 640 }
 * @example getModelWindowPreset("phone")  → { maximized: false, width: 720, height: 500 }
 */
export const getModelWindowPreset = (model: string): EnsureWindowOptions =>
  MODEL_WINDOW_PRESET[model] ?? WINDOW_PRESETS.DETAIL;

// ---------------------------------------------------------------------------
// Route path mapping
// ---------------------------------------------------------------------------

const MODEL_DETAIL_BASES: Record<string, string> = {
  // Orgs
  customer: "/org/customer/detail",
  vendor: "/org/vendor/detail",
  employee: "/org/employee/detail",
  manufacturer: "/org/manufacturer/detail",
  organization: "/org/organization/detail",
  rep: "/org/rep/detail",

  // Transactions
  order: "/transactions/order/detail",
  invoice: "/transactions/invoice/detail",
  proposal: "/transactions/proposal/detail",
  purchase: "/transactions/purchase-order/detail",
  receipt: "/transactions/receipt/detail",
  workorder: "/transactions/work-order/detail",
  adjustment: "/transactions/adjustment/detail",

  // Products
  item: "/products/item/detail",
  serial: "/products/serial/detail",

  // Accounts
  audit: "/accounts/audit/detail",
  currency: "/accounts/currency/detail",
  ledger: "/accounts/ledger/detail",
  payment: "/accounts/payment/detail",

  // Communications
  domain: "/communications/domain/detail",
  email: "/communications/email/detail",
  address: "/communications/address/detail",
  phone: "/communications/phone/detail",

  // Core
  contact: "/core/contact/detail",
  action: "/core/actions/detail",
  setting: "/core/setting/detail",
  report: "/core/report/detail",
  template: "/core/template/detail",

  // Docs
  document: "/docs/document/detail",
};

/**
 * Returns the detail route path for a given model and record ID.
 *
 * @example getModelDetailPath("order", 42)  → "/transactions/order/detail/42"
 * @example getModelDetailPath("item", 100)  → "/products/item/detail/100"
 */
export const getModelDetailPath = (model: string, id: number | string): string => {
  const base = MODEL_DETAIL_BASES[model];
  if (base) return `${base}/${id}`;
  // Fallback: build a conventional path
  return `/model/${model}/detail/${id}`;
};

/**
 * Build a human-readable window title from model + record.
 *
 * @example getModelWindowTitle("order", 42, "ORD-042") → "Order ORD-042"
 */
export const getModelWindowTitle = (
  model: string,
  id: number | string,
  ida?: string | null,
  name?: string | null,
): string => {
  const label = model.charAt(0).toUpperCase() + model.slice(1);
  const display = ida ?? name ?? `#${id}`;
  return `${label} ${display}`;
};

/**
 * All-in-one helper: returns { path, title, options } ready for ensureWindow().
 *
 * @example
 * const win = getModelWindowArgs("item", 42, "ABC-123");
 * windowManager.ensureWindow(win.path, win.title, win.options);
 */
export const getModelWindowArgs = (
  model: string,
  id: number | string,
  ida?: string | null,
  name?: string | null,
  optionOverrides?: Partial<EnsureWindowOptions>,
): { path: string; title: string; options: EnsureWindowOptions } => ({
  path: getModelDetailPath(model, id),
  title: getModelWindowTitle(model, id, ida, name),
  options: { ...getModelWindowPreset(model), ...optionOverrides },
});
