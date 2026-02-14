/**
 * getModelDetailPath — Maps a model name + record ID to its detail route.
 *
 * Used by panel row buttons to open records in floating windows
 * via WindowManager.ensureWindow(path, title).
 *
 * Route patterns sourced from src/routes/Routes.ts (PageRoutes).
 */

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
  item: "/products/item/dashboard",
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
 * @example getModelDetailPath("item", 100)  → "/products/item/dashboard/100"
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
