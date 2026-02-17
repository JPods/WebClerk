/**
 * Model Name Resolver
 *
 * Centralizes all model name translation for the wcapi endpoints.
 * Converts RESTful-style paths and various naming conventions to
 * the canonical wcapi model_name format.
 *
 * Security: All data access flows through wcapi endpoints, never directly to REST endpoints.
 * This provides a single point of control for authentication, authorization, and auditing.
 *
 * Usage:
 *   resolveModelName('order')           -> 'order'
 *   resolveModelName('order')            -> 'order'
 *   resolveModelName('order')            -> 'order'
 *   resolveModelName('purchase')        -> 'purchase'
 *   resolveModelName('invoice')         -> 'invoice'
 */

// Canonical model name mappings
// Keys are normalized (lowercase, no separators), values are the wcapi model_name
const MODEL_NAME_MAP: Record<string, string> = {
  // Transactions - canonical names match Django model._meta.model_name
  order: 'order',
  invoice: 'invoice',
  purchase: 'purchase',
  po: 'purchase',
  proposal: 'proposal',
  quote: 'proposal',
  workorder: 'workorder',  // Django model_name is 'workorder' (no underscore)
  work: 'workorder',
  wo: 'workorder',
  requisition: 'requisition',
  req: 'requisition',
  project: 'project',
  receipt: 'receipt',
  purchasereceipt: 'receipt',
  
  // Transaction Lines
  orderline: 'order_line',
  invoiceline: 'invoice_line',
  purchaseline: 'purchase_line',
  poline: 'purchase_line',
  proposalline: 'proposal_line',
  quoteline: 'proposal_line',
  workorderline: 'workorderline',  // Django model_name is 'workorderline' (no underscore)
  woline: 'workorderline',
  requisitionline: 'requisition_line',
  reqline: 'requisition_line',
  
  // Organizations
  customer: "customer",
  vendor: "vendor",
  manufacturer: "manufacturer",
  rep: "rep",
  employee: "employee",
  organization: "org",
  org: "org",

  // Products
  item: "item",
  product: "item",
  service: "service",
  category: "category",
  warehouse: "warehouse",
  serial: "serial",
  variant: "variant",
  specification: "specification",
  spec: "specification",
  catalog: "catalog",
  billofmaterial: "bill_of_material",
  bom: "bill_of_material",
  flow: "flow",
  usage: "usage",
  matrics: "matrics",
  metrics: "metrics",
  orgitem: "org_item",
  itemxref: "item_xref",

  // Core
  contact: "contact",
  address: "address",
  setting: "setting",
  report: "report",
  action: "action",
  template: "template",
  notification: "notification",
  apilog: "api_log",

  // Communications
  email: "email",
  phone: "phone",
  domain: "domain",

  // Accounts
  audit: "audit",
  currency: "currency",
  exchangerate: "exchange_rate",
  exchangetransaction: "exchange_transaction",
  glaccount: "gl_account",
  gljournal: "gl_journal",
  ledger: "ledger",
  taxjurisdiction: "tax_jurisdiction",
  term: "term",

  // Support
  campaign: "campaign",
  task: "task",
  event: "event",

  // Docs
  document: "document",
  tag: "tag",
  questionanswer: "question_answer",
  qa: "question_answer",
  linkageentry: "linkage_entry",
  linkage: "linkage_entry",

  // Sync
  bundle: "bundle",
  connection: "connection",
};

// RESTful path patterns to model name
// Handles paths like /api/transactions/order/22
const PATH_PATTERN_MAP: Record<string, string> = {
  // Transactions
  'transactions/order': 'order',
  'transactions/invoice': 'invoice',
  'transactions/purchase-order': 'purchase',
  'transactions/purchase': 'purchase',
  'transactions/proposal': 'proposal',
  'transactions/quote': 'proposal',
  'transactions/work-order': 'workorder',
  'transactions/workorder': 'workorder',
  'transactions/requisition': 'requisition',
  'transactions/project': 'project',
  'transactions/receipt': 'receipt',
  
  // Orgs
  "orgs/customer": "customer",
  "orgs/vendor": "vendor",
  "orgs/manufacturer": "manufacturer",
  "orgs/rep": "rep",
  "orgs/employee": "employee",
  "orgs/organization": "organization",
  "orgs/contact": "contact",

  // Products
  "products/item": "item",
  "products/service": "service",
  "products/category": "category",
  "products/warehouse": "warehouse",
  "products/serial": "serial",
  "products/variant": "variant",
  "products/specification": "specification",
  "products/catalog": "catalog",
  "products/bill-of-material": "bill_of_material",
  "products/bom": "bill_of_material",
  "products/flow": "flow",
  "products/usage": "usage",
  "products/matrics": "matrics",
  "products/metrics": "metrics",
  "products/org-item": "org_item",
  "products/item-xref": "item_xref",

  // Core
  "core/contact": "contact",
  "core/address": "address",
  "core/setting": "setting",
  "core/action": "action",
  "core/template": "template",
  "core/notification": "notification",
  "core/report": "report",
  "core/api-log": "api_log",

  // Communications
  "communications/email": "email",
  "communications/phone": "phone",
  "communications/domain": "domain",
  "communications/address": "address",

  // Accounts
  "accounts/audit": "audit",
  "accounts/currency": "currency",
  "accounts/exchange-rate": "exchange_rate",
  "accounts/exchange-transaction": "exchange_transaction",
  "accounts/gl-account": "gl_account",
  "accounts/gl-journal": "gl_journal",
  "accounts/ledger": "ledger",
  "accounts/term": "term",
  "accounts/tax-jurisdiction": "tax_jurisdiction",

  // Docs
  "docs/document": "document",
  "docs/tag": "tag",
  "docs/question-answer": "question_answer",
  "docs/qa": "question_answer",
  "docs/linkage": "linkage_entry",
  "docs/linkage-entry": "linkage_entry",

  // Support
  "support/campaign": "campaign",
  "support/task": "task",
  "support/event": "event",

  // Sync
  "sync/bundle": "bundle",
  "sync/connection": "connection",
};

/**
 * Normalize a string by removing separators and converting to lowercase
 */
function normalize(input: string): string {
  return input
    .replace(/[-_/]/g, "") // Remove hyphens, underscores, slashes
    .toLowerCase();
}

/**
 * Resolve a model name from various formats to the canonical wcapi model_name.
 *
 * @param input - Model name in any format (kebab-case, snake_case, camelCase, etc.)
 * @returns Canonical wcapi model_name
 * @throws Error if model name cannot be resolved
 */
export function resolveModelName(input: string): string {
  if (!input) {
    throw new Error("Model name is required");
  }

  // First, try direct lookup after normalization
  const normalized = normalize(input);
  if (MODEL_NAME_MAP[normalized]) {
    return MODEL_NAME_MAP[normalized];
  }

  // If input looks like a path, try path pattern matching
  const lowerInput = input.toLowerCase();
  for (const [pattern, modelName] of Object.entries(PATH_PATTERN_MAP)) {
    if (lowerInput.includes(pattern)) {
      return modelName;
    }
  }

  // Fallback: assume the normalized input IS the model name
  // This handles cases where the exact model name is passed
  console.warn(
    `[resolveModelName] Unknown model "${input}", using normalized: "${normalized}"`,
  );
  return normalized;
}

/**
 * Extract model name and ID from a RESTful path.
 *
 * Handles patterns like:
 *   /api/transactions/order/22
 *   /transactions/order/detail/22
 *   /api/order/22
 * 
 * @param path - URL path
 * @returns Object with modelName and optional id
 */
export function parseRestfulPath(path: string): {
  modelName: string;
  id?: number;
} {
  // Remove leading slash and split
  const segments = path.replace(/^\/+/, "").split("/").filter(Boolean);

  // Try to find an ID (numeric segment)
  let id: number | undefined;
  const numericIdx = segments.findIndex((s) => /^\d+$/.test(s));
  if (numericIdx !== -1) {
    id = parseInt(segments[numericIdx], 10);
    segments.splice(numericIdx, 1);
  }

  // Remove common prefixes
  const filtered = segments.filter(
    (s) =>
      !["api", "wcapi", "detail", "list", "edit", "new"].includes(
        s.toLowerCase(),
      ),
  );

  // Join remaining segments and resolve
  const pathPart = filtered.join("/");
  const modelName = resolveModelName(pathPart);

  return { modelName, id };
}

/**
 * Convert a URL path segment to wcapi model_name format.
 * Used for URL-based routing to API calls.
 * 
 * @param urlSegment - URL segment like "order" or "purchase"
 * @returns wcapi model_name like "order" or "purchase"
 */
export function urlToModelName(urlSegment: string): string {
  return resolveModelName(urlSegment);
}

/**
 * Convert a wcapi model_name to URL-friendly format.
 * Used for building navigation URLs.
 * 
 * @param modelName - wcapi model_name like "order"
 * @returns URL segment like "sales-order"
 */
export function modelNameToUrl(modelName: string): string {
  // Special cases with hyphens in URL
  const URL_MAP: Record<string, string> = {
    order: 'order',
    purchase: 'purchase',
    workorder: 'workorder',
    order_line: 'order-line',
    purchase_line: 'purchase-line',
    workorderline: 'workorderline',
    invoice_line: 'invoice-line',
    proposal_line: 'proposal-line',
    exchange_rate: 'exchange-rate',
    gl_account: 'gl-account',
    gl_journal: 'gl-journal',
    tax_jurisdiction: 'tax-jurisdiction',
  };

  return URL_MAP[modelName] || modelName.replace(/_/g, "-");
}

/**
 * Get the transaction type for routing purposes from a model name.
 *
 * @param modelName - wcapi model_name
 * @returns Transaction type for routing (e.g., "order", "invoice")
 */
export function getTransactionType(modelName: string): string {
  const TYPE_MAP: Record<string, string> = {
    order: 'order',
    invoice: 'invoice',
    purchase: 'purchase',
    proposal: 'proposal',
    workorder: 'workorder',
    requisition: 'requisition',
  };

  return TYPE_MAP[modelName] || modelName;
}

// Export the maps for testing/debugging
export { MODEL_NAME_MAP, PATH_PATTERN_MAP };
